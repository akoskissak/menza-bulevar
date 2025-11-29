import pytest
from unittest.mock import patch
from datetime import date, time, timedelta
from src.domain.models import Student, Canteen, WorkingHour, Reservation
from src.dto.restriction_dto import CreateRestrictionDTO
from src.services.canteen_service import CanteenService
from src.repository.repo import MemoryRepository

@pytest.fixture
def repo():
    return MemoryRepository()

@pytest.fixture
def service(repo):
    return CanteenService(repo)

@pytest.fixture
def admin_student(repo):
    student = Student(name="Admin", email="admin@test.com", isAdmin=True)
    return repo.add_student(student)

@pytest.fixture
def regular_student(repo):
    student = Student(name="Student", email="student@test.com", isAdmin=False)
    return repo.add_student(student)

@pytest.fixture
def canteen(repo, admin_student):
    wh = WorkingHour(meal="breakfast", **{"from": time(8, 0), "to": time(10, 0)})
    canteen = Canteen(name="Menza 1", location="Loc 1", capacity=100, workingHours=[wh])
    return repo.add_canteen(canteen)

def test_create_restriction_success(service, admin_student, canteen):
    wh = WorkingHour(meal="breakfast", **{"from": time(8, 0), "to": time(9, 0)})
    dto = CreateRestrictionDTO(
        startDate=date(2025, 10, 29),
        endDate=date(2025, 10, 30),
        workingHours=[wh]
    )
    
    restriction = service.create_restriction(admin_student.id, canteen.id, dto)
    
    assert restriction.canteenId == canteen.id
    assert restriction.startDate == dto.startDate
    assert restriction.endDate == dto.endDate
    assert len(restriction.workingHours) == 1
    assert restriction.workingHours[0].to_time == time(9, 0)

def test_create_restriction_not_admin(service, regular_student, canteen):
    wh = WorkingHour(meal="breakfast", **{"from": time(8, 0), "to": time(9, 0)})
    dto = CreateRestrictionDTO(
        startDate=date(2025, 10, 29),
        endDate=date(2025, 10, 30),
        workingHours=[wh]
    )
    
    with pytest.raises(PermissionError):
        service.create_restriction(regular_student.id, canteen.id, dto)

def test_create_restriction_overlap(service, admin_student, canteen):
    wh = WorkingHour(meal="breakfast", **{"from": time(8, 0), "to": time(9, 0)})
    dto1 = CreateRestrictionDTO(
        startDate=date(2025, 10, 29),
        endDate=date(2025, 10, 30),
        workingHours=[wh]
    )
    service.create_restriction(admin_student.id, canteen.id, dto1)
    
    dto2 = CreateRestrictionDTO(
        startDate=date(2025, 10, 30),
        endDate=date(2025, 10, 31),
        workingHours=[wh]
    )
    
    with pytest.raises(ValueError, match="Postoji preklapanje"):
        service.create_restriction(admin_student.id, canteen.id, dto2)

def test_restriction_cancels_conflicting_reservations(service, repo, admin_student, regular_student, canteen):
    # Reservation 1: 08:00 - 09:00 (Valid under restriction)
    res1 = Reservation(
        studentId=regular_student.id,
        canteenId=canteen.id,
        date=date(2025, 10, 29),
        time=time(8, 0),
        duration=60
    )
    repo.add_reservation(res1)
    
    # Reservation 2: 09:00 - 10:00 (Invalid under restriction 08-09)
    res2 = Reservation(
        studentId=regular_student.id,
        canteenId=canteen.id,
        date=date(2025, 10, 29),
        time=time(9, 0),
        duration=60
    )
    repo.add_reservation(res2)
    
    # Reservation 3: 08:30 - 09:30 (Invalid under restriction 08-09)
    res3 = Reservation(
        studentId=regular_student.id,
        canteenId=canteen.id,
        date=date(2025, 10, 29),
        time=time(8, 30),
        duration=60
    )
    repo.add_reservation(res3)

    # Create restriction 08:00 - 09:00
    wh = WorkingHour(meal="breakfast", **{"from": time(8, 0), "to": time(9, 0)})
    dto = CreateRestrictionDTO(
        startDate=date(2025, 10, 29),
        endDate=date(2025, 10, 29),
        workingHours=[wh]
    )
    
    service.create_restriction(admin_student.id, canteen.id, dto)
    
    # Check statuses
    updated_res1 = repo.get_reservations_by_student_id(regular_student.id)[0]
    updated_res2 = repo.get_reservations_by_student_id(regular_student.id)[1]
    updated_res3 = repo.get_reservations_by_student_id(regular_student.id)[2]
    
    assert updated_res1.status == "Active"
    assert updated_res2.status == "Cancelled"
    assert updated_res3.status == "Cancelled"

