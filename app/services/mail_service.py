"""Safe test-email sending through Mailtrap's SMTP sandbox.

Mailtrap captures messages in a sandbox inbox — nothing reaches real people.
Credentials come from environment variables, never from code.
"""
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from flask import current_app

# Allowed personalization variables. We replace these tokens explicitly
# (NOT with Jinja) so user-supplied templates can never execute code.
SAMPLE_CONTEXT = {
    "first_name": "Aysel",
    "last_name": "Məmmədova",
    "email": "aysel.mammadova@example.com",
    "department": "IT",
}
ALLOWED_VARS = list(SAMPLE_CONTEXT.keys())


def render_personalized(html: str, context: dict | None = None) -> str:
    """Replace {{var}} / {{ var }} tokens with values. Safe string replace only."""
    context = context or SAMPLE_CONTEXT
    out = html or ""
    for key, value in context.items():
        out = out.replace("{{" + key + "}}", value)
        out = out.replace("{{ " + key + " }}", value)
    return out


def is_mailtrap_configured() -> bool:
    cfg = current_app.config
    return bool(cfg.get("MAILTRAP_USERNAME") and cfg.get("MAILTRAP_PASSWORD"))


def send_test_email(to_email, subject, html_body, from_name, from_email):
    """Send one test email via Mailtrap. Returns (ok, message)."""
    if not is_mailtrap_configured():
        return False, ("Mailtrap konfiqurasiya olunmayıb. .env faylında "
                       "MAILTRAP_USERNAME və MAILTRAP_PASSWORD təyin edin.")

    cfg = current_app.config
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{from_name} <{from_email}>"
    msg["To"] = to_email
    msg.attach(MIMEText(render_personalized(html_body), "html", "utf-8"))

    try:
        with smtplib.SMTP(cfg["MAILTRAP_HOST"], cfg["MAILTRAP_PORT"], timeout=15) as s:
            s.starttls()
            s.login(cfg["MAILTRAP_USERNAME"], cfg["MAILTRAP_PASSWORD"])
            s.sendmail(from_email, [to_email], msg.as_string())
        return True, f"Test email Mailtrap sandbox-a göndərildi: {to_email}"
    except Exception as exc:  # noqa: BLE001  (show a friendly message)
        return False, f"Göndərmə alınmadı: {exc}"
