"""phase_5a_actions

Revision ID: 2a3b4c5d6e7f
Revises: 16cea21c9002
Create Date: 2026-09-25 10:55:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2a3b4c5d6e7f'
down_revision = '16cea21c9002'
branch_labels = None
depends_on = None


def upgrade():
    # action_policies table
    op.create_table('action_policies',
        sa.Column('pk', sa.String(), nullable=False),
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('approval_level', sa.Integer(), nullable=False, server_default='2'),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
        sa.PrimaryKeyConstraint('pk'),
        sa.UniqueConstraint('company_id', 'id', 'version', name='uq_action_policy_identity')
    )

    # action_instances table
    op.create_table('action_instances',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('company_id', sa.String(), nullable=False),
        sa.Column('plant_id', sa.String(), nullable=True),
        sa.Column('policy_id', sa.String(), nullable=False),
        sa.Column('policy_version', sa.Integer(), nullable=False),
        sa.Column('action_type', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='PROPOSED'),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('target_work_order_id', sa.String(), nullable=True),
        sa.Column('target_machine_id', sa.String(), nullable=True),
        sa.Column('target_product_id', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['company_id', 'policy_id', 'policy_version'], ['action_policies.company_id', 'action_policies.id', 'action_policies.version'], name='fk_action_instance_policy'),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
        sa.ForeignKeyConstraint(['plant_id'], ['plants.id'], ),
        sa.ForeignKeyConstraint(['target_machine_id'], ['machines.id'], ),
        sa.ForeignKeyConstraint(['target_product_id'], ['products.id'], ),
        sa.ForeignKeyConstraint(['target_work_order_id'], ['work_orders.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint(
            '(target_work_order_id IS NOT NULL)::int + (target_machine_id IS NOT NULL)::int + (target_product_id IS NOT NULL)::int = 1',
            name='ck_action_instance_target_xor'
        )
    )

    # action_evidence_links table
    op.create_table('action_evidence_links',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('action_instance_id', sa.String(), nullable=False),
        sa.Column('company_id', sa.String(), nullable=False),
        sa.Column('evidence_alert_id', sa.String(), nullable=True),
        sa.Column('evidence_risk_history_id', sa.String(), nullable=True),
        sa.Column('evidence_root_cause_assessment_id', sa.String(), nullable=True),
        sa.Column('evidence_manufacturing_event_id', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['action_instance_id'], ['action_instances.id'], ),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
        sa.ForeignKeyConstraint(['evidence_alert_id'], ['alert_instances.id'], ),
        sa.ForeignKeyConstraint(['evidence_manufacturing_event_id'], ['manufacturing_events.id'], ),
        sa.ForeignKeyConstraint(['evidence_risk_history_id'], ['work_order_risk_history.id'], ),
        sa.ForeignKeyConstraint(['evidence_root_cause_assessment_id'], ['root_cause_assessments.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint(
            '(evidence_alert_id IS NOT NULL)::int + (evidence_risk_history_id IS NOT NULL)::int + (evidence_root_cause_assessment_id IS NOT NULL)::int + (evidence_manufacturing_event_id IS NOT NULL)::int = 1',
            name='ck_action_evidence_xor'
        )
    )

    # action_history table
    op.create_table('action_history',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('action_id', sa.String(), nullable=False),
        sa.Column('company_id', sa.String(), nullable=False),
        sa.Column('previous_state', sa.String(), nullable=False),
        sa.Column('new_state', sa.String(), nullable=False),
        sa.Column('actor_id', sa.String(), nullable=False),
        sa.Column('actor_type', sa.String(), nullable=False),
        sa.Column('reason', sa.String(), nullable=True),
        sa.Column('policy_id', sa.String(), nullable=False),
        sa.Column('policy_version', sa.Integer(), nullable=False),
        sa.Column('action_version', sa.Integer(), nullable=False),
        sa.Column('correlation_id', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['action_id'], ['action_instances.id'], ),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # action_outcomes table
    op.create_table('action_outcomes',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('action_id', sa.String(), nullable=False),
        sa.Column('company_id', sa.String(), nullable=False),
        sa.Column('outcome_state', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['action_id'], ['action_instances.id'], ),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('action_outcomes')
    op.drop_table('action_history')
    op.drop_table('action_evidence_links')
    op.drop_table('action_instances')
    op.drop_table('action_policies')
