from flask_wtf import FlaskForm
from wtforms import (StringField, TextAreaField, SelectField, SubmitField)
from wtforms.validators import DataRequired, Email, Length

CATEGORY_CHOICES = [
    ("credential", "Credential harvest (password)"),
    ("update", "Software update notice"),
    ("hr", "HR / payroll"),
    ("delivery", "Parcel / delivery"),
    ("other", "Other"),
]


class TemplateForm(FlaskForm):
    name = StringField("Template name", validators=[DataRequired(), Length(max=150)])
    subject = StringField("Subject", validators=[DataRequired(), Length(max=255)])
    sender_name = StringField("Sender name", validators=[DataRequired(), Length(max=120)])
    sender_email = StringField("Sender email", validators=[DataRequired(), Email(), Length(max=255)])
    category = SelectField("Category", choices=CATEGORY_CHOICES)
    html_body = TextAreaField("HTML body", validators=[DataRequired()])
    submit = SubmitField("Save")


class TestEmailForm(FlaskForm):
    recipient = StringField("Test recipient email", validators=[DataRequired(), Email()])
    submit = SubmitField("Send test email")
