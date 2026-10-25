"""User accounts and roles (admin / analyst).

Role is stored as a short string column rather than a separate Role table:
for two roles this is simpler and standard for small apps. If the role set
grows, it can be promoted to its own table later.
"""
from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db

ROLE_ADMIN = "admin"
ROLE_ANALYST = "analyst"


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default=ROLE_ANALYST)
    active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def set_password(self, raw_password: str) -> None:
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return check_password_hash(self.password_hash, raw_password)

    @property
    def is_admin(self) -> bool:
        return self.role == ROLE_ADMIN

    # Flask-Login uses this to decide if the account may log in.
    @property
    def is_active(self) -> bool:  # noqa: D401
        return self.active

    def __repr__(self) -> str:
        return f"<User {self.email} ({self.role})>"
