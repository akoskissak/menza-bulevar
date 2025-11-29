import pytest
from datetime import date, time, timedelta, datetime
from src.domain.models import Student, Canteen, WorkingHour, Reservation
from src.dto.reservation_dto import CreateReservationDTO
from src.services.reservation_service import ReservationService
from src.repository.repo import MemoryRepository

TOMORROW = date.today() + timedelta(days=1)

@pytest.fixture
def repo():
    return MemoryRepository()

@pytest.fixture
def reservation_service(repo):
    return ReservationService(repo)

import pytest
from datetime import date, time, timedelta
from src.domain.models import Student, Canteen, WorkingHour, Reservation
from src.dto.reservation_dto import CreateReservationDTO
from src.services.reservation_service import ReservationService
from src.repository.repo import MemoryRepository

TOMORROW = date.today() + timedelta(days=1)


@pytest.fixture
def repo():
    return MemoryRepository()


@pytest.fixture
def reservation_service(repo):
    return ReservationService(repo)


@pytest.fixture
def student_a(repo):
    student = Student(name="Test Student A", email="test.a@test.com", isAdmin=False)
    return repo.add_student(student)


@pytest.fixture
def multi_meal_canteen(repo):
    wh = [
        WorkingHour(meal="breakfast", **{"from": time(8, 0), "to": time(10, 0)}),
        WorkingHour(meal="lunch", **{"from": time(12, 0), "to": time(14, 0)}),
        WorkingHour(meal="dinner", **{"from": time(18, 0), "to": time(20, 0)}),
    ]
    canteen = Canteen(name="Sva Tri Obroka", location="Test Loc", capacity=10, workingHours=wh)
    return repo.add_canteen(canteen)


@pytest.fixture
def breakfast_payload(student_a, multi_meal_canteen):
    return CreateReservationDTO(
        studentId=student_a.id,
        canteenId=multi_meal_canteen.id,
        date=TOMORROW,
        time=time(8, 30),
        duration=30,
    )


@pytest.fixture
def lunch_payload(student_a, multi_meal_canteen):
    return CreateReservationDTO(
        studentId=student_a.id,
        canteenId=multi_meal_canteen.id,
        date=TOMORROW,
        time=time(12, 30),
        duration=30,
    )


def test_create_breakfast_success(reservation_service, breakfast_payload):
    res = reservation_service.create_reservation(breakfast_payload)
    assert res.studentId == breakfast_payload.studentId
    assert res.canteenId == breakfast_payload.canteenId
    assert res.status == "Active"
    assert hasattr(res, "id") and res.id is not None


def test_prevent_student_overlap(reservation_service, breakfast_payload):
    # First reservation at 08:30 (30m)
    res1 = reservation_service.create_reservation(breakfast_payload)

    # Overlapping reservation (08:00 - 09:00) for same student should raise
    overlapping = CreateReservationDTO(
        studentId=breakfast_payload.studentId,
        canteenId=breakfast_payload.canteenId,
        date=TOMORROW,
        time=time(8, 0),
        duration=60,
    )

    with pytest.raises(ValueError, match="preklapa|već ima"):
        reservation_service.create_reservation(overlapping)


def test_meal_type_limit(reservation_service, student_a, multi_meal_canteen):
    # Create two breakfast reservations (different times within breakfast window)
    r1 = CreateReservationDTO(studentId=student_a.id, canteenId=multi_meal_canteen.id, date=TOMORROW, time=time(8, 0), duration=30)
    r2 = CreateReservationDTO(studentId=student_a.id, canteenId=multi_meal_canteen.id, date=TOMORROW, time=time(8, 30), duration=30)

    reservation_service.create_reservation(r1)
    reservation_service.create_reservation(r2)

    # Third breakfast reservation should fail (limit 2)
    r3 = CreateReservationDTO(studentId=student_a.id, canteenId=multi_meal_canteen.id, date=TOMORROW, time=time(9, 0), duration=30)
    with pytest.raises(ValueError, match="maksimalno|maksimum|maksimal"):
        reservation_service.create_reservation(r3)
