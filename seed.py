"""Local demo-data seeding (DESTRUCTIVE reset).

Run after migrations:  python seed.py

Clears existing demo rows and re-creates a fresh synthetic dataset. For the
deploy environment, use the idempotent `flask init-app` command instead.
"""
from app import create_app
from app.extensions import db
from app.services.demo_seed import seed_demo
from app.models import (Department, Participant, EmailTemplate, Campaign,
                        CampaignEvent, TrainingModule, QuizQuestion)


def run():
    seed_demo(reset=True)
    print("Demo data seeded:")
    print(f"  Departments:  {Department.query.count()}")
    print(f"  Participants: {Participant.query.count()}")
    print(f"  Templates:    {EmailTemplate.query.count()}")
    print(f"  Campaigns:    {Campaign.query.count()}")
    print(f"  Events:       {CampaignEvent.query.count()}")
    print(f"  Training:     {TrainingModule.query.count()} module(s), "
          f"{QuizQuestion.query.count()} question(s)")


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        run()
