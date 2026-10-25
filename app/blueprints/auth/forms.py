from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, Length


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Şifrə", validators=[DataRequired(), Length(min=1)])
    remember = BooleanField("Məni xatırla")
    submit = SubmitField("Daxil ol")
