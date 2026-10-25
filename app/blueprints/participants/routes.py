"""Participant management: CRUD, department handling and CSV import.

Participants are the people targeted by simulations. For the public demo they
are synthetic (@example.com). Real passwords are never involved here.
"""
import csv
import io

from flask import (Blueprint, render_template, redirect, url_for, flash,
                   request, Response)
from flask_login import login_required, current_user
from email_validator import validate_email, EmailNotValidError

from app.extensions import db
from app.models import Participant, Department, AuditLog
from app.blueprints.auth.decorators import admin_required
from .forms import ParticipantForm, CSVImportForm

participants_bp = Blueprint("participants", __name__, url_prefix="/participants")

CSV_COLUMNS = ["first_name", "last_name", "email", "department"]


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
            flash("Bu email ilə iştirakçı artıq mövcuddur.", "danger")
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
            flash("İştirakçı əlavə olundu.", "success")
            return redirect(url_for("participants.index"))
    return render_template("participants/form.html", form=form,
                          title="Yeni iştirakçı")


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
            flash("Bu email başqa iştirakçıya aiddir.", "danger")
        else:
            p.first_name = form.first_name.data.strip()
            p.last_name = form.last_name.data.strip()
            p.email = email
            p.department = _find_or_create_department(form.department.data)
            db.session.add(AuditLog(user_id=current_user.id,
                                    action="participant_edit", detail=email,
                                    ip_address=request.remote_addr))
            db.session.commit()
            flash("İştirakçı yeniləndi.", "success")
            return redirect(url_for("participants.index"))
    return render_template("participants/form.html", form=form,
                          title="İştirakçını redaktə et")


@participants_bp.route("/<int:pid>/delete", methods=["POST"])
@login_required
@admin_required
def delete(pid):
    p = db.session.get(Participant, pid) or _abort_404()
    email = p.email
    db.session.delete(p)
    db.session.add(AuditLog(user_id=current_user.id, action="participant_delete",
                            detail=email, ip_address=request.remote_addr))
    db.session.commit()
    flash("İştirakçı silindi.", "success")
    return redirect(url_for("participants.index"))


@participants_bp.route("/import", methods=["GET", "POST"])
@login_required
def import_csv():
    form = CSVImportForm()
    if form.validate_on_submit():
        try:
            raw = form.file.data.stream.read().decode("utf-8-sig")
        except UnicodeDecodeError:
            flash("Fayl UTF-8 kodlaşmasında olmalıdır.", "danger")
            return render_template("participants/import.html", form=form,
                                  columns=CSV_COLUMNS)

        reader = csv.DictReader(io.StringIO(raw))
        imported = skipped = errors = 0
        error_rows = []
        seen_in_file = set()

        for line_no, row in enumerate(reader, start=2):  # row 1 = header
            fn = (row.get("first_name") or "").strip()
            ln = (row.get("last_name") or "").strip()
            em = (row.get("email") or "").strip().lower()
            dep = (row.get("department") or "").strip()

            if not (fn and ln and em):
                errors += 1
                error_rows.append((line_no, "boş sahə (ad/soyad/email)"))
                continue
            try:
                validate_email(em, check_deliverability=False)
            except EmailNotValidError:
                errors += 1
                error_rows.append((line_no, "yanlış email formatı"))
                continue
            if em in seen_in_file or Participant.query.filter_by(email=em).first():
                skipped += 1
                continue

            seen_in_file.add(em)
            db.session.add(Participant(
                first_name=fn, last_name=ln, email=em,
                department=_find_or_create_department(dep), is_demo=False,
            ))
            imported += 1

        db.session.add(AuditLog(
            user_id=current_user.id, action="participant_import",
            detail=f"imported={imported} skipped={skipped} errors={errors}",
            ip_address=request.remote_addr))
        db.session.commit()
        flash(f"İmport tamamlandı: {imported} əlavə, {skipped} dublikat, "
              f"{errors} xəta.", "success")
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
              "Aysel,Məmmədova,aysel.mammadova@example.com,IT\n"
              "Rauf,Əliyev,rauf.aliyev@example.com,Maliyyə\n")
    return Response(sample, mimetype="text/csv",
                    headers={"Content-Disposition":
                             "attachment; filename=participants_sample.csv"})


def _abort_404():
    from flask import abort
    abort(404)
