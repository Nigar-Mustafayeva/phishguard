from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Email, Length, Optional


class ParticipantForm(FlaskForm):
    first_name = StringField("First name", validators=[DataRequired(), Length(max=80)])
    last_name = StringField("Last name", validators=[DataRequired(), Length(max=80)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=255)])
    department = StringField("Department", validators=[Optional(), Length(max=120)])
    submit = SubmitField("Save")


class CSVImportForm(FlaskForm):
    file = FileField("CSV file", validators=[
        FileRequired("Choose a file"),
        FileAllowed(["csv"], "Only .csv files are accepted"),
    ])
    submit = SubmitField("Import")
