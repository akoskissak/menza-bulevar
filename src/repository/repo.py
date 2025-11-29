import uuid
from typing import Dict, List, Optional
from datetime import date
from src.domain.models import Student, Canteen, Reservation

class MemoryRepository:
    def __init__(self):
        self._students: Dict[str, Student] = {}
        self._canteens: Dict[str, Canteen] = {}
        self._reservations: Dict[str, Reservation] = {}

    def add_student(self, data: Student) -> Student:
        if self.get_student_by_email(data.email):
            raise ValueError(f"Student sa ovim email-om {data.email} već postoji.")
        
        new_id = str(uuid.uuid4())
        new_student = data.model_copy(update={"id": new_id})
        self._students[new_id] = new_student
        return new_student

    def get_student_by_id(self, student_id: str) -> Optional[Student]:
        return self._students.get(student_id)
    
    def get_student_by_email(self, email: str) -> Optional[Student]:
        for student in self._students.values():
            if student.email == email:
                return student
        return None

    def add_canteen(self, data: Canteen) -> Canteen:
        new_id = str(uuid.uuid4())
        new_canteen = data.model_copy(update={"id": new_id})
        self._canteens[new_id] = new_canteen
        return new_canteen
    
    def get_canteen_by_id(self, canteen_id: str) -> Optional[Canteen]:
        return self._canteens.get(canteen_id)
    
    def get_all_canteens(self) -> List[Canteen]:
        return list(self._canteens.values())
    
    def update_canteen(self, canteen_id: str, data: dict) -> Optional[Canteen]:
        if canteen_id not in self._canteens:
            return None
        
        existing_canteen = self._canteens[canteen_id]
        update_canteen = existing_canteen.model_copy(update=data)
        self._canteens[canteen_id] = update_canteen
        return update_canteen

    def delete_canteen(self, canteen_id: str) -> bool:
        if canteen_id not in self._canteens:
            return False
        
        del self._canteens[canteen_id]
        return True

    def add_reservation(self, data: Reservation) -> Reservation:
        new_id = str(uuid.uuid4())
        new_reservation = data.model_copy(update={"id": new_id})
        self._reservations[new_id] = new_reservation
        return new_reservation
    
    def get_reservation_by_id(self, reservation_id: str) -> Optional[Reservation]:
        return self._reservations.get(reservation_id)

    def get_reservations_by_student_id(self, student_id: str) -> List[Reservation]:
        return [res for res in self._reservations.values() if res.studentId == student_id]
    
    def cancel_reservation(self, reservation_id: str) -> Reservation:
        reservation = self._reservations.get(reservation_id)
        if not reservation:
            return None

        reservation.status = "Cancelled"
        self._reservations[reservation_id] = reservation
        return reservation
    
    def get_active_reservations_by_canteen_and_date(self, canteen_id: str, reservation_date: date) -> List[Reservation]:
        return [res for res in self._reservations.values() if res.canteenId == canteen_id and res.date == reservation_date and res.status == "Active"]
    
    def delete_reservations_by_canteen_id(self, canteen_id: str) -> int:
        ids_to_delete = [res_id for res_id, res in self._reservations.items() if res.canteenId == canteen_id]
        count = 0
        for res_id in ids_to_delete:
            del self._reservations[res_id]
            count += 1
        return count

    def clear_all(self):
        self._students.clear()
        self._canteens.clear()
        self._reservations.clear()

repo = MemoryRepository()