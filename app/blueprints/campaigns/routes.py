"""Campaign management: CRUD + safe launch/stop lifecycle.

A campaign moves: draft -> active -> completed/stopped.
Only drafts can be edited or deleted. Launching requires a template and at
least one participant, and a campaign can never be launched twice.
In demo mode, launching records synthetic "sent" events (no real email).
"""
from datetime import datetime

from flask import (Blueprint, render_template, redirect, url_for, flash,
                   request, abort)
from flask_login import login_required, current_user

from app.extensions import db
from app.models import (Campaign, EmailTemplate, Participant, CampaignParticipant,
                        CampaignEvent, AuditLog,
                        STATUS_DRAFT, STATUS_ACTIVE, STATUS_COMPLETED,
                        STATUS_STOPPED, EVENT_SENT)
from app.blueprints.auth.decorators import admin_required
from app.services import gophish_service
from .forms import CampaignForm

campaigns_bp = Blueprint("campaigns", __name__, url_prefix="/campaigns")


def _populate_choices(form):
    form.template_id.choices = [(t.id, t.name)
                                for t in EmailTemplate.query.order_by(EmailTemplate.name)]
    form.participant_ids.choices = [(p.id, f"{p.full_name} ({p.email})")
                                    for p in Participant.query.order_by(Participant.first_name)]


@campaigns_bp.route("/")
@login_required
def index():
    campaigns = Campaign.query.order_by(Campaign.id.desc()).all()
    return render_template("campaigns/index.html", campaigns=campaigns)


@campaigns_bp.route("/new", methods=["GET", "POST"])
@login_required
def create():
    form = CampaignForm()
    _populate_choices(form)
    if form.validate_on_submit():
        camp = Campaign(
            name=form.name.data.strip(), description=form.description.data,
            template_id=form.template_id.data, status=STATUS_DRAFT,
            is_demo=False, created_by_id=current_user.id,
        )
        db.session.add(camp)
        db.session.flush()
        for pid in form.participant_ids.data:
            db.session.add(CampaignParticipant(campaign_id=camp.id, participant_id=pid))
        db.session.add(AuditLog(user_id=current_user.id, action="campaign_create",
                                detail=camp.name, ip_address=request.remote_addr))
        db.session.commit()
        flash("Campaign created as a draft.", "success")
        return redirect(url_for("campaigns.detail", cid=camp.id))
    return render_template("campaigns/form.html", form=form, title="New campaign")


@campaigns_bp.route("/<int:cid>")
@login_required
def detail(cid):
    camp = db.session.get(Campaign, cid) or abort(404)
    # Event counts for this campaign
    counts = {}
    for ev in camp.events:
        counts[ev.event_type] = counts.get(ev.event_type, 0) + 1
    return render_template("campaigns/detail.html", camp=camp, counts=counts,
                          gophish=gophish_service.check_status(),
                          STATUS_DRAFT=STATUS_DRAFT, STATUS_ACTIVE=STATUS_ACTIVE)


@campaigns_bp.route("/<int:cid>/edit", methods=["GET", "POST"])
@login_required
def edit(cid):
    camp = db.session.get(Campaign, cid) or abort(404)
    if camp.status != STATUS_DRAFT:
        flash("Only draft campaigns can be edited.", "danger")
        return redirect(url_for("campaigns.detail", cid=camp.id))

    form = CampaignForm(obj=camp)
    _populate_choices(form)
    if request.method == "GET":
        form.participant_ids.data = [cp.participant_id for cp in camp.participants]
    if form.validate_on_submit():
        camp.name = form.name.data.strip()
        camp.description = form.description.data
        camp.template_id = form.template_id.data
        # Reset participant links
        CampaignParticipant.query.filter_by(campaign_id=camp.id).delete()
        for pid in form.participant_ids.data:
            db.session.add(CampaignParticipant(campaign_id=camp.id, participant_id=pid))
        db.session.add(AuditLog(user_id=current_user.id, action="campaign_edit",
                                detail=camp.name, ip_address=request.remote_addr))
        db.session.commit()
        flash("Campaign updated.", "success")
        return redirect(url_for("campaigns.detail", cid=camp.id))
    return render_template("campaigns/form.html", form=form,
                          title="Edit campaign")


