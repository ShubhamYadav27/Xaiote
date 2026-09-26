"""phase 4d remediation

Revision ID: 0450dd418bde
Revises: a8c9d0e1f2g3
Create Date: 2026-09-24 03:15:03.362972

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0450dd418bde"
down_revision: str | None = "a8c9d0e1f2g3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:

    # Update existing values deterministically
    op.execute(
        "UPDATE root_cause_assessments SET provenance = 'HUMAN_CONFIRMED' WHERE provenance = 'HUMAN_ASSERTED'"
    )

    # Add CHECK constraints
    op.execute(
        "ALTER TABLE root_cause_assessments ADD CONSTRAINT chk_assessment_provenance CHECK (provenance IN ('EXPLICIT', 'MODEL_DERIVED', 'HUMAN_CONFIRMED'))"
    )
    op.execute(
        "ALTER TABLE root_cause_assessments ADD CONSTRAINT chk_assessment_status CHECK (status IN ('CANDIDATE', 'NEEDS_REVIEW', 'CONFIRMED', 'REJECTED', 'SUPERSEDED'))"
    )


def downgrade() -> None:

    # Drop CHECK constraints
    op.execute(
        "ALTER TABLE root_cause_assessments DROP CONSTRAINT IF EXISTS chk_assessment_status"
    )
    op.execute(
        "ALTER TABLE root_cause_assessments DROP CONSTRAINT IF EXISTS chk_assessment_provenance"
    )

    # Revert if downgrading
    op.execute(
        "UPDATE root_cause_assessments SET provenance = 'HUMAN_ASSERTED' WHERE provenance = 'HUMAN_CONFIRMED'"
    )
