"""pg_trgm_indexes

Revision ID: 7f8a9b0c1d2e
Revises: 6e7f8a9b0c1d
Create Date: 2026-09-26 16:36:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '7f8a9b0c1d2e'
down_revision = '6e7f8a9b0c1d'
branch_labels = None
depends_on = None

def upgrade():
    # Adding GIN indexes for pg_trgm fuzzy matching on high-volume masters
    op.execute("CREATE INDEX IF NOT EXISTS ix_machines_name_trgm ON machines USING gin (name gin_trgm_ops)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_work_orders_order_number_trgm ON work_orders USING gin (order_number gin_trgm_ops)")

def downgrade():
    op.execute("DROP INDEX IF EXISTS ix_work_orders_order_number_trgm")
    op.execute("DROP INDEX IF EXISTS ix_machines_name_trgm")
