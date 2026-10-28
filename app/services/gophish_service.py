"""GoPhish integration service layer.

Design goals (from the project spec):
- Never expose the API key to the frontend; read it from env only.
- Handle API failures and timeouts gracefully.
- Avoid duplicate event records on repeated syncs.
- Fall back to a clearly-labelled DEMO mode when GoPhish is unavailable, so the
  app stays usable without ever claiming a real campaign was executed.

Only documented GoPhish endpoints are used:
    GET /api/campaigns/            -> list campaigns
    GET /api/campaigns/{id}        -> one campaign incl. "timeline" events
"""
import random
from datetime import datetime, timedelta

import requests
from flask import current_app

from app.extensions import db
from app.models import (Campaign, CampaignEvent, CampaignParticipant, Participant,
                        EVENT_SENT, EVENT_OPENED, EVENT_CLICKED,
                        EVENT_SUBMITTED, EVENT_REPORTED,
                        STATUS_ACTIVE, STATUS_COMPLETED)

# Map GoPhish timeline messages -> our event types.
GOPHISH_EVENT_MAP = {
    "Email Sent": EVENT_SENT,
    "Email Opened": EVENT_OPENED,
    "Clicked Link": EVENT_CLICKED,
    "Submitted Data": EVENT_SUBMITTED,
    "Email Reported": EVENT_REPORTED,
}

FUNNEL_EVENTS = [EVENT_OPENED, EVENT_CLICKED, EVENT_SUBMITTED, EVENT_REPORTED]


class GoPhishError(Exception):
    pass


def is_configured() -> bool:
    cfg = current_app.config
    return bool(cfg.get("GOPHISH_API_URL") and cfg.get("GOPHISH_API_KEY"))


def demo_mode_active() -> bool:
    """Demo mode is on if DEMO_MODE=true OR GoPhish is not configured."""
    return current_app.config.get("DEMO_MODE", True) or not is_configured()


def _request(path: str):
    cfg = current_app.config
    url = cfg["GOPHISH_API_URL"].rstrip("/") + path
    headers = {"Authorization": f"Bearer {cfg['GOPHISH_API_KEY']}"}
    return requests.get(url, headers=headers, timeout=8,
                        verify=cfg.get("GOPHISH_VERIFY_SSL", False))


def check_status() -> dict:
    """Return a status dict for the UI (never raises)."""
    if demo_mode_active():
        reason = "DEMO_MODE is on" if current_app.config.get("DEMO_MODE", True) \
            else "GoPhish is not configured"
        return {"mode": "demo", "reachable": False,
                "message": f"Demo mode — synthetic data ({reason})."}
    try:
        resp = _request("/api/campaigns/")
    except requests.RequestException as exc:
        return {"mode": "live", "reachable": False,
                "message": f"Could not connect to GoPhish: {exc}"}
    if resp.status_code == 200:
        return {"mode": "live", "reachable": True,
                "message": "GoPhish is reachable."}
    if resp.status_code in (401, 403):
        return {"mode": "live", "reachable": False,
                "message": "Invalid API key (401/403)."}
    return {"mode": "live", "reachable": False,
            "message": f"GoPhish responded: HTTP {resp.status_code}."}


def fetch_campaigns() -> list:
    """List GoPhish campaigns (live mode only): [{id, name, status}, ...]."""
    if demo_mode_active():
        raise GoPhishError("The GoPhish campaign list is not available in demo mode.")
    resp = _request("/api/campaigns/")
    if resp.status_code != 200:
        raise GoPhishError(f"HTTP {resp.status_code}")
    return resp.json()


def fetch_campaign(gophish_id: int) -> dict:
    """Fetch one GoPhish campaign (incl. results + timeline)."""
    if demo_mode_active():
        raise GoPhishError("GoPhish data is not available in demo mode.")
    resp = _request(f"/api/campaigns/{gophish_id}")
    if resp.status_code != 200:
        raise GoPhishError(f"GoPhish HTTP {resp.status_code}")
    return resp.json()


