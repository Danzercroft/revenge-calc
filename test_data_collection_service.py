import pytest
import asyncio
import math
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import models
from database import Base
from data_collection_service import DataCollectionService, data_collection_service
from exchange_service import exchange_service


@pytest.fixture
def test_db():
    """Создает тестовую базу данных в памяти"""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return testing_session_local()


@pytest.fixture
def mock_exchange():
    """Создает мок биржи"""
    exchange = models.Exchange(
        id=1,
        name="Test Exchange",
        code="test",
        environment="sandbox",
        api_key="test_key",
        api_secret="test_secret",
        is_active=True
    )
    return exchange


@pytest.fixture
def mock_symbol():
    """Создает мок символа"""
    symbol = models.Symbol(
        name="Bitcoin",
        symbol="BTC",
        is_active=True
    )
    return symbol


@pytest.fixture
def mock_symbol():
    """Создает мок символа"""
    symbol = models.Symbol(
        name="Bitcoin",
        symbol="BTC",
        is_active=True
    )
    return symbol


@pytest.fixture
def mock_exchange():
    """Создает мок биржи"""
    exchange = models.Exchange(
        name="Test Exchange",
        code="test",
        environment="sandbox",
        api_key="test_key",
        api_secret="test_secret",
        is_active=True
    )
    return exchange


@pytest.fixture
def mock_time_period():
    """Создает мок периода времени"""
    period = models.TimePeriod(
        name="1 minute",
        minutes=1,
        is_active=True
    )
    return period


@pytest.fixture
def sample_candle_data():
    """Создает образец данных свечи"""
    return {
        'timestamp': datetime(2023, 1, 1, 12, 0, tzinfo=timezone.utc),
        'open': 50000.0,
        'high': 51000.0,
        'low': 49000.0,
        'close': 50500.0,
        'volume': 100.5
    }


