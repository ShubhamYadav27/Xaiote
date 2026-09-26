"""phase 4d root cause intelligence

Revision ID: a8c9d0e1f2g3
Revises: a7c8d9e0f1g2
Create Date: 2026-09-23 22:20:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "a8c9d0e1f2g3"
down_revision = "a7c8d9e0f1g2"
branch_labels = None
depends_on = None


def upgrade():
    # 1. Add UniqueConstraints to parent tables for composite FKs
    op.create_unique_constraint(
        "uq_incident_company", "incidents", ["id", "company_id"]
    )
    op.create_unique_constraint(
        "uq_event_company", "manufacturing_events", ["id", "company_id"]
    )

    # 2. Create IncidentAnalysis table
    op.create_table(
        "incident_analyses",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("incident_id", sa.String(), nullable=False),
        sa.Column("company_id", sa.String(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("evidence_snapshot_hash", sa.String(), nullable=False),
        sa.Column("generation_fingerprint", sa.String(), nullable=False),
        sa.Column("request_idempotency_key", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["incident_id", "company_id"],
            ["incidents.id", "incidents.company_id"],
            name="fk_analysis_incident_company",
        ),
    )
    op.create_index(
        op.f("ix_incident_analyses_company_id"),
        "incident_analyses",
        ["company_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_incident_analyses_incident_id"),
        "incident_analyses",
        ["incident_id"],
        unique=False,
    )
    op.create_unique_constraint(
        "uq_analysis_company", "incident_analyses", ["id", "company_id"]
    )

    # 3. Create RootCauseAssessment table
    op.create_table(
        "root_cause_assessments",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("analysis_id", sa.String(), nullable=False),
        sa.Column("company_id", sa.String(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("explanation", sa.String(), nullable=False),
        sa.Column("provenance", sa.String(), nullable=False),
        sa.Column("model_confidence", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["analysis_id", "company_id"],
            ["incident_analyses.id", "incident_analyses.company_id"],
            name="fk_assessment_analysis_company",
        ),
    )
    op.create_index(
        op.f("ix_root_cause_assessments_analysis_id"),
        "root_cause_assessments",
        ["analysis_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_root_cause_assessments_company_id"),
        "root_cause_assessments",
        ["company_id"],
        unique=False,
    )
    op.create_unique_constraint(
        "uq_assessment_company", "root_cause_assessments", ["id", "company_id"]
    )

    # 4. Create AssessmentEvidenceLink table
    op.create_table(
        "assessment_evidence_links",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("assessment_id", sa.String(), nullable=False),
        sa.Column("event_id", sa.String(), nullable=False),
        sa.Column("company_id", sa.String(), nullable=False),
        sa.Column("relationship_type", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["assessment_id", "company_id"],
            ["root_cause_assessments.id", "root_cause_assessments.company_id"],
            name="fk_link_assessment_company",
        ),
        sa.ForeignKeyConstraint(
            ["event_id", "company_id"],
            ["manufacturing_events.id", "manufacturing_events.company_id"],
            name="fk_link_event_company",
        ),
    )
    op.create_index(
        op.f("ix_assessment_evidence_links_assessment_id"),
        "assessment_evidence_links",
        ["assessment_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_assessment_evidence_links_company_id"),
        "assessment_evidence_links",
        ["company_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_assessment_evidence_links_event_id"),
        "assessment_evidence_links",
        ["event_id"],
        unique=False,
    )

    # 5. Create AssessmentDecisionHistory table
    op.create_table(
        "assessment_decision_history",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("assessment_id", sa.String(), nullable=False),
        sa.Column("company_id", sa.String(), nullable=False),
        sa.Column("actor_id", sa.String(), nullable=False),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("previous_state", sa.String(), nullable=True),
        sa.Column("new_state", sa.String(), nullable=True),
        sa.Column("reason", sa.String(), nullable=True),
        sa.Column("analysis_version", sa.Integer(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["assessment_id", "company_id"],
            ["root_cause_assessments.id", "root_cause_assessments.company_id"],
            name="fk_history_assessment_company",
        ),
        sa.ForeignKeyConstraint(
            ["actor_id"],
            ["users.id"],
        ),
    )
    op.create_index(
        op.f("ix_assessment_decision_history_actor_id"),
        "assessment_decision_history",
        ["actor_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_assessment_decision_history_assessment_id"),
        "assessment_decision_history",
        ["assessment_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_assessment_decision_history_company_id"),
        "assessment_decision_history",
        ["company_id"],
        unique=False,
    )


def downgrade():
    op.drop_index(
        op.f("ix_assessment_decision_history_company_id"),
        table_name="assessment_decision_history",
    )
    op.drop_index(
        op.f("ix_assessment_decision_history_assessment_id"),
        table_name="assessment_decision_history",
    )
    op.drop_index(
        op.f("ix_assessment_decision_history_actor_id"),
        table_name="assessment_decision_history",
    )
    op.drop_table("assessment_decision_history")

    op.drop_index(
        op.f("ix_assessment_evidence_links_event_id"),
        table_name="assessment_evidence_links",
    )
    op.drop_index(
        op.f("ix_assessment_evidence_links_company_id"),
        table_name="assessment_evidence_links",
    )
    op.drop_index(
        op.f("ix_assessment_evidence_links_assessment_id"),
        table_name="assessment_evidence_links",
    )
    op.drop_table("assessment_evidence_links")

    op.drop_constraint(
        "uq_assessment_company", "root_cause_assessments", type_="unique"
    )
    op.drop_index(
        op.f("ix_root_cause_assessments_company_id"),
        table_name="root_cause_assessments",
    )
    op.drop_index(
        op.f("ix_root_cause_assessments_analysis_id"),
        table_name="root_cause_assessments",
    )
    op.drop_table("root_cause_assessments")

    op.drop_constraint("uq_analysis_company", "incident_analyses", type_="unique")
    op.drop_index(
        op.f("ix_incident_analyses_incident_id"), table_name="incident_analyses"
    )
    op.drop_index(
        op.f("ix_incident_analyses_company_id"), table_name="incident_analyses"
    )
    op.drop_table("incident_analyses")

    op.drop_constraint("uq_event_company", "manufacturing_events", type_="unique")
    op.drop_constraint("uq_incident_company", "incidents", type_="unique")
