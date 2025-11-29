import pytest
from fastapi.testclient import TestClient
from datetime import date, timedelta
from main import app
from src.repository.repo import repo

@pytest.fixture(autouse=True)
def clean_db():
    """Resetuje bazu pre svakog testa."""
    repo.clear_all()

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def admin_user(client):
    admin_data = {"name": "Admin Tester", "email": "admin@test.com", "isAdmin": True}
    resp = client.post("/students", json=admin_data)
    assert resp.status_code == 201
    return resp.json()

@pytest.fixture
def student_user(client):
    student_data = {"name": "Marko Marković", "email": "marko.markovic@ftn.com"}
    resp = client.post("/students", json=student_data)
    assert resp.status_code == 201
    return resp.json()

@pytest.fixture
def canteen(client, admin_user):
    canteen_data = {
        "name": "Studentski Grad Test",
        "location": "Beograd",
        "capacity": 20,
        "workingHours": [
            {"meal": "breakfast", "from": "08:00", "to": "10:00"},
            {"meal": "lunch", "from": "12:00", "to": "15:00"},
        ]
    }
    headers = {"studentId": admin_user["id"]}
    resp = client.post("/canteens", json=canteen_data, headers=headers)
    assert resp.status_code == 201
    return resp.json()

def test_create_valid_reservation(client, student_user, canteen):
    """Testira uspesno kreiranje validne rezervacije"""
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    
    payload = {
        "studentId": student_user["id"],
        "canteenId": canteen["id"],
        "date": tomorrow,
        "time": "08:30",
        "duration": 30
    }
    
    response = client.post("/reservations", json=payload)
    
    assert response.status_code == 201
    reservation_data = response.json()
    
    assert reservation_data["studentId"] == student_user["id"]
    assert reservation_data["status"] == "Active"

def test_prevent_reservation_overlap(client, student_user, canteen):
    """Testira zabranu kreiranja druge rezervacije koja se preklapa"""
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    
    # Prva rezervacija
    payload1 = {
        "studentId": student_user["id"],
        "canteenId": canteen["id"],
        "date": tomorrow,
        "time": "08:00", 
        "duration": 60 
    }
    client.post("/reservations", json=payload1)

    # Druga (preklapajuca)
    payload2 = {
        "studentId": student_user["id"],
        "canteenId": canteen["id"],
        "date": tomorrow,
        "time": "08:30", 
        "duration": 30 
    }
    
    response = client.post("/reservations", json=payload2)
    
    assert response.status_code == 400 
    assert "Student već ima aktivnu rezervaciju" in response.json()["detail"]

def test_cancel_reservation(client, student_user, canteen):
    """Testira uspesno otkazivanje rezervacije"""
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    
    payload = {
        "studentId": student_user["id"],
        "canteenId": canteen["id"],
        "date": tomorrow,
        "time": "08:30",
        "duration": 30
    }
    create_resp = client.post("/reservations", json=payload)
    reservation_id = create_resp.json()["id"]
    
    headers = {"studentId": student_user["id"]}
    response = client.delete(f"/reservations/{reservation_id}", headers=headers)
    
    assert response.status_code == 200
    assert response.json()["status"] == "Cancelled"

def test_create_reservation_invalid_duration(client, student_user, canteen):
    """Testira neuspesno kreiranje sa trajanjem van granica"""
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    
    payload = {
        "studentId": student_user["id"],
        "canteenId": canteen["id"],
        "date": tomorrow,
        "time": "13:00",
        "duration": 15
    }
    
    response = client.post("/reservations", json=payload)
    assert response.status_code == 400

def test_create_reservation_past_date(client, student_user, canteen):
    """Testira neuspesno kreiranje rezervacije za prosli datum"""
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    
    payload = {
        "studentId": student_user["id"],
        "canteenId": canteen["id"],
        "date": yesterday,
        "time": "12:00",
        "duration": 30
    }
    
    response = client.post("/reservations", json=payload)
    assert response.status_code == 400 

def test_create_reservation_outside_working_hours(client, student_user, canteen):
    """Testira neuspesno kreiranje rezervacije van radnog vremena"""
    tomorrow = (date.today() + timedelta(days=1)).isoformat()

    # Radno vreme je do 15:00
    payload = {
        "studentId": student_user["id"],
        "canteenId": canteen["id"],
        "date": tomorrow,
        "time": "20:00", 
        "duration": 30
    }
    
    response = client.post("/reservations", json=payload)
    assert response.status_code == 400

