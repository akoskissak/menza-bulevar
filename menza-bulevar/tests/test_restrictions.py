import pytest
from unittest.mock import patch, MagicMock
from datetime import date, time, timedelta
from src.domain.models import Student, Canteen, WorkingHour, Reservation
from src.dto.restriction_dto import CreateRestrictionDTO
from src.services.canteen_service import CanteenService
from src.repository.repo import DynamoRepository

# --- Fixtures ---

@pytest.fixture
def repo():
    return DynamoRepository()

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
    # Canteen works 08:00 - 14:00 for breakfast/lunch combined for simplicity in some tests,
    # or we can define specific meals. Let's define standard meals.
    wh_breakfast = WorkingHour(meal="breakfast", **{"from": time(8, 0), "to": time(10, 0)})
    wh_lunch = WorkingHour(meal="lunch", **{"from": time(11, 0), "to": time(14, 0)})
    wh_dinner = WorkingHour(meal="dinner", **{"from": time(18, 0), "to": time(20, 0)})
    
    canteen = Canteen(
        name="Menza Test", 
        location="Loc Test", 
        capacity=100, 
        workingHours=[wh_breakfast, wh_lunch, wh_dinner]
    )
    return repo.add_canteen(canteen)

# --- 1. Input Validation Tests ---

def test_create_restriction_end_date_before_start_date(service, admin_student, canteen):
    """Pokušaj kreiranja restrikcije gde je datum završetka pre datuma početka."""
    dto = CreateRestrictionDTO(
        startDate=date(2025, 10, 30),
        endDate=date(2025, 10, 29),
        workingHours=[]
    )
    with pytest.raises(ValueError):
        service.create_restriction(admin_student.id, canteen.id, dto)

def test_create_restriction_outside_original_hours(service, admin_student, canteen):
    """
    Pokušaj definisanja skraćenog vremena koje je van originalnog radnog vremena menze.
    Menza doručak: 08-10. Restrikcija pokušava 08-11.
    """
    wh_extended = WorkingHour(meal="breakfast", **{"from": time(8, 0), "to": time(11, 0)})
    dto = CreateRestrictionDTO(
        startDate=date(2025, 10, 29),
        endDate=date(2025, 10, 29),
        workingHours=[wh_extended]
    )
    # Očekujemo grešku jer restrikcija ne može da produži radno vreme, samo da ga skrati ili promeni unutar opsega?
    # Ili bar da validira da je unutar nekog logičnog opsega.
    with pytest.raises(ValueError, match="van originalnog radnog vremena"):
        service.create_restriction(admin_student.id, canteen.id, dto)

# --- 2. Overlapping Logic Tests ---

def test_create_restriction_overlap_exact(service, admin_student, canteen):
    """Dodavanje restrikcije koja se datumski potpuno poklapa sa postojećom."""
    dto = CreateRestrictionDTO(
        startDate=date(2025, 11, 1),
        endDate=date(2025, 11, 5),
        workingHours=[]
    )
    service.create_restriction(admin_student.id, canteen.id, dto)
    
    with pytest.raises(ValueError, match="Postoji preklapanje"):
        service.create_restriction(admin_student.id, canteen.id, dto)

def test_create_restriction_overlap_partial_left(service, admin_student, canteen):
    """Nova počinje pre, a završava se u toku postojeće."""
    # Postojeća: 01.11 - 05.11
    service.create_restriction(admin_student.id, canteen.id, CreateRestrictionDTO(
        startDate=date(2025, 11, 1), endDate=date(2025, 11, 5), workingHours=[]
    ))
    
    # Nova: 30.10 - 02.11
    dto_new = CreateRestrictionDTO(
        startDate=date(2025, 10, 30),
        endDate=date(2025, 11, 2),
        workingHours=[]
    )
    with pytest.raises(ValueError, match="Postoji preklapanje"):
        service.create_restriction(admin_student.id, canteen.id, dto_new)

def test_create_restriction_overlap_partial_right(service, admin_student, canteen):
    """Nova počinje u toku, a završava se posle postojeće."""
    # Postojeća: 01.11 - 05.11
    service.create_restriction(admin_student.id, canteen.id, CreateRestrictionDTO(
        startDate=date(2025, 11, 1), endDate=date(2025, 11, 5), workingHours=[]
    ))
    
    # Nova: 04.11 - 08.11
    dto_new = CreateRestrictionDTO(
        startDate=date(2025, 11, 4),
        endDate=date(2025, 11, 8),
        workingHours=[]
    )
    with pytest.raises(ValueError, match="Postoji preklapanje"):
        service.create_restriction(admin_student.id, canteen.id, dto_new)

