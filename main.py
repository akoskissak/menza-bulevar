from fastapi import FastAPI
from src.api import students, canteens, reservations

app = FastAPI(title="Rezervacija Menzi")

app.include_router(students.router, prefix="/students", tags=["Students"])
app.include_router(canteens.router, prefix="/canteens", tags=["Canteens"])
app.include_router(reservations.router, prefix="/reservations", tags=["Reservations"])

from src.repository.repo import repo 
@app.post("/clear-database", status_code=204, tags=["Utility"])
async def clear_database():
    repo.clear_all()
    return {}