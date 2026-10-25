"""Report records, audit logs and integration settings.

IMPORTANT: secrets (API keys, passwords) are NEVER stored here. They live in
environment variables. IntegrationSetting holds only non-sensitive config/status.
"""
from datetime import datetime

from app.extensions import db


class ReportRecord(db.Model):
    __tablename__ = "report_records"

    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey("campaigns.id"), nullable=True)
    format = db.Column(db.String(10), nullable=False, default="pdf")  # pdf | csv
    file_name = db.Column(db.String(255), nullable=True)
    generated_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<ReportRecord {self.format} c={self.campaign_id}>"


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    action = db.Column(db.String(120), nullable=False)
    detail = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)  # fits IPv6
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)

    def __repr__(self) -> str:
        return f"<AuditLog {self.action}>"


class IntegrationSetting(db.Model):
    __tablename__ = "integration_settings"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(80), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=True)   # non-secret config/status only
    updated_at = db.Column(db.DateTime, nullable=False,
                          default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<IntegrationSetting {self.key}>"
