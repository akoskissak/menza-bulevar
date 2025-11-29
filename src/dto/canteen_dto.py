from typing import Optional, List
from pydantic import BaseModel
from src.domain.models import WorkingHour


class UpdateCanteenDTO(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    capacity: Optional[int] = None
    workingHours: Optional[List[WorkingHour]] = None