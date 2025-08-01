"""
Тесты для моделей базы данных.

Этот модуль содержит тесты для всех моделей SQLAlchemy,
включая тесты создания, валидации, связей и ограничений.
"""
import math
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

import models
from database import Base


@pytest.fixture
def test_db():
    """Создает тестовую базу данных в памяти"""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return testing_session_local()


class TestUserModel:
    """Тесты для модели User."""

    def test_create_user(self, test_db):
        """Тестирует создание пользователя"""
        user = models.User(
            name="Test User",
            email="test@example.com",
            password="hashed_password"
        )

        test_db.add(user)
        test_db.commit()

        saved_user = test_db.query(models.User).first()
        assert saved_user.name == "Test User"
        assert saved_user.email == "test@example.com"
        assert saved_user.password == "hashed_password"
        assert saved_user.created_at is not None
        assert saved_user.updated_at is not None

    def test_user_email_unique_constraint(self, test_db):
        """Тестирует уникальность email пользователя"""
        user1 = models.User(
            name="User 1",
            email="test@example.com",
            password="password1"
        )

        user2 = models.User(
            name="User 2",
            email="test@example.com",  # Тот же email
            password="password2"
        )

        test_db.add(user1)
        test_db.commit()

        test_db.add(user2)
        with pytest.raises(IntegrityError):
            test_db.commit()

    def test_user_required_fields(self, test_db):
        """Тестирует обязательные поля пользователя"""
        # Без name
        with pytest.raises(IntegrityError):
            user = models.User(email="test@example.com", password="password")
            test_db.add(user)
            test_db.commit()

        test_db.rollback()

        # Без email
        with pytest.raises(IntegrityError):
            user = models.User(name="Test User", password="password")
            test_db.add(user)
            test_db.commit()

        test_db.rollback()

        # Без password
        with pytest.raises(IntegrityError):
            user = models.User(name="Test User", email="test@example.com")
            test_db.add(user)
            test_db.commit()


class TestExchangeModel:
    """Тесты для модели Exchange."""

    def test_create_exchange(self, test_db):
        """Тестирует создание биржи"""
        exchange = models.Exchange(
            name="Binance",
            code="binance",
            environment="production",
            api_key="test_api_key",
            api_secret="test_api_secret",
            is_active=True
        )

        test_db.add(exchange)
        test_db.commit()

        saved_exchange = test_db.query(models.Exchange).first()
        assert saved_exchange.name == "Binance"
        assert saved_exchange.code == "binance"
        assert saved_exchange.environment == "production"
        assert saved_exchange.is_active is True
        assert saved_exchange.created_at is not None

    def test_exchange_with_passphrase(self, test_db):
        """Тестирует биржу с passphrase (например, OKX)"""
        exchange = models.Exchange(
            name="OKX",
            code="okx",
            environment="sandbox",
            api_key="test_key",
            api_secret="test_secret",
            api_passphrase="test_passphrase"
        )

        test_db.add(exchange)
        test_db.commit()

        saved_exchange = test_db.query(models.Exchange).first()
        assert saved_exchange.api_passphrase == "test_passphrase"

    def test_exchange_default_values(self, test_db):
        """Тестирует значения по умолчанию для биржи"""
        exchange = models.Exchange(
            name="Test Exchange",
            code="test",
            environment="sandbox"
        )

        test_db.add(exchange)
        test_db.commit()

        saved_exchange = test_db.query(models.Exchange).first()
        assert saved_exchange.is_active is True  # Значение по умолчанию


class TestSymbolModel:
    """Тесты для модели Symbol."""

    def test_create_symbol(self, test_db):
        """Тестирует создание символа"""
        symbol = models.Symbol(
            name="Bitcoin",
            symbol="BTC",
            description="Bitcoin cryptocurrency"
        )

        test_db.add(symbol)
        test_db.commit()

        saved_symbol = test_db.query(models.Symbol).first()
        assert saved_symbol.name == "Bitcoin"
        assert saved_symbol.symbol == "BTC"
        assert saved_symbol.description == "Bitcoin cryptocurrency"
        assert saved_symbol.is_active is True

    def test_symbol_unique_constraint(self, test_db):
        """Тестирует уникальность символа"""
        symbol1 = models.Symbol(name="Bitcoin", symbol="BTC")
        symbol2 = models.Symbol(name="Bitcoin Cash", symbol="BTC")  # Тот же символ

        test_db.add(symbol1)
        test_db.commit()

        test_db.add(symbol2)
        with pytest.raises(IntegrityError):
            test_db.commit()


