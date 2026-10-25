"""Security-awareness training modules, quiz questions and attempts."""
from datetime import datetime

from app.extensions import db


class TrainingModule(db.Model):
    __tablename__ = "training_modules"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(120), unique=True, nullable=False, index=True)
    content = db.Column(db.Text, nullable=False, default="")
    order_index = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    questions = db.relationship(
        "QuizQuestion", back_populates="module",
        cascade="all, delete-orphan", order_by="QuizQuestion.id",
    )

    def __repr__(self) -> str:
        return f"<TrainingModule {self.slug}>"


class QuizQuestion(db.Model):
    __tablename__ = "quiz_questions"

    id = db.Column(db.Integer, primary_key=True)
    module_id = db.Column(
        db.Integer, db.ForeignKey("training_modules.id"), nullable=False, index=True
    )
    question = db.Column(db.Text, nullable=False)
    option_a = db.Column(db.String(255), nullable=False)
    option_b = db.Column(db.String(255), nullable=False)
    option_c = db.Column(db.String(255), nullable=True)
    option_d = db.Column(db.String(255), nullable=True)
    correct_option = db.Column(db.String(1), nullable=False)  # "A" | "B" | "C" | "D"
    explanation = db.Column(db.Text, nullable=True)

    module = db.relationship("TrainingModule", back_populates="questions")

    def __repr__(self) -> str:
        return f"<QuizQuestion {self.id} m={self.module_id}>"


class QuizAttempt(db.Model):
    __tablename__ = "quiz_attempts"

    id = db.Column(db.Integer, primary_key=True)
    module_id = db.Column(
        db.Integer, db.ForeignKey("training_modules.id"), nullable=False, index=True
    )
    participant_id = db.Column(
        db.Integer, db.ForeignKey("participants.id"), nullable=True, index=True
    )
    score = db.Column(db.Integer, nullable=False, default=0)
    total = db.Column(db.Integer, nullable=False, default=0)
    completed_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    module = db.relationship("TrainingModule")
    participant = db.relationship("Participant")

    def __repr__(self) -> str:
        return f"<QuizAttempt {self.score}/{self.total}>"
