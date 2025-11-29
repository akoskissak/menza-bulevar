from typing import Optional
from src.domain.models import Student
from src.repository.repo import MemoryRepository

class CreateStudentDTO(Student):
    id: Optional[str] = None

class StudentService:
    def __init__(self, repo: MemoryRepository):
        self.repo = repo

    def create_student(self, payload: CreateStudentDTO) -> Student:
        if self.repo.get_student_by_email(payload.email):
            raise ValueError(f"Student sa emailom '{payload.email}' već postoji.")
        
        new_student = self.repo.add_student(payload)
        return new_student

    def get_student(self, student_id: str) -> Optional[Student]:
        student = self.repo.get_student_by_id(student_id)
        if not student:
            raise ValueError(f"Student sa ID-om '{student_id}' nije pronađen.")
        return student