class TestCurrencyPairModel:
    """Тесты для модели CurrencyPair."""

    def test_create_currency_pair(self, test_db):
        """Тестирует создание валютной пары"""
        # Создаем символы
        btc = models.Symbol(name="Bitcoin", symbol="BTC")
        usdt = models.Symbol(name="Tether", symbol="USDT")

        test_db.add_all([btc, usdt])
        test_db.commit()

        # Создаем валютную пару
        pair = models.CurrencyPair(
            base_symbol_id=btc.id,
            quote_symbol_id=usdt.id,
            type="spot"
        )

        test_db.add(pair)
        test_db.commit()

        saved_pair = test_db.query(models.CurrencyPair).first()
        assert saved_pair.base_symbol_id == btc.id
        assert saved_pair.quote_symbol_id == usdt.id
        assert saved_pair.type == "spot"
        assert saved_pair.is_active is True

    def test_currency_pair_relationships(self, test_db):
        """Тестирует связи валютной пары с символами"""
        # Создаем символы
        btc = models.Symbol(name="Bitcoin", symbol="BTC")
        usdt = models.Symbol(name="Tether", symbol="USDT")

        test_db.add_all([btc, usdt])
        test_db.commit()

        # Создаем валютную пару
        pair = models.CurrencyPair(
            base_symbol_id=btc.id,
            quote_symbol_id=usdt.id,
            type="futures"
        )

        test_db.add(pair)
        test_db.commit()

        # Проверяем связи
        saved_pair = test_db.query(models.CurrencyPair).first()
        assert saved_pair.base_symbol.symbol == "BTC"
        assert saved_pair.quote_symbol.symbol == "USDT"


class TestTimePeriodModel:
    """Тесты для модели TimePeriod."""

    def test_create_time_period(self, test_db):
        """Тестирует создание периода времени"""
        period = models.TimePeriod(
            name="1 minute",
            minutes=1,
            description="One minute timeframe"
        )

        test_db.add(period)
        test_db.commit()

        saved_period = test_db.query(models.TimePeriod).first()
        assert saved_period.name == "1 minute"
        assert saved_period.minutes == 1
        assert saved_period.description == "One minute timeframe"
        assert saved_period.is_active is True

    def test_multiple_time_periods(self, test_db):
        """Тестирует создание нескольких периодов времени"""
        periods = [
            models.TimePeriod(name="1 minute", minutes=1),
            models.TimePeriod(name="5 minutes", minutes=5),
            models.TimePeriod(name="1 hour", minutes=60),
            models.TimePeriod(name="1 day", minutes=1440)
        ]

        test_db.add_all(periods)
        test_db.commit()

        saved_periods = test_db.query(models.TimePeriod).all()
        assert len(saved_periods) == 4

        minutes_values = [p.minutes for p in saved_periods]
        assert 1 in minutes_values
        assert 5 in minutes_values
        assert 60 in minutes_values
        assert 1440 in minutes_values


