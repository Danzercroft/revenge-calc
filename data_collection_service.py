import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

import models
from database import SessionLocal
from exchange_service import exchange_service

logger = logging.getLogger(__name__)


class DataCollectionService:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        
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
            # Получаем все активные биржи
            exchanges = db.query(models.Exchange).filter(models.Exchange.is_active == True).all()
            
            # Получаем все активные валютные пары
            currency_pairs = db.query(models.CurrencyPair).filter(models.CurrencyPair.is_active == True).all()
            
            # Получаем все активные таймфреймы
            time_periods = db.query(models.TimePeriod).filter(models.TimePeriod.is_active == True).all()
            
            for exchange in exchanges:
                try:
                    exchange_instance = exchange_service.get_exchange_instance(exchange)
                    
                    for pair in currency_pairs:
                        # Формируем символ для биржи
                        base_symbol = pair.base_symbol.symbol
                        quote_symbol = pair.quote_symbol.symbol
                        symbol = f"{base_symbol}/{quote_symbol}"
                        
                        for time_period in time_periods:
                            try:
                                # Конвертируем минуты в таймфрейм ccxt
                                timeframe = self.convert_minutes_to_timeframe(time_period.minutes)
                                if not timeframe:
                                    continue
                                
                                # Получаем текущую свечу
                                candle_data = exchange_service.fetch_current_candle(
                                    exchange_instance, symbol, timeframe
                                )
                                
                                if candle_data:
                                    # Проверяем, существует ли уже такая свеча
                                    existing_candle = db.query(models.Candle).filter(
                                        models.Candle.symbol == symbol,
                                        models.Candle.exchange_id == exchange.id,
                                        models.Candle.time_period_id == time_period.id,
                                        models.Candle.timestamp == candle_data['timestamp']
                                    ).first()
                                    
                                    if not existing_candle:
                                        # Создаем новую свечу
                                        new_candle = models.Candle(
                                            symbol=symbol,
                                            exchange_id=exchange.id,
                                            time_period_id=time_period.id,
                                            open_price=candle_data['open'],
                                            high_price=candle_data['high'],
                                            low_price=candle_data['low'],
                                            close_price=candle_data['close'],
                                            volume=candle_data['volume'],
                                            timestamp=candle_data['timestamp']
                                        )
                                        db.add(new_candle)
                                    else:
                                        # Обновляем существующую свечу
                                        existing_candle.open_price = candle_data['open']
                                        existing_candle.high_price = candle_data['high']
                                        existing_candle.low_price = candle_data['low']
                                        existing_candle.close_price = candle_data['close']
                                        existing_candle.volume = candle_data['volume']
                                        existing_candle.updated_at = datetime.now(timezone.utc)
                                
                            except Exception as e:
                                logger.error(f"Error collecting current candle for {symbol} "
                                           f"on {exchange.name} {timeframe}: {e}")
                                continue
                    
                except Exception as e:
                    logger.error(f"Error with exchange {exchange.name}: {e}")
                    continue
            
            db.commit()
            logger.info("Current candles collection completed")
            
        except Exception as e:
            logger.error(f"Error in current candles collection: {e}")
            db.rollback()
        finally:
            db.close()
    
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
            # Дата начала сбора исторических данных
            start_date = datetime(2020, 1, 1, tzinfo=timezone.utc)
            
            # Получаем все активные биржи
            exchanges = db.query(models.Exchange).filter(models.Exchange.is_active == True).all()
            
            # Получаем все активные валютные пары
            currency_pairs = db.query(models.CurrencyPair).filter(models.CurrencyPair.is_active == True).all()
            
            # Получаем все активные таймфреймы
            time_periods = db.query(models.TimePeriod).filter(models.TimePeriod.is_active == True).all()
            
            for exchange in exchanges:
                try:
                    exchange_instance = exchange_service.get_exchange_instance(exchange)
                    
                    for pair in currency_pairs:
                        # Формируем символ для биржи
                        base_symbol = pair.base_symbol.symbol
                        quote_symbol = pair.quote_symbol.symbol
                        symbol = f"{base_symbol}/{quote_symbol}"
                        
                        for time_period in time_periods:
                            try:
                                # Конвертируем минуты в таймфрейм ccxt
                                timeframe = self.convert_minutes_to_timeframe(time_period.minutes)
                                if not timeframe:
                                    continue
                                
                                # Находим промежутки с недостающими данными
                                missing_ranges = exchange_service.get_missing_candles_timerange(
                                    db, symbol, exchange.id, time_period.id, start_date
                                )
                                
                                for start_time, end_time in missing_ranges:
                                    # Собираем данные по частям (по 1000 свечей за раз)
                                    current_time = start_time
                                    
                                    while current_time < end_time:
                                        historical_candles = exchange_service.fetch_historical_candles(
                                            exchange_instance, symbol, timeframe, 
                                            current_time, limit=1000
                                        )
                                        
                                        if not historical_candles:
                                            break
                                        
                                        # Сохраняем полученные свечи
                                        for candle_data in historical_candles:
                                            existing_candle = db.query(models.Candle).filter(
                                                models.Candle.symbol == symbol,
                                                models.Candle.exchange_id == exchange.id,
                                                models.Candle.time_period_id == time_period.id,
                                                models.Candle.timestamp == candle_data['timestamp']
                                            ).first()
                                            
                                            if not existing_candle:
                                                new_candle = models.Candle(
                                                    symbol=symbol,
                                                    exchange_id=exchange.id,
                                                    time_period_id=time_period.id,
                                                    open_price=candle_data['open'],
                                                    high_price=candle_data['high'],
                                                    low_price=candle_data['low'],
                                                    close_price=candle_data['close'],
                                                    volume=candle_data['volume'],
                                                    timestamp=candle_data['timestamp']
                                                )
                                                db.add(new_candle)
                                        
                                        # Обновляем время для следующей итерации
                                        if historical_candles:
                                            current_time = historical_candles[-1]['timestamp']
                                        else:
                                            break
                                        
                                        # Коммитим данные частями
                                        db.commit()
                                
                            except Exception as e:
                                logger.error(f"Error collecting historical candles for {symbol} "
                                           f"on {exchange.name} {timeframe}: {e}")
                                continue
                    
                except Exception as e:
                    logger.error(f"Error with exchange {exchange.name}: {e}")
                    continue
            
            db.commit()
            logger.info("Historical candles collection completed")
            
        except Exception as e:
            logger.error(f"Error in historical candles collection: {e}")
            db.rollback()
        finally:
            db.close()


data_collection_service = DataCollectionService()
