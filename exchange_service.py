"""
Сервис для работы с криптовалютными биржами.

Модуль предоставляет функциональность для получения данных с различных
криптовалютных бирж через библиотеку CCXT.
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional

import ccxt
from sqlalchemy.orm import Session

import models

logger = logging.getLogger(__name__)


class ExchangeService:
    """Сервис для работы с криптовалютными биржами."""

    def __init__(self):
        """Инициализирует сервис."""
        self.exchanges = {}

    def _get_currency_pair_id(self, db: Session, symbol: str) -> int:
        """Получает currency_pair_id по символу (например BTC/USDT)."""
        try:
            # Разбираем символ на базовую и котируемую валюты
            if '/' in symbol:
                base_symbol, quote_symbol = symbol.split('/')
            else:
                raise ValueError(f"Invalid symbol format: {symbol}")

            # Находим символы в базе
            base_sym = db.query(models.Symbol).filter(
                models.Symbol.symbol == base_symbol
            ).first()
            quote_sym = db.query(models.Symbol).filter(
                models.Symbol.symbol == quote_symbol
            ).first()

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
            logger.error("Error getting currency_pair_id for %s: %s", symbol, e)
            raise

    def get_exchange_instance(self, exchange: models.Exchange) -> ccxt.Exchange:
        """Получает или создает экземпляр биржи."""
        exchange_id = exchange.id

        if exchange_id not in self.exchanges:
            exchange_code = exchange.code.lower()

            # Поддерживаемые биржи
            if exchange_code in ('binance', 'binance_testnet'):
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

    async def fetch_current_candle(self, exchange: ccxt.Exchange, symbol: str,
                                   timeframe: str) -> Optional[Dict]:
        """Получает текущую свечу с биржи."""
        try:
            # Получаем последние 2 свечи (текущую и предыдущую)
            loop = asyncio.get_event_loop()
            ohlcv = await loop.run_in_executor(None, exchange.fetch_ohlcv,
                                               symbol, timeframe, None, 2)
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
            logger.error("Error fetching current candle for %s on %s: %s",
                        symbol, exchange.id, e)
            return None

    async def fetch_historical_candles(self, exchange: ccxt.Exchange, symbol: str,
                                       timeframe: str, since: datetime,
                                       limit: int = 1000) -> List[Dict]:
        """Получает исторические свечи с биржи."""
        try:
            since_timestamp = int(since.timestamp() * 1000)
            loop = asyncio.get_event_loop()
            ohlcv = await loop.run_in_executor(None, exchange.fetch_ohlcv,
                                               symbol, timeframe, since_timestamp, limit)

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
            logger.error("Error fetching historical candles for %s on %s: %s",
                        symbol, exchange.id, e)
            return []

    async def get_missing_candles_timerange(self, db: Session, symbol: str,
                                            exchange_id: int, time_period_id: int,
                                            start_date: datetime) -> List[tuple]:
        """Определяет промежутки времени с недостающими данными."""

        def _get_existing_candles():
            currency_pair_id = self._get_currency_pair_id(db, symbol)
            return db.query(models.Candle).filter(
                models.Candle.currency_pair_id == currency_pair_id,
                models.Candle.exchange_id == exchange_id,
                models.Candle.time_period_id == time_period_id,
                models.Candle.open_time >= start_date
            ).order_by(models.Candle.open_time).all()

        # Получаем все существующие свечи для данного символа, биржи и таймфрейма
        loop = asyncio.get_event_loop()
        existing_candles = await loop.run_in_executor(None, _get_existing_candles)

        if not existing_candles:
            # Если нет данных, возвращаем весь период
            return [(start_date, datetime.now(timezone.utc))]

        gaps = []
        current_time = start_date

        for candle in existing_candles:
            # Приводим timestamp из БД к UTC если он без timezone
            candle_timestamp = candle.open_time
            if candle_timestamp.tzinfo is None:
                candle_timestamp = candle_timestamp.replace(tzinfo=timezone.utc)

            if candle_timestamp > current_time:
                gaps.append((current_time, candle_timestamp))
            current_time = max(current_time, candle_timestamp + timedelta(minutes=1))

        # Проверяем последний промежуток до текущего времени
        now = datetime.now(timezone.utc)
        if current_time < now:
            gaps.append((current_time, now))

        return gaps


exchange_service = ExchangeService()