class TestDataCollectionService:
    
    def test_init(self):
        """Тестирует инициализацию сервиса"""
        service = DataCollectionService()
        assert service.scheduler is not None
        assert service.scheduler.running is False  # Планировщик не запущен по умолчанию
    
    def test_convert_minutes_to_timeframe(self):
        """Тестирует конвертацию минут в таймфрейм"""
        service = DataCollectionService()
        
        # Тестируем известные значения
        assert service.convert_minutes_to_timeframe(1) == '1m'
        assert service.convert_minutes_to_timeframe(5) == '5m'
        assert service.convert_minutes_to_timeframe(15) == '15m'
        assert service.convert_minutes_to_timeframe(60) == '1h'
        assert service.convert_minutes_to_timeframe(1440) == '1d'
        
        # Тестируем неизвестное значение
        assert service.convert_minutes_to_timeframe(7) is None
    
    def test_get_active_entities(self, test_db, mock_exchange, mock_time_period):
        """Тестирует получение активных сущностей"""
        service = DataCollectionService()
        
        # Создаем символы и валютную пару
        btc = models.Symbol(name="Bitcoin", symbol="BTC", is_active=True)
        usdt = models.Symbol(name="Tether", symbol="USDT", is_active=True)
        
        test_db.add_all([mock_exchange, btc, usdt, mock_time_period])
        test_db.commit()
        
        currency_pair = models.CurrencyPair(
            base_symbol_id=btc.id,
            quote_symbol_id=usdt.id,
            type="spot",
            is_active=True
        )
        
        test_db.add(currency_pair)
        test_db.commit()
        
        entities = service._get_active_entities(test_db)
        
        assert len(entities['exchanges']) == 1
        assert len(entities['currency_pairs']) == 1
        assert len(entities['time_periods']) == 1
        assert entities['exchanges'][0].name == "Test Exchange"
    
    def test_save_or_update_candle_new(self, test_db, mock_exchange, mock_time_period, sample_candle_data):
        """Тестирует сохранение новой свечи"""
        service = DataCollectionService()
        
        # Создаем новые объекты для этого теста
        btc = models.Symbol(name="Bitcoin", symbol="BTC", is_active=True)
        usdt = models.Symbol(name="Tether", symbol="USDT", is_active=True)
        
        # Добавляем зависимые объекты
        test_db.add_all([mock_exchange, mock_time_period, btc, usdt])
        test_db.commit()
        
        # Создаем валютную пару
        currency_pair = models.CurrencyPair(
            base_symbol_id=btc.id,
            quote_symbol_id=usdt.id,
            type="spot",
            is_active=True
        )
        
        test_db.add(currency_pair)
        test_db.commit()
        
        service._save_or_update_candle(test_db, mock_exchange, mock_time_period, "BTC/USDT", sample_candle_data)
        test_db.commit()  # Коммитим изменения
        
        # Проверяем что свеча была создана
        candle = test_db.query(models.Candle).first()
        assert candle is not None
        assert candle.currency_pair_id == currency_pair.id
        assert math.isclose(candle.open_price, 50000.0, rel_tol=1e-9)
        assert math.isclose(candle.close_price, 50500.0, rel_tol=1e-9)
    
    def test_save_or_update_candle_existing(self, test_db, mock_exchange, mock_time_period, sample_candle_data):
        """Тестирует обновление существующей свечи"""
        service = DataCollectionService()
        
        # Создаем новые объекты для этого теста
        btc = models.Symbol(name="Bitcoin", symbol="BTC", is_active=True)
        usdt = models.Symbol(name="Tether", symbol="USDT", is_active=True)
        
        # Добавляем зависимые объекты
        test_db.add_all([mock_exchange, mock_time_period, btc, usdt])
        test_db.commit()
        
        # Создаем валютную пару
        currency_pair = models.CurrencyPair(
            base_symbol_id=btc.id,
            quote_symbol_id=usdt.id,
            type="spot",
            is_active=True
        )
        
        test_db.add(currency_pair)
        test_db.commit()
        
        # Создаем существующую свечу
        existing_candle = models.Candle(
            currency_pair_id=currency_pair.id,
            exchange_id=mock_exchange.id,
            time_period_id=mock_time_period.id,
            open_time=sample_candle_data['timestamp'],
            close_time=sample_candle_data['timestamp'],
            open_price=45000.0,
            high_price=46000.0,
            low_price=44000.0,
            close_price=45500.0,
            volume=50.0,
            quote_volume=0,
            trades_count=0
        )
        test_db.add(existing_candle)
        test_db.commit()
        
        # Обновляем свечу
        service._save_or_update_candle(test_db, mock_exchange, mock_time_period, "BTC/USDT", sample_candle_data)
        
        # Проверяем что свеча была обновлена
        candle = test_db.query(models.Candle).first()
        assert math.isclose(candle.open_price, 50000.0, rel_tol=1e-9)  # Новое значение
        assert math.isclose(candle.close_price, 50500.0, rel_tol=1e-9)  # Новое значение
        assert candle.updated_at is not None
    
    def test_save_historical_candles(self, test_db, mock_exchange, mock_time_period):
        """Тестирует сохранение исторических свечей"""
        service = DataCollectionService()
        
        # Создаем новые объекты для этого теста
        btc = models.Symbol(name="Bitcoin", symbol="BTC", is_active=True)
        usdt = models.Symbol(name="Tether", symbol="USDT", is_active=True)
        
        # Добавляем зависимые объекты
        test_db.add_all([mock_exchange, mock_time_period, btc, usdt])
        test_db.commit()
        
        # Создаем валютную пару
        currency_pair = models.CurrencyPair(
            base_symbol_id=btc.id,
            quote_symbol_id=usdt.id,
            type="spot",
            is_active=True
        )
        
        test_db.add(currency_pair)
        test_db.commit()
        
        # Создаем список исторических свечей
        candles_data = [
            {
                'timestamp': datetime(2023, 1, 1, 12, 0, tzinfo=timezone.utc),
                'open': 50000.0,
                'high': 51000.0,
                'low': 49000.0,
                'close': 50500.0,
                'volume': 100.5
            },
            {
                'timestamp': datetime(2023, 1, 1, 12, 1, tzinfo=timezone.utc),
                'open': 50500.0,
                'high': 51500.0,
                'low': 49500.0,
                'close': 51000.0,
                'volume': 120.3
            }
        ]
        
        service._save_historical_candles(test_db, mock_exchange, mock_time_period, "BTC/USDT", candles_data)
        test_db.commit()  # Коммитим изменения
        
        # Проверяем что свечи были сохранены
        candles = test_db.query(models.Candle).all()
        assert len(candles) == 2
        assert math.isclose(candles[0].open_price, 50000.0, rel_tol=1e-9)
        assert math.isclose(candles[1].open_price, 50500.0, rel_tol=1e-9)
    
    @pytest.mark.asyncio
    async def test_process_timeframe_candle_success(self, test_db, mock_exchange, mock_time_period):
        """Тестирует успешную обработку свечи для таймфрейма"""
        service = DataCollectionService()
        
        # Мокаем exchange_service
        mock_exchange_instance = Mock()
        mock_candle_data = {
            'timestamp': datetime(2023, 1, 1, 12, 0, tzinfo=timezone.utc),
            'open': 50000.0,
            'high': 51000.0,
            'low': 49000.0,
            'close': 50500.0,
            'volume': 100.5
        }
        
        with patch.object(exchange_service, 'fetch_current_candle', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_candle_data
            
            with patch.object(service, '_save_or_update_candle') as mock_save:
                await service._process_timeframe_candle(test_db, mock_exchange, mock_exchange_instance, "BTC/USDT", mock_time_period)
                
                mock_fetch.assert_called_once_with(mock_exchange_instance, "BTC/USDT", "1m")
                mock_save.assert_called_once_with(test_db, mock_exchange, mock_time_period, "BTC/USDT", mock_candle_data)
    
    @pytest.mark.asyncio
    async def test_process_timeframe_candle_no_data(self, test_db, mock_exchange, mock_time_period):
        """Тестирует обработку свечи когда нет данных"""
        service = DataCollectionService()
        mock_exchange_instance = Mock()
        
        with patch.object(exchange_service, 'fetch_current_candle', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = None
            
            with patch.object(service, '_save_or_update_candle') as mock_save:
                await service._process_timeframe_candle(test_db, mock_exchange, mock_exchange_instance, "BTC/USDT", mock_time_period)
                
                mock_fetch.assert_called_once()
                mock_save.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_process_timeframe_candle_invalid_timeframe(self, test_db, mock_exchange):
        """Тестирует обработку свечи с неподдерживаемым таймфреймом"""
        service = DataCollectionService()
        mock_exchange_instance = Mock()
        
        # Создаем период с неподдерживаемым количеством минут
        invalid_time_period = models.TimePeriod(
            id=99,
            name="7 minutes",
            minutes=7,  # Неподдерживаемое значение
            is_active=True
        )
        
        with patch.object(exchange_service, 'fetch_current_candle', new_callable=AsyncMock) as mock_fetch:
            await service._process_timeframe_candle(test_db, mock_exchange, mock_exchange_instance, "BTC/USDT", invalid_time_period)
            
            # Не должно вызывать fetch_current_candle для неподдерживаемого таймфрейма
            mock_fetch.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_collect_candles_for_range(self, test_db, mock_exchange, mock_time_period):
        """Тестирует сбор свечей для временного диапазона"""
        service = DataCollectionService()
        mock_exchange_instance = Mock()
        
        start_time = datetime(2023, 1, 1, 12, 0, tzinfo=timezone.utc)
        end_time = datetime(2023, 1, 1, 13, 0, tzinfo=timezone.utc)
        
        # Мокаем данные свечей
        mock_candles = [
            {
                'timestamp': datetime(2023, 1, 1, 12, 0, tzinfo=timezone.utc),
                'open': 50000.0,
                'high': 51000.0,
                'low': 49000.0,
                'close': 50500.0,
                'volume': 100.5
            }
        ]
        
        with patch.object(exchange_service, 'fetch_historical_candles', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_candles
            
            with patch.object(service, '_save_historical_candles') as mock_save:
                await service._collect_candles_for_range(
                    test_db, mock_exchange, mock_exchange_instance, 
                    "BTC/USDT", mock_time_period, "1m", start_time, end_time
                )
                
                mock_fetch.assert_called_once_with(mock_exchange_instance, "BTC/USDT", "1m", start_time, limit=1000)
                mock_save.assert_called_once_with(test_db, mock_exchange, mock_time_period, "BTC/USDT", mock_candles)
    
    @pytest.mark.asyncio
    async def test_collect_current_candles_integration(self):
        """Интеграционный тест сбора текущих свечей"""
        service = DataCollectionService()
        
        # Создаем моки для SessionLocal и всех зависимостей
        mock_db = Mock(spec=Session)
        mock_db.query.return_value.filter.return_value.all.return_value = []
        mock_db.commit = Mock()
        mock_db.rollback = Mock()
        mock_db.close = Mock()
        
        with patch('data_collection_service.SessionLocal', return_value=mock_db):
            with patch.object(service, '_get_active_entities') as mock_get_entities:
                mock_get_entities.return_value = {
                    'exchanges': [],
                    'currency_pairs': [],
                    'time_periods': []
                }
                
                await service.collect_current_candles()
                
                mock_db.commit.assert_called_once()
                mock_db.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_collect_current_candles_with_error(self):
        """Тестирует обработку ошибок при сборе текущих свечей"""
        service = DataCollectionService()
        
        mock_db = Mock(spec=Session)
        mock_db.rollback = Mock()
        mock_db.close = Mock()
        
        with patch('data_collection_service.SessionLocal', return_value=mock_db):
            with patch.object(service, '_get_active_entities', side_effect=Exception("Test error")):
                await service.collect_current_candles()
                
                mock_db.rollback.assert_called_once()
                mock_db.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_collect_historical_candles_integration(self):
        """Интеграционный тест сбора исторических свечей"""
        service = DataCollectionService()
        
        mock_db = Mock(spec=Session)
        mock_db.commit = Mock()
        mock_db.rollback = Mock()
        mock_db.close = Mock()
        
        with patch('data_collection_service.SessionLocal', return_value=mock_db):
            with patch.object(service, '_get_active_entities') as mock_get_entities:
                mock_get_entities.return_value = {
                    'exchanges': [],
                    'currency_pairs': [],
                    'time_periods': []
                }
                
                with patch.object(service, '_process_exchange_historical_data', new_callable=AsyncMock):
                    await service.collect_historical_candles()
                    
                    mock_db.commit.assert_called_once()
                    mock_db.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_scheduler_start_stop(self):
        """Тестирует запуск и остановку планировщика"""
        service = DataCollectionService()
        
        # Тестируем запуск
        service.start_scheduler()
        assert service.scheduler.running
        
        # Проверяем что задачи добавлены
        jobs = service.scheduler.get_jobs()
        job_ids = [job.id for job in jobs]
        assert 'collect_current_candles' in job_ids
        assert 'collect_historical_candles' in job_ids
        
        # Тестируем остановку
        service.stop_scheduler()
        
        # Даем немного времени для полной остановки
        import asyncio
        await asyncio.sleep(0.1)
        
        assert not service.scheduler.running
    
    @pytest.mark.asyncio
    async def test_process_exchange_candles_error_handling(self, test_db, mock_exchange, mock_time_period):
        """Тестирует обработку ошибок при обработке свечей биржи"""
        service = DataCollectionService()
        
        # Создаем символы и валютную пару
        btc = models.Symbol(name="Bitcoin", symbol="BTC", is_active=True)
        usdt = models.Symbol(name="Tether", symbol="USDT", is_active=True)
        
        test_db.add_all([mock_exchange, btc, usdt, mock_time_period])
        test_db.commit()
        
        currency_pair = models.CurrencyPair(
            base_symbol_id=btc.id,
            quote_symbol_id=usdt.id,
            type="spot",
            is_active=True
        )
        currency_pair.base_symbol = btc
        currency_pair.quote_symbol = usdt
        
        test_db.add(currency_pair)
        test_db.commit()
        
        with patch.object(exchange_service, 'get_exchange_instance', side_effect=Exception("Exchange error")):
            # Не должно поднимать исключение, только логировать
            await service._process_exchange_candles(test_db, mock_exchange, [currency_pair], [mock_time_period])
    
    @pytest.mark.asyncio
    async def test_collect_timeframe_historical_data_with_missing_ranges(self, test_db, mock_exchange, mock_time_period):
        """Тестирует сбор исторических данных с отсутствующими диапазонами"""
        service = DataCollectionService()
        mock_exchange_instance = Mock()
        
        start_date = datetime(2023, 1, 1, tzinfo=timezone.utc)
        missing_ranges = [
            (datetime(2023, 1, 1, 12, 0, tzinfo=timezone.utc), datetime(2023, 1, 1, 13, 0, tzinfo=timezone.utc)),
            (datetime(2023, 1, 1, 14, 0, tzinfo=timezone.utc), datetime(2023, 1, 1, 15, 0, tzinfo=timezone.utc))
        ]
        
        with patch.object(exchange_service, 'get_missing_candles_timerange', new_callable=AsyncMock) as mock_missing:
            mock_missing.return_value = missing_ranges
            
            with patch.object(service, '_collect_candles_for_range', new_callable=AsyncMock) as mock_collect:
                await service._collect_timeframe_historical_data(
                    test_db, mock_exchange, mock_exchange_instance, 
                    "BTC/USDT", mock_time_period, "1m", start_date
                )
                
                # Проверяем что _collect_candles_for_range вызван для каждого диапазона
                assert mock_collect.call_count == 2


class TestDataCollectionServiceSingleton:
    """Тесты для глобального экземпляра сервиса"""
    
    def test_singleton_instance(self):
        """Тестирует что глобальный экземпляр создан"""
        assert data_collection_service is not None
        assert isinstance(data_collection_service, DataCollectionService)
    
    def test_singleton_scheduler_initialized(self):
        """Тестирует что планировщик инициализирован"""
        assert data_collection_service.scheduler is not None


# Дополнительные функциональные тесты
class TestDataCollectionServiceFunctional:
    
    @pytest.mark.asyncio
    async def test_full_current_candles_workflow(self, test_db):
        """Функциональный тест полного цикла сбора текущих свечей"""
        service = DataCollectionService()
        
        # Создаем полный набор тестовых данных
        exchange = models.Exchange(
            name="Binance", code="binance", 
            environment="sandbox", is_active=True
        )
        
        base_symbol = models.Symbol(name="Bitcoin", symbol="BTC", is_active=True)
        quote_symbol = models.Symbol(name="Tether", symbol="USDT", is_active=True)
        
        time_period = models.TimePeriod(
            name="1 minute", minutes=1, is_active=True
        )
        
        test_db.add_all([exchange, base_symbol, quote_symbol, time_period])
        test_db.commit()
        
        currency_pair = models.CurrencyPair(
            base_symbol_id=base_symbol.id, quote_symbol_id=quote_symbol.id, 
            type="spot", is_active=True
        )
        currency_pair.base_symbol = base_symbol
        currency_pair.quote_symbol = quote_symbol
        
        test_db.add(currency_pair)
        test_db.commit()
        
        # Мокаем exchange_service
        mock_exchange_instance = Mock()
        mock_candle_data = {
            'timestamp': datetime(2023, 1, 1, 12, 0, tzinfo=timezone.utc),
            'open': 50000.0,
            'high': 51000.0,
            'low': 49000.0,
            'close': 50500.0,
            'volume': 100.5
        }
        
        with patch.object(exchange_service, 'get_exchange_instance', return_value=mock_exchange_instance):
            with patch.object(exchange_service, 'fetch_current_candle', new_callable=AsyncMock) as mock_fetch:
                mock_fetch.return_value = mock_candle_data
                
                await service._process_exchange_candles(test_db, exchange, [currency_pair], [time_period])
                test_db.commit()  # Коммитим изменения
                
                # Проверяем что свеча была сохранена
                candle = test_db.query(models.Candle).first()
                assert candle is not None
                assert candle.currency_pair_id == currency_pair.id
                assert math.isclose(candle.open_price, 50000.0, rel_tol=1e-9)
    
    @pytest.mark.asyncio
    async def test_multiple_timeframes_processing(self, test_db):
        """Тестирует обработку нескольких таймфреймов"""
        service = DataCollectionService()
        
        # Создаем несколько периодов времени
        time_periods = [
            models.TimePeriod(name="1 minute", minutes=1, is_active=True),
            models.TimePeriod(name="5 minutes", minutes=5, is_active=True),
            models.TimePeriod(name="1 hour", minutes=60, is_active=True),
        ]
        
        exchange = models.Exchange(
            name="Test Exchange", code="test", 
            environment="sandbox", is_active=True
        )
        
        # Создаем символы
        btc = models.Symbol(name="Bitcoin", symbol="BTC", is_active=True)
        usdt = models.Symbol(name="Tether", symbol="USDT", is_active=True)
        
        test_db.add_all([exchange, btc, usdt] + time_periods)
        test_db.commit()
        
        # Создаем валютную пару
        currency_pair = models.CurrencyPair(
            base_symbol_id=btc.id,
            quote_symbol_id=usdt.id,
            type="spot",
            is_active=True
        )
        
        test_db.add(currency_pair)
        test_db.commit()
        
        mock_exchange_instance = Mock()
        
        with patch.object(exchange_service, 'fetch_current_candle', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = {
                'timestamp': datetime(2023, 1, 1, 12, 0, tzinfo=timezone.utc),
                'open': 50000.0, 'high': 51000.0, 'low': 49000.0, 'close': 50500.0, 'volume': 100.5
            }
            
            await service._process_symbol_candles(test_db, exchange, mock_exchange_instance, "BTC/USDT", time_periods)
            test_db.commit()  # Коммитим изменения
            
            # Проверяем что fetch_current_candle вызван для каждого таймфрейма
            assert mock_fetch.call_count == 3
            
            # Проверяем что свечи созданы для всех таймфреймов
            candles = test_db.query(models.Candle).all()
            assert len(candles) == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
