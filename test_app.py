"""
Тестовая версия FastAPI приложения без планировщика для изоляции тестов
"""
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy import text
from sqlalchemy.orm import Session
import logging
import os

from database import engine, get_db
from logging_config import setup_logging

# Настройка логирования с сохранением в файлы для тестов
setup_logging(log_dir="logs/tests", log_level=logging.DEBUG)

# Создаем приложение БЕЗ lifespan для тестов
app = FastAPI(
    title="Revenge Calculator API (Test)",
    description="A FastAPI application for collecting cryptocurrency market data (Test Version)",
    version="1.0.0-test"
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

# Status endpoint for data collection (мокированный для тестов)
@app.get("/data-collection-status")
async def get_data_collection_status():
    """Получить статус сервиса сбора данных (тестовая версия)"""
    return {
        "status": "mocked",
        "jobs": [
            {
                "id": "collect_current_candles",
                "name": "Collect Current Candles",
                "next_run": "2023-01-01T12:00:00"
            }
        ]
    }

# Manual trigger endpoints for testing (мокированные)
@app.post("/trigger-current-collection")
async def trigger_current_collection():
    """Запустить сбор текущих свечей вручную (тестовая версия)"""
    return {"status": "success", "message": "Current candles collection triggered (mocked)"}

@app.post("/trigger-historical-collection")
async def trigger_historical_collection():
    """Запустить сбор исторических свечей вручную (тестовая версия)"""
    return {"status": "success", "message": "Historical candles collection triggered (mocked)"}

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
                {
                    "exchange": row[0], 
                    "last_update": row[1].isoformat() if row[1] and hasattr(row[1], 'isoformat') else str(row[1]) if row[1] else None
                }
                for row in latest_updates
            ]
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}
