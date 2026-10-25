"""Custom Flask CLI commands.

Usage:
    flask create-admin      # create the first administrator (prompts for password)
"""
import click

from app.extensions import db
from app.models import User, ROLE_ADMIN


def register_commands(app):
    @app.cli.command("create-admin")
    @click.option("--name", prompt="Ad", help="Admin's display name")
    @click.option("--email", prompt="Email", help="Login email")
    @click.option("--password", prompt="Şifrə", hide_input=True,
                  confirmation_prompt=True, help="Admin password")
    def create_admin(name, email, password):
        """Create an administrator account (password is never stored in code)."""
        email = email.lower().strip()
        if User.query.filter_by(email=email).first():
            click.echo(f"Xəta: {email} artıq mövcuddur.")
            return
        if len(password) < 8:
            click.echo("Xəta: şifrə ən az 8 simvol olmalıdır.")
            return
        user = User(name=name, email=email, role=ROLE_ADMIN)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        click.echo(f"Admin yaradıldı: {email}")

    @app.cli.command("seed-training")
    def seed_training_cmd():
        """Add training modules (idempotent — does not delete existing data)."""
        from app.services.training_content import seed_training
        created = seed_training()
        click.echo(f"{created} yeni təlim modulu əlavə olundu.")

    @app.cli.command("init-app")
    def init_app_cmd():
        """Idempotent deploy bootstrap: admin from env, training, demo data.

        Safe to run on every deploy/restart. Reads optional env vars:
          ADMIN_EMAIL, ADMIN_PASSWORD  -> create first admin if none exists.
          SEED_DEMO=true               -> seed synthetic demo data if empty.
        """
        import os
        # 1. First admin from environment (never hard-coded).
        if User.query.count() == 0:
            email = os.environ.get("ADMIN_EMAIL", "").lower().strip()
            password = os.environ.get("ADMIN_PASSWORD", "")
            if email and len(password) >= 8:
                u = User(name=os.environ.get("ADMIN_NAME", "Admin"),
                         email=email, role=ROLE_ADMIN)
                u.set_password(password)
                db.session.add(u)
                db.session.commit()
                click.echo(f"Admin yaradıldı: {email}")
            else:
                click.echo("Admin yaradılmadı (ADMIN_EMAIL/ADMIN_PASSWORD təyin edilməyib).")

        # 2. Demo data (only if empty and enabled).
        if os.environ.get("SEED_DEMO", "true").lower() == "true":
            from app.services.demo_seed import seed_demo
            seeded = seed_demo(reset=False)
            click.echo("Demo data əlavə olundu." if seeded
                       else "Demo data artıq mövcuddur (ötürüldü).")
        else:
            from app.services.training_content import seed_training
            seed_training()
        click.echo("init-app tamamlandı.")
