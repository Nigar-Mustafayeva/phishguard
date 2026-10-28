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


# Assignment lifecycle
ASSIGN_ASSIGNED = "assigned"    # created, email not (yet) delivered
ASSIGN_SENT = "sent"            # invitation email sent
ASSIGN_OPENED = "opened"        # participant opened the training link
ASSIGN_COMPLETED = "completed"  # participant finished the quiz


class TrainingAssignment(db.Model):
    """A training module assigned to one participant, reached by a private link.

    The token is the only credential for the public training page, so it is
    long and random. No passwords or personal answers are stored — only the
    quiz score.
    """
    __tablename__ = "training_assignments"

    id = db.Column(db.Integer, primary_key=True)
    participant_id = db.Column(
        db.Integer, db.ForeignKey("participants.id", ondelete="CASCADE"),
        nullable=False, index=True)
    module_id = db.Column(
        db.Integer, db.ForeignKey("training_modules.id", ondelete="CASCADE"),
        nullable=False, index=True)
    token = db.Column(db.String(64), unique=True, nullable=False, index=True)
    reason = db.Column(db.Text, nullable=True)          # why it was assigned
    source = db.Column(db.String(10), nullable=False, default="rules")  # ai | rules
    status = db.Column(db.String(12), nullable=False, default=ASSIGN_ASSIGNED)
    risk_score = db.Column(db.Integer, nullable=True)   # score at assignment time
    email_error = db.Column(db.Text, nullable=True)
    score = db.Column(db.Integer, nullable=True)
    total = db.Column(db.Integer, nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    sent_at = db.Column(db.DateTime, nullable=True)
    opened_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)

    participant = db.relationship("Participant")
    module = db.relationship("TrainingModule")

    def __repr__(self) -> str:
        return f"<TrainingAssignment p={self.participant_id} m={self.module_id} {self.status}>"
