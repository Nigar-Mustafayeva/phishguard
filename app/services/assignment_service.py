"""Adaptive training assignments: recommend, assign, invite, measure.

Recommendations come from Claude when ANTHROPIC_API_KEY is set, otherwise from
transparent rules based on the risk profile. Only behavioural data is sent to
the model (department, counts, risk factors) — never names or email addresses.

Invitations go out over SMTP when SMTP_* is configured; otherwise the private
training link is shown in the app so it can be shared manually.
"""
import json
import secrets
import smtplib
from collections import defaultdict
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import parseaddr

from flask import current_app
from markupsafe import escape

from app.extensions import db
from app.models import (TrainingModule, TrainingAssignment, Campaign, CampaignEvent,
                        ASSIGN_ASSIGNED, ASSIGN_SENT, ASSIGN_OPENED, ASSIGN_COMPLETED,
                        EVENT_SENT, EVENT_CLICKED, EVENT_REPORTED, STATUS_DRAFT)
from app.services.training_content import TRAINING_MODULES, module_meta

MAX_MODULES_PER_PERSON = 2

AI_SYSTEM_PROMPT = """You are a security-awareness training advisor inside PhishGuard, \
a phishing-simulation platform used by authorised organisations.

For each participant you receive their behaviour in phishing simulations (how many \
campaigns targeted them, clicks, form submissions, reports), their risk score (0-100) \
and the factors behind it. Choose the training modules from the catalogue that would \
most reduce that person's risk, and explain why in one or two short sentences that \
the participant could read without feeling blamed.

Guidelines:
- Assign 1 or 2 modules per participant, most important first. Use only slugs from the catalogue.
- Entering data into a form points to passwords/MFA and "what to do if you clicked".
- Repeated clicks call for red-flag recognition and sender verification.
- Someone who reports suspicious emails is doing well; give them one module that \
builds on that strength.
- Write the reason in plain, encouraging English addressed to the participant ("you")."""


# ---- Recommendations --------------------------------------------------------

def module_catalog() -> list[dict]:
    return [{"slug": m["slug"], "title": m["title"], "level": m["level"],
             "summary": m["summary"]} for m in TRAINING_MODULES]


def _rule_recommendation(profile: dict) -> dict:
    """Deterministic fallback built from the explainable risk profile."""
    stats = profile["stats"]
    slugs = [profile["rec_slug"]] if profile["rec_slug"] else ["phishing-basics"]
    if stats["submitted"] and "reporting-incidents" not in slugs:
        slugs.append("reporting-incidents")
    elif stats["clicked"] > 1 and "sender-verification" not in slugs:
        slugs.append("sender-verification")
    elif not stats["clicked"] and stats["reported"]:
        slugs = ["social-engineering"]
    if stats["submitted"]:
        reason = ("In a recent phishing exercise you entered details into a simulated login "
                  "form. This training shows how to spot fake pages and what to do if it happens.")
    elif stats["clicked"] > 1:
        reason = ("You clicked links in more than one phishing exercise. This training helps "
                  "you spot the warning signs before you click.")
    elif stats["clicked"]:
        reason = ("You clicked a link in a recent phishing exercise. This short training "
                  "shows the red flags to check first.")
    elif stats["reported"]:
        reason = ("Great job reporting a suspicious email! This module builds on that "
                  "instinct with other tricks attackers use.")
    else:
        reason = ("A short refresher to keep your phishing instincts sharp.")
    return {"slugs": slugs[:MAX_MODULES_PER_PERSON], "reason": reason, "source": "rules"}


def ai_available() -> bool:
    return bool(current_app.config.get("ANTHROPIC_API_KEY"))