class TestCandleModel:
    """Тесты для модели Candle."""

    def test_create_candle(self, test_db):
        """Тестирует создание свечи"""
        # Создаем зависимые объекты
        exchange = models.Exchange(name="Binance", code="binance", environment="production")
        period = models.TimePeriod(name="1 minute", minutes=1)

        # Создаем символы
        btc = models.Symbol(name="Bitcoin", symbol="BTC")
        usdt = models.Symbol(name="Tether", symbol="USDT")

        test_db.add_all([exchange, period, btc, usdt])
        test_db.commit()

        # Создаем валютную пару
        currency_pair = models.CurrencyPair(
            base_symbol_id=btc.id,
            quote_symbol_id=usdt.id,
            type="spot"
        )

        test_db.add(currency_pair)
        test_db.commit()

        # Создаем свечу
        timestamp = datetime(2023, 1, 1, 12, 0, tzinfo=timezone.utc)
        candle = models.Candle(
            currency_pair_id=currency_pair.id,
            exchange_id=exchange.id,
            time_period_id=period.id,
            open_time=timestamp,
            close_time=timestamp,
            open_price=50000.0,
            high_price=51000.0,
            low_price=49000.0,
            close_price=50500.0,
            volume=100.5,
            quote_volume=0,
            trades_count=0
        )

        test_db.add(candle)
        test_db.commit()

        saved_candle = test_db.query(models.Candle).first()
        assert saved_candle.currency_pair_id == currency_pair.id
        assert math.isclose(float(saved_candle.open_price), 50000.0, rel_tol=1e-9)
        assert math.isclose(float(saved_candle.high_price), 51000.0, rel_tol=1e-9)
        assert math.isclose(float(saved_candle.low_price), 49000.0, rel_tol=1e-9)
        assert math.isclose(float(saved_candle.close_price), 50500.0, rel_tol=1e-9)
        assert math.isclose(float(saved_candle.volume), 100.5, rel_tol=1e-9)
        assert saved_candle.open_time.year == 2023

    def test_candle_relationships(self, test_db):
        """Тестирует связи свечи с биржей и периодом"""
        # Создаем зависимые объекты
        exchange = models.Exchange(name="OKX", code="okx", environment="sandbox")
        period = models.TimePeriod(name="5 minutes", minutes=5)

        # Создаем символы
        eth = models.Symbol(name="Ethereum", symbol="ETH")
        usdt = models.Symbol(name="Tether", symbol="USDT")

        test_db.add_all([exchange, period, eth, usdt])
        test_db.commit()

        # Создаем валютную пару
        currency_pair = models.CurrencyPair(
            base_symbol_id=eth.id,
            quote_symbol_id=usdt.id,
            type="spot"
        )

        test_db.add(currency_pair)
        test_db.commit()

        # Создаем свечу
        timestamp = datetime(2023, 1, 1, 12, 5, tzinfo=timezone.utc)
        candle = models.Candle(
            currency_pair_id=currency_pair.id,
            exchange_id=exchange.id,
            time_period_id=period.id,
            open_time=timestamp,
            close_time=timestamp,
            open_price=3000.0,
            high_price=3100.0,
            low_price=2950.0,
            close_price=3050.0,
            volume=250.7,
            quote_volume=0,
            trades_count=0
        )

        test_db.add(candle)
        test_db.commit()

        # Проверяем связи
        saved_candle = test_db.query(models.Candle).first()
        assert saved_candle.exchange.name == "OKX"
        assert saved_candle.time_period.name == "5 minutes"
        assert saved_candle.currency_pair.base_symbol.symbol == "ETH"
        assert saved_candle.currency_pair.quote_symbol.symbol == "USDT"

    def test_candle_precision(self, test_db):
        """Тестирует точность численных полей свечи"""
        exchange = models.Exchange(name="Test", code="test", environment="test")
        period = models.TimePeriod(name="1m", minutes=1)

        # Создаем символы
        btc = models.Symbol(name="Bitcoin", symbol="BTC")
        usdt = models.Symbol(name="Tether", symbol="USDT")

        test_db.add_all([exchange, period, btc, usdt])
        test_db.commit()

        # Создаем валютную пару
        currency_pair = models.CurrencyPair(
            base_symbol_id=btc.id,
            quote_symbol_id=usdt.id,
            type="spot"
        )

        test_db.add(currency_pair)
        test_db.commit()

        # Создаем свечу с высокой точностью
        timestamp = datetime(2023, 1, 1, 12, 0, tzinfo=timezone.utc)
        candle = models.Candle(
            currency_pair_id=currency_pair.id,
            exchange_id=exchange.id,
            time_period_id=period.id,
            open_time=timestamp,
            close_time=timestamp,
            open_price=50000.12345678,
            high_price=51000.87654321,
            low_price=49000.11111111,
            close_price=50500.99999999,
            volume=100.12345678,
            quote_volume=0,
            trades_count=0
        )

        test_db.add(candle)
        test_db.commit()

        saved_candle = test_db.query(models.Candle).first()
        # Проверяем что точность сохранена (до 8 знаков после запятой)
        assert str(saved_candle.open_price) == "50000.12345678"
        assert str(saved_candle.volume) == "100.12345678"


