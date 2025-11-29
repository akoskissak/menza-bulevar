from datetime import date, time
from pydantic import BaseModel

class CreateReservationDTO(BaseModel):
    studentId: str
    canteenId: str
    date: date
    time: time 
    duration: int