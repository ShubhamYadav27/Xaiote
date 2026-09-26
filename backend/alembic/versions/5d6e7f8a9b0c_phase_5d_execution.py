"""phase_5d_execution_gateway

Revision ID: 5d6e7f8a9b0c
Revises: 4c5d6e7f8a9b
Create Date: 2026-09-26 15:35:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '5d6e7f8a9b0c'
down_revision = '4c5d6e7f8a9b'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('execution_attempts',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('company_id', sa.String(), nullable=False),
        sa.Column('action_instance_id', sa.String(), nullable=False),
        sa.Column('attempt_number', sa.Integer(), nullable=False),
        sa.Column('downstream_idempotency_key', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('provider_type', sa.String(), nullable=False),
        sa.Column('worker_id', sa.String(), nullable=True),
        sa.Column('lease_expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('external_correlation_id', sa.String(), nullable=True),
        sa.Column('error_payload', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['action_instance_id'], ['action_instances.id'], name='fk_exec_attempt_action'),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], name='fk_exec_attempt_company'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('action_instance_id', 'attempt_number', name='uq_execution_attempt_number'),
        sa.UniqueConstraint('company_id', 'downstream_idempotency_key', name='uq_execution_idempotency_key')
    )

def downgrade():
    op.drop_table('execution_attempts')
