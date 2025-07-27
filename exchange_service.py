import ccxt
import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from typing import List, Dict, Optional
import models
from database import SessionLocal

logger = logging.getLogger(__name__)


class ExchangeService:
    def __init__(self):
        self.exchanges = {}
        
    def get_exchange_instance(self, exchange: models.Exchange) -> ccxt.Exchange:
        """Получает или создает экземпляр биржи"""
        exchange_id = exchange.id
        
        if exchange_id not in self.exchanges:
            exchange_code = exchange.code.lower()
            
            # Поддерживаемые биржи
            if exchange_code == 'binance' or exchange_code == 'binance_testnet':
                exchange_class = ccxt.binance
            elif exchange_code == 'okx':
                exchange_class = ccxt.okx
            elif exchange_code == 'bybit':
                exchange_class = ccxt.bybit
            elif exchange_code == 'gate':
                exchange_class = ccxt.gate
            else:
                raise ValueError(f"Unsupported exchange: {exchange_code}")
            
            # Создаем экземпляр биржи
            config = {
                'apiKey': exchange.api_key,
                'secret': exchange.api_secret,
                'sandbox': exchange.environment == 'sandbox',
                'enableRateLimit': True,
            }
            
            # Добавляем passphrase для OKX и Coinbase
            if exchange.api_passphrase:
                config['password'] = exchange.api_passphrase
            
            exchange_instance = exchange_class(config)
            self.exchanges[exchange_id] = exchange_instance
            
        return self.exchanges[exchange_id]
    
    def fetch_current_candle(self, exchange: ccxt.Exchange, symbol: str, timeframe: str) -> Optional[Dict]:
        """Получает текущую свечу с биржи"""
        try:
            # Получаем последние 2 свечи (текущую и предыдущую)
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=2)
            if ohlcv:
                # Берем последнюю свечу
                candle = ohlcv[-1]
                return {
                    'timestamp': datetime.fromtimestamp(candle[0] / 1000, tz=timezone.utc),
                    'open': candle[1],
                    'high': candle[2],
                    'low': candle[3],
                    'close': candle[4],
                    'volume': candle[5]
                }
        except Exception as e:
            logger.error(f"Error fetching current candle for {symbol} on {exchange.id}: {e}")
            return None
    
    def fetch_historical_candles(self, exchange: ccxt.Exchange, symbol: str, timeframe: str, 
                                since: datetime, limit: int = 1000) -> List[Dict]:
        """Получает исторические свечи с биржи"""
        try:
            since_timestamp = int(since.timestamp() * 1000)
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since=since_timestamp, limit=limit)
            
            candles = []
            for candle in ohlcv:
                candles.append({
                    'timestamp': datetime.fromtimestamp(candle[0] / 1000, tz=timezone.utc),
                    'open': candle[1],
                    'high': candle[2],
                    'low': candle[3],
                    'close': candle[4],
                    'volume': candle[5]
                })
            
            return candles
        except Exception as e:
            logger.error(f"Error fetching historical candles for {symbol} on {exchange.id}: {e}")
            return []
    
    def get_missing_candles_timerange(self, db: Session, symbol: str, exchange_id: int, 
                                    time_period_id: int, start_date: datetime) -> List[tuple]:
        """Определяет промежутки времени с недостающими данными"""
        
        # Получаем все существующие свечи для данного символа, биржи и таймфрейма
        existing_candles = db.query(models.Candle).filter(
            models.Candle.symbol == symbol,
            models.Candle.exchange_id == exchange_id,
            models.Candle.time_period_id == time_period_id,
            models.Candle.timestamp >= start_date
        ).order_by(models.Candle.timestamp).all()
        
        if not existing_candles:
            # Если нет данных, возвращаем весь период
            return [(start_date, datetime.now(timezone.utc))]
        
        gaps = []
        current_time = start_date
        
        for candle in existing_candles:
            if candle.timestamp > current_time:
                gaps.append((current_time, candle.timestamp))
            current_time = max(current_time, candle.timestamp + timedelta(minutes=1))
        
        # Проверяем последний промежуток до текущего времени
        now = datetime.now(timezone.utc)
        if current_time < now:
            gaps.append((current_time, now))
        
        return gaps


exchange_service = ExchangeService()
