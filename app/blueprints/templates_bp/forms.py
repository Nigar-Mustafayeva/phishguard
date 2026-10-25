from flask_wtf import FlaskForm
from wtforms import (StringField, TextAreaField, SelectField, SubmitField)
from wtforms.validators import DataRequired, Email, Length

CATEGORY_CHOICES = [
    ("credential", "Credential harvest (şifrə)"),
    ("update", "Proqram/update bildirişi"),
    ("hr", "HR / maaş"),
    ("delivery", "Kargo / çatdırılma"),
    ("other", "Digər"),
]


class TemplateForm(FlaskForm):
    name = StringField("Şablon adı", validators=[DataRequired(), Length(max=150)])
    subject = StringField("Mövzu (subject)", validators=[DataRequired(), Length(max=255)])
    sender_name = StringField("Göndərən adı", validators=[DataRequired(), Length(max=120)])
    sender_email = StringField("Göndərən email", validators=[DataRequired(), Email(), Length(max=255)])
    category = SelectField("Kateqoriya", choices=CATEGORY_CHOICES)
    html_body = TextAreaField("HTML məzmun", validators=[DataRequired()])
    submit = SubmitField("Yadda saxla")


class TestEmailForm(FlaskForm):
    recipient = StringField("Test alıcı email", validators=[DataRequired(), Email()])
    submit = SubmitField("Test email göndər")