def test_create_restriction_overlap_encompassing(service, admin_student, canteen):
    """Nova obuhvata postojeću (veća je)."""
    # Postojeća: 03.11 - 03.11
    service.create_restriction(admin_student.id, canteen.id, CreateRestrictionDTO(
        startDate=date(2025, 11, 3), endDate=date(2025, 11, 3), workingHours=[]
    ))
    
    # Nova: 01.11 - 05.11
    dto_new = CreateRestrictionDTO(
        startDate=date(2025, 11, 1),
        endDate=date(2025, 11, 5),
        workingHours=[]
    )
    with pytest.raises(ValueError, match="Postoji preklapanje"):
        service.create_restriction(admin_student.id, canteen.id, dto_new)

def test_create_restriction_overlap_inside(service, admin_student, canteen):
    """Nova je unutar postojeće (manja je)."""
    # Postojeća: 01.11 - 05.11
    service.create_restriction(admin_student.id, canteen.id, CreateRestrictionDTO(
        startDate=date(2025, 11, 1), endDate=date(2025, 11, 5), workingHours=[]
    ))
    
    # Nova: 03.11 - 03.11
    dto_new = CreateRestrictionDTO(
        startDate=date(2025, 11, 3),
        endDate=date(2025, 11, 3),
        workingHours=[]
    )
    with pytest.raises(ValueError, match="Postoji preklapanje"):
        service.create_restriction(admin_student.id, canteen.id, dto_new)

def test_create_restriction_touching(service, admin_student, canteen):
    """Restrikcije se dodiruju (jedna do 12.05, druga od 13.05). Treba da prođe."""
    # Prva: 01.11 - 05.11
    service.create_restriction(admin_student.id, canteen.id, CreateRestrictionDTO(
        startDate=date(2025, 11, 1), endDate=date(2025, 11, 5), workingHours=[]
    ))
    
    # Druga: 06.11 - 10.11
    dto_new = CreateRestrictionDTO(
        startDate=date(2025, 11, 6),
        endDate=date(2025, 11, 10),
        workingHours=[]
    )
    # Ovo ne treba da baci grešku
    service.create_restriction(admin_student.id, canteen.id, dto_new)

# --- 3. Business Logic: Vanredni neradni dani ---

def test_restriction_non_working_days_cancellations(service, repo, admin_student, regular_student, canteen):
    """Kreiranje restrikcije 'Neradni dani' i provera da su OTKAZANE sve rezervacije."""
    # Rezervacija doručak
    res1 = repo.add_reservation(Reservation(
        studentId=regular_student.id, canteenId=canteen.id, date=date(2025, 12, 1), time=time(8, 30), duration=30
    ))
    # Rezervacija ručak
    res2 = repo.add_reservation(Reservation(
        studentId=regular_student.id, canteenId=canteen.id, date=date(2025, 12, 1), time=time(12, 0), duration=60
    ))
    
    # Restrikcija: Neradni dan 01.12.
    dto = CreateRestrictionDTO(
        startDate=date(2025, 12, 1), endDate=date(2025, 12, 1), workingHours=[]
    )
    service.create_restriction(admin_student.id, canteen.id, dto)
    
    assert repo.get_reservation_by_id(res1.id).status == "Cancelled"
    assert repo.get_reservation_by_id(res2.id).status == "Cancelled"

def test_restriction_boundary_days_reservations_intact(service, repo, admin_student, regular_student, canteen):
    """Provera da rezervacije dan PRE i dan POSLE restrikcije nisu otkazane."""
    # Dan pre (30.11)
    res_before = repo.add_reservation(Reservation(
        studentId=regular_student.id, canteenId=canteen.id, date=date(2025, 11, 30), time=time(12, 0), duration=60
    ))
    # Dan posle (02.12)
    res_after = repo.add_reservation(Reservation(
        studentId=regular_student.id, canteenId=canteen.id, date=date(2025, 12, 2), time=time(12, 0), duration=60
    ))
    
    # Restrikcija: Neradni dan 01.12.
    dto = CreateRestrictionDTO(
        startDate=date(2025, 12, 1), endDate=date(2025, 12, 1), workingHours=[]
    )
    service.create_restriction(admin_student.id, canteen.id, dto)
    
    assert repo.get_reservation_by_id(res_before.id).status == "Active"
    assert repo.get_reservation_by_id(res_after.id).status == "Active"

