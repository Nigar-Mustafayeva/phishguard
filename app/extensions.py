"""Flask extensions created here, initialised in the app factory.

Keeping them in a separate module avoids circular imports.
"""
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_wtf import CSRFProtect

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()

# Where @login_required redirects when a user is not logged in.
# The "auth" blueprint is added in Stage 3.
login_manager.login_view = "auth.login"
login_manager.login_message_category = "warning"
