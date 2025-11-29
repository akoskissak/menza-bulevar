from fastapi import FastAPI, HTTPException
from src.api import students, canteens, reservations
from mangum import Mangum
print("APP STARTED LOADING...")
from src.repository.repo import repo 
print("REPO IMPORTED SUCCESSFULLY")

app = FastAPI(title="Rezervacija Menzi")

app.include_router(students.router, prefix="/students", tags=["Students"])
app.include_router(canteens.router, prefix="/canteens", tags=["Canteens"])
app.include_router(reservations.router, prefix="/reservations", tags=["Reservations"])

import asyncio
@app.delete("/cleanup", status_code=204, tags=["Utility"])
async def clear_database():
    try:
        await asyncio.to_thread(repo.clear_all)
        return {}
    except Exception as e:
        print(f"Error in clear_database: {e}")
        raise HTTPException(status_code=500, detail=str(e))

handler = Mangum(app)

