import httpx
import pytest
from datetime import date, timedelta

BASE_URL = "http://localhost:8080" 

STUDENT_ID = None
ADMIN_ID = None
CANTEEN_ID = None
RESERVATION_ID = None

@pytest.fixture(scope="session")
def client():
    """Vraca HTTP klijenta za API pozive i osigurava pracenje redirect-a"""
    return httpx.Client(base_url=BASE_URL, follow_redirects=True)

def test_00_setup_initial_entities(client):
    """
    Kreira Admin i Obicnog studenta, i jednu menzu
    """
    global STUDENT_ID, ADMIN_ID, CANTEEN_ID
    
    admin_data = {"name": "Admin Tester", "email": "admin@test.com", "isAdmin": True}
    admin_resp = client.post("/students", json=admin_data)
    assert admin_resp.status_code == 201
    ADMIN_ID = admin_resp.json()["id"]
    
    student_data = {"name": "Marko Marković", "email": "marko.markovic@ftn.com"}
    student_resp = client.post("/students", json=student_data)
    assert student_resp.status_code == 201
    STUDENT_ID = student_resp.json()["id"]

    canteen_data = {
        "name": "Studentski Grad Test",
        "location": "Beograd",
        "capacity": 20,
        "workingHours": [
            {"meal": "breakfast", "from": "08:00", "to": "10:00"},
            {"meal": "lunch", "from": "12:00", "to": "15:00"},
        ]
    }
    headers = {"studentId": ADMIN_ID}
    canteen_resp = client.post("/canteens", json=canteen_data, headers=headers)
    assert canteen_resp.status_code == 201
    CANTEEN_ID = canteen_resp.json()["id"]


def test_01_create_valid_reservation(client):
    """
    Testira uspesno kreiranje validne rezervacije
    """
    global RESERVATION_ID
    
    assert STUDENT_ID is not None and CANTEEN_ID is not None, "Setup nije uspesno kreirao Student ID i Canteen ID."

    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    
    payload = {
        "studentId": STUDENT_ID,
        "canteenId": CANTEEN_ID,
        "date": tomorrow,
        "time": "08:30",
        "duration": 30
    }
    
    response = client.post("/reservations", json=payload)
    
    assert response.status_code == 201
    reservation_data = response.json()
    
    assert reservation_data["studentId"] == STUDENT_ID
    assert reservation_data["status"] == "Active"
    
    RESERVATION_ID = reservation_data["id"] 


def test_02_prevent_reservation_overlap(client):
    """
    Testira zabranu kreiranja druge rezervacije koja se preklapa
    """
    
    assert STUDENT_ID is not None and CANTEEN_ID is not None, "Setup nije uspesno kreirao Student ID i Canteen ID."

    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    
    payload = {
        "studentId": STUDENT_ID,
        "canteenId": CANTEEN_ID,
        "date": tomorrow,
        "time": "08:00", 
        "duration": 60 
    }
    
    response = client.post("/reservations", json=payload)
    
    assert response.status_code == 400 
    assert "Student već ima aktivnu rezervaciju" in response.json()["detail"]


def test_03_cancel_reservation(client):
    """
    Testira uspesno otkazivanje rezervacije
    """
    
    assert STUDENT_ID is not None and RESERVATION_ID is not None, "Setup nije uspesno kreirala potrebne ID-ove."
    
    headers = {"studentId": STUDENT_ID}
    response = client.delete(f"/reservations/{RESERVATION_ID}", headers=headers)
    
    assert response.status_code == 200
    assert response.json()["status"] == "Cancelled"

def test_04_create_reservation_invalid_duration(client):
    """
    Testira neuspesno kreiranje sa trajanjem van granica
    """
    
    assert STUDENT_ID is not None and CANTEEN_ID is not None

    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    
    payload = {
        "studentId": STUDENT_ID,
        "canteenId": CANTEEN_ID,
        "date": tomorrow,
        "time": "13:00",
        "duration": 15
    }
    
    response = client.post("/reservations", json=payload)
    
    assert response.status_code == 400


def test_05_create_reservation_past_date(client):
    """
    Testira neuspesno kreiranje rezervacije za prosli datum
    """
    
    assert STUDENT_ID is not None and CANTEEN_ID is not None

    yesterday = (date.today() - timedelta(days=1)).isoformat()
    
    payload = {
        "studentId": STUDENT_ID,
        "canteenId": CANTEEN_ID,
        "date": yesterday,
        "time": "12:00",
        "duration": 30
    }
    
    response = client.post("/reservations", json=payload)
    
    assert response.status_code == 400 


def test_06_create_reservation_outside_working_hours(client):
    """
    Testira neuspesno kreiranje rezervacije van radnog vremena
    """
    
    assert STUDENT_ID is not None and CANTEEN_ID is not None

    tomorrow = (date.today() + timedelta(days=1)).isoformat()

    # Radno vreme je do 15:00
    payload = {
        "studentId": STUDENT_ID,
        "canteenId": CANTEEN_ID,
        "date": tomorrow,
        "time": "20:00", 
        "duration": 30
    }
    
    response = client.post("/reservations", json=payload)
    
    assert response.status_code == 400

