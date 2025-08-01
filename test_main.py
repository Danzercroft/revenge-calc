"""
Тестирование основного FastAPI приложения.

Содержит тесты для всех эндпоинтов API и проверку их корректной работы.
"""
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

import models
from main import app, get_db
from database import get_engine  # Используем тестовое приложение БЕЗ планировщика


@pytest.fixture
def client(test_db_session, test_db_engine, mock_data_collection_service):
    """Создает тестовый клиент FastAPI с тестовой БД"""
    def override_get_db():
        try:
            yield test_db_session
        finally:
            test_db_session.close()

    def override_get_engine():
        return test_db_engine

    # Переопределяем dependency functions
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_engine] = override_get_engine

    # Мокируем data_collection_service в main модуле
    with patch('main.data_collection_service', mock_data_collection_service):
        with TestClient(app) as test_client:
            yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def populated_test_db(test_db_session):
    """Заполняет тестовую БД тестовыми данными"""
    # Создаем биржу
    exchange = models.Exchange(
        name="Test Exchange",
        code="test",
        environment="sandbox",
        is_active=True
    )

    # Создаем символы
    btc = models.Symbol(name="Bitcoin", symbol="BTC", is_active=True)
    usdt = models.Symbol(name="Tether", symbol="USDT", is_active=True)

    # Создаем валютную пару
    test_db_session.add_all([exchange, btc, usdt])
    test_db_session.commit()

    pair = models.CurrencyPair(
        base_symbol_id=btc.id,
        quote_symbol_id=usdt.id,
        type="spot",
        is_active=True
    )

    # Создаем период времени
    period = models.TimePeriod(
        name="1 minute",
        minutes=1,
        is_active=True
    )

    test_db_session.add_all([pair, period])
    test_db_session.commit()

    # Создаем тестовые свечи
    candles = []
    for i in range(5):
        timestamp = datetime(2023, 1, 1, 12, i, tzinfo=timezone.utc)
        candle = models.Candle(
            currency_pair_id=pair.id,
            exchange_id=exchange.id,
            time_period_id=period.id,
            open_time=timestamp,
            close_time=timestamp,
            open_price=50000.0 + i * 100,
            high_price=51000.0 + i * 100,
            low_price=49000.0 + i * 100,
            close_price=50500.0 + i * 100,
            volume=100.0 + i * 10,
            quote_volume=0,
            trades_count=0
        )
        candles.append(candle)

    test_db_session.add_all(candles)
    test_db_session.commit()

    return test_db_session


class TestMainAPI:
    """Тесты для основных эндпоинтов API"""

    def test_read_root_without_static_file(self, client):
        """Тестирует корневой endpoint без статического файла"""
        with patch('os.path.exists', return_value=False):
            response = client.get("/")
            assert response.status_code == 200
            assert response.json() == {"message": "Welcome to FastAPI!", "status": "running"}

    def test_api_root(self, client):
        """Тестирует API root endpoint"""
        response = client.get("/api")
        assert response.status_code == 200
        assert response.json() == {"message": "Revenge Calculator API", "status": "running"}

    def test_health_check(self, client):
        """Тестирует health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}

    def test_db_status_success(self, client):
        """Тестирует успешную проверку статуса БД"""
        response = client.get("/db-status")
        assert response.status_code == 200
        json_response = response.json()
        assert "database" in json_response
        assert "status" in json_response
        assert json_response["status"] == "healthy"

    def test_data_collection_status_mocked(self, client):
        """Тестирует мокированный статус сбора данных"""
        response = client.get("/data-collection-status")
        assert response.status_code == 200
        json_response = response.json()
        assert json_response["status"] == "running"
        assert len(json_response["jobs"]) == 1
        assert json_response["jobs"][0]["id"] == "collect_current_candles"

    def test_trigger_current_collection_mocked(self, client):
        """Тестирует мокированный запуск сбора текущих свечей"""
        response = client.post("/trigger-current-collection")
        assert response.status_code == 200
        json_response = response.json()
        assert json_response["status"] == "success"
        assert "Current candles collection triggered" in json_response["message"]

    def test_trigger_historical_collection_mocked(self, client):
        """Тестирует мокированный запуск сбора исторических свечей"""
        response = client.post("/trigger-historical-collection")
        assert response.status_code == 200
        json_response = response.json()
        assert json_response["status"] == "success"
        assert "Historical candles collection triggered" in json_response["message"]

    def test_stats_success(self, client, populated_test_db):
        """Тестирует успешное получение статистики"""
        response = client.get("/stats")
        assert response.status_code == 200
        json_response = response.json()

        assert "total_candles" in json_response
        assert "total_exchanges" in json_response
        assert "total_currency_pairs" in json_response
        assert "total_time_periods" in json_response
        assert "latest_updates" in json_response

        assert json_response["total_candles"] == 5
        assert json_response["total_exchanges"] == 1
        assert json_response["total_currency_pairs"] == 1
        assert json_response["total_time_periods"] == 1

    def test_stats_with_empty_database(self, client):
        """Тестирует получение статистики с пустой БД"""
        response = client.get("/stats")
        assert response.status_code == 200
        json_response = response.json()

        assert json_response["total_candles"] == 0
        assert json_response["total_exchanges"] == 0
        assert json_response["total_currency_pairs"] == 0
        assert json_response["total_time_periods"] == 0
        assert json_response["latest_updates"] == []


# Интеграционные тесты
class TestAPIIntegration:
    """Интеграционные тесты для проверки совместной работы компонентов"""

    def test_api_health_check_sequence(self, client):
        """Интеграционный тест: последовательность проверок здоровья API"""
        # Проверяем основные endpoints в последовательности
        endpoints = ["/health", "/api", "/db-status", "/data-collection-status"]

        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code == 200
            assert response.json() is not None

    def test_trigger_endpoints_sequence(self, client):
        """Интеграционный тест: последовательность ручных запусков"""
        # Запускаем сбор текущих данных
        response1 = client.post("/trigger-current-collection")
        assert response1.status_code == 200
        assert response1.json()["status"] == "success"

        # Запускаем сбор исторических данных
        response2 = client.post("/trigger-historical-collection")
        assert response2.status_code == 200
        assert response2.json()["status"] == "success"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
