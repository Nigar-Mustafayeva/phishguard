"""Human Risk Intelligence: per-participant risk scoring, explanations,
adaptive training recommendations and training-effectiveness tracking.

Everything is computed from stored campaign events. The scoring formula is
transparent (documented below) so a High/Medium/Low label can always be
explained, never a black box.

Score (0-100), per participant, across ALL campaigns they were sent:
    click_ratio = clicked_campaigns / sent_campaigns
    score  = click_ratio * 55
    score += 25   if they ever submitted the training form
    score += 15   if they clicked in more than one campaign (repeat offender)
    score -= (reported_campaigns / sent_campaigns) * 20   (reporting is good)
    score clamped to [0, 100]

Levels:  High >= 60,  Medium 30-59,  Low < 30.
"""
from collections import defaultdict

from app.extensions import db
from app.models import (Participant, Campaign, CampaignEvent,
                        EVENT_SENT, EVENT_OPENED, EVENT_CLICKED,
                        EVENT_SUBMITTED, EVENT_REPORTED, STATUS_DRAFT)
from app.services.metrics import campaign_metrics

# Which training module best addresses each phishing category.
CATEGORY_TO_TRAINING = {
    "credential": ("links-and-passwords", "Suspicious links, passwords & MFA"),
    "update": ("phishing-basics", "Recognising phishing red flags"),
    "hr": ("sender-verification", "Verifying the sender"),
    "delivery": ("sender-verification", "Verifying the sender"),
}
DEFAULT_TRAINING = ("phishing-basics", "Recognising phishing red flags")
PASSWORD_TRAINING = ("links-and-passwords", "Suspicious links, passwords & MFA")


def _level(score: int):
    if score >= 60:
        return "high", "High"
    if score >= 30:
        return "medium", "Medium"
    return "low", "Low"


def participant_risk(participant, campaign_ids=None) -> dict:
    """Return a risk profile dict for one participant.

    When campaign_ids is given, only events from those campaigns are scored.
    """
    by_campaign = defaultdict(set)
    events = CampaignEvent.query.filter_by(participant_id=participant.id)
    if campaign_ids is not None:
        events = events.filter(CampaignEvent.campaign_id.in_(campaign_ids))
    for ev in events.all():
        by_campaign[ev.campaign_id].add(ev.event_type)

    sent_campaigns = [cid for cid, s in by_campaign.items() if EVENT_SENT in s]
    n = len(sent_campaigns)
    if n == 0:
        return {"participant": participant, "has_data": False, "score": 0,
                "level": "none", "level_label": "—",
                "factors": ["No campaign data yet."],
                "rec_slug": None, "rec_title": None,
                "stats": {"sent": 0, "clicked": 0, "submitted": 0,
                          "reported": 0, "opened": 0}}

    clicked = sum(1 for cid in sent_campaigns if EVENT_CLICKED in by_campaign[cid])
    submitted = sum(1 for cid in sent_campaigns if EVENT_SUBMITTED in by_campaign[cid])
    reported = sum(1 for cid in sent_campaigns if EVENT_REPORTED in by_campaign[cid])
    opened = sum(1 for cid in sent_campaigns if EVENT_OPENED in by_campaign[cid])

    score = (clicked / n) * 55
    if submitted > 0:
        score += 25
    if clicked > 1:
        score += 15
    score -= (reported / n) * 20
    score = max(0, min(100, round(score)))
    level, level_label = _level(score)

    # Explanations
    factors = [f"Targeted in {n} campaign(s)."]
    if clicked:
        factors.append(f"Clicked the link in {clicked}/{n} campaign(s).")
    if clicked > 1:
        factors.append("Repeat clicker — made the same mistake more than once.")
    if submitted:
        factors.append(f"Entered data into the training form {submitted} time(s) "
                       "(no real password was stored).")
    if reported:
        factors.append(f"Reported the suspicious email {reported} time(s) (positive behaviour).")
    if clicked == 0 and opened:
        factors.append("Opened the email but did not click the link.")
    if clicked == 0 and opened == 0:
        factors.append("No risky behaviour recorded.")

    # Adaptive training recommendation
    if submitted > 0:
        rec = PASSWORD_TRAINING
    elif clicked > 0:
        rec = DEFAULT_TRAINING
        for cid in sent_campaigns:
            if EVENT_CLICKED in by_campaign[cid]:
                c = db.session.get(Campaign, cid)
                if c and c.template and c.template.category:
                    rec = CATEGORY_TO_TRAINING.get(c.template.category, DEFAULT_TRAINING)
                    break
    elif reported == 0:
        rec = ("sender-verification", "Verifying the sender")
    else:
        rec = DEFAULT_TRAINING

    return {"participant": participant, "has_data": True, "score": score,
            "level": level, "level_label": level_label, "factors": factors,
            "rec_slug": rec[0], "rec_title": rec[1],
            "stats": {"sent": n, "clicked": clicked, "submitted": submitted,
                      "reported": reported, "opened": opened}}


def all_risk_profiles(campaign_ids=None) -> list:
    """Risk profiles for participants with data, highest risk first."""
    profiles = [participant_risk(p, campaign_ids) for p in Participant.query.all()]
    profiles = [p for p in profiles if p["has_data"]]
    profiles.sort(key=lambda r: r["score"], reverse=True)
    return profiles


def org_summary(profiles: list) -> dict:
    if not profiles:
        return {"count": 0, "avg": 0, "high": 0, "medium": 0, "low": 0}
    counts = {"high": 0, "medium": 0, "low": 0}
    for p in profiles:
        counts[p["level"]] += 1
    avg = round(sum(p["score"] for p in profiles) / len(profiles), 1)
    return {"count": len(profiles), "avg": avg, **counts}


def training_effectiveness() -> dict | None:
    """Compare the earliest vs latest launched campaign (trend over time).

    This is an honest proxy: it shows how click/report rates changed between
    the first and most recent campaigns, not a controlled before/after study.
    """
    launched = (Campaign.query
                .filter(Campaign.status != STATUS_DRAFT)
                .filter(Campaign.launched_at.isnot(None))
                .order_by(Campaign.launched_at).all())
    if len(launched) < 2:
        return None
    first, last = launched[0], launched[-1]
    mf, ml = campaign_metrics(first), campaign_metrics(last)
    return {
        "first": {"name": first.name, "date": first.launched_at,
                  "click_rate": mf["click_rate"], "report_rate": mf["report_rate"]},
        "last": {"name": last.name, "date": last.launched_at,
                 "click_rate": ml["click_rate"], "report_rate": ml["report_rate"]},
        "click_delta": round(ml["click_rate"] - mf["click_rate"], 1),
        "report_delta": round(ml["report_rate"] - mf["report_rate"], 1),
    }