def test_restriction_non_working_day(service, repo, admin_student, regular_student, canteen):
    # Create reservations on the day
    res1 = Reservation(
        studentId=regular_student.id,
        canteenId=canteen.id,
        date=date(2025, 10, 29),
        time=time(8, 0),
        duration=60
    )
    res1 = repo.add_reservation(res1)
    
    # Create restriction with empty working hours (non-working day)
    dto = CreateRestrictionDTO(
        startDate=date(2025, 10, 29),
        endDate=date(2025, 10, 29),
        workingHours=[]
    )
    
    service.create_restriction(admin_student.id, canteen.id, dto)
    
    updated_res1 = repo.get_reservation_by_id(res1.id)
    assert updated_res1.status == "Cancelled"

def test_restriction_remove_meal(service, repo, admin_student, regular_student):
    # Setup canteen with breakfast and lunch
    wh_breakfast = WorkingHour(meal="breakfast", **{"from": time(8, 0), "to": time(10, 0)})
    wh_lunch = WorkingHour(meal="lunch", **{"from": time(12, 0), "to": time(15, 0)})
    canteen = Canteen(name="Menza 2", location="Loc 2", capacity=100, workingHours=[wh_breakfast, wh_lunch])
    canteen = repo.add_canteen(canteen)

    # Reservation for breakfast (should stay)
    res_breakfast = Reservation(
        studentId=regular_student.id,
        canteenId=canteen.id,
        date=date(2025, 10, 29),
        time=time(8, 30),
        duration=30
    )
    res_breakfast = repo.add_reservation(res_breakfast)

    # Reservation for lunch (should be cancelled)
    res_lunch = Reservation(
        studentId=regular_student.id,
        canteenId=canteen.id,
        date=date(2025, 10, 29),
        time=time(12, 30),
        duration=30
    )
    res_lunch = repo.add_reservation(res_lunch)

    # Restriction: Only breakfast served
    dto = CreateRestrictionDTO(
        startDate=date(2025, 10, 29),
        endDate=date(2025, 10, 29),
        workingHours=[wh_breakfast]
    )
    
    service.create_restriction(admin_student.id, canteen.id, dto)
    
    updated_res_breakfast = repo.get_reservation_by_id(res_breakfast.id)
    updated_res_lunch = repo.get_reservation_by_id(res_lunch.id)
    
    assert updated_res_breakfast.status == "Active"
    assert updated_res_lunch.status == "Cancelled"

def test_email_sending_mocked(service, repo, admin_student, regular_student, canteen):
    res1 = Reservation(
        studentId=regular_student.id,
        canteenId=canteen.id,
        date=date(2025, 10, 29),
        time=time(8, 0),
        duration=60
    )
    res1 = repo.add_reservation(res1)
    
    wh = WorkingHour(meal="breakfast", **{"from": time(8, 0), "to": time(9, 0)})
    dto = CreateRestrictionDTO(
        startDate=date(2025, 10, 29),
        endDate=date(2025, 10, 29),
        workingHours=[] # Non working day
    )
    
    with patch.object(service, '_send_cancellation_email') as mock_email:
        service.create_restriction(admin_student.id, canteen.id, dto)
        mock_email.assert_called_once()
        # Verify arguments if needed
        args, _ = mock_email.call_args
        assert args[0].id == res1.id
        assert args[1].id == canteen.id
