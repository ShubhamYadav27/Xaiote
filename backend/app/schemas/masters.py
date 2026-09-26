from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CustomerBase(BaseModel):
    name: str
    external_id: str | None = None


class CustomerCreate(CustomerBase):
    pass


class CustomerResponse(CustomerBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    company_id: str
    created_at: datetime
    updated_at: datetime
    source_import_job_id: str | None = None


class VendorBase(BaseModel):
    name: str
    external_id: str | None = None


class VendorCreate(VendorBase):
    pass


class VendorResponse(VendorBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    company_id: str
    created_at: datetime
    updated_at: datetime
    source_import_job_id: str | None = None


class ProductBase(BaseModel):
    name: str
    sku: str | None = None
    external_id: str | None = None


class ProductCreate(ProductBase):
    pass


class ProductResponse(ProductBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    company_id: str
    created_at: datetime
    updated_at: datetime


class MachineBase(BaseModel):
    plant_id: str
    name: str
    category: str | None = None
    external_id: str | None = None


class MachineCreate(MachineBase):
    pass


class MachineResponse(MachineBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    company_id: str
    created_at: datetime
    updated_at: datetime