def test_07_full_capacity_scenario(client):
    """
    Testira da li je nemoguce kreirati rezervaciju kada je kapacitet u slotu popunjen (20/20)
    21. rezervacija bi trebalo da puca sa Status 400
    """
    
    global CANTEEN_ID
    
    assert CANTEEN_ID is not None, "Canteen ID nije postavljen u Setup testu."

    CAPACITY = 20
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    test_time = "12:00"
    
    for i in range(1, CAPACITY + 1):
        student_data = {"name": f"Student tstt. {i}", "email": f"testt{i}@test.com"}
        student_resp = client.post("/students", json=student_data)
        assert student_resp.status_code == 201, f"Neuspeh kreiranja studenta #{i}"
        student_id = student_resp.json()["id"]
        
        payload = {
            "studentId": student_id,
            "canteenId": CANTEEN_ID,
            "date": tomorrow,
            "time": test_time,
            "duration": 30
        }
        reservation_resp = client.post("/reservations", json=payload)
        
        assert reservation_resp.status_code == 201, f"Rezervacija #{i} je neuspesna! Status: {reservation_resp.status_code}, Detalj: {reservation_resp.text}"
        
    print(f"\nUspesno kreirano {CAPACITY} rezervacija za popunjavanje kapaciteta menze.")


    student_data_21 = {"name": "Prebukirani Student", "email": "testt21@test.com"}
    student_resp_21 = client.post("/students", json=student_data_21)
    assert student_resp_21.status_code == 201
    student_id_21 = student_resp_21.json()["id"]

    payload_21 = {
        "studentId": student_id_21,
        "canteenId": CANTEEN_ID,
        "date": tomorrow,
        "time": test_time,
        "duration": 30
    }
    
    response_21 = client.post("/reservations", json=payload_21)
    
    assert response_21.status_code == 400

def test_08_create_reservation_nonexistent_canteen(client):
    """
    Testira neuspesno kreiranje za nepostojecu menzu
    """
    
    assert STUDENT_ID is not None

    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    
    payload = {
        "studentId": STUDENT_ID,
        "canteenId": "nepostojeci-id", 
        "date": tomorrow,
        "time": "12:00",
        "duration": 30
    }
    
    response = client.post("/reservations", json=payload)
    
    assert response.status_code == 400 


def test_09_prevent_overlap_across_duration_boundary(client):
    """
    Testira da li je zabranjena rezervacija koja pocinje tacno kada se prethodna zavrsava. 
    """
    
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    student_data_B = {"name": "Student B", "email": "studentb@test.com", "isAdmin": False}
    student_resp_B = client.post("/students", json=student_data_B)
    STUDENT_ID_B = student_resp_B.json()["id"]

    payload_A = {
        "studentId": STUDENT_ID_B,
        "canteenId": CANTEEN_ID,
        "date": tomorrow,
        "time": "13:00",
        "duration": 30
    }
    client.post("/reservations/", json=payload_A)
    
    student_data_C = {"name": "Student C", "email": "studentc@test.com", "isAdmin": False}
    student_resp_C = client.post("/students", json=student_data_C)
    STUDENT_ID_C = student_resp_C.json()["id"]

    payload_B = {
        "studentId": STUDENT_ID_C,
        "canteenId": CANTEEN_ID,
        "date": tomorrow,
        "time": "13:30", 
        "duration": 30 
    }
    
    response = client.post("/reservations", json=payload_B)
    
    assert response.status_code == 201


def test_10_cancel_nonexistent_reservation(client):
    """
    Testira neuspesno otkazivanje nepostojece rezervacije
    """
    
    assert STUDENT_ID is not None
    
    headers = {"studentId": STUDENT_ID}
    response = client.delete("/reservations/nepostojeci-uuid-za-otkazivanje", headers=headers)
    
    assert response.status_code == 404


def test_11_cancel_reservation_by_wrong_student(client):
    """
    Testira neuspesno otkazivanje rezervacije od strane drugog studenta
    """
    
    assert RESERVATION_ID is not None
    
    student_data_D = {"name": "Student D", "email": "studentd@test.com"}
    student_resp_D = client.post("/students", json=student_data_D)
    STUDENT_ID_D = student_resp_D.json()["id"]

    headers = {"studentId": STUDENT_ID_D}
    response = client.delete(f"/reservations/{RESERVATION_ID}", headers=headers)
    
    assert response.status_code == 403 
    assert "Nije dozvoljeno otkazivanje" in response.json()["detail"]


def test_12_cancel_already_cancelled_reservation(client):
    """
    Testira neuspesno ponovno otkazivanje rezervacije
    """
    
    assert RESERVATION_ID is not None 

    headers = {"studentId": STUDENT_ID}
    response = client.delete(f"/reservations/{RESERVATION_ID}", headers=headers)
    
    assert response.status_code == 400
    assert "Rezervacija je već otkazana" in response.json()["detail"]