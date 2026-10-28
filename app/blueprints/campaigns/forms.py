from flask_wtf import FlaskForm
from wtforms import (StringField, TextAreaField, SelectField,
                     SelectMultipleField, SubmitField)
from wtforms.validators import DataRequired, Length, Optional


class CampaignForm(FlaskForm):
    name = StringField("Campaign name", validators=[DataRequired(), Length(max=150)])
    description = TextAreaField("Description", validators=[Optional()])
    template_id = SelectField("Email template", coerce=int,
                              validators=[DataRequired(message="Choose a template")])
    participant_ids = SelectMultipleField("Participants", coerce=int)
    submit = SubmitField("Save")
