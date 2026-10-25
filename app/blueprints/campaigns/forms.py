from flask_wtf import FlaskForm
from wtforms import (StringField, TextAreaField, SelectField,
                     SelectMultipleField, SubmitField)
from wtforms.validators import DataRequired, Length, Optional


class CampaignForm(FlaskForm):
    name = StringField("Kampaniya adı", validators=[DataRequired(), Length(max=150)])
    description = TextAreaField("Təsvir", validators=[Optional()])
    template_id = SelectField("Email şablonu", coerce=int,
                              validators=[DataRequired(message="Şablon seçin")])
    participant_ids = SelectMultipleField("İştirakçılar", coerce=int)
    submit = SubmitField("Yadda saxla")
