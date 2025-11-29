import uuid
from datetime import date, time
from typing import List, Optional

import boto3
from boto3.dynamodb.conditions import Key

from src.domain.models import Student, Canteen, Reservation, WorkingHour

dynamodb = boto3.resource("dynamodb")

students_table = dynamodb.Table("Students")
canteens_table = dynamodb.Table("Canteens")
reservations_table = dynamodb.Table("Reservations")


class DynamoRepository:
    def add_student(self, data: Student) -> Student:
        response = students_table.query(
            IndexName="EmailIndex",
            KeyConditionExpression=Key("email").eq(data.email)
        )
        if response.get("Items"):
            raise ValueError(f"Student sa ovim email-om {data.email} već postoji.")

        new_id = str(uuid.uuid4())
        item = data.model_dump()
        item["id"] = new_id
        students_table.put_item(Item=item)
        return data.model_copy(update={"id": new_id})

    def get_student_by_id(self, student_id: str) -> Optional[Student]:
        response = students_table.get_item(Key={"id": student_id})
        item = response.get("Item")
        if not item:
            return None
        return Student(**item)

    def get_student_by_email(self, email: str) -> Optional[Student]:
        response = students_table.query(
            IndexName="EmailIndex",
            KeyConditionExpression=Key("email").eq(email)
        )
        items = response.get("Items", [])
        if not items:
            return None
        return Student(**items[0])

    def add_canteen(self, data: Canteen) -> Canteen:
        new_id = str(uuid.uuid4())
        item = data.model_dump()
        item["id"] = new_id
        item["workingHours"] = [wh.model_dump() for wh in data.workingHours]
        canteens_table.put_item(Item=item)
        return data.model_copy(update={"id": new_id})

    def get_canteen_by_id(self, canteen_id: str) -> Optional[Canteen]:
        response = canteens_table.get_item(Key={"id": canteen_id})
        item = response.get("Item")
        if not item:
            return None
        wh_list = [WorkingHour(**wh) for wh in item.get("workingHours", [])]
        item["workingHours"] = wh_list
        return Canteen(**item)

    def get_all_canteens(self) -> List[Canteen]:
        response = canteens_table.scan()
        items = response.get("Items", [])
        canteens = []
        for item in items:
            wh_list = [WorkingHour(**wh) for wh in item.get("workingHours", [])]
            item["workingHours"] = wh_list
            canteens.append(Canteen(**item))
        return canteens

    def update_canteen(self, canteen_id: str, data: dict) -> Optional[Canteen]:
        existing = self.get_canteen_by_id(canteen_id)
        if not existing:
            return None
        updated = existing.model_copy(update=data)
        item = updated.model_dump()
        item["workingHours"] = [wh.model_dump() for wh in updated.workingHours]
        canteens_table.put_item(Item=item)
        return updated

    def delete_canteen(self, canteen_id: str) -> bool:
        canteens_table.delete_item(Key={"id": canteen_id})
        self.delete_reservations_by_canteen_id(canteen_id)
        return True

    def add_reservation(self, data: Reservation) -> Reservation:
        new_id = str(uuid.uuid4())
        item = data.model_dump()
        item["id"] = new_id
        # Serialize time
        item["time"] = data.time.strftime("%H:%M")
        reservations_table.put_item(Item=item)
        return data.model_copy(update={"id": new_id})

    def get_reservation_by_id(self, reservation_id: str) -> Optional[Reservation]:
        response = reservations_table.get_item(Key={"id": reservation_id})
        item = response.get("Item")
        if not item:
            return None
        item["time"] = time.fromisoformat(item["time"])
        return Reservation(**item)

    def get_reservations_by_student_id(self, student_id: str) -> List[Reservation]:
        response = reservations_table.query(
            IndexName="StudentIndex",
            KeyConditionExpression=Key("studentId").eq(student_id)
        )
        items = response.get("Items", [])
        for item in items:
            item["time"] = time.fromisoformat(item["time"])
        return [Reservation(**item) for item in items]

    def cancel_reservation(self, reservation_id: str) -> Optional[Reservation]:
        reservation = self.get_reservation_by_id(reservation_id)
        if not reservation:
            return None
        reservation.status = "Cancelled"
        item = reservation.model_dump()
        item["time"] = reservation.time.strftime("%H:%M")
        reservations_table.put_item(Item=item)
        return reservation

    def get_active_reservations_by_canteen_and_date(
        self, canteen_id: str, reservation_date: date
    ) -> List[Reservation]:
        response = reservations_table.query(
            IndexName="CanteenIndex",
            KeyConditionExpression=Key("canteenId").eq(canteen_id)
        )
        items = response.get("Items", [])
        result = []
        for item in items:
            if item["status"] == "Active" and item["date"] == reservation_date.isoformat():
                item["time"] = time.fromisoformat(item["time"])
                result.append(Reservation(**item))
        return result

    def delete_reservations_by_canteen_id(self, canteen_id: str) -> int:
        items = self.get_active_reservations_by_canteen_and_date(canteen_id, date.today())
        count = 0
        for res in items:
            reservations_table.delete_item(Key={"id": res.id})
            count += 1
        return count

    def clear_all(self):
        for table in [students_table, canteens_table, reservations_table]:
            scan = table.scan()
            with table.batch_writer() as batch:
                for item in scan.get("Items", []):
                    batch.delete_item(Key={"id": item["id"]})


repo = DynamoRepository()