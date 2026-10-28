"""Email template builder: CRUD, preview and Mailtrap test send.

Templates use fictional sender domains (@example.com). Impersonating a real
organization is out of scope. Personalization uses a fixed set of safe tokens.
"""
from flask import (Blueprint, render_template, redirect, url_for, flash,
                   request, abort)
from flask_login import login_required, current_user

from app.extensions import db
from app.models import EmailTemplate, AuditLog
from app.blueprints.auth.decorators import admin_required
from app.services.mail_service import (render_personalized, send_test_email,
                                       is_mailtrap_configured, ALLOWED_VARS)
from .forms import TemplateForm, TestEmailForm

templates_bp = Blueprint("templates_bp", __name__, url_prefix="/templates")


@templates_bp.route("/")
@login_required
def index():
    templates = EmailTemplate.query.order_by(EmailTemplate.id.desc()).all()
    return render_template("templates_bp/index.html", templates=templates)


@templates_bp.route("/new", methods=["GET", "POST"])
@login_required
def create():
    form = TemplateForm()
    if form.validate_on_submit():
        t = EmailTemplate(
            name=form.name.data.strip(), subject=form.subject.data.strip(),
            sender_name=form.sender_name.data.strip(),
            sender_email=form.sender_email.data.lower().strip(),
            category=form.category.data, html_body=form.html_body.data,
            is_demo=False, created_by_id=current_user.id,
        )
        db.session.add(t)
        db.session.add(AuditLog(user_id=current_user.id, action="template_create",
                                detail=t.name, ip_address=request.remote_addr))
        db.session.commit()
        flash("Template created.", "success")
        return redirect(url_for("templates_bp.preview", tid=t.id))
    return render_template("templates_bp/form.html", form=form,
                          title="New template", allowed_vars=ALLOWED_VARS)


@templates_bp.route("/<int:tid>/edit", methods=["GET", "POST"])
@login_required
def edit(tid):
    t = db.session.get(EmailTemplate, tid) or abort(404)
    form = TemplateForm(obj=t)
    if form.validate_on_submit():
        t.name = form.name.data.strip()
        t.subject = form.subject.data.strip()
        t.sender_name = form.sender_name.data.strip()
        t.sender_email = form.sender_email.data.lower().strip()
        t.category = form.category.data
        t.html_body = form.html_body.data
        db.session.add(AuditLog(user_id=current_user.id, action="template_edit",
                                detail=t.name, ip_address=request.remote_addr))
        db.session.commit()
        flash("Template updated.", "success")
        return redirect(url_for("templates_bp.preview", tid=t.id))
    return render_template("templates_bp/form.html", form=form,
                          title="Edit template", allowed_vars=ALLOWED_VARS)


@templates_bp.route("/<int:tid>/delete", methods=["POST"])
@login_required
@admin_required
def delete(tid):
    t = db.session.get(EmailTemplate, tid) or abort(404)
    name = t.name
    db.session.delete(t)
    db.session.add(AuditLog(user_id=current_user.id, action="template_delete",
                            detail=name, ip_address=request.remote_addr))
    db.session.commit()
    flash("Template deleted.", "success")
    return redirect(url_for("templates_bp.index"))


@templates_bp.route("/<int:tid>/preview", methods=["GET", "POST"])
@login_required
def preview(tid):
    t = db.session.get(EmailTemplate, tid) or abort(404)
    form = TestEmailForm()
    rendered = render_personalized(t.html_body)

    if form.validate_on_submit():
        ok, message = send_test_email(
            to_email=form.recipient.data.strip(), subject=t.subject,
            html_body=t.html_body, from_name=t.sender_name,
            from_email=t.sender_email)
        if ok:
            db.session.add(AuditLog(user_id=current_user.id,
                                    action="template_test_email",
                                    detail=f"{t.name} -> {form.recipient.data}",
                                    ip_address=request.remote_addr))
            db.session.commit()
        flash(message, "success" if ok else "danger")
        return redirect(url_for("templates_bp.preview", tid=t.id))

    return render_template("templates_bp/preview.html", template=t,
                          rendered=rendered, form=form,
                          mailtrap_ok=is_mailtrap_configured())
