from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.imports import ImportEntityType, ImportJobStatus, ValidationStatus


class ImportJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    company_id: str
    status: ImportJobStatus
    import_type: ImportEntityType

    source_filename: str
    source_file_hash: str
    file_size: int

    total_rows: int
    valid_rows: int
    invalid_rows: int
    needs_review_rows: int
    created_rows: int
    updated_rows: int
    unchanged_rows: int

    error_message: str | None = None
    created_by: str

    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None


class ImportAuditResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    import_job_id: str
    source_row_number: int
    target_entity_type: str
    target_record_id: str | None = None
    validation_status: ValidationStatus
    validation_reason: str | None = None
    action: str | None = None
    previous_source_import_job_id: str | None = None
    created_at: datetime
