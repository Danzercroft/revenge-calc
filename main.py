from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy import text
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager
import logging
import os

from database import engine, get_db
from data_collection_service import data_collection_service

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    data_collection_service.start_scheduler()
    yield
    # Shutdown
    data_collection_service.stop_scheduler()

app = FastAPI(
    title="Revenge Calculator API",
    description="A FastAPI application for collecting cryptocurrency market data",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# Root endpoint - serve monitoring dashboard
@app.get("/")
async def read_root():
    if os.path.exists("static/index.html"):
        return FileResponse("static/index.html")
    return {"message": "Welcome to FastAPI!", "status": "running"}

# API Root endpoint
@app.get("/api")
async def api_root():
    return {"message": "Revenge Calculator API", "status": "running"}

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Database connection test endpoint
@app.get("/db-status")
async def check_database():
    try:
        # Test database connection
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            return {"database": "connected", "status": "healthy"}
    except Exception as e:
        return {"database": "disconnected", "status": "error", "error": str(e)}


# Status endpoint for data collection
@app.get("/data-collection-status")
async def get_data_collection_status():
    """Получить статус сервиса сбора данных"""
    try:
        jobs = []
        for job in data_collection_service.scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None
            })
        
        return {
            "status": "running" if data_collection_service.scheduler.running else "stopped",
            "jobs": jobs
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


# Manual trigger endpoints for testing
@app.post("/trigger-current-collection")
async def trigger_current_collection():
    """Запустить сбор текущих свечей вручную"""
    try:
        await data_collection_service.collect_current_candles()
        return {"status": "success", "message": "Current candles collection triggered"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/trigger-historical-collection")
async def trigger_historical_collection():
    """Запустить сбор исторических свечей вручную"""
    try:
        await data_collection_service.collect_historical_candles()
        return {"status": "success", "message": "Historical candles collection triggered"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


# Statistics endpoint
@app.get("/stats")
async def get_statistics(db: Session = Depends(get_db)):
    """Получить статистику собранных данных"""
    try:
        total_candles = db.execute(text("SELECT COUNT(*) FROM candles")).scalar()
        total_exchanges = db.execute(text("SELECT COUNT(*) FROM exchanges")).scalar()
        total_pairs = db.execute(text("SELECT COUNT(*) FROM currency_pairs")).scalar()
        total_periods = db.execute(text("SELECT COUNT(*) FROM time_periods")).scalar()
        
        # Последние обновления по биржам
        latest_updates = db.execute(text("""
            SELECT e.name as exchange_name, MAX(c.created_at) as last_update
            FROM candles c
            JOIN exchanges e ON c.exchange_id = e.id
            GROUP BY e.id, e.name
            ORDER BY last_update DESC
        """)).fetchall()
        
        return {
            "total_candles": total_candles,
            "total_exchanges": total_exchanges,
            "total_currency_pairs": total_pairs,
            "total_time_periods": total_periods,
            "latest_updates": [
                {"exchange": row[0], "last_update": row[1].isoformat() if row[1] else None}
                for row in latest_updates
            ]
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
