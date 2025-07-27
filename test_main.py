import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to FastAPI!", "status": "running"}

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_db_status():
    response = client.get("/db-status")
    assert response.status_code == 200
    # Проверяем что ответ содержит информацию о статусе базы данных
    json_response = response.json()
    assert "database" in json_response
    assert "status" in json_response
