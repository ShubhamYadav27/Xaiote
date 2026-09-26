"""Phase 4C Incident Correlation

Revision ID: a7c8d9e0f1g2
Revises: 65d4578441d5
Create Date: 2026-09-23 17:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a7c8d9e0f1g2"
down_revision: str | None = "65d4578441d5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create incidents table
    op.create_table(
        "incidents",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("company_id", sa.String(), nullable=False),
        sa.Column("plant_id", sa.String(), nullable=False),
        sa.Column("machine_id", sa.String(), nullable=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="ACTIVE"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
        ),
        sa.ForeignKeyConstraint(
            ["plant_id"],
            ["plants.id"],
        ),
        sa.ForeignKeyConstraint(
            ["machine_id"],
            ["machines.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_incidents_company_id"), "incidents", ["company_id"], unique=False
    )
    op.create_index(
        op.f("ix_incidents_plant_id"), "incidents", ["plant_id"], unique=False
    )
    op.create_index(
        op.f("ix_incidents_machine_id"), "incidents", ["machine_id"], unique=False
    )

    # Create incident_events table
    op.create_table(
        "incident_events",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("incident_id", sa.String(), nullable=False),
        sa.Column("event_id", sa.String(), nullable=False),
        sa.Column("link_state", sa.String(), nullable=False, server_default="LINKED"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["incident_id"],
            ["incidents.id"],
        ),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["manufacturing_events.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("incident_id", "event_id", name="uq_incident_event"),
    )
    op.create_index(
        op.f("ix_incident_events_incident_id"),
        "incident_events",
        ["incident_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_incident_events_event_id"),
        "incident_events",
        ["event_id"],
        unique=False,
    )

    # Create incident_decision_history table
    op.create_table(
        "incident_decision_history",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("incident_id", sa.String(), nullable=False),
        sa.Column("actor_id", sa.String(), nullable=True),
        sa.Column("event_id", sa.String(), nullable=True),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("previous_state", sa.String(), nullable=True),
        sa.Column("new_state", sa.String(), nullable=True),
        sa.Column("reason", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["incident_id"],
            ["incidents.id"],
        ),
        sa.ForeignKeyConstraint(
            ["actor_id"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["manufacturing_events.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_incident_decision_history_incident_id"),
        "incident_decision_history",
        ["incident_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_incident_decision_history_actor_id"),
        "incident_decision_history",
        ["actor_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_incident_decision_history_event_id"),
        "incident_decision_history",
        ["event_id"],
        unique=False,
    )

    # Add incident_id FK to production_order_impacts (nullable for legacy records)
    op.add_column(
        "production_order_impacts", sa.Column("incident_id", sa.String(), nullable=True)
    )
    op.create_foreign_key(
        "fk_impact_incident_id",
        "production_order_impacts",
        "incidents",
        ["incident_id"],
        ["id"],
    )
    op.create_index(
        op.f("ix_production_order_impacts_incident_id"),
        "production_order_impacts",
        ["incident_id"],
        unique=False,
    )

    # Add new trigger types to risktriggertype enum
    op.execute("ALTER TYPE risktriggertype ADD VALUE IF NOT EXISTS 'INCIDENT_RESOLVED'")
    op.execute("ALTER TYPE risktriggertype ADD VALUE IF NOT EXISTS 'EVENT_UNLINKED'")


def downgrade() -> None:
    # Remove incident_id from production_order_impacts
    op.drop_index(
        op.f("ix_production_order_impacts_incident_id"),
        table_name="production_order_impacts",
    )
    op.drop_constraint(
        "fk_impact_incident_id", "production_order_impacts", type_="foreignkey"
    )
    op.drop_column("production_order_impacts", "incident_id")

    # Drop incident_decision_history
    op.drop_index(
        op.f("ix_incident_decision_history_event_id"),
        table_name="incident_decision_history",
    )
    op.drop_index(
        op.f("ix_incident_decision_history_actor_id"),
        table_name="incident_decision_history",
    )
    op.drop_index(
        op.f("ix_incident_decision_history_incident_id"),
        table_name="incident_decision_history",
    )
    op.drop_table("incident_decision_history")

    # Drop incident_events
    op.drop_index(op.f("ix_incident_events_event_id"), table_name="incident_events")
    op.drop_index(op.f("ix_incident_events_incident_id"), table_name="incident_events")
    op.drop_table("incident_events")

    # Drop incidents
    op.drop_index(op.f("ix_incidents_machine_id"), table_name="incidents")
    op.drop_index(op.f("ix_incidents_plant_id"), table_name="incidents")
    op.drop_index(op.f("ix_incidents_company_id"), table_name="incidents")
    op.drop_table("incidents")

    # Note: PostgreSQL ENUM values cannot be removed in downgrade.
    # The extra enum values INCIDENT_RESOLVED and EVENT_UNLINKED will remain
    # but are harmless.
