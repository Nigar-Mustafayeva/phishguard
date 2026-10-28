"""Adaptive training: AI-assisted assignment, email invitations, effectiveness.

Flow: pick participants from their risk profiles -> "Analyze" builds
recommendations (Claude or rules) -> review/edit -> assign and email the
private training links -> track completion and behaviour change.
"""
from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, abort, current_app)
from flask_login import login_required, current_user

from app.extensions import db
from app.models import (Campaign, Participant, TrainingModule, TrainingAssignment,
                        AuditLog)
from app.services import assignment_service as svc
from app.services.risk_service import all_risk_profiles, participant_risk
from app.services.training_content import module_meta

assignments_bp = Blueprint("assignments", __name__, url_prefix="/assignments")


def _scope_ids():
    """Score risk on imported GoPhish campaigns when there are any, else all."""
    ids = [c.id for c in Campaign.query.filter(Campaign.gophish_campaign_id.isnot(None))]
    return ids or None


def _link(a: TrainingAssignment) -> str:
    base = current_app.config.get("PUBLIC_BASE_URL") or request.url_root
    return base.rstrip("/") + url_for("learn.take", token=a.token)


@assignments_bp.route("/")
@login_required
def index():
    profiles = all_risk_profiles(_scope_ids())
    assignments = (TrainingAssignment.query
                   .order_by(TrainingAssignment.created_at.desc()).limit(50).all())
    return render_template("assignments/index.html", profiles=profiles,
                          assignments=assignments, link=_link,
                          ai_ready=svc.ai_available(),
                          smtp_ready=svc.smtp_configured())


@assignments_bp.route("/analyze", methods=["POST"])
@login_required
def analyze():
    pids = {int(p) for p in request.form.getlist("pid") if p.isdigit()}
    if not pids:
        flash("Select at least one participant.", "danger")
        return redirect(url_for("assignments.index"))
    scope = _scope_ids()
    profiles = [participant_risk(p, scope) for p in
                Participant.query.filter(Participant.id.in_(pids)).all()]
    profiles = [p for p in profiles if p["has_data"]]
    rows, notice = svc.recommend(profiles, use_ai=request.form.get("mode") != "rules")
    modules = TrainingModule.query.order_by(TrainingModule.order_index).all()
    return render_template("assignments/review.html", rows=rows, notice=notice,
                          modules=modules, smtp_ready=svc.smtp_configured())


@assignments_bp.route("/create", methods=["POST"])
@login_required
def create():
    modules = {m.slug: m for m in TrainingModule.query.all()}
    send = request.form.get("send") == "1"
    created = sent = failed = 0
    for raw in request.form.getlist("pid"):
        if not raw.isdigit():
            continue
        p = db.session.get(Participant, int(raw))
        if p is None:
            continue
        slugs = [request.form.get(f"m1_{p.id}"), request.form.get(f"m2_{p.id}")]
        reason = (request.form.get(f"reason_{p.id}") or "").strip()[:1000]
        source = "ai" if request.form.get(f"source_{p.id}") == "ai" else "rules"
        risk = request.form.get(f"risk_{p.id}", type=int)
        for slug in dict.fromkeys(s for s in slugs if s in modules):
            a, is_new = svc.create_assignment(p, modules[slug], reason, source, risk,
                                              current_user.id)
            if not is_new:
                continue
            created += 1
            if send:
                ok, _ = svc.send_invitation(a, _link(a))
                sent += ok
                failed += not ok
    db.session.add(AuditLog(user_id=current_user.id, action="training_assign",
                            detail=f"{created} assignments, {sent} emailed",
                            ip_address=request.remote_addr))
    db.session.commit()

    msg = f"{created} training assignments created"
    if send:
        msg += f", {sent} emailed" + (f", {failed} not sent (see the table)" if failed else "")
    flash(msg + ".", "success" if not failed else "warning")
    return redirect(url_for("assignments.index"))


@assignments_bp.route("/<int:aid>/send", methods=["POST"])
@login_required
def resend(aid):
    a = db.session.get(TrainingAssignment, aid) or abort(404)
    ok, message = svc.send_invitation(a, _link(a))
    db.session.commit()
    flash(f"Invitation sent to {a.participant.email}." if ok else message,
          "success" if ok else "danger")
    return redirect(url_for("assignments.index"))


@assignments_bp.route("/<int:aid>/delete", methods=["POST"])
@login_required
def delete(aid):
    a = db.session.get(TrainingAssignment, aid) or abort(404)
    db.session.delete(a)
    db.session.commit()
    flash("Assignment removed.", "success")
    return redirect(url_for("assignments.index"))


@assignments_bp.route("/effectiveness")
@login_required
def effectiveness():
    return render_template("assignments/effectiveness.html", data=svc.effectiveness(),
                          module_meta=module_meta)
