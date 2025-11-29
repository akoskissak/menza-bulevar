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
    from_time: time = Field(
        ..., 
        validation_alias="from", 
        serialization_alias="from"
    )
    
    to_time: time = Field(
        ..., 
        validation_alias="to", 
        serialization_alias="to"
    )

    @field_serializer('from_time', 'to_time')
    def serialize_time(self, time_obj: time) -> str:
        return time_obj.strftime("%H:%M")
    
    class Config:
        populate_by_name = True

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
    
    @field_serializer('date')
    def serialize_reservation_date(self, date_obj: date) -> str:
        return date_obj.isoformat()
    
class Restriction(BaseModel):
    id: Optional[str] = None
    canteenId: str
    startDate: date
    endDate: date
    workingHours: List[WorkingHour]