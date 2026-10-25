"""PDF report generation with reportlab.

Uses a bundled DejaVuSans font so Azerbaijani characters (ə, ğ, ı …) render
correctly. Reports are built entirely from stored data.
"""
import io
import os
from datetime import datetime

from flask import current_app
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                TableStyle)

_FONTS_REGISTERED = False


def _register_fonts():
    global _FONTS_REGISTERED
    if _FONTS_REGISTERED:
        return
    base = os.path.join(current_app.root_path, "static", "fonts")
    pdfmetrics.registerFont(TTFont("DejaVu", os.path.join(base, "DejaVuSans.ttf")))
    pdfmetrics.registerFont(TTFont("DejaVu-Bold",
                                  os.path.join(base, "DejaVuSans-Bold.ttf")))
    _FONTS_REGISTERED = True


def build_observations(metrics: dict) -> list[str]:
    """Generate plain-language observations and suggested training."""
    obs = []
    cr = metrics["click_rate"]
    rr = metrics["report_rate"]
    if metrics["sent"] == 0:
        return ["Bu kampaniyada hələ göndərilmiş email yoxdur."]
    if cr >= 30:
        obs.append(f"Klik faizi yüksəkdir ({cr}%). Təcili maarifləndirmə tövsiyə olunur.")
    elif cr >= 15:
        obs.append(f"Klik faizi orta səviyyədədir ({cr}%). Təlim davam etdirilməlidir.")
    else:
        obs.append(f"Klik faizi aşağıdır ({cr}%). Yaxşı nəticə.")
    if rr < 15:
        obs.append(f"Report faizi aşağıdır ({rr}%). İstifadəçilərə şübhəli emaili "
                   "'Report' etməyi öyrədin.")
    else:
        obs.append(f"Report faizi yaxşıdır ({rr}%).")
    if metrics["submitted"] > 0:
        obs.append(f"{metrics['submitted']} nəfər təlim formasına məlumat daxil etdi "
                   "(real parol saxlanmadı). Parol təhlükəsizliyi təlimi tövsiyə olunur.")
    return obs


SUGGESTED_TRAINING = [
    "Phishing əlamətlərini tanımaq",
    "Göndərən ünvanını yoxlamaq",
    "Şübhəli linklər, parol və MFA",
]


def build_pdf(campaign, metrics: dict) -> bytes:
    _register_fonts()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, title=f"PhishGuard - {campaign.name}",
                            topMargin=20 * mm, bottomMargin=20 * mm)

    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=styles["Title"], fontName="DejaVu-Bold",
                        fontSize=20, textColor=colors.HexColor("#0f1e3d"))
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontName="DejaVu-Bold",
                        fontSize=13, textColor=colors.HexColor("#2563eb"),
                        spaceBefore=12)
    body = ParagraphStyle("body", parent=styles["Normal"], fontName="DejaVu",
                          fontSize=10, leading=15)
    small = ParagraphStyle("small", parent=body, fontSize=8,
                           textColor=colors.grey)

    story = [Paragraph("PhishGuard — Kampaniya Hesabatı", h1)]
    story.append(Paragraph(
        f"Yaradılma tarixi: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC", small))
    if campaign.is_demo:
        story.append(Paragraph("⚠ Bu hesabat NÜMUNƏ (demo) data əsasındadır.", small))
    story.append(Spacer(1, 8))

    # Summary table
    story.append(Paragraph("Xülasə", h2))
    summary = [
        ["Kampaniya", campaign.name],
        ["Status", campaign.status],
        ["Şablon", campaign.template.name if campaign.template else "—"],
        ["Hədəf iştirakçı", str(metrics["targeted"])],
    ]
    story.append(_kv_table(summary))

    # Metrics table
    story.append(Paragraph("Metrikalar", h2))
    met = [
        ["Metrika", "Say", "Faiz"],
        ["Göndərildi", metrics["sent"], "100%"],
        ["Açıldı", metrics["opened"], f"{metrics['open_rate']}%"],
        ["Kliklədi", metrics["clicked"], f"{metrics['click_rate']}%"],
        ["Form doldurdu", metrics["submitted"], f"{metrics['submit_rate']}%"],
        ["Report etdi", metrics["reported"], f"{metrics['report_rate']}%"],
    ]
    story.append(_metrics_table(met))

    # Observations
    story.append(Paragraph("Əsas müşahidələr", h2))
    for o in build_observations(metrics):
        story.append(Paragraph(f"• {o}", body))

    # Suggested training
    story.append(Paragraph("Tövsiyə olunan təlim", h2))
    for t in SUGGESTED_TRAINING:
        story.append(Paragraph(f"• {t}", body))

    story.append(Spacer(1, 16))
    story.append(Paragraph(
        "Qeyd: Real parollar heç vaxt saxlanmır. Nəticələr maarifləndirmə "
        "məqsədi daşıyır, fərdi cəzalandırma üçün deyil.", small))

    doc.build(story)
    return buf.getvalue()


def _kv_table(rows):
    t = Table(rows, colWidths=[45 * mm, 110 * mm])
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "DejaVu"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.grey),
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


def _metrics_table(rows):
    t = Table(rows, colWidths=[70 * mm, 40 * mm, 45 * mm])
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "DejaVu-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "DejaVu"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f1e3d")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("LINEBELOW", (0, 1), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
    ]))
    return t
