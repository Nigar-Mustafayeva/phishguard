from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, SubmitField
from wtforms.validators import DataRequired, Email, Length

from app.models import ROLE_ADMIN, ROLE_ANALYST


class UserForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=120)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=255)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8)])
    role = SelectField("Role", choices=[(ROLE_ANALYST, "Analyst"), (ROLE_ADMIN, "Admin")])
    submit = SubmitField("Create user")
