import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

import models
from database import SessionLocal
from exchange_service import exchange_service
from logging_config import clean_old_logs

logger = logging.getLogger(__name__)


class DataCollectionService:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
    
    def _get_currency_pair_id(self, db: Session, symbol: str) -> int:
        """Получает currency_pair_id по символу (например BTC/USDT)"""
        try:
            # Разбираем символ на базовую и котируемую валюты
            if '/' in symbol:
                base_symbol, quote_symbol = symbol.split('/')
            else:
                raise ValueError(f"Invalid symbol format: {symbol}")
            
            # Находим символы в базе
            base_sym = db.query(models.Symbol).filter(models.Symbol.symbol == base_symbol).first()
            quote_sym = db.query(models.Symbol).filter(models.Symbol.symbol == quote_symbol).first()
            
            if not base_sym:
                raise ValueError(f"Base symbol {base_symbol} not found in database")
            if not quote_sym:
                raise ValueError(f"Quote symbol {quote_symbol} not found in database")
            
            # Находим валютную пару
            currency_pair = db.query(models.CurrencyPair).filter(
                models.CurrencyPair.base_symbol_id == base_sym.id,
                models.CurrencyPair.quote_symbol_id == quote_sym.id
            ).first()
            
            if not currency_pair:
                raise ValueError(f"Currency pair {symbol} not found in database")
            
            return currency_pair.id
            
        except Exception as e:
            logger.error(f"Error getting currency_pair_id for {symbol}: {e}")
            raise
        
    def start_scheduler(self):
        """Запускает планировщик задач"""
        # Задача сбора текущих свечей - каждые 15 секунд (4 раза в минуту)
        self.scheduler.add_job(
            self.collect_current_candles,
            IntervalTrigger(seconds=15),
            id='collect_current_candles',
            name='Collect Current Candles',
            max_instances=1
        )
        
        # Задача сбора исторических данных - каждый день в 00:30
        self.scheduler.add_job(
            self.collect_historical_candles,
            CronTrigger(hour=0, minute=30),
            id='collect_historical_candles',
            name='Collect Historical Candles',
            max_instances=1
        )
        
        # Задача очистки старых логов - каждый день в 02:00
        self.scheduler.add_job(
            self.cleanup_old_logs,
            CronTrigger(hour=2, minute=0),
            id='cleanup_old_logs',
            name='Cleanup Old Logs',
            max_instances=1
        )
        
        self.scheduler.start()
        logger.info("Scheduler started successfully")
    
    def stop_scheduler(self):
        """Останавливает планировщик задач"""
        self.scheduler.shutdown()
        logger.info("Scheduler stopped")
    
    async def collect_current_candles(self):
        """Собирает текущие свечи с бирж"""
        logger.info("Starting current candles collection")
        
        db = SessionLocal()
        try:
            entities = self._get_active_entities(db)
            
            for exchange in entities['exchanges']:
                # Обрабатываем каждую биржу в отдельной транзакции
                await self._process_exchange_candles(db, exchange, entities['currency_pairs'], entities['time_periods'])
                logger.debug(f"Successfully processed exchange {exchange.name}")
            
            db.commit()  # Коммитим все изменения
            logger.info("Current candles collection completed")
            
        except Exception as e:
            logger.error(f"Error in current candles collection: {e}")
            db.rollback()
        finally:
            db.close()
    
    def _get_active_entities(self, db: Session):
        """Получает все активные сущности из базы данных"""
        return {
            'exchanges': db.query(models.Exchange).filter(models.Exchange.is_active == True).all(),
            'currency_pairs': db.query(models.CurrencyPair).filter(models.CurrencyPair.is_active == True).all(),
            'time_periods': db.query(models.TimePeriod).filter(models.TimePeriod.is_active == True).all()
        }
    
    async def _process_exchange_candles(self, db: Session, exchange, currency_pairs, time_periods) -> bool:
        """Обрабатывает свечи для одной биржи. Возвращает True в случае успеха, False при ошибке"""
        try:
            exchange_instance = exchange_service.get_exchange_instance(exchange)
        except Exception as e:
            logger.error(f"Error initializing exchange {exchange.name}: {e}")
            return False
        
        for pair in currency_pairs:
            symbol = f"{pair.base_symbol.symbol}/{pair.quote_symbol.symbol}"
            try:
                await self._process_symbol_candles(db, exchange, exchange_instance, symbol, time_periods)
            except Exception as e:
                logger.error(f"Error processing symbol {symbol} on exchange {exchange.name}: {e}")
                # Продолжаем обработку следующих символов
                continue
        
        return True
    
    async def _process_symbol_candles(self, db: Session, exchange, exchange_instance, symbol: str, time_periods):
        """Обрабатывает свечи для одного символа"""
        for time_period in time_periods:
            try:
                await self._process_timeframe_candle(db, exchange, exchange_instance, symbol, time_period)
            except Exception as e:
                logger.error(f"Error processing timeframe {time_period.name} for symbol {symbol} on exchange {exchange.name}: {e}")
                # Продолжаем обработку следующих таймфреймов
                continue
    
    async def _process_timeframe_candle(self, db: Session, exchange, exchange_instance, symbol: str, time_period):
        """Обрабатывает свечу для одного таймфрейма"""
        try:
            timeframe = self.convert_minutes_to_timeframe(time_period.minutes)
            if not timeframe:
                return
            
            candle_data = await exchange_service.fetch_current_candle(exchange_instance, symbol, timeframe)
            if candle_data:
                self._save_or_update_candle(db, exchange, time_period, symbol, candle_data)
                
        except Exception as e:
            logger.error(f"Error collecting current candle for {symbol} on {exchange.name} {timeframe}: {e}")
    
    def _save_or_update_candle(self, db: Session, exchange, time_period, symbol: str, candle_data: dict):
        """Сохраняет или обновляет свечу в базе данных"""
        try:
            currency_pair_id = self._get_currency_pair_id(db, symbol)
            
            existing_candle = db.query(models.Candle).filter(
                models.Candle.currency_pair_id == currency_pair_id,
                models.Candle.exchange_id == exchange.id,
                models.Candle.time_period_id == time_period.id,
                models.Candle.open_time == candle_data['timestamp']
            ).first()
            
            if not existing_candle:
                new_candle = models.Candle(
                    currency_pair_id=currency_pair_id,
                    exchange_id=exchange.id,
                    time_period_id=time_period.id,
                    open_time=candle_data['timestamp'],
                    close_time=candle_data['timestamp'],  # Для текущих свечей open_time = close_time
                    open_price=candle_data['open'],
                    high_price=candle_data['high'],
                    low_price=candle_data['low'],
                    close_price=candle_data['close'],
                    volume=candle_data['volume'],
                    quote_volume=candle_data.get('quote_volume', 0),
                    trades_count=candle_data.get('trades_count', 0)
                )
                db.add(new_candle)
                db.commit()
                logger.debug(f"Added new candle for {symbol} on {exchange.name} at {candle_data['timestamp']}")
            else:
                existing_candle.open_price = candle_data['open']
                existing_candle.high_price = candle_data['high']
                existing_candle.low_price = candle_data['low']
                existing_candle.close_price = candle_data['close']
                existing_candle.volume = candle_data['volume']
                existing_candle.quote_volume = candle_data.get('quote_volume', 0)
                existing_candle.trades_count = candle_data.get('trades_count', 0)
                existing_candle.updated_at = datetime.now(timezone.utc)
                db.commit()
                logger.debug(f"Updated existing candle for {symbol} on {exchange.name} at {candle_data['timestamp']}")
        except Exception as e:
            db.rollback()
            logger.error(f"Error saving/updating candle for {symbol} on {exchange.name}: {e}")
            raise  # Поднимаем ошибку для обработки на более высоком уровне
    
    def convert_minutes_to_timeframe(self, minutes: int) -> str:
        """Конвертирует минуты в таймфрейм ccxt"""
        timeframe_map = {
            1: '1m',
            3: '3m',
            5: '5m',
            15: '15m',
            30: '30m',
            60: '1h',
            120: '2h',
            240: '4h',
            360: '6h',
            480: '8h',
            720: '12h',
            1440: '1d',
            10080: '1w',
            43200: '1M'
        }
        return timeframe_map.get(minutes)
    
    async def collect_historical_candles(self):
        """Собирает исторические свечи с бирж"""
        logger.info("Starting historical candles collection")
        
        db = SessionLocal()
        try:
            start_date = datetime(2020, 1, 1, tzinfo=timezone.utc)
            entities = self._get_active_entities(db)
            
            for exchange in entities['exchanges']:
                # Обрабатываем каждую биржу в отдельной транзакции
                success = await self._process_exchange_historical_data(db, exchange, entities, start_date)
                if success:
                    db.commit()
                    logger.debug(f"Successfully processed historical data for exchange {exchange.name}")
                else:
                    db.rollback()
                    logger.error(f"Failed to process historical data for exchange {exchange.name}")
            
            # Если нет бирж для обработки, всё равно делаем commit
            if not entities['exchanges']:
                db.commit()
            
            logger.info("Historical candles collection completed")
            
        except Exception as e:
            logger.error(f"Error in historical candles collection: {e}")
            db.rollback()
        finally:
            db.close()

    async def _process_exchange_historical_data(self, db: Session, exchange, entities: dict, start_date: datetime) -> bool:
        """Обрабатывает исторические данные для одной биржи. Возвращает True в случае успеха, False при ошибке"""
        try:
            exchange_instance = exchange_service.get_exchange_instance(exchange)
        except Exception as e:
            logger.error(f"Error initializing exchange {exchange.name} for historical data: {e}")
            return False
        
        for pair in entities['currency_pairs']:
            symbol = f"{pair.base_symbol.symbol}/{pair.quote_symbol.symbol}"
            try:
                await self._process_pair_historical_data(db, exchange, exchange_instance, symbol, entities['time_periods'], start_date)
            except Exception as e:
                logger.error(f"Error processing historical data for symbol {symbol} on exchange {exchange.name}: {e}")
                # Продолжаем обработку следующих символов
                continue
        
        return True

    async def _process_pair_historical_data(self, db: Session, exchange, exchange_instance, symbol: str, time_periods, start_date: datetime):
        """Обрабатывает исторические данные для одной валютной пары"""
        for time_period in time_periods:
            timeframe = self.convert_minutes_to_timeframe(time_period.minutes)
            if timeframe:
                await self._collect_timeframe_historical_data(db, exchange, exchange_instance, symbol, time_period, timeframe, start_date)

    async def _collect_timeframe_historical_data(self, db: Session, exchange, exchange_instance, symbol: str, time_period, timeframe: str, start_date: datetime):
        """Собирает исторические данные для одного таймфрейма"""
        try:
            missing_ranges = await exchange_service.get_missing_candles_timerange(
                db, symbol, exchange.id, time_period.id, start_date
            )
            
            for start_time, end_time in missing_ranges:
                await self._collect_candles_for_range(db, exchange, exchange_instance, symbol, time_period, timeframe, start_time, end_time)
                
        except Exception as e:
            logger.error(f"Error collecting historical candles for {symbol} on {exchange.name} {timeframe}: {e}")

    async def _collect_candles_for_range(self, db: Session, exchange, exchange_instance, symbol: str, time_period, timeframe: str, start_time: datetime, end_time: datetime):
        """Собирает свечи для заданного временного диапазона"""
        current_time = start_time
        
        while current_time < end_time:
            historical_candles = await exchange_service.fetch_historical_candles(
                exchange_instance, symbol, timeframe, current_time, limit=1000
            )
            
            if not historical_candles:
                break
            
            self._save_historical_candles(db, exchange, time_period, symbol, historical_candles)
            
            # Обновляем current_time на основе последней свечи + интервал
            last_candle_time = historical_candles[-1]['timestamp']
            if last_candle_time <= current_time:
                # Если время не продвинулось, добавляем интервал
                current_time = current_time + timedelta(minutes=time_period.minutes * 100)
            else:
                current_time = last_candle_time + timedelta(minutes=time_period.minutes)

    def _save_historical_candles(self, db: Session, exchange, time_period, symbol: str, candles_data: list):
        """Сохраняет список исторических свечей"""
        currency_pair_id = self._get_currency_pair_id(db, symbol)
        saved_count = 0
        for candle_data in candles_data:
            try:
                existing_candle = db.query(models.Candle).filter(
                    models.Candle.currency_pair_id == currency_pair_id,
                    models.Candle.exchange_id == exchange.id,
                    models.Candle.time_period_id == time_period.id,
                    models.Candle.open_time == candle_data['timestamp']
                ).first()
                
                if not existing_candle:
                    new_candle = models.Candle(
                        currency_pair_id=currency_pair_id,
                        exchange_id=exchange.id,
                        time_period_id=time_period.id,
                        open_time=candle_data['timestamp'],
                        close_time=candle_data['timestamp'],  # Для исторических данных тоже используем одно время
                        open_price=candle_data['open'],
                        high_price=candle_data['high'],
                        low_price=candle_data['low'],
                        close_price=candle_data['close'],
                        volume=candle_data['volume'],
                        quote_volume=candle_data.get('quote_volume', 0),
                        trades_count=candle_data.get('trades_count', 0)
                    )
                    db.add(new_candle)
                    db.commit()  # Сразу сохраняем каждую свечу
                    saved_count += 1
            except Exception as e:
                db.rollback()
                logger.error(f"Error saving historical candle for {symbol} on {exchange.name} at {candle_data.get('timestamp', 'unknown')}: {e}")
                # Продолжаем сохранение остальных свечей
                continue
        
        if saved_count > 0:
            logger.debug(f"Saved {saved_count} historical candles for {symbol} on {exchange.name}")

    def cleanup_old_logs(self):
        """Очищает старые файлы логов"""
        logger.info("Starting log cleanup")
        try:
            # Очищаем основные логи (храним 30 дней)
            clean_old_logs(log_dir="logs", days_to_keep=30)
            
            # Очищаем тестовые логи (храним 7 дней)
            clean_old_logs(log_dir="logs/tests", days_to_keep=7)
            
            logger.info("Log cleanup completed successfully")
        except Exception as e:
            logger.error(f"Error during log cleanup: {e}")


data_collection_service = DataCollectionService()
