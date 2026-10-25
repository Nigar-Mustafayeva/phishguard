from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Email, Length, Optional


class ParticipantForm(FlaskForm):
    first_name = StringField("Ad", validators=[DataRequired(), Length(max=80)])
    last_name = StringField("Soyad", validators=[DataRequired(), Length(max=80)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=255)])
    department = StringField("Şöbə", validators=[Optional(), Length(max=120)])
    submit = SubmitField("Yadda saxla")


class CSVImportForm(FlaskForm):
    file = FileField("CSV faylı", validators=[
        FileRequired("Fayl seçin"),
        FileAllowed(["csv"], "Yalnız .csv faylı qəbul olunur"),
    ])
    submit = SubmitField("İmport et")
