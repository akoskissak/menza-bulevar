from datetime import datetime, date, time, timedelta
from src.domain.models import Reservation, Canteen
from src.dto.reservation_dto import CreateReservationDTO
from src.repository.repo import MemoryRepository

class ReservationService:
    def __init__(self, repo: MemoryRepository):
        self.repo = repo
        
    def _validate_reservation_payload(self, payload: CreateReservationDTO):
        if payload.date < date.today():
            raise ValueError("Nije dozvoljeno kreirati rezervaciju za dane u prošlosti.")
            
        if payload.duration not in [30, 60]:
            raise ValueError("Trajanje rezervacije mora biti 30 ili 60 minuta.")
            
        reservation_time = payload.time
        if reservation_time.minute not in [0, 30]:
            raise ValueError("Termin mora krenuti na pun sat ili na pola sata (primer 15:00 ili 15:30).")
            
        if not self.repo.get_student_by_id(payload.studentId):
            raise ValueError(f"Student sa ID-jem '{payload.studentId}' nije pronađen.")
            
        canteen = self.repo.get_canteen_by_id(payload.canteenId)
        if not canteen:
            raise ValueError(f"Menza sa ID-jem '{payload.canteenId}' nije pronađena.")

        return reservation_time, canteen

    def _check_student_overlap(self, student_id: str, requested_start: datetime, requested_end: datetime):
        student_reservations = self.repo.get_reservations_by_student_id(student_id)
        
        for res in student_reservations:
            if res.status != "Active":
                continue

            res_start = datetime.combine(res.date, res.time)
            res_end = res_start + timedelta(minutes=res.duration)
            
            if requested_start < res_end and requested_end > res_start:
                raise ValueError(f"Student već ima aktivnu rezervaciju koja se preklapa u terminu {res.date} {res.time.strftime('%H:%M')}.")


    def _check_capacity(self, canteen: Canteen, date: date, start_time: time, duration: int):
        slot_start = datetime.combine(date, start_time)
        slot_end = slot_start + timedelta(minutes=duration)
        
        is_open = False
        for h in canteen.workingHours:
            meal_start = datetime.combine(date, h.from_time)
            meal_end = datetime.combine(date, h.to_time)
            
            if meal_start <= slot_start and slot_end <= meal_end:
                 is_open = True
                 break
        
        if not is_open:
            raise ValueError("Menza nije otvorena u traženom terminu.")

        active_reservations = self.repo.get_active_reservations_by_canteen_and_date(canteen.id, date)
        
        current_reservations_in_slot = 0
        for res in active_reservations:
            res_start = datetime.combine(res.date, res.time )
            res_end = res_start + timedelta(minutes=res.duration)
            
            if slot_start < res_end and slot_end > res_start:
                current_reservations_in_slot += 1
                
        remaining_capacity = canteen.capacity - current_reservations_in_slot
        
        if remaining_capacity <= 0:
            raise ValueError(f"Kapacitet za menzu '{canteen.name}' je pun u terminu {start_time.strftime('%H:%M')} na dan {date}.")


    def create_reservation(self, payload: CreateReservationDTO) -> Reservation:
        reservation_time, canteen = self._validate_reservation_payload(payload)
        
        requested_start = datetime.combine(payload.date, reservation_time)
        requested_end = requested_start + timedelta(minutes=payload.duration)

        self._check_student_overlap(payload.studentId, requested_start, requested_end)
        self._check_capacity(canteen, payload.date, reservation_time, payload.duration)
        
        new_reservation = Reservation(
            studentId=payload.studentId,
            canteenId=payload.canteenId,
            date=payload.date,
            time=reservation_time,
            duration=payload.duration
        )
        
        return self.repo.add_reservation(new_reservation)


    def cancel_reservation(self, reservation_id: str, student_id: str) -> Reservation:
        reservation = self.repo.get_reservation_by_id(reservation_id)
        
        if not reservation:
            raise ValueError(f"Rezervacija sa ID-om '{reservation_id}' nije pronađena.")

        if reservation.studentId != student_id:
            raise PermissionError("Nije dozvoljeno otkazivanje tuđe rezervacije.")
            
        if reservation.status == "Cancelled":
            raise ValueError("Rezervacija je već otkazana.")
            
        updated_reservation = self.repo.cancel_reservation(reservation_id)
        return updated_reservation