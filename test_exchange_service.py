import pytest
import ccxt
import math
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import models
from database import Base
from exchange_service import ExchangeService, exchange_service
from exchange_service import ExchangeService, exchange_service


@pytest.fixture
def test_db():
    """Создает тестовую базу данных в памяти"""
    engine = create_engine(
        "sqlite:///:memory:", 
        echo=False,
        poolclass=StaticPool,
        connect_args={
            "check_same_thread": False,
        }
    )
    Base.metadata.create_all(engine)
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    db = testing_session_local()
    
    # Создаем тестовые данные
    exchange = models.Exchange(id=1, name="Binance", code="binance", environment="production", is_active=True)
    time_period = models.TimePeriod(id=1, name="1 minute", minutes=1, description="1 minute")
    
    db.add(exchange)
    db.add(time_period)
    db.commit()
    
    return db


@pytest.fixture
def mock_exchange():
    """Создает мок биржи"""
    exchange = models.Exchange(
        id=1,
        name="Binance",
        code="binance",
        environment="sandbox",
        api_key="test_api_key",
        api_secret="test_api_secret",
        is_active=True
    )
    return exchange


@pytest.fixture
def mock_okx_exchange():
    """Создает мок биржи OKX с passphrase"""
    exchange = models.Exchange(
        id=2,
        name="OKX",
        code="okx",
        environment="production",
        api_key="test_api_key",
        api_secret="test_api_secret",
        api_passphrase="test_passphrase",
        is_active=True
    )
    return exchange


