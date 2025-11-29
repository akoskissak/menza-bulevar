from fastapi import APIRouter, Depends, HTTPException, status, Header
from src.domain.models import Reservation
from src.services.reservation_service import ReservationService
from src.dto.reservation_dto import CreateReservationDTO
from src.repository.repo import repo


router = APIRouter()
reservation_service = ReservationService(repo)

def get_student_id(student_id: str = Header(..., alias="studentId")):
    return student_id

@router.post("/", response_model=Reservation, status_code=status.HTTP_201_CREATED)
def create_reservation_endpoint(payload: CreateReservationDTO):
    try:
        new_reservation = reservation_service.create_reservation(payload)
        return new_reservation
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Greška pri kreiranju rezervacije.")
    
@router.delete("/{reservation_id}", response_model=Reservation)
def cancel_reservation_endpoint(reservation_id: str, student_id: str = Depends(get_student_id)):
    try:
        cancelled_reservation = reservation_service.cancel_reservation(reservation_id, student_id)
        return cancelled_reservation
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        if "nije pronađena" in str(e):
             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        else:
             raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Greška pri otkazivanju rezervacije.")