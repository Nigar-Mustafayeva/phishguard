"""Authentication: login and logout with audit logging."""
from urllib.parse import urlparse

from flask import (Blueprint, render_template, redirect, url_for, flash, request)
from flask_login import login_user, logout_user, login_required, current_user

from app.extensions import db
from app.models import User, AuditLog
from .forms import LoginForm

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data.lower().strip()
        user = User.query.filter_by(email=email).first()
        if user and user.active and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            db.session.add(AuditLog(user_id=user.id, action="login",
                                    ip_address=request.remote_addr))
            db.session.commit()

            # Safe redirect: only allow local "next" targets (no open redirect).
            next_page = request.args.get("next")
            if not next_page or urlparse(next_page).netloc != "":
                next_page = url_for("dashboard.index")
            return redirect(next_page)

        flash("Invalid email or password.", "danger")

    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    db.session.add(AuditLog(user_id=current_user.id, action="logout",
                            ip_address=request.remote_addr))
    db.session.commit()
    logout_user()
    flash("You have been signed out.", "success")
    return redirect(url_for("auth.login"))
