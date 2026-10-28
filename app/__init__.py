"""Application factory.

create_app() builds and configures the Flask app. This pattern keeps the
app easy to test and lets us register modules (blueprints) one by one.
"""
import os
from datetime import date

from flask import Flask, render_template, redirect, url_for, request
from flask_login import current_user

from .config import config_by_name
from .extensions import db, migrate, login_manager, csrf


def create_app(config_name: str | None = None, test_config: dict | None = None) -> Flask:
    config_name = config_name or os.environ.get("FLASK_CONFIG", "development")

    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])

    # Test overrides must be applied BEFORE extensions bind to the config
    # (e.g. the database engine reads SQLALCHEMY_DATABASE_URI at init time).
    if test_config:
        app.config.update(test_config)

    # Initialise extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    # Import models so SQLAlchemy/Flask-Migrate can see every table.
    from app import models  # noqa: F401

    _register_blueprints(app)
    _register_misc(app)

    from app.commands import register_commands
    register_commands(app)

    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User
        return db.session.get(User, int(user_id))

    # Every page requires login except the public landing page, the login
    # page, static files and health.
    @app.before_request
    def require_login():
        if request.endpoint in ("landing.index", "auth.login", "static", "health"):
            return
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login", next=request.path))

    return app


def _register_blueprints(app: Flask) -> None:
    from .blueprints.landing.routes import landing_bp
    from .blueprints.auth.routes import auth_bp
    from .blueprints.dashboard.routes import dashboard_bp
    from .blueprints.campaigns.routes import campaigns_bp
    from .blueprints.templates_bp.routes import templates_bp
    from .blueprints.participants.routes import participants_bp
    from .blueprints.results.routes import results_bp
    from .blueprints.training.routes import training_bp
    from .blueprints.reports.routes import reports_bp
    from .blueprints.integration.routes import integration_bp
    from .blueprints.settings.routes import settings_bp
    from .blueprints.risk.routes import risk_bp

    app.register_blueprint(landing_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(campaigns_bp)
    app.register_blueprint(templates_bp)
    app.register_blueprint(participants_bp)
    app.register_blueprint(results_bp)
    app.register_blueprint(training_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(integration_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(risk_bp)


def _register_misc(app: Flask) -> None:
    @app.context_processor
    def inject_globals():
        from app.services.gophish_service import demo_mode_active
        return {"demo_mode": demo_mode_active(), "today": date.today()}

    @app.route("/health")
    def health():
        """Health-check endpoint used by Render and uptime monitors."""
        return {"status": "ok"}, 200

    @app.errorhandler(403)
    def forbidden(_e):
        return render_template("shared/403.html"), 403

    @app.errorhandler(404)
    def not_found(_e):
        return render_template("shared/404.html"), 404
