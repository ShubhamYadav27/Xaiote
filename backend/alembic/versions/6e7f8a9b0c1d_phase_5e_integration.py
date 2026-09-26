"""phase_5e_integration

Revision ID: 6e7f8a9b0c1d
Revises: 5d6e7f8a9b0c
Create Date: 2026-09-26 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '6e7f8a9b0c1d'
down_revision = '5d6e7f8a9b0c'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('external_integrations',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('company_id', sa.String(), nullable=False),
        sa.Column('plant_id', sa.String(), nullable=True),
        sa.Column('provider', sa.String(), nullable=False),
        sa.Column('adapter_type', sa.String(), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.Column('environment', sa.String(), nullable=False),
        sa.Column('credential_reference', sa.String(), nullable=False),
        sa.Column('credential_version', sa.Integer(), nullable=False),
        sa.Column('supported_operations', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('capability_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], name='fk_ext_int_company'),
        sa.ForeignKeyConstraint(['company_id', 'plant_id'], ['plants.company_id', 'plants.id'], name='fk_ext_int_composite_plant'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('company_id', 'plant_id', 'provider', 'environment', name='uq_integration_scope')
    )
    op.create_index(
        'uq_integration_scope_null_plant', 
        'external_integrations', 
        ['company_id', 'provider', 'environment'], 
        unique=True, 
        postgresql_where=sa.text('plant_id IS NULL')
    )

def downgrade():
    op.drop_index('uq_integration_scope_null_plant', table_name='external_integrations', postgresql_where=sa.text('plant_id IS NULL'))
    op.drop_table('external_integrations')