def _ai_recommendations(profiles: list[dict]) -> dict[int, dict]:
    """Ask Claude for assignments. Returns {participant_id: {...}}; raises on failure."""
    import anthropic

    slugs = [m["slug"] for m in TRAINING_MODULES]
    people = [{
        "participant_id": p["participant"].id,
        "department": p["participant"].department.name if p["participant"].department else None,
        "risk_score": p["score"],
        "risk_level": p["level"],
        "campaigns_targeted": p["stats"]["sent"],
        "opened": p["stats"]["opened"],
        "clicked": p["stats"]["clicked"],
        "submitted_form": p["stats"]["submitted"],
        "reported": p["stats"]["reported"],
        "risk_factors": p["factors"],
    } for p in profiles]

    schema = {
        "type": "object",
        "properties": {
            "assignments": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "participant_id": {"type": "integer"},
                        "modules": {"type": "array", "items": {"type": "string", "enum": slugs}},
                        "reason": {"type": "string"},
                    },
                    "required": ["participant_id", "modules", "reason"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["assignments"],
        "additionalProperties": False,
    }

    client = anthropic.Anthropic(api_key=current_app.config["ANTHROPIC_API_KEY"],
                                 timeout=120.0)
    response = client.beta.messages.create(
        model=current_app.config.get("AI_MODEL") or "claude-opus-5-5",
        max_tokens=16000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        system=AI_SYSTEM_PROMPT,
        output_config={"effort": "medium",
                       "format": {"type": "json_schema", "schema": schema}},
        messages=[{"role": "user", "content": (
            "Training catalogue:\n" + json.dumps(module_catalog(), indent=2) +
            "\n\nParticipants:\n" + json.dumps(people, indent=2))}],
    )
    if response.stop_reason in ("refusal", "max_tokens"):
        raise RuntimeError(f"AI response ended with stop_reason={response.stop_reason}")

    text = next(b.text for b in response.content if b.type == "text")
    result = {}
    for item in json.loads(text)["assignments"]:
        chosen = [s for s in dict.fromkeys(item["modules"]) if s in slugs]
        if chosen:
            result[item["participant_id"]] = {
                "slugs": chosen[:MAX_MODULES_PER_PERSON],
                "reason": item["reason"].strip(), "source": "ai"}
    return result


def recommend(profiles: list[dict], use_ai: bool = True) -> tuple[list[dict], str | None]:
    """Recommend modules per profile. Returns (rows, notice).

    Each row: {profile, slugs, reason, source}. Falls back to rules for anyone
    the AI did not cover, and for everyone if the AI call fails.
    """
    ai, notice = {}, None
    if use_ai and profiles:
        if ai_available():
            try:
                ai = _ai_recommendations(profiles)
            except Exception as exc:  # noqa: BLE001  (fallback keeps the feature usable)
                current_app.logger.warning("AI recommendation failed: %s", exc)
                notice = "The AI service could not be reached, so rule-based recommendations are shown."
        else:
            notice = ("AI is not configured (set ANTHROPIC_API_KEY), so rule-based "
                      "recommendations are shown.")
    rows = []
    for p in profiles:
        rec = ai.get(p["participant"].id) or _rule_recommendation(p)
        rows.append({"profile": p, **rec})
    return rows, notice


# ---- Assignment + invitation -------------------------------------------------

def create_assignment(participant, module, reason, source, risk_score, user_id):
    """Create an assignment unless an unfinished one already exists. Returns (a, created)."""
    existing = (TrainingAssignment.query
                .filter_by(participant_id=participant.id, module_id=module.id)
                .filter(TrainingAssignment.status != ASSIGN_COMPLETED).first())
    if existing:
        return existing, False
    a = TrainingAssignment(participant_id=participant.id, module_id=module.id,
                           token=secrets.token_urlsafe(32), reason=reason,
                           source=source, risk_score=risk_score,
                           created_by_id=user_id, status=ASSIGN_ASSIGNED)
    db.session.add(a)
    db.session.flush()
    return a, True


def smtp_configured() -> bool:
    cfg = current_app.config
    return bool(cfg.get("SMTP_HOST") and cfg.get("SMTP_FROM"))


def _invitation_html(a: TrainingAssignment, link: str) -> str:
    meta = module_meta(a.module.slug)
    reason = f"<p style='color:#475569'>{escape(a.reason)}</p>" if a.reason else ""
    return f"""<div style="font-family:Arial,sans-serif;max-width:560px;margin:auto;color:#0f172a">
  <h2 style="color:#0f1e3d">Your security training: {escape(a.module.title)}</h2>
  <p>Hi {escape(a.participant.first_name)},</p>
  <p>Based on recent phishing-awareness exercises, we've picked a short training module for you
  (about {meta['minutes']} minutes).</p>
  {reason}
  <p style="margin:28px 0">
    <a href="{escape(link)}" style="background:#2563eb;color:#fff;padding:12px 20px;border-radius:8px;
       text-decoration:none;font-weight:bold">Start the training</a></p>
  <p style="font-size:13px;color:#64748b">This link is personal to you. Results are used for
  awareness only, never to punish. If you weren't expecting this email, check with your security
  team through a channel you already know before clicking.</p>
</div>"""


def send_invitation(a: TrainingAssignment, link: str) -> tuple[bool, str]:
    """Email the training link. Updates the assignment status. Returns (ok, message)."""
    if not smtp_configured():
        a.email_error = "SMTP not configured"
        return False, "SMTP is not configured — share the link manually."

    cfg = current_app.config
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Your security training: {a.module.title}"
    msg["From"] = cfg["SMTP_FROM"]
    msg["To"] = a.participant.email
    msg.attach(MIMEText(f"Start your training: {link}", "plain", "utf-8"))
    msg.attach(MIMEText(_invitation_html(a, link), "html", "utf-8"))
    sender = parseaddr(cfg["SMTP_FROM"])[1] or cfg["SMTP_FROM"]
    try:
        with smtplib.SMTP(cfg["SMTP_HOST"], cfg["SMTP_PORT"], timeout=20) as s:
            if cfg.get("SMTP_USE_TLS", True):
                s.starttls()
            if cfg.get("SMTP_USERNAME"):
                s.login(cfg["SMTP_USERNAME"], cfg["SMTP_PASSWORD"])
            s.sendmail(sender, [a.participant.email], msg.as_string())
    except Exception as exc:  # noqa: BLE001  (store a friendly error per assignment)
        a.email_error = str(exc)[:500]
        return False, f"Sending failed: {exc}"
    a.email_error = None
    a.sent_at = datetime.utcnow()
    if a.status == ASSIGN_ASSIGNED:
        a.status = ASSIGN_SENT
    return True, "sent"


def mark_opened(a: TrainingAssignment) -> None:
    if a.opened_at is None:
        a.opened_at = datetime.utcnow()
    if a.status in (ASSIGN_ASSIGNED, ASSIGN_SENT):
        a.status = ASSIGN_OPENED


def mark_completed(a: TrainingAssignment, score: int, total: int) -> None:
    mark_opened(a)
    a.score, a.total = score, total
    a.completed_at = datetime.utcnow()
    a.status = ASSIGN_COMPLETED


# ---- Effectiveness -----------------------------------------------------------

def _click_rate(campaign_sets: list[set]) -> float | None:
    sent = [s for s in campaign_sets if EVENT_SENT in s]
    if not sent:
        return None
    return round(100 * sum(1 for s in sent if EVENT_CLICKED in s) / len(sent), 1)


def _report_rate(campaign_sets: list[set]) -> float | None:
    sent = [s for s in campaign_sets if EVENT_SENT in s]
    if not sent:
        return None
    return round(100 * sum(1 for s in sent if EVENT_REPORTED in s) / len(sent), 1)


def effectiveness() -> dict:
    """Funnel, scores and before/after behaviour of trained participants.

    Before/after compares each trained participant's campaigns launched before
    their first completed training with campaigns launched after it.
    """
    rows = TrainingAssignment.query.order_by(TrainingAssignment.created_at.desc()).all()
    n = len(rows)
    sent = sum(1 for a in rows if a.sent_at)
    opened = sum(1 for a in rows if a.opened_at)
    completed = [a for a in rows if a.status == ASSIGN_COMPLETED]
    scores = [100 * a.score / a.total for a in completed if a.total]

    funnel = {
        "assigned": n, "sent": sent, "opened": opened, "completed": len(completed),
        "completion_rate": round(100 * len(completed) / n, 1) if n else 0.0,
        "avg_score": round(sum(scores) / len(scores), 1) if scores else None,
        "ai_share": round(100 * sum(1 for a in rows if a.source == "ai") / n) if n else 0,
    }

    # Per module
    per_module = defaultdict(lambda: {"assigned": 0, "completed": 0, "scores": []})
    for a in rows:
        m = per_module[a.module_id]
        m["module"] = a.module
        m["assigned"] += 1
        if a.status == ASSIGN_COMPLETED:
            m["completed"] += 1
            if a.total:
                m["scores"].append(100 * a.score / a.total)
    modules = []
    for m in per_module.values():
        m["avg_score"] = round(sum(m["scores"]) / len(m["scores"]), 1) if m["scores"] else None
        m["completion_rate"] = round(100 * m["completed"] / m["assigned"], 1)
        modules.append(m)
    modules.sort(key=lambda m: m["assigned"], reverse=True)

    # Before / after for trained participants
    trained_at = {}
    for a in completed:
        t = trained_at.get(a.participant_id)
        trained_at[a.participant_id] = min(t, a.completed_at) if t else a.completed_at

    launch = {c.id: c.launched_at for c in Campaign.query.filter(
        Campaign.status != STATUS_DRAFT, Campaign.launched_at.isnot(None))}
    before, after = [], []
    if trained_at:
        by_pc = defaultdict(set)
        for ev in CampaignEvent.query.filter(
                CampaignEvent.participant_id.in_(list(trained_at))).all():
            if ev.campaign_id in launch:
                by_pc[(ev.participant_id, ev.campaign_id)].add(ev.event_type)
        per_person = defaultdict(lambda: ([], []))
        for (pid, cid), types in by_pc.items():
            target = per_person[pid][0] if launch[cid] < trained_at[pid] else per_person[pid][1]
            target.append(types)
        for pid, (b, af) in per_person.items():
            before.extend(b)
            after.extend(af)

    cb, ca = _click_rate(before), _click_rate(after)
    trend = {
        "trained": len(trained_at),
        "click_before": cb, "click_after": ca,
        "report_before": _report_rate(before), "report_after": _report_rate(after),
        "click_delta": round(ca - cb, 1) if cb is not None and ca is not None else None,
        "has_after": ca is not None,
    }
    return {"rows": rows, "funnel": funnel, "modules": modules, "trend": trend}


def module_by_slug(slug: str):
    return TrainingModule.query.filter_by(slug=slug).first()