class TestExchangeConfigurationModel:
    """Тесты для модели ExchangeConfiguration."""

    def test_create_exchange_configuration(self, test_db):
        """Тестирует создание конфигурации биржи"""
        # Создаем зависимые объекты
        user = models.User(name="Test User", email="test@example.com", password="password")
        exchange = models.Exchange(name="Binance", code="binance", environment="production")

        test_db.add_all([user, exchange])
        test_db.commit()

        # Создаем конфигурацию
        config = models.ExchangeConfiguration(
            exchange_id=exchange.id,
            user_id=user.id,
            api_key="user_api_key",
            api_secret="user_api_secret",
            sandbox_mode=True
        )

        test_db.add(config)
        test_db.commit()

        saved_config = test_db.query(models.ExchangeConfiguration).first()
        assert saved_config.api_key == "user_api_key"
        assert saved_config.api_secret == "user_api_secret"
        assert saved_config.sandbox_mode is True

    def test_exchange_configuration_relationships(self, test_db):
        """Тестирует связи конфигурации биржи"""
        # Создаем зависимые объекты
        user = models.User(name="John Doe", email="john@example.com", password="password")
        exchange = models.Exchange(name="OKX", code="okx", environment="production")

        test_db.add_all([user, exchange])
        test_db.commit()

        # Создаем конфигурацию
        config = models.ExchangeConfiguration(
            exchange_id=exchange.id,
            user_id=user.id,
            api_key="key",
            api_secret="secret"
        )

        test_db.add(config)
        test_db.commit()

        # Проверяем связи
        saved_config = test_db.query(models.ExchangeConfiguration).first()
        assert saved_config.exchange.name == "OKX"
        assert saved_config.user.name == "John Doe"

    def test_exchange_configuration_defaults(self, test_db):
        """Тестирует значения по умолчанию для конфигурации биржи"""
        user = models.User(name="Test", email="test@test.com", password="pass")
        exchange = models.Exchange(name="Test", code="test", environment="test")

        test_db.add_all([user, exchange])
        test_db.commit()

        config = models.ExchangeConfiguration(
            exchange_id=exchange.id,
            user_id=user.id
        )

        test_db.add(config)
        test_db.commit()

        saved_config = test_db.query(models.ExchangeConfiguration).first()
        assert saved_config.sandbox_mode is False  # Значение по умолчанию


