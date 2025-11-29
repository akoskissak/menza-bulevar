from fastapi import APIRouter, HTTPException, status
from src.domain.models import Student
from src.services.student_service import StudentService, CreateStudentDTO
from src.repository.repo import repo

router = APIRouter()

student_service = StudentService(repo)

@router.post("/", response_model=Student, status_code=status.HTTP_201_CREATED)
def create_student_endpoint(payload: CreateStudentDTO):
    try:
        new_student = student_service.create_student(payload)
        return new_student
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    
@router.get("/{student_id}", response_model=Student)
def get_student_endpoint(student_id: str):
    try:
        student = student_service.get_student(student_id)
        return student
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))