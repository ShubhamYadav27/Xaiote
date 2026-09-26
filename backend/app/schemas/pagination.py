from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PaginatedData(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int


class PaginatedResponse(BaseModel, Generic[T]):
    data: PaginatedData[T]