def test_full_capacity_scenario(client, canteen):
    """
    Testira da li je nemoguce kreirati rezervaciju kada je kapacitet u slotu popunjen (20/20)
    """
    CAPACITY = 20
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    test_time = "12:00"
    
    # Popuni kapacitet
    for i in range(1, CAPACITY + 1):
        student_data = {"name": f"Student {i}", "email": f"test{i}@test.com"}
        student_resp = client.post("/students", json=student_data)
        student_id = student_resp.json()["id"]
        
        payload = {
            "studentId": student_id,
            "canteenId": canteen["id"],
            "date": tomorrow,
            "time": test_time,
            "duration": 30
        }
        client.post("/reservations", json=payload)

    # Pokusaj 21. rezervaciju
    student_data_21 = {"name": "Prebukirani Student", "email": "test21@test.com"}
    student_resp_21 = client.post("/students", json=student_data_21)
    student_id_21 = student_resp_21.json()["id"]

    payload_21 = {
        "studentId": student_id_21,
        "canteenId": canteen["id"],
        "date": tomorrow,
        "time": test_time,
        "duration": 30
    }
    
    response_21 = client.post("/reservations", json=payload_21)
    assert response_21.status_code == 400

def test_create_reservation_nonexistent_canteen(client, student_user):
    """Testira neuspesno kreiranje za nepostojecu menzu"""
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    
    payload = {
        "studentId": student_user["id"],
        "canteenId": "nepostojeci-id", 
        "date": tomorrow,
        "time": "12:00",
        "duration": 30
    }
    
    response = client.post("/reservations", json=payload)
    assert response.status_code == 400 

def test_prevent_overlap_across_duration_boundary(client, canteen):
    """
    Testira da li je zabranjena rezervacija koja pocinje tacno kada se prethodna zavrsava. 
    """
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    
    # Student B
    student_data_B = {"name": "Student B", "email": "studentb@test.com"}
    student_resp_B = client.post("/students", json=student_data_B)
    student_id_B = student_resp_B.json()["id"]

    payload_A = {
        "studentId": student_id_B,
        "canteenId": canteen["id"],
        "date": tomorrow,
        "time": "13:00",
        "duration": 30
    }
    client.post("/reservations", json=payload_A)
    
    # Student C
    student_data_C = {"name": "Student C", "email": "studentc@test.com"}
    student_resp_C = client.post("/students", json=student_data_C)
    student_id_C = student_resp_C.json()["id"]

    # Rezervacija pocinje u 13:30, kada se prva zavrsava. Ovo treba da prodje (nije overlap).
    payload_B = {
        "studentId": student_id_C,
        "canteenId": canteen["id"],
        "date": tomorrow,
        "time": "13:30", 
        "duration": 30 
    }
    
    response = client.post("/reservations", json=payload_B)
    assert response.status_code == 201

def test_cancel_nonexistent_reservation(client, student_user):
    """Testira neuspesno otkazivanje nepostojece rezervacije"""
    headers = {"studentId": student_user["id"]}
    response = client.delete("/reservations/nepostojeci-uuid-za-otkazivanje", headers=headers)
    assert response.status_code == 404

def test_cancel_reservation_by_wrong_student(client, student_user, canteen):
    """Testira neuspesno otkazivanje rezervacije od strane drugog studenta"""
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    
    # Kreiraj rezervaciju kao student_user
    payload = {
        "studentId": student_user["id"],
        "canteenId": canteen["id"],
        "date": tomorrow,
        "time": "08:30",
        "duration": 30
    }
    create_resp = client.post("/reservations", json=payload)
    reservation_id = create_resp.json()["id"]
    
    # Pokusaj otkazati kao Student D
    student_data_D = {"name": "Student D", "email": "studentd@test.com"}
    student_resp_D = client.post("/students", json=student_data_D)
    student_id_D = student_resp_D.json()["id"]

    headers = {"studentId": student_id_D}
    response = client.delete(f"/reservations/{reservation_id}", headers=headers)
    
    assert response.status_code == 403 
    assert "Nije dozvoljeno otkazivanje" in response.json()["detail"]

def test_cancel_already_cancelled_reservation(client, student_user, canteen):
    """Testira neuspesno ponovno otkazivanje rezervacije"""
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    
    payload = {
        "studentId": student_user["id"],
        "canteenId": canteen["id"],
        "date": tomorrow,
        "time": "08:30",
        "duration": 30
    }
    create_resp = client.post("/reservations", json=payload)
    reservation_id = create_resp.json()["id"]

    headers = {"studentId": student_user["id"]}
    
    # Prvo otkazivanje
    client.delete(f"/reservations/{reservation_id}", headers=headers)
    
    # Drugo otkazivanje
    response = client.delete(f"/reservations/{reservation_id}", headers=headers)
    
    assert response.status_code == 400
    assert "Rezervacija je već otkazana" in response.json()["detail"]
