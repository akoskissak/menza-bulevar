from pydantic import BaseModel, Field
from datetime import date, time
from typing import List
from src.domain.models import WorkingHour

class CreateRestrictionDTO(BaseModel):
    startDate: date
    endDate: date
    workingHours: List[WorkingHour]
