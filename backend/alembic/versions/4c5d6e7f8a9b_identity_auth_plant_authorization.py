"""identity_auth_plant_authorization

Revision ID: 4c5d6e7f8a9b
Revises: 3b4c5d6e7f8a
Create Date: 2026-09-25 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '4c5d6e7f8a9b'
down_revision = '3b4c5d6e7f8a'
branch_labels = None
depends_on = None

def upgrade():
    # 1. Add Unique Constraints to Phase 1 tables
    op.create_unique_constraint('uq_users_company_id_id', 'users', ['company_id', 'id'])
    op.create_unique_constraint('uq_plants_company_id_id', 'plants', ['company_id', 'id'])
    
    # 2. Create user_plants association table
    op.create_table('user_plants',
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('plant_id', sa.String(), nullable=False),
        sa.Column('company_id', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id', 'plant_id'], ['plants.company_id', 'plants.id'], name='fk_user_plants_plant_company'),
        sa.ForeignKeyConstraint(['company_id', 'user_id'], ['users.company_id', 'users.id'], name='fk_user_plants_user_company'),
        sa.PrimaryKeyConstraint('user_id', 'plant_id'),
        sa.UniqueConstraint('user_id', 'plant_id', name='uq_user_plants_user_id_plant_id')
    )

def downgrade():
    # 1. Drop user_plants table
    op.drop_table('user_plants')
    
    # 2. Drop unique constraints from Phase 1 tables
    op.drop_constraint('uq_plants_company_id_id', 'plants', type_='unique')
    op.drop_constraint('uq_users_company_id_id', 'users', type_='unique')
