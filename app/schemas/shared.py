

from pydantic import BaseModel
from typing import Generic, TypeVar


T = TypeVar("T")

class ApiResponse(BaseModel, Generic[T]):
    message: str
    details: str
    errorGroup: str
    data: T | None = None