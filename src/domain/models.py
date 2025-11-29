from pydantic import BaseModel, Field, field_serializer
from datetime import date, time
from typing import List, Optional


class Student(BaseModel):
    id: Optional[str] = None
    name: str
    email: str
    isAdmin: bool = Field(default=False)

class WorkingHour(BaseModel):
    meal: str
    from_time: time = Field(..., alias="from")
    to_time: time = Field(..., alias="to")

    @field_serializer('from_time', 'to_time')
    def serialize_time(self, time_obj: time) -> str:
        return time_obj.strftime("%H:%M")

class Canteen(BaseModel):
    id: Optional[str] = None
    name: str
    location: str
    capacity: int
    workingHours: List[WorkingHour]

class Reservation(BaseModel):
    id: Optional[str] = None
    studentId: str
    canteenId: str
    date: date
    time: time
    duration: int = Field(..., ge=30, le=60)
    status: str = Field(default="Active")

    @field_serializer('time')
    def serialize_reservation_time(self, time_obj: time) -> str:
        return time_obj.strftime("%H:%M")