# --- 4. Business Logic: Neposluživanje pojedinih obroka ---

def test_restriction_no_dinner(service, repo, admin_student, regular_student, canteen):
    """Kreiranje restrikcije 'Nema večere'. Otkazati večeru, sačuvati doručak/ručak."""
    res_breakfast = repo.add_reservation(Reservation(
        studentId=regular_student.id, canteenId=canteen.id, date=date(2025, 12, 5), time=time(8, 30), duration=30
    ))
    res_lunch = repo.add_reservation(Reservation(
        studentId=regular_student.id, canteenId=canteen.id, date=date(2025, 12, 5), time=time(12, 0), duration=60
    ))
    res_dinner = repo.add_reservation(Reservation(
        studentId=regular_student.id, canteenId=canteen.id, date=date(2025, 12, 5), time=time(19, 0), duration=60
    ))
    
    # Restrikcija: Samo doručak i ručak rade
    wh_breakfast = WorkingHour(meal="breakfast", **{"from": time(8, 0), "to": time(10, 0)})
    wh_lunch = WorkingHour(meal="lunch", **{"from": time(11, 0), "to": time(14, 0)})
    
    dto = CreateRestrictionDTO(
        startDate=date(2025, 12, 5), endDate=date(2025, 12, 5), 
        workingHours=[wh_breakfast, wh_lunch] # Nema večere
    )
    service.create_restriction(admin_student.id, canteen.id, dto)
    
    assert repo.get_reservation_by_id(res_breakfast.id).status == "Active"
    assert repo.get_reservation_by_id(res_lunch.id).status == "Active"
    assert repo.get_reservation_by_id(res_dinner.id).status == "Cancelled"

# --- 5. Business Logic: Skraćeno vreme posluživanja ---

def test_restriction_shortened_hours_boundary_cases(service, repo, admin_student, regular_student, canteen):
    """
    Menza doručak 08-10. Restrikcija skraćuje na 08-09.
    """
    # 1. Završava se PRE limita (08:00 - 08:30) -> Active
    res1 = repo.add_reservation(Reservation(
        studentId=regular_student.id, canteenId=canteen.id, date=date(2025, 12, 10), time=time(8, 0), duration=30
    ))
    # 2. Završava se TAČNO u limit (08:30 - 09:00) -> Active
    res2 = repo.add_reservation(Reservation(
        studentId=regular_student.id, canteenId=canteen.id, date=date(2025, 12, 10), time=time(8, 30), duration=30
    ))
    # 3. Završava se POSLE limita (08:30 - 09:30) -> Cancelled (jer traje 60 min, a limit je 09:00)
    res3 = repo.add_reservation(Reservation(
        studentId=regular_student.id, canteenId=canteen.id, date=date(2025, 12, 10), time=time(8, 30), duration=60
    ))
    # 4. Počinje POSLE limita (09:00 - 09:30) -> Cancelled
    res4 = repo.add_reservation(Reservation(
        studentId=regular_student.id, canteenId=canteen.id, date=date(2025, 12, 10), time=time(9, 0), duration=30
    ))

    # Restrikcija: Doručak 08-09
    wh_short = WorkingHour(meal="breakfast", **{"from": time(8, 0), "to": time(9, 0)})
    dto = CreateRestrictionDTO(
        startDate=date(2025, 12, 10), endDate=date(2025, 12, 10), workingHours=[wh_short]
    )
    service.create_restriction(admin_student.id, canteen.id, dto)
    
    assert repo.get_reservation_by_id(res1.id).status == "Active", "08:00-08:30 should be Active"
    assert repo.get_reservation_by_id(res2.id).status == "Active", "08:30-09:00 should be Active"
    assert repo.get_reservation_by_id(res3.id).status == "Cancelled", "08:30-09:30 should be Cancelled"
    assert repo.get_reservation_by_id(res4.id).status == "Cancelled", "09:00-09:30 should be Cancelled"

def test_restriction_shifted_start_time(service, repo, admin_student, regular_student, canteen):
    """
    Menza doručak 08-10. Restrikcija pomera na 09-10.
    """
    # 08:00 - 08:30 -> Cancelled
    res1 = repo.add_reservation(Reservation(
        studentId=regular_student.id, canteenId=canteen.id, date=date(2025, 12, 11), time=time(8, 0), duration=30
    ))
    # 09:00 - 09:30 -> Active
    res2 = repo.add_reservation(Reservation(
        studentId=regular_student.id, canteenId=canteen.id, date=date(2025, 12, 11), time=time(9, 0), duration=30
    ))

    # Restrikcija: Doručak 09-10
    wh_shifted = WorkingHour(meal="breakfast", **{"from": time(9, 0), "to": time(10, 0)})
    dto = CreateRestrictionDTO(
        startDate=date(2025, 12, 11), endDate=date(2025, 12, 11), workingHours=[wh_shifted]
    )
    service.create_restriction(admin_student.id, canteen.id, dto)
    
    assert repo.get_reservation_by_id(res1.id).status == "Cancelled"
    assert repo.get_reservation_by_id(res2.id).status == "Active"

# --- 7. Testovi Autorizacije ---

def test_create_restriction_as_student(service, regular_student, canteen):
    """Pokušaj kreiranja restrikcije od strane običnog Studenta -> PermissionError."""
    dto = CreateRestrictionDTO(
        startDate=date(2025, 12, 1), endDate=date(2025, 12, 1), workingHours=[]
    )
    with pytest.raises(PermissionError):
        service.create_restriction(regular_student.id, canteen.id, dto)

# --- 8. Napredni Edge Cases i integritet ---

def test_restriction_creation_email_failure_persistence(service, repo, admin_student, regular_student, canteen):
    """
    Transakcioni test: Ako slanje emaila pukne, restrikcija treba ipak da se kreira i rezervacije otkažu.
    (Poželjno ponašanje definisano u zahtevu).
    """
    res = repo.add_reservation(Reservation(
        studentId=regular_student.id, canteenId=canteen.id, date=date(2025, 12, 20), time=time(8, 0), duration=60
    ))
    
    dto = CreateRestrictionDTO(
        startDate=date(2025, 12, 20), endDate=date(2025, 12, 20), workingHours=[]
    )
    
    # Mockujemo email da baci grešku
    with patch.object(service, '_send_cancellation_email', side_effect=Exception("Email server down")):
        # Očekujemo da metoda možda baci exception ili ga proguta, zavisno od implementacije.
        # Ako želimo da uspe uprkos grešci, service mora da uhvati exception.
        # Ako service ne hvata, test će pasti ovde. Za sada pretpostavljamo da service NE hvata, pa ćemo videti.
        # Ali zahtev kaže "Poželjno je da otkazivanje uspe".
        try:
            service.create_restriction(admin_student.id, canteen.id, dto)
        except Exception:
            pass # Ignorišemo grešku emaila da proverimo stanje baze
            
    # Provera stanja
    restriction = repo.get_restrictions_by_canteen_id(canteen.id)
    assert len(restriction) == 1, "Restrikcija bi trebalo da bude kreirana čak i ako email pukne"
    assert repo.get_reservation_by_id(res.id).status == "Cancelled", "Rezervacija bi trebalo da bude otkazana"

def test_delete_restriction_does_not_uncancel(service, repo, admin_student, regular_student, canteen):
    """Brisanje restrikcije ne 'oživljava' magično stare rezervacije."""
    # 1. Kreiraj rezervaciju
    res = repo.add_reservation(Reservation(
        studentId=regular_student.id, canteenId=canteen.id, date=date(2025, 12, 25), time=time(8, 0), duration=60
    ))
    
    # 2. Kreiraj restrikciju koja je otkazuje
    dto = CreateRestrictionDTO(
        startDate=date(2025, 12, 25), endDate=date(2025, 12, 25), workingHours=[]
    )
    service.create_restriction(admin_student.id, canteen.id, dto)
    assert repo.get_reservation_by_id(res.id).status == "Cancelled"
    
    # 3. Obriši restrikciju (simulacija, pošto service.delete_restriction možda ne postoji, brišemo iz repoa direktno ili dodamo metodu)
    # Pretpostavimo da postoji način ili direktno u repo.
    # Repo nema delete_restriction metodu javno izloženu u interfejsu servisa verovatno.
    # Ali možemo simulirati brisanje iz repoa.
    restrictions = repo.get_restrictions_by_canteen_id(canteen.id)
    if restrictions:
        del repo._restrictions[restrictions[0].id]
        
    # 4. Proveri da je rezervacija i dalje Cancelled
    assert repo.get_reservation_by_id(res.id).status == "Cancelled", "Rezervacija ne sme da se aktivira sama od sebe"
