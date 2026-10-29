"""Participant management: CRUD, department handling and CSV import.

Participants are the people targeted by simulations. For the public demo they
are synthetic (@example.com). Real passwords are never involved here.
"""
from flask import (Blueprint, render_template, redirect, url_for, flash,
                   request, Response)
from flask_login import login_required, current_user

from app.extensions import db
from app.models import Participant, Department, AuditLog, TrainingAssignment
from app.blueprints.auth.decorators import admin_required
from app.services.participant_import import CSV_COLUMNS, CSVError, parse_csv, save_rows
from .forms import ParticipantForm, CSVImportForm

participants_bp = Blueprint("participants", __name__, url_prefix="/participants")


def _find_or_create_department(name: str):
    name = (name or "").strip()
    if not name:
        return None
    dept = Department.query.filter_by(name=name).first()
    if dept is None:
        dept = Department(name=name)
        db.session.add(dept)
        db.session.flush()
    return dept


@participants_bp.route("/")
@login_required
def index():
    participants = Participant.query.order_by(Participant.id.desc()).all()
    return render_template("participants/index.html", participants=participants)


@participants_bp.route("/new", methods=["GET", "POST"])
@login_required
def create():
    form = ParticipantForm()
    if form.validate_on_submit():
        email = form.email.data.lower().strip()
        if Participant.query.filter_by(email=email).first():
            flash("A participant with this email already exists.", "danger")
        else:
            p = Participant(
                first_name=form.first_name.data.strip(),
                last_name=form.last_name.data.strip(),
                email=email,
                department=_find_or_create_department(form.department.data),
                is_demo=False,
            )
            db.session.add(p)
            db.session.add(AuditLog(user_id=current_user.id,
                                    action="participant_create", detail=email,
                                    ip_address=request.remote_addr))
            db.session.commit()
            flash("Participant added.", "success")
            return redirect(url_for("participants.index"))
    return render_template("participants/form.html", form=form,
                          title="New participant")


@participants_bp.route("/<int:pid>/edit", methods=["GET", "POST"])
@login_required
def edit(pid):
    p = db.session.get(Participant, pid) or _abort_404()
    form = ParticipantForm(obj=p)
    if request.method == "GET" and p.department:
        form.department.data = p.department.name
    if form.validate_on_submit():
        email = form.email.data.lower().strip()
        existing = Participant.query.filter_by(email=email).first()
        if existing and existing.id != p.id:
            flash("This email belongs to another participant.", "danger")
        else:
            p.first_name = form.first_name.data.strip()
            p.last_name = form.last_name.data.strip()
            p.email = email
            p.department = _find_or_create_department(form.department.data)
            db.session.add(AuditLog(user_id=current_user.id,
                                    action="participant_edit", detail=email,
                                    ip_address=request.remote_addr))
            db.session.commit()
            flash("Participant updated.", "success")
            return redirect(url_for("participants.index"))
    return render_template("participants/form.html", form=form,
                          title="Edit participant")


@participants_bp.route("/<int:pid>/delete", methods=["POST"])
@login_required
@admin_required
def delete(pid):
    p = db.session.get(Participant, pid) or _abort_404()
    email = p.email
    TrainingAssignment.query.filter_by(participant_id=p.id).delete()
    db.session.delete(p)
    db.session.add(AuditLog(user_id=current_user.id, action="participant_delete",
                            detail=email, ip_address=request.remote_addr))
    db.session.commit()
    flash("Participant deleted.", "success")
    return redirect(url_for("participants.index"))


@participants_bp.route("/import", methods=["GET", "POST"])
@login_required
def import_csv():
    form = CSVImportForm()
    if form.validate_on_submit():
        try:
            rows, error_rows = parse_csv(form.file.data.stream.read())
        except CSVError as exc:
            flash(str(exc), "danger")
            return render_template("participants/import.html", form=form,
                                  columns=CSV_COLUMNS)

        _, imported = save_rows(rows)
        skipped, errors = len(rows) - imported, len(error_rows)
        db.session.add(AuditLog(
            user_id=current_user.id, action="participant_import",
            detail=f"imported={imported} skipped={skipped} errors={errors}",
            ip_address=request.remote_addr))
        db.session.commit()
        flash(f"Import finished: {imported} added, {skipped} already existed, "
              f"{errors} errors.", "success")
        return render_template("participants/import.html", form=CSVImportForm(),
                              columns=CSV_COLUMNS, done=True,
                              imported=imported, skipped=skipped,
                              errors=errors, error_rows=error_rows)

    return render_template("participants/import.html", form=form,
                          columns=CSV_COLUMNS)


@participants_bp.route("/sample.csv")
@login_required
def sample_csv():
    """Download a small example CSV with the expected columns."""
    sample = ("first_name,last_name,email,department\n"
              "Aysel,Mammadova,aysel.mammadova@example.com,IT\n"
              "Rauf,Aliyev,rauf.aliyev@example.com,Finance\n")
    return Response(sample, mimetype="text/csv",
                    headers={"Content-Disposition":
                             "attachment; filename=participants_sample.csv"})


def _abort_404():
    from flask import abort
    abort(404)
