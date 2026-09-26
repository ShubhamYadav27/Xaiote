from pydantic import BaseModel


class PlantCreate(BaseModel):
    name: str
    location: str | None = None
    timezone: str | None = None


class PlantResponse(BaseModel):
    id: str
    company_id: str
    name: str
    location: str | None = None
    timezone: str | None = None