class TestExchangeService:
    
    def test_init(self):
        """Тестирует инициализацию сервиса"""
        service = ExchangeService()
        assert service.exchanges == {}
    
    def test_get_exchange_instance_binance(self, mock_exchange):
        """Тестирует создание экземпляра Binance"""
        service = ExchangeService()
        
        with patch('ccxt.binance') as mock_binance_class:
            mock_instance = Mock()
            mock_binance_class.return_value = mock_instance
            
            result = service.get_exchange_instance(mock_exchange)
            
            assert result == mock_instance
            assert service.exchanges[mock_exchange.id] == mock_instance
            
            # Проверяем правильность конфигурации
            expected_config = {
                'apiKey': 'test_api_key',
                'secret': 'test_api_secret',
                'sandbox': True,
                'enableRateLimit': True,
            }
            mock_binance_class.assert_called_once_with(expected_config)
    
    def test_get_exchange_instance_okx_with_passphrase(self, mock_okx_exchange):
        """Тестирует создание экземпляра OKX с passphrase"""
        service = ExchangeService()
        
        with patch('ccxt.okx') as mock_okx_class:
            mock_instance = Mock()
            mock_okx_class.return_value = mock_instance
            
            result = service.get_exchange_instance(mock_okx_exchange)
            
            assert result == mock_instance
            
            # Проверяем что passphrase добавлен как password
            expected_config = {
                'apiKey': 'test_api_key',
                'secret': 'test_api_secret',
                'sandbox': False,  # production environment
                'enableRateLimit': True,
                'password': 'test_passphrase'
            }
            mock_okx_class.assert_called_once_with(expected_config)
    
    def test_get_exchange_instance_cached(self, mock_exchange):
        """Тестирует кэширование экземпляров биржи"""
        service = ExchangeService()
        
        with patch('ccxt.binance') as mock_binance_class:
            mock_instance = Mock()
            mock_binance_class.return_value = mock_instance
            
            # Первый вызов - создает экземпляр
            result1 = service.get_exchange_instance(mock_exchange)
            
            # Второй вызов - возвращает кэшированный экземпляр
            result2 = service.get_exchange_instance(mock_exchange)
            
            assert result1 == result2
            assert mock_binance_class.call_count == 1  # Вызван только один раз
    
    def test_get_exchange_instance_unsupported(self):
        """Тестирует обработку неподдерживаемой биржи"""
        service = ExchangeService()
        
        unsupported_exchange = models.Exchange(
            id=99,
            name="Unsupported Exchange",
            code="unsupported",
            environment="production",
            api_key="test_key",
            api_secret="test_secret",
            is_active=True
        )
        
        with pytest.raises(ValueError, match="Unsupported exchange: unsupported"):
            service.get_exchange_instance(unsupported_exchange)
    
    def test_get_exchange_instance_bybit(self):
        """Тестирует создание экземпляра Bybit"""
        service = ExchangeService()
        
        bybit_exchange = models.Exchange(
            id=3,
            name="Bybit",
            code="bybit",
            environment="production",
            api_key="test_key",
            api_secret="test_secret",
            is_active=True
        )
        
        with patch('ccxt.bybit') as mock_bybit_class:
            mock_instance = Mock()
            mock_bybit_class.return_value = mock_instance
            
            result = service.get_exchange_instance(bybit_exchange)
            
            assert result == mock_instance
            mock_bybit_class.assert_called_once()
    
    def test_get_exchange_instance_gate(self):
        """Тестирует создание экземпляра Gate.io"""
        service = ExchangeService()
        
        gate_exchange = models.Exchange(
            id=4,
            name="Gate.io",
            code="gate",
            environment="sandbox",
            api_key="test_key",
            api_secret="test_secret",
            is_active=True
        )
        
        with patch('ccxt.gate') as mock_gate_class:
            mock_instance = Mock()
            mock_gate_class.return_value = mock_instance
            
            result = service.get_exchange_instance(gate_exchange)
            
            assert result == mock_instance
            mock_gate_class.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_fetch_current_candle_success(self):
        """Тестирует успешное получение текущей свечи"""
        service = ExchangeService()

        mock_exchange_instance = Mock()
        # Исправляем AsyncMock - делаем синхронный мок для fetch_ohlcv
        mock_exchange_instance.fetch_ohlcv = Mock(return_value=[
            [1672574400000, 50000.0, 51000.0, 49000.0, 50500.0, 100.5]  # timestamp, o, h, l, c, v
        ])

        result = await service.fetch_current_candle(mock_exchange_instance, "BTC/USDT", "1m")

        assert result is not None
        assert math.isclose(result['open'], 50000.0, rel_tol=1e-9)
        assert math.isclose(result['high'], 51000.0, rel_tol=1e-9)
        assert math.isclose(result['low'], 49000.0, rel_tol=1e-9)
        assert math.isclose(result['close'], 50500.0, rel_tol=1e-9)
        assert math.isclose(result['volume'], 100.5, rel_tol=1e-9)
        assert isinstance(result['timestamp'], datetime)
        
        mock_exchange_instance.fetch_ohlcv.assert_called_once_with("BTC/USDT", "1m", None, 2)
    
    @pytest.mark.asyncio
    async def test_fetch_current_candle_no_data(self):
        """Тестирует получение текущей свечи когда нет данных"""
        service = ExchangeService()
        
        mock_exchange_instance = Mock()
        mock_exchange_instance.fetch_ohlcv = Mock(return_value=[])
        
        result = await service.fetch_current_candle(mock_exchange_instance, "BTC/USDT", "1m")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_fetch_current_candle_exception(self):
        """Тестирует обработку исключений при получении текущей свечи"""
        service = ExchangeService()
        
        mock_exchange_instance = Mock()
        mock_exchange_instance.fetch_ohlcv = Mock(side_effect=Exception("Network error"))
        
        result = await service.fetch_current_candle(mock_exchange_instance, "BTC/USDT", "1m")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_fetch_historical_candles_success(self):
        """Тестирует успешное получение исторических свечей"""
        service = ExchangeService()
        
        mock_exchange_instance = Mock()
        mock_data = [
            [1672574400000, 50000.0, 51000.0, 49000.0, 50500.0, 100.5],
            [1672574460000, 50500.0, 51500.0, 49500.0, 51000.0, 120.3]
        ]
        mock_exchange_instance.fetch_ohlcv = Mock(return_value=mock_data)
        
        start_time = datetime(2023, 1, 1, 12, 0, tzinfo=timezone.utc)
        result = await service.fetch_historical_candles(mock_exchange_instance, "BTC/USDT", "1m", start_time)
        
        assert len(result) == 2
        assert math.isclose(result[0]['open'], 50000.0, rel_tol=1e-9)
        assert math.isclose(result[1]['open'], 50500.0, rel_tol=1e-9)
        
        # Проверяем правильность передачи параметров
        expected_since = int(start_time.timestamp() * 1000)
        mock_exchange_instance.fetch_ohlcv.assert_called_once_with(
            "BTC/USDT", "1m", expected_since, 1000
        )
    
    @pytest.mark.asyncio
    async def test_fetch_historical_candles_with_custom_limit(self):
        """Тестирует получение исторических свечей с кастомным лимитом"""
        service = ExchangeService()
        
        mock_exchange_instance = Mock()
        mock_exchange_instance.fetch_ohlcv = Mock(return_value=[])
        
        start_time = datetime(2023, 1, 1, 12, 0, tzinfo=timezone.utc)
        await service.fetch_historical_candles(mock_exchange_instance, "BTC/USDT", "1m", start_time, limit=500)
        
        expected_since = int(start_time.timestamp() * 1000)
        mock_exchange_instance.fetch_ohlcv.assert_called_once_with(
            "BTC/USDT", "1m", expected_since, 500
        )
    
    @pytest.mark.asyncio
    async def test_fetch_historical_candles_exception(self):
        """Тестирует обработку исключений при получении исторических свечей"""
        service = ExchangeService()
        
        mock_exchange_instance = Mock()
        mock_exchange_instance.fetch_ohlcv = Mock(side_effect=Exception("API error"))
        
        start_time = datetime(2023, 1, 1, 12, 0, tzinfo=timezone.utc)
        result = await service.fetch_historical_candles(mock_exchange_instance, "BTC/USDT", "1m", start_time)
        
        assert result == []
    
    def test_convert_candle_data(self):
        """Тестирует конвертацию данных свечи - удаляем этот тест так как метод не существует"""
        # Этот тест удаляется, так как метод _convert_candle_data отсутствует в service
        pass
    
    @pytest.mark.asyncio
    async def test_get_missing_candles_timerange_no_data(self, test_db):
        """Тестирует получение отсутствующих диапазонов когда нет данных в БД"""
        service = ExchangeService()
        
        # Создаем символы и валютную пару
        btc = models.Symbol(name="Bitcoin", symbol="BTC", is_active=True)
        usdt = models.Symbol(name="Tether", symbol="USDT", is_active=True)
        
        test_db.add_all([btc, usdt])
        test_db.commit()
        
        currency_pair = models.CurrencyPair(
            base_symbol_id=btc.id,
            quote_symbol_id=usdt.id,
            type="spot",
            is_active=True
        )
        
        test_db.add(currency_pair)
        test_db.commit()
        
        start_date = datetime(2023, 1, 1, tzinfo=timezone.utc)
        
        result = await service.get_missing_candles_timerange(test_db, "BTC/USDT", 1, 1, start_date)
        
        # Должен вернуть один диапазон от start_date до текущего времени
        assert len(result) == 1
        assert result[0][0] == start_date
        # end_date должна быть близка к текущему времени
        assert result[0][1] <= datetime.now(timezone.utc)
    
    @pytest.mark.asyncio
    async def test_get_missing_candles_timerange_with_existing_data(self, test_db):
        """Тестирует получение отсутствующих диапазонов с существующими данными"""
        service = ExchangeService()
        
        # Создаем символы, валютную пару, биржу и период
        btc = models.Symbol(name="Bitcoin", symbol="BTC", is_active=True)
        usdt = models.Symbol(name="Tether", symbol="USDT", is_active=True)
        exchange = models.Exchange(name="Test", code="test", environment="test", is_active=True)
        time_period = models.TimePeriod(name="1m", minutes=1, is_active=True)
        
        test_db.add_all([btc, usdt, exchange, time_period])
        test_db.commit()
        
        currency_pair = models.CurrencyPair(
            base_symbol_id=btc.id,
            quote_symbol_id=usdt.id,
            type="spot",
            is_active=True
        )
        
        test_db.add(currency_pair)
        test_db.commit()
        
        # Создаем тестовые данные
        timestamp = datetime(2023, 1, 1, 12, 0, tzinfo=timezone.utc)
        existing_candle = models.Candle(
            currency_pair_id=currency_pair.id,
            exchange_id=exchange.id,
            time_period_id=time_period.id,
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
        test_db.add(existing_candle)
        test_db.commit()
        
        start_date = datetime(2023, 1, 1, tzinfo=timezone.utc)
        result = await service.get_missing_candles_timerange(test_db, "BTC/USDT", exchange.id, time_period.id, start_date)
        
        # Должны быть диапазоны до и после существующей свечи
        assert len(result) >= 1
    
    def test_singleton_instance(self):
        """Тестирует что глобальный экземпляр создан"""
        assert exchange_service is not None
        assert isinstance(exchange_service, ExchangeService)


# Интеграционные тесты
class TestExchangeServiceIntegration:
    
    @pytest.mark.asyncio
    async def test_full_workflow_current_candle(self, mock_exchange):
        """Интеграционный тест полного цикла получения текущей свечи"""
        service = ExchangeService()
        
        with patch('ccxt.binance') as mock_binance_class:
            mock_instance = Mock()
            mock_instance.fetch_ohlcv = Mock(return_value=[
                [1672574400000, 50000.0, 51000.0, 49000.0, 50500.0, 100.5]
            ])
            mock_binance_class.return_value = mock_instance
            
            # Получаем экземпляр биржи
            exchange_instance = service.get_exchange_instance(mock_exchange)
            
            # Получаем текущую свечу
            candle_data = await service.fetch_current_candle(exchange_instance, "BTC/USDT", "1m")
            
            assert candle_data is not None
            assert math.isclose(candle_data['open'], 50000.0, rel_tol=1e-9)
            assert math.isclose(candle_data['close'], 50500.0, rel_tol=1e-9)
    
    @pytest.mark.asyncio
    async def test_multiple_exchanges_support(self):
        """Тестирует поддержку нескольких бирж одновременно"""
        service = ExchangeService()
        
        binance_exchange = models.Exchange(
            id=1, name="Binance", code="binance", 
            environment="sandbox", api_key="key1", api_secret="secret1", is_active=True
        )
        
        okx_exchange = models.Exchange(
            id=2, name="OKX", code="okx", 
            environment="production", api_key="key2", api_secret="secret2", 
            api_passphrase="pass2", is_active=True
        )
        
        with patch('ccxt.binance') as mock_binance, patch('ccxt.okx') as mock_okx:
            mock_binance_instance = Mock()
            mock_okx_instance = Mock()
            mock_binance.return_value = mock_binance_instance
            mock_okx.return_value = mock_okx_instance
            
            # Создаем экземпляры разных бирж
            binance_inst = service.get_exchange_instance(binance_exchange)
            okx_inst = service.get_exchange_instance(okx_exchange)
            
            assert binance_inst == mock_binance_instance
            assert okx_inst == mock_okx_instance
            assert len(service.exchanges) == 2
    
    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self, mock_exchange):
        """Тестирует обработку ошибок и восстановление"""
        service = ExchangeService()
        
        with patch('ccxt.binance') as mock_binance_class:
            mock_instance = Mock()
            # Первый вызов - ошибка, второй - успех
            mock_instance.fetch_ohlcv = Mock(side_effect=[
                Exception("Network error"),
                [[1672574400000, 50000.0, 51000.0, 49000.0, 50500.0, 100.5]]
            ])
            mock_binance_class.return_value = mock_instance
            
            exchange_instance = service.get_exchange_instance(mock_exchange)
            
            # Первый вызов - должен вернуть None из-за ошибки
            result1 = await service.fetch_current_candle(exchange_instance, "BTC/USDT", "1m")
            assert result1 is None
            
            # Второй вызов - должен быть успешным
            result2 = await service.fetch_current_candle(exchange_instance, "BTC/USDT", "1m")
            assert result2 is not None
            assert math.isclose(result2['open'], 50000.0, rel_tol=1e-9)


