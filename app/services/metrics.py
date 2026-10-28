"""Metric calculations, documented for transparency.

Every rate counts DISTINCT participants per stage (a participant who clicks
twice counts once). The denominator is the number of emails SENT, so rates
answer "of those who received the email, what share reached this stage".

    open_rate    = opened    / sent
    click_rate   = clicked   / sent
    submit_rate  = submitted / sent
    report_rate  = reported  / sent
"""
from app.models import (Campaign, CampaignEvent, CampaignParticipant,
                        EVENT_SENT, EVENT_OPENED, EVENT_CLICKED,
                        EVENT_SUBMITTED, EVENT_REPORTED)


def campaign_metrics(campaign) -> dict:
    by_type = {}
    for ev in campaign.events:
        by_type.setdefault(ev.event_type, set()).add(ev.participant_id)

    sent = len(by_type.get(EVENT_SENT, set()))

    def rate(event_type):
        n = len(by_type.get(event_type, set()))
        return round(100 * n / sent, 1) if sent else 0.0

    return {
        "targeted": len(campaign.participants),
        "sent": sent,
        "opened": len(by_type.get(EVENT_OPENED, set())),
        "clicked": len(by_type.get(EVENT_CLICKED, set())),
        "submitted": len(by_type.get(EVENT_SUBMITTED, set())),
        "reported": len(by_type.get(EVENT_REPORTED, set())),
        "open_rate": rate(EVENT_OPENED),
        "click_rate": rate(EVENT_CLICKED),
        "submit_rate": rate(EVENT_SUBMITTED),
        "report_rate": rate(EVENT_REPORTED),
    }


def overall_metrics(campaigns=None):
    """Aggregate across campaigns (all by default), for the dashboard."""
    if campaigns is None:
        campaigns = Campaign.query.all()
    totals = {"campaigns": len(campaigns), "targeted": 0, "sent": 0,
              "opened": 0, "clicked": 0, "submitted": 0, "reported": 0}
    for c in campaigns:
        m = campaign_metrics(c)
        for k in ("targeted", "sent", "opened", "clicked", "submitted", "reported"):
            totals[k] += m[k]

    sent = totals["sent"]

    def rate(key):
        return round(100 * totals[key] / sent, 1) if sent else 0.0

    totals["click_rate"] = rate("clicked")
    totals["open_rate"] = rate("opened")
    totals["report_rate"] = rate("reported")
    totals["submit_rate"] = rate("submitted")
    return totals


def department_breakdown(campaign_ids=None):
    """Per-department participant counts and distinct click/report counts.

    click_rate here = distinct participants in the department who clicked in any
    campaign / participants in the department. When campaign_ids is given, only
    participants targeted by those campaigns and their events are counted.
    """
    from app.extensions import db
    from app.models import Participant, Department

    rows = {d.id: {"name": d.name, "participants": 0, "clicked": 0, "reported": 0}
            for d in Department.query.all()}

    # participant -> department map (only participants with a department)
    participants = Participant.query.all()
    if campaign_ids is not None:
        targeted = {cp.participant_id for cp in CampaignParticipant.query.filter(
            CampaignParticipant.campaign_id.in_(campaign_ids))}
        participants = [p for p in participants if p.id in targeted]

    pid_to_dept = {}
    for p in participants:
        if p.department_id in rows:
            rows[p.department_id]["participants"] += 1
            pid_to_dept[p.id] = p.department_id

    seen = {EVENT_CLICKED: set(), EVENT_REPORTED: set()}
    events = CampaignEvent.query.filter(
        CampaignEvent.event_type.in_([EVENT_CLICKED, EVENT_REPORTED]))
    if campaign_ids is not None:
        events = events.filter(CampaignEvent.campaign_id.in_(campaign_ids))
    for ev in events.all():
        dept_id = pid_to_dept.get(ev.participant_id)
        if dept_id is None:
            continue
        if ev.participant_id in seen[ev.event_type]:
            continue
        seen[ev.event_type].add(ev.participant_id)
        key = "clicked" if ev.event_type == EVENT_CLICKED else "reported"
        rows[dept_id][key] += 1

    result = []
    for r in rows.values():
        n = r["participants"]
        r["click_rate"] = round(100 * r["clicked"] / n, 1) if n else 0.0
        result.append(r)
    return sorted(result, key=lambda r: r["click_rate"], reverse=True)
