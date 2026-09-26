from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.work_order import WorkOrderStatus


class WorkOrderBase(BaseModel):
    plant_id: str
    customer_id: str | None = None
    product_id: str
    machine_id: str | None = None

    order_number: str
    quantity: Decimal = Field(..., ge=0)
    planned_production_info: str | None = None
    due_date: datetime | None = None

    status: WorkOrderStatus = WorkOrderStatus.PLANNED
    production_progress: Decimal = Field(0.0, ge=0, le=100)

    external_id: str | None = None
    source_import_job_id: str | None = None


class WorkOrderCreate(WorkOrderBase):
    pass


class WorkOrderResponse(WorkOrderBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    company_id: str
    created_at: datetime
    updated_at: datetime
