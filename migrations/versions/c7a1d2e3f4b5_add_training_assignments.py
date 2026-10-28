"""add training_assignments

Revision ID: c7a1d2e3f4b5
Revises: bc4fe404abea
Create Date: 2026-10-28 21:40:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c7a1d2e3f4b5'
down_revision = 'bc4fe404abea'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'training_assignments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('participant_id', sa.Integer(), nullable=False),
        sa.Column('module_id', sa.Integer(), nullable=False),
        sa.Column('token', sa.String(length=64), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('source', sa.String(length=10), nullable=False),
        sa.Column('status', sa.String(length=12), nullable=False),
        sa.Column('risk_score', sa.Integer(), nullable=True),
        sa.Column('email_error', sa.Text(), nullable=True),
        sa.Column('score', sa.Integer(), nullable=True),
        sa.Column('total', sa.Integer(), nullable=True),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.Column('opened_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id']),
        sa.ForeignKeyConstraint(['module_id'], ['training_modules.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['participant_id'], ['participants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('training_assignments', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_training_assignments_participant_id'), ['participant_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_training_assignments_module_id'), ['module_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_training_assignments_token'), ['token'], unique=True)


def downgrade():
    with op.batch_alter_table('training_assignments', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_training_assignments_token'))
        batch_op.drop_index(batch_op.f('ix_training_assignments_module_id'))
        batch_op.drop_index(batch_op.f('ix_training_assignments_participant_id'))
    op.drop_table('training_assignments')