@campaigns_bp.route("/<int:cid>/launch", methods=["POST"])
@login_required
def launch(cid):
    camp = db.session.get(Campaign, cid) or abort(404)

    # Guard rails: prevent duplicate / invalid launches.
    if camp.status != STATUS_DRAFT:
        flash("This campaign has already been launched or completed.", "danger")
        return redirect(url_for("campaigns.detail", cid=camp.id))
    if not camp.template_id:
        flash("Choose a template before launching.", "danger")
        return redirect(url_for("campaigns.detail", cid=camp.id))
    links = CampaignParticipant.query.filter_by(campaign_id=camp.id).all()
    if not links:
        flash("Add at least one participant before launching.", "danger")
        return redirect(url_for("campaigns.detail", cid=camp.id))

    camp.status = STATUS_ACTIVE
    camp.launched_at = datetime.utcnow()
    # Demo: record a "sent" event per participant. Real send comes via GoPhish.
    for cp in links:
        db.session.add(CampaignEvent(campaign_id=camp.id,
                                     participant_id=cp.participant_id,
                                     event_type=EVENT_SENT, source="demo"))
    db.session.add(AuditLog(user_id=current_user.id, action="campaign_launch",
                            detail=f"{camp.name} ({len(links)} participants)",
                            ip_address=request.remote_addr))
    db.session.commit()
    flash(f"Campaign launched (demo): {len(links)} emails recorded.", "success")
    return redirect(url_for("campaigns.detail", cid=camp.id))


@campaigns_bp.route("/<int:cid>/stop", methods=["POST"])
@login_required
def stop(cid):
    camp = db.session.get(Campaign, cid) or abort(404)
    if camp.status != STATUS_ACTIVE:
        flash("Only an active campaign can be stopped.", "danger")
        return redirect(url_for("campaigns.detail", cid=camp.id))
    camp.status = STATUS_COMPLETED
    db.session.add(AuditLog(user_id=current_user.id, action="campaign_stop",
                            detail=camp.name, ip_address=request.remote_addr))
    db.session.commit()
    flash("Campaign stopped (completed).", "success")
    return redirect(url_for("campaigns.detail", cid=camp.id))


@campaigns_bp.route("/<int:cid>/sync", methods=["POST"])
@login_required
def sync(cid):
    camp = db.session.get(Campaign, cid) or abort(404)
    if camp.status == STATUS_DRAFT:
        flash("A draft campaign cannot be synced. Launch it first.",
              "danger")
        return redirect(url_for("campaigns.detail", cid=camp.id))
    try:
        message = gophish_service.sync_campaign(camp)
        db.session.add(AuditLog(user_id=current_user.id, action="campaign_sync",
                                detail=camp.name, ip_address=request.remote_addr))
        db.session.commit()
        flash(message, "success")
    except gophish_service.GoPhishError as exc:
        flash(f"Sync failed: {exc}", "danger")
    return redirect(url_for("campaigns.detail", cid=camp.id))


@campaigns_bp.route("/<int:cid>/delete", methods=["POST"])
@login_required
@admin_required
def delete(cid):
    camp = db.session.get(Campaign, cid) or abort(404)
    # Drafts, and campaigns imported from GoPhish (a local copy of GoPhish
    # data), can be removed. Locally launched campaigns keep their history.
    if camp.status != STATUS_DRAFT and camp.gophish_campaign_id is None:
        flash("Only draft or imported campaigns can be deleted.", "danger")
        return redirect(url_for("campaigns.detail", cid=camp.id))
    name = camp.name
    db.session.delete(camp)
    db.session.add(AuditLog(user_id=current_user.id, action="campaign_delete",
                            detail=name, ip_address=request.remote_addr))
    db.session.commit()
    flash("Campaign deleted.", "success")
    # Only local paths are allowed as a return target (no open redirect).
    nxt = request.form.get("next", "")
    if not nxt.startswith("/") or nxt.startswith("//"):
        nxt = url_for("campaigns.index")
    return redirect(nxt)
