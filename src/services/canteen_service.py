from datetime import datetime, date, time, timedelta
from typing import List, Dict, Optional
from src.services.student_service import StudentService
from src.domain.models import Canteen, WorkingHour
from src.repository.repo import MemoryRepository

class CanteenService:
    def __init__(self, repo: MemoryRepository):
        self.repo = repo
        self.student_service = StudentService(repo)

    def _check_admin_rights(self, student_id: str):
        student = self.student_service.get_student(student_id)
        if not student.isAdmin:
            raise PermissionError("Only Admin students can manage Canteens.")
        
    def create_canteen(self, admin_id: str, payload: Canteen) -> Canteen:
        self._check_admin_rights(admin_id)

        return self.repo.add_canteen(payload)
    
    def get_all_canteens(self) -> List[Canteen]:
        return self.repo.get_all_canteens()
    
    def get_canteen_by_id(self, canteen_id: str) -> Canteen:
        canteen = self.repo.get_canteen_by_id(canteen_id)
        if not canteen:
            raise ValueError(f"Canteen sa ID-jem '{canteen_id}' nije pronađena.")
        return canteen
    
    def update_canteen(self, admin_id: str, canteen_id: str, update_data: dict) -> Canteen:
        self._check_admin_rights(admin_id)

        updated = self.repo.update_canteen(canteen_id, update_data)
        if not updated:
            raise ValueError(f"Canteen with ID {canteen_id} not found.")
        return updated

    def delete_canteen(self, admin_id: str, canteen_id: str) -> None:
        self._check_admin_rights(admin_id)

        deleted = self.repo.delete_canteen(canteen_id)
        if not deleted:
            raise ValueError(f"Canteen with ID {canteen_id} not found.")
        
        self.repo.delete_reservations_by_canteen_id(canteen_id)

    def get_capacity_status(self, canteen_id: Optional[str], start_date: date, end_date: date, start_time: time, end_time: time, duration: int) -> List[Dict]:
        # Validacija
        if duration not in [30, 60]:
            raise ValueError("Trajanje obroka mora biti 30 ili 60 minuta.")
        if start_date > end_date:
            raise ValueError("startDate ne može biti nakon endDate.")
        if start_time >= end_time:
            raise ValueError("startTime mora biti pre endTime.")
        
        check_canteens = self._get_relevant_canteens(canteen_id)
        results = []

        for canteen in check_canteens:
            canteen_slots = self._calculate_canteen_slots(canteen, start_date, end_date, start_time, end_time, duration)
            
            if canteen_slots:
                results.append({"canteenId": canteen.id,
                                "slots": canteen_slots})
        
        return results
    
    def _get_relevant_canteens(self, canteen_id: Optional[str]) -> List[Canteen]:
        if canteen_id:
            canteen = self.repo.get_canteen_by_id(canteen_id)
            return [canteen] if canteen else []
        else:
            return self.repo.get_all_canteens()
    
    def _calculate_canteen_slots(self, canteen: Canteen, start_date: date, end_date: date, start_time: time, end_time: time, duration: int) -> List[Dict]:
        slots = []
        current_date = start_date

        while current_date <= end_date:

            active_reservations = self.repo.get_active_reservations_by_canteen_and_date(canteen.id, current_date)

            for current_slot_time in self._generate_time_slots(start_time, end_time, duration):

                meal_info = self._get_meal_for_slot(canteen.workingHours, current_slot_time)
                if not meal_info:
                    continue

                remaining_capacity = canteen.capacity

                slot_start = datetime.combine(current_date, current_slot_time)
                slot_end = slot_start + timedelta(minutes=duration)
                    
                for res in active_reservations:
                    res_start = datetime.combine(current_date, res.time)
                    res_end = res_start + timedelta(minutes=res.duration)

                    if slot_start < res_end and slot_end > res_start:
                        remaining_capacity -= 1
                
                slots.append({"date": current_date.isoformat(), "meal": meal_info['meal'], "startTime": current_slot_time.strftime("%H:%M"), "remainingCapacity": max(0, remaining_capacity)})

            current_date += timedelta(days=1)
        
        return slots
        
    def _generate_time_slots(self, start: time, end: time, step_minutes: int):
        current = datetime.combine(date.min, start)
        end_dt = datetime.combine(date.min, end)
        step_delta = timedelta(minutes=step_minutes)

        slots = []
        while current < end_dt:
            slots.append(current.time())
            current += step_delta
        
        return slots

    def _get_meal_for_slot(self, working_hours: List[WorkingHour], slot_time: time) -> Optional[Dict]:
        for h in working_hours:
            if h.from_time <= slot_time < h.to_time:
                return {"meal": h.meal, "from": h.from_time, "to": h.to_time}
        return None