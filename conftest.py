"""
Общие фикстуры для всех тестов проекта revenge-calc
"""
import pytest
import asyncio
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import Mock, AsyncMock

import models
from database import Base


@pytest.fixture(scope="session")
def event_loop():
    """Создает event loop для всей сессии тестирования"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_db_engine():
    """Создает тестовый движок базы данных"""
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={
            "check_same_thread": False,
            "isolation_level": None
        },
        poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def test_db_session(test_db_engine):
    """Создает сессию тестовой базы данных"""
    testing_session_local = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_db_engine
    )
    session = testing_session_local()
    yield session
    session.close()


@pytest.fixture
def sample_exchange():
    """Создает образец биржи для тестов"""
    return models.Exchange(
        name="Test Exchange",
        code="test",
        environment="sandbox",
        api_key="test_api_key",
        api_secret="test_api_secret",
        is_active=True
    )


@pytest.fixture
def sample_binance_exchange():
    """Создает образец биржи Binance для тестов"""
    return models.Exchange(
        name="Binance",
        code="binance",
        environment="production",
        api_key="binance_api_key",
        api_secret="binance_api_secret",
        is_active=True
    )


@pytest.fixture
def sample_okx_exchange():
    """Создает образец биржи OKX с passphrase для тестов"""
    return models.Exchange(
        name="OKX",
        code="okx",
        environment="sandbox",
        api_key="okx_api_key",
        api_secret="okx_api_secret",
        api_passphrase="okx_passphrase",
        is_active=True
    )


@pytest.fixture
def sample_symbols():
    """Создает образцы символов для тестов"""
    btc = models.Symbol(
        name="Bitcoin",
        symbol="BTC",
        description="Bitcoin cryptocurrency",
        is_active=True
    )
    
    usdt = models.Symbol(
        name="Tether",
        symbol="USDT",
        description="Tether stablecoin",
        is_active=True
    )
    
    eth = models.Symbol(
        name="Ethereum",
        symbol="ETH",
        description="Ethereum cryptocurrency",
        is_active=True
    )
    
    return {"BTC": btc, "USDT": usdt, "ETH": eth}


@pytest.fixture
def sample_currency_pair(sample_symbols):
    """Создает образец валютной пары для тестов"""
    btc = sample_symbols["BTC"]
    usdt = sample_symbols["USDT"]
    
    pair = models.CurrencyPair(
        base_symbol_id=btc.id,
        quote_symbol_id=usdt.id,
        type="spot",
        is_active=True
    )
    pair.base_symbol = btc
    pair.quote_symbol = usdt
    return pair


@pytest.fixture
def sample_time_periods():
    """Создает образцы периодов времени для тестов"""
    return [
        models.TimePeriod(name="1 minute", minutes=1, is_active=True),
        models.TimePeriod(name="5 minutes", minutes=5, is_active=True),
        models.TimePeriod(name="15 minutes", minutes=15, is_active=True),
        models.TimePeriod(name="1 hour", minutes=60, is_active=True),
        models.TimePeriod(name="1 day", minutes=1440, is_active=True),
    ]


@pytest.fixture
def sample_candle_data():
    """Создает образец данных свечи для тестов"""
    return {
        'timestamp': datetime(2023, 1, 1, 12, 0, tzinfo=timezone.utc),
        'open': 50000.0,
        'high': 51000.0,
        'low': 49000.0,
        'close': 50500.0,
        'volume': 100.5
    }


@pytest.fixture
def sample_candles_batch():
    """Создает пакет образцов данных свечей для тестов"""
    base_time = datetime(2023, 1, 1, 12, 0, tzinfo=timezone.utc)
    candles = []
    
    for i in range(10):
        candle = {
            'timestamp': base_time.replace(minute=i),
            'open': 50000.0 + i * 50,
            'high': 51000.0 + i * 50,
            'low': 49000.0 + i * 50,
            'close': 50500.0 + i * 50,
            'volume': 100.0 + i * 5
        }
        candles.append(candle)
    
    return candles


@pytest.fixture
def mock_ccxt_exchange():
    """Создает мок для CCXT биржи"""
    mock_exchange = Mock()
    mock_exchange.fetch_ohlcv = AsyncMock()
    mock_exchange.load_markets = AsyncMock()
    mock_exchange.has = {"fetchOHLCV": True}
    return mock_exchange


@pytest.fixture
def populated_test_db(test_db_session, sample_exchange, sample_symbols, sample_currency_pair, sample_time_periods):
    """Заполняет тестовую БД полным набором тестовых данных"""
    # Добавляем базовые объекты
    test_db_session.add(sample_exchange)
    test_db_session.add_all(sample_symbols.values())
    test_db_session.commit()
    
    # Устанавливаем правильные ID для валютной пары после commit
    sample_currency_pair.base_symbol_id = sample_symbols["BTC"].id
    sample_currency_pair.quote_symbol_id = sample_symbols["USDT"].id
    
    test_db_session.add(sample_currency_pair)
    test_db_session.add_all(sample_time_periods)
    test_db_session.commit()
    
    # Создаем свечи для каждого периода времени
    candles = []
    base_time = datetime(2023, 1, 1, 12, 0, tzinfo=timezone.utc)
    
    for period in sample_time_periods:
        for i in range(5):  # 5 свечей на каждый период
            timestamp = base_time.replace(minute=i * period.minutes)
            candle = models.Candle(
                currency_pair_id=sample_currency_pair.id,
                exchange_id=sample_exchange.id,
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


@pytest.fixture
def sample_user():
    """Создает образец пользователя для тестов"""
    return models.User(
        name="Test User",
        email="test@example.com",
        password="hashed_password_123"
    )


@pytest.fixture
def sample_exchange_configuration(sample_user, sample_exchange):
    """Создает образец конфигурации биржи для тестов"""
    return models.ExchangeConfiguration(
        exchange_id=sample_exchange.id,
        user_id=sample_user.id,
        api_key="user_api_key",
        api_secret="user_api_secret",
        sandbox_mode=True
    )


# Фикстуры для мокирования
@pytest.fixture
def mock_session_local():
    """Мок для SessionLocal"""
    return Mock()


@pytest.fixture
def mock_data_collection_service():
    """Мок для data_collection_service"""
    mock_service = Mock()
    mock_service.collect_current_candles = AsyncMock()
    mock_service.collect_historical_candles = AsyncMock()
    mock_service.scheduler = Mock()
    mock_service.scheduler.running = True
    
    # Создаем мок job для тестов
    mock_job = Mock()
    mock_job.id = "collect_current_candles"
    mock_job.name = "Collect Current Candles"
    mock_job.next_run_time = None
    
    mock_service.scheduler.get_jobs = Mock(return_value=[mock_job])
    mock_service.start_scheduler = Mock()
    mock_service.stop_scheduler = Mock()
    return mock_service


@pytest.fixture
def mock_exchange_service():
    """Мок для exchange_service"""
    mock_service = Mock()
    mock_service.get_exchange_instance = Mock()
    mock_service.fetch_current_candle = AsyncMock()
    mock_service.fetch_historical_candles = AsyncMock()
    mock_service.get_missing_candles_timerange = AsyncMock()
    return mock_service


# Утилитарные фикстуры
@pytest.fixture
def datetime_now():
    """Возвращает текущее время в UTC"""
    return datetime.now(timezone.utc)


@pytest.fixture
def datetime_yesterday():
    """Возвращает вчерашнее время в UTC"""
    from datetime import timedelta
    return datetime.now(timezone.utc) - timedelta(days=1)


@pytest.fixture
def datetime_week_ago():
    """Возвращает время неделю назад в UTC"""
    from datetime import timedelta
    return datetime.now(timezone.utc) - timedelta(weeks=1)


# Маркеры для pytest
def pytest_configure(config):
    """Конфигурация pytest с пользовательскими маркерами"""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "api: API tests")
    config.addinivalue_line("markers", "database: Database tests")
    config.addinivalue_line("markers", "slow: Slow tests")
    config.addinivalue_line("markers", "performance: Performance tests")


# Hooks для pytest
def pytest_collection_modifyitems(config, items):
    """Автоматически добавляет маркеры к тестам на основе их расположения"""
    for item in items:
        # Маркируем асинхронные тесты
        if asyncio.iscoroutinefunction(item.function):
            item.add_marker(pytest.mark.asyncio)
        
        # Маркируем тесты по файлам
        if "test_main" in item.nodeid:
            item.add_marker(pytest.mark.api)
        elif "test_models" in item.nodeid:
            item.add_marker(pytest.mark.database)
        elif "test_data_collection" in item.nodeid:
            item.add_marker(pytest.mark.unit)
        elif "test_exchange" in item.nodeid:
            item.add_marker(pytest.mark.unit)
        
        # Маркируем медленные тесты
        if "performance" in item.name.lower() or "large" in item.name.lower():
            item.add_marker(pytest.mark.slow)
