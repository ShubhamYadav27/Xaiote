"""Phase 3B WhatsApp webhook integration

Revision ID: a1b2c3d4e5f6
Revises: 6e50084c4532
Create Date: 2026-09-18 16:10:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "6e50084c4532"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # WhatsApp Integration table
    op.create_table(
        "whatsapp_integrations",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("company_id", sa.String(), nullable=False),
        sa.Column("external_business_account_id", sa.String(), nullable=False),
        sa.Column("phone_number_id", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("app_secret_encrypted", sa.String(), nullable=False),
        sa.Column("access_token_encrypted", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id"),
        sa.UniqueConstraint("phone_number_id"),
    )

    # Authorized Sender table
    op.create_table(
        "authorized_senders",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("company_id", sa.String(), nullable=False),
        sa.Column("phone_number", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # Add new columns to communication_attachments for media state machine
    op.add_column(
        "communication_attachments",
        sa.Column("status", sa.String(), nullable=True),
    )
    op.add_column(
        "communication_attachments",
        sa.Column("provider_media_id", sa.String(), nullable=True),
    )
    op.add_column(
        "communication_attachments",
        sa.Column("retry_count", sa.Integer(), nullable=True),
    )
    op.add_column(
        "communication_attachments",
        sa.Column("last_error", sa.String(), nullable=True),
    )

    # Make object_storage_key nullable (MEDIA_PENDING attachments don't have it yet)
    op.alter_column(
        "communication_attachments",
        "object_storage_key",
        existing_type=sa.String(),
        nullable=True,
    )

    # Make file_size nullable
    op.alter_column(
        "communication_attachments",
        "file_size",
        existing_type=sa.Integer(),
        nullable=True,
    )

    # Set defaults for existing rows
    op.execute(
        "UPDATE communication_attachments SET status = 'MEDIA_PERSISTED' WHERE status IS NULL"
    )
    op.execute(
        "UPDATE communication_attachments SET retry_count = 0 WHERE retry_count IS NULL"
    )

    # Now make status and retry_count NOT NULL
    op.alter_column(
        "communication_attachments",
        "status",
        existing_type=sa.String(),
        nullable=False,
    )
    op.alter_column(
        "communication_attachments",
        "retry_count",
        existing_type=sa.Integer(),
        nullable=False,
    )

    # Change raw_payload column type from JSON to String
    op.alter_column(
        "communication_messages",
        "raw_payload",
        existing_type=sa.JSON(),
        type_=sa.String(),
        existing_nullable=True,
    )


def downgrade() -> None:
    # Revert raw_payload back to JSON
    op.alter_column(
        "communication_messages",
        "raw_payload",
        existing_type=sa.String(),
        type_=sa.JSON(),
        existing_nullable=True,
    )

    # Remove new columns from communication_attachments
    op.alter_column(
        "communication_attachments",
        "file_size",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.alter_column(
        "communication_attachments",
        "object_storage_key",
        existing_type=sa.String(),
        nullable=False,
    )
    op.drop_column("communication_attachments", "last_error")
    op.drop_column("communication_attachments", "retry_count")
    op.drop_column("communication_attachments", "provider_media_id")
    op.drop_column("communication_attachments", "status")

    # Drop new tables
    op.drop_table("authorized_senders")
    op.drop_table("whatsapp_integrations")