def import_campaign(gophish_id: int) -> str:
    """Import a GoPhish campaign into the local database.

    Creates/updates a local campaign linked by gophish_campaign_id, creates
    participants from the campaign's recipients, and maps timeline events.
    Idempotent: re-importing refreshes events without duplicating participants.
    """
    data = fetch_campaign(gophish_id)
    name = data.get("name") or f"GoPhish #{gophish_id}"

    camp = Campaign.query.filter_by(gophish_campaign_id=gophish_id).first()
    if camp is None:
        camp = Campaign(name=name, gophish_campaign_id=gophish_id, is_demo=False)
        db.session.add(camp)
    else:
        camp.name = name
    camp.status = (STATUS_COMPLETED if str(data.get("status", "")).lower() == "completed"
                   else STATUS_ACTIVE)
    camp.launched_at = _parse_time(data.get("launch_date")) or camp.launched_at
    db.session.flush()

    # Participants from the campaign's recipients.
    new_participants = 0
    for r in data.get("results", []):
        email = (r.get("email") or "").lower().strip()
        if not email:
            continue
        p = Participant.query.filter_by(email=email).first()
        if p is None:
            p = Participant(first_name=r.get("first_name") or "?",
                            last_name=r.get("last_name") or "?",
                            email=email, is_demo=False)
            db.session.add(p)
            db.session.flush()
            new_participants += 1
        if not CampaignParticipant.query.filter_by(
                campaign_id=camp.id, participant_id=p.id).first():
            db.session.add(CampaignParticipant(campaign_id=camp.id, participant_id=p.id))
    db.session.flush()

    email_to_pid = {}
    for cp in CampaignParticipant.query.filter_by(campaign_id=camp.id):
        p = db.session.get(Participant, cp.participant_id)
        if p:
            email_to_pid[p.email.lower()] = p.id

    # Replace any previous GoPhish events for this campaign (idempotent).
    CampaignEvent.query.filter_by(campaign_id=camp.id, source="gophish").delete(
        synchronize_session=False)

    events = 0
    seen_sent = set()
    for entry in data.get("timeline", []):
        etype = GOPHISH_EVENT_MAP.get(entry.get("message"))
        if not etype:
            continue
        pid = email_to_pid.get((entry.get("email") or "").lower())
        db.session.add(CampaignEvent(campaign_id=camp.id, participant_id=pid,
                                     event_type=etype, source="gophish",
                                     occurred_at=_parse_time(entry.get("time"))))
        if etype == EVENT_SENT and pid:
            seen_sent.add(pid)
        events += 1

    # Ensure every recipient has a "sent" event so metrics compute correctly.
    for pid in email_to_pid.values():
        if pid not in seen_sent:
            db.session.add(CampaignEvent(campaign_id=camp.id, participant_id=pid,
                                         event_type=EVENT_SENT, source="gophish",
                                         occurred_at=camp.launched_at or datetime.utcnow()))

    db.session.commit()
    return (f"Imported from GoPhish: '{name}' — "
            f"{len(email_to_pid)} participants ({new_participants} new), {events} events.")


def _clear_source_events(campaign, source, keep_sent=True):
    q = CampaignEvent.query.filter_by(campaign_id=campaign.id, source=source)
    if keep_sent:
        q = q.filter(CampaignEvent.event_type != EVENT_SENT)
    q.delete(synchronize_session=False)


def sync_campaign(campaign) -> str:
    """Sync results for one campaign. Returns a human-readable summary."""
    if demo_mode_active():
        return _sync_demo(campaign)
    return _sync_live(campaign)


def _sync_demo(campaign) -> str:
    """Generate a realistic synthetic funnel from the 'sent' events.

    Idempotent: clears previous demo funnel events first, keeps 'sent'.
    """
    sent = CampaignEvent.query.filter_by(
        campaign_id=campaign.id, event_type=EVENT_SENT).all()
    if not sent:
        return "This campaign has no 'sent' events yet (launch it first)."

    _clear_source_events(campaign, source="demo", keep_sent=True)

    rng = random.Random(campaign.id)  # stable per-campaign numbers
    base = campaign.launched_at or datetime.utcnow()
    opened = clicked = submitted = reported = 0
    for ev in sent:
        pid = ev.participant_id
        if rng.random() < 0.65:        # opened
            _add(campaign.id, pid, EVENT_OPENED, base + timedelta(hours=1))
            opened += 1
            if rng.random() < 0.45:    # clicked (of opened)
                _add(campaign.id, pid, EVENT_CLICKED, base + timedelta(hours=2))
                clicked += 1
                if rng.random() < 0.30:  # submitted (of clicked)
                    _add(campaign.id, pid, EVENT_SUBMITTED,
                         base + timedelta(hours=2, minutes=10))
                    submitted += 1
        if rng.random() < 0.18:        # reported
            _add(campaign.id, pid, EVENT_REPORTED, base + timedelta(hours=3))
            reported += 1

    db.session.commit()
    return (f"Demo sync: {opened} opened, {clicked} clicked, "
            f"{submitted} submitted, {reported} reported.")


def _sync_live(campaign) -> str:
    if not campaign.gophish_campaign_id:
        raise GoPhishError("No GoPhish campaign ID is assigned to this campaign.")
    resp = _request(f"/api/campaigns/{campaign.gophish_campaign_id}")
    if resp.status_code != 200:
        raise GoPhishError(f"GoPhish HTTP {resp.status_code}")
    data = resp.json()

    # Replace previous GoPhish-sourced events (idempotent sync).
    _clear_source_events(campaign, source="gophish", keep_sent=False)

    # Build email -> participant_id map for this campaign.
    email_to_pid = {}
    for cp in CampaignParticipant.query.filter_by(campaign_id=campaign.id):
        p = db.session.get(Participant, cp.participant_id)
        if p:
            email_to_pid[p.email.lower()] = p.id

    imported = 0
    for entry in data.get("timeline", []):
        etype = GOPHISH_EVENT_MAP.get(entry.get("message"))
        if not etype:
            continue
        email = (entry.get("email") or "").lower()
        pid = email_to_pid.get(email)
        occurred = _parse_time(entry.get("time"))
        db.session.add(CampaignEvent(
            campaign_id=campaign.id, participant_id=pid,
            event_type=etype, source="gophish", occurred_at=occurred))
        imported += 1

    db.session.commit()
    return f"GoPhish sync: {imported} events updated."


def _add(campaign_id, participant_id, event_type, when):
    db.session.add(CampaignEvent(campaign_id=campaign_id,
                                 participant_id=participant_id,
                                 event_type=event_type, source="demo",
                                 occurred_at=when))


def _parse_time(value):
    if not value:
        return datetime.utcnow()
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except (ValueError, AttributeError):
        return datetime.utcnow()
