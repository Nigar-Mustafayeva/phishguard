"""Departments and the (synthetic) participants targeted by campaigns."""
from datetime import datetime

from app.extensions import db


class Department(db.Model):
    __tablename__ = "departments"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    participants = db.relationship(
        "Participant", back_populates="department", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Department {self.name}>"


class Participant(db.Model):
    __tablename__ = "participants"

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    department_id = db.Column(
        db.Integer, db.ForeignKey("departments.id"), nullable=True
    )
    # Clearly marks synthetic demo records so they are never mistaken for real data.
    is_demo = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    department = db.relationship("Department", back_populates="participants")

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def __repr__(self) -> str:
        return f"<Participant {self.email}>"