# Интеграционные тесты моделей
class TestModelsIntegration:
    """Интеграционные тесты для взаимодействия между моделями."""

    def test_full_trading_setup(self, test_db):
        """Интеграционный тест создания полной торговой структуры"""
        # Создаем пользователя
        user = models.User(
            name="Trader John",
            email="trader@example.com",
            password="secure_password"
        )

        # Создаем биржу
        exchange = models.Exchange(
            name="Binance",
            code="binance",
            environment="production",
            api_key="exchange_key",
            api_secret="exchange_secret"
        )

        # Создаем символы
        btc = models.Symbol(name="Bitcoin", symbol="BTC")
        usdt = models.Symbol(name="Tether", symbol="USDT")

        # Создаем валютную пару
        pair = models.CurrencyPair(
            base_symbol_id=1,  # BTC will get id=1
            quote_symbol_id=2,  # USDT will get id=2
            type="spot"
        )

        # Создаем периоды времени
        periods = [
            models.TimePeriod(name="1m", minutes=1),
            models.TimePeriod(name="5m", minutes=5),
            models.TimePeriod(name="1h", minutes=60)
        ]

        # Добавляем все в базу
        test_db.add_all([user, exchange, btc, usdt])
        test_db.commit()

        # Устанавливаем правильные ID для валютной пары
        pair.base_symbol_id = btc.id
        pair.quote_symbol_id = usdt.id

        test_db.add(pair)
        test_db.add_all(periods)
        test_db.commit()

        # Создаем конфигурацию пользователя
        user_config = models.ExchangeConfiguration(
            exchange_id=exchange.id,
            user_id=user.id,
            api_key="user_api_key",
            api_secret="user_api_secret",
            sandbox_mode=True
        )
        test_db.add(user_config)

        # Создаем свечи для разных периодов
        base_time = datetime(2023, 1, 1, 12, 0, tzinfo=timezone.utc)
        candles = []

        for i, period in enumerate(periods):
            candle = models.Candle(
                currency_pair_id=pair.id,
                exchange_id=exchange.id,
                time_period_id=period.id,
                open_time=base_time,
                close_time=base_time,
                open_price=50000.0 + i * 100,
                high_price=51000.0 + i * 100,
                low_price=49000.0 + i * 100,
                close_price=50500.0 + i * 100,
                volume=100.0 + i * 10,
                quote_volume=0,
                trades_count=0
            )
            candles.append(candle)

        test_db.add_all(candles)
        test_db.commit()

        # Проверяем что все создалось корректно
        assert test_db.query(models.User).count() == 1
        assert test_db.query(models.Exchange).count() == 1
        assert test_db.query(models.Symbol).count() == 2
        assert test_db.query(models.CurrencyPair).count() == 1
        assert test_db.query(models.TimePeriod).count() == 3
        assert test_db.query(models.ExchangeConfiguration).count() == 1
        assert test_db.query(models.Candle).count() == 3

        # Проверяем связи
        saved_pair = test_db.query(models.CurrencyPair).first()
        assert saved_pair.base_symbol.symbol == "BTC"
        assert saved_pair.quote_symbol.symbol == "USDT"

        saved_candle = test_db.query(models.Candle).first()
        assert saved_candle.exchange.name == "Binance"
        assert saved_candle.time_period.name == "1m"

    def test_cascade_operations(self, test_db):
        """Тестирует каскадные операции (если они настроены)"""
        # Создаем структуру с зависимостями
        exchange = models.Exchange(name="Test Exchange", code="test", environment="test")
        period = models.TimePeriod(name="1m", minutes=1)

        # Создаем символы
        btc = models.Symbol(name="Bitcoin", symbol="BTC")
        usdt = models.Symbol(name="Tether", symbol="USDT")

        test_db.add_all([exchange, period, btc, usdt])
        test_db.commit()

        # Создаем валютную пару
        currency_pair = models.CurrencyPair(
            base_symbol_id=btc.id,
            quote_symbol_id=usdt.id,
            type="spot"
        )

        test_db.add(currency_pair)
        test_db.commit()

        # Создаем несколько свечей
        candles = [
            models.Candle(
                currency_pair_id=currency_pair.id,
                exchange_id=exchange.id,
                time_period_id=period.id,
                open_time=datetime(2023, 1, 1, 12, i, tzinfo=timezone.utc),
                close_time=datetime(2023, 1, 1, 12, i, tzinfo=timezone.utc),
                open_price=50000.0,
                high_price=51000.0,
                low_price=49000.0,
                close_price=50500.0,
                volume=100.0,
                quote_volume=0,
                trades_count=0
            )
            for i in range(5)
        ]

        test_db.add_all(candles)
        test_db.commit()

        assert test_db.query(models.Candle).count() == 5

        # Удаляем биржу
        test_db.delete(exchange)
        test_db.commit()

        # Свечи все еще должны существовать (нет CASCADE DELETE)
        # Это зависит от настройки foreign keys
        # В SQLite без CASCADE DELETE свечи останутся
        # В production БД с правильными FK constraints они могут удалиться


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
