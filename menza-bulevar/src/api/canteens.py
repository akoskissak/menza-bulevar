from datetime import date, time
from fastapi import APIRouter, Depends, HTTPException, Query, status, Header
from src.domain.models import Canteen
from src.services.canteen_service import CanteenService
from src.repository.repo import repo
from src.dto.canteen_dto import UpdateCanteenDTO
from typing import List


router = APIRouter()
canteen_service = CanteenService(repo)

def get_admin_id(student_id: str = Header(..., alias="studentId")):
    return student_id

@router.get("/status", response_model=List[dict]) 
def get_capacity_endpoint(
    start_date: date = Query(..., alias="startDate"),
    end_date: date = Query(..., alias="endDate"),
    start_time: time = Query(..., alias="startTime"), 
    end_time: time = Query(..., alias="endTime"),
    duration: int = Query(..., alias="duration"),
):
    try:
        capacity_data = canteen_service.get_capacity_status(
            None, start_date, end_date, start_time, end_time, duration
        )
        return capacity_data
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    
@router.get("/{canteen_id}/status", response_model=dict) 
def get_single_canteen_capacity_endpoint(
    canteen_id: str,
    start_date: date = Query(..., alias="startDate"),
    end_date: date = Query(..., alias="endDate"),
    start_time: time = Query(..., alias="startTime"), 
    end_time: time = Query(..., alias="endTime"),
    duration: int = Query(..., alias="duration"),
):
    try:
        capacity_data = canteen_service.get_capacity_status(
            canteen_id, start_date, end_date, start_time, end_time, duration
        )
        if not capacity_data:
            return {"canteenId": canteen_id, "slots": []}
        
        return capacity_data[0]
    except ValueError as e:
        if "nije pronađena" in str(e):
             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        else:
             raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/", response_model=Canteen, status_code=status.HTTP_201_CREATED)
def create_canteen_endpoint(payload: Canteen, admin_id: str = Depends(get_admin_id)):
    try:
        new_canteen = canteen_service.create_canteen(admin_id, payload)
        return new_canteen
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    
@router.get("/", response_model=List[Canteen])
def get_all_canteens_endpoint():
    try:
        canteens = canteen_service.get_all_canteens()
        return canteens
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Greška pri dohvatanju menzi.")

@router.get("/{canteen_id}", response_model=Canteen)
def get_single_canteen_endpoint(canteen_id: str):
    try:
        canteen = canteen_service.get_canteen_by_id(canteen_id)
        return canteen
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Greška pri dohvatanju menze.")

@router.put("/{canteen_id}", response_model=Canteen)
def update_canteen_endpoint(
    canteen_id: str, 
    payload: UpdateCanteenDTO, 
    student_id: str = Depends(get_admin_id)
):

    update_data = payload.model_dump(exclude_none=True)

    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nema podataka za ažuriranje.")
        
    try:
        updated_canteen = canteen_service.update_canteen(student_id, canteen_id, update_data)
        return updated_canteen
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        if "nije pronađena" in str(e):
             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        else:
             raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.delete("/{canteen_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_canteen_endpoint(canteen_id: str, admin_id: str = Depends(get_admin_id)):
    try:
        canteen_service.delete_canteen(admin_id, canteen_id)
        return {}
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))