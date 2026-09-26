"""phase_5b_recommendations

Revision ID: 3b4c5d6e7f8a
Revises: 2a3b4c5d6e7f
Create Date: 2026-09-25 11:27:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '3b4c5d6e7f8a'
down_revision = '2a3b4c5d6e7f'
branch_labels = None
depends_on = None


def upgrade():
    # action_recommendations table
    op.create_table('action_recommendations',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('company_id', sa.String(), nullable=False),
        sa.Column('plant_id', sa.String(), nullable=True),
        sa.Column('generation_request_id', sa.String(), nullable=False),
        sa.Column('context_hash', sa.String(), nullable=False),
        sa.Column('prompt_hash', sa.String(), nullable=True),
        sa.Column('schema_version', sa.String(), nullable=True),
        sa.Column('model_provider_id', sa.String(), nullable=True),
        sa.Column('action_type', sa.String(), nullable=False),
        sa.Column('target_work_order_id', sa.String(), nullable=True),
        sa.Column('target_machine_id', sa.String(), nullable=True),
        sa.Column('target_product_id', sa.String(), nullable=True),
        sa.Column('rationale', sa.String(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('action_parameters', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('policy_id', sa.String(), nullable=False),
        sa.Column('policy_version', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='PROPOSED'),
        sa.Column('stale_reason', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
        sa.ForeignKeyConstraint(['plant_id'], ['plants.id'], ),
        sa.ForeignKeyConstraint(['target_machine_id'], ['machines.id'], ),
        sa.ForeignKeyConstraint(['target_product_id'], ['products.id'], ),
        sa.ForeignKeyConstraint(['target_work_order_id'], ['work_orders.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('company_id', 'generation_request_id', name='uq_recommendation_generation_request'),
        sa.CheckConstraint(
            '(target_work_order_id IS NOT NULL)::int + (target_machine_id IS NOT NULL)::int + (target_product_id IS NOT NULL)::int = 1',
            name='ck_recommendation_target_xor'
        )
    )

    # recommendation_evidence_links table
    op.create_table('recommendation_evidence_links',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('recommendation_id', sa.String(), nullable=False),
        sa.Column('company_id', sa.String(), nullable=False),
        sa.Column('evidence_alert_id', sa.String(), nullable=True),
        sa.Column('evidence_risk_history_id', sa.String(), nullable=True),
        sa.Column('evidence_root_cause_assessment_id', sa.String(), nullable=True),
        sa.Column('evidence_manufacturing_event_id', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
        sa.ForeignKeyConstraint(['evidence_alert_id'], ['alert_instances.id'], ),
        sa.ForeignKeyConstraint(['evidence_manufacturing_event_id'], ['manufacturing_events.id'], ),
        sa.ForeignKeyConstraint(['evidence_risk_history_id'], ['work_order_risk_history.id'], ),
        sa.ForeignKeyConstraint(['evidence_root_cause_assessment_id'], ['root_cause_assessments.id'], ),
        sa.ForeignKeyConstraint(['recommendation_id'], ['action_recommendations.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint(
            '(evidence_alert_id IS NOT NULL)::int + (evidence_risk_history_id IS NOT NULL)::int + (evidence_root_cause_assessment_id IS NOT NULL)::int + (evidence_manufacturing_event_id IS NOT NULL)::int = 1',
            name='ck_recommendation_evidence_xor'
        )
    )

    # recommendation_conversions table
    op.create_table('recommendation_conversions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('company_id', sa.String(), nullable=False),
        sa.Column('recommendation_id', sa.String(), nullable=False),
        sa.Column('action_instance_id', sa.String(), nullable=False),
        sa.Column('conversion_idempotency_key', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['action_instance_id'], ['action_instances.id'], ),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
        sa.ForeignKeyConstraint(['recommendation_id'], ['action_recommendations.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('action_instance_id', name='uq_conversion_action_instance'),
        sa.UniqueConstraint('conversion_idempotency_key', name='uq_conversion_idempotency_key'),
        sa.UniqueConstraint('recommendation_id', name='uq_conversion_recommendation')
    )


def downgrade():
    op.drop_table('recommendation_conversions')
    op.drop_table('recommendation_evidence_links')
    op.drop_table('action_recommendations')