# Тесты производительности (можно запускать отдельно)
class TestExchangeServicePerformance:
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_large_historical_data_processing(self):
        """Тестирует обработку большого объема исторических данных"""
        service = ExchangeService()
        
        # Создаем большой массив данных (1000 свечей)
        large_data = []
        base_timestamp = 1672574400000
        for i in range(1000):
            large_data.append([
                base_timestamp + i * 60000,  # +1 минута для каждой свечи
                50000.0 + i, 51000.0 + i, 49000.0 + i, 50500.0 + i, 100.5
            ])
        
        mock_exchange_instance = Mock()
        mock_exchange_instance.fetch_ohlcv = Mock(return_value=large_data)
        
        start_time = datetime(2023, 1, 1, 12, 0, tzinfo=timezone.utc)
        result = await service.fetch_historical_candles(mock_exchange_instance, "BTC/USDT", "1m", start_time)
        
        assert len(result) == 1000
        assert all('timestamp' in candle for candle in result)
        assert all(isinstance(candle['timestamp'], datetime) for candle in result)
    
    def test_exchange_instance_caching_performance(self):
        """Тестирует производительность кэширования экземпляров бирж"""
        service = ExchangeService()
        
        exchange = models.Exchange(
            id=1, name="Binance", code="binance", 
            environment="sandbox", api_key="key", api_secret="secret", is_active=True
        )
        
        with patch('ccxt.binance') as mock_binance_class:
            mock_instance = Mock()
            mock_binance_class.return_value = mock_instance
            
            # Множественные вызовы должны использовать кэш
            instances = []
            for _ in range(100):
                instances.append(service.get_exchange_instance(exchange))
            
            # Все экземпляры должны быть одинаковыми (из кэша)
            assert all(inst == mock_instance for inst in instances)
            # ccxt.binance должен быть вызван только один раз
            assert mock_binance_class.call_count == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
