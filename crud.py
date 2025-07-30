from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from datetime import datetime

import models
import schemas


# User CRUD operations
def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()


def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.User).offset(skip).limit(limit).all()


def create_user(db: Session, user: schemas.UserCreate):
    db_user = models.User(
        name=user.name,
        email=user.email,
        password=user.password  # В реальном приложении нужно хэшировать пароль
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


# Exchange CRUD operations
def get_exchange(db: Session, exchange_id: int):
    return db.query(models.Exchange).filter(models.Exchange.id == exchange_id).first()


def get_exchanges(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Exchange).offset(skip).limit(limit).all()


def create_exchange(db: Session, exchange: schemas.ExchangeCreate):
    db_exchange = models.Exchange(**exchange.dict())
    db.add(db_exchange)
    db.commit()
    db.refresh(db_exchange)
    return db_exchange


# Currency Pair CRUD operations
def get_currency_pair(db: Session, pair_id: int):
    return db.query(models.CurrencyPair).filter(models.CurrencyPair.id == pair_id).first()


def get_currency_pairs(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.CurrencyPair).offset(skip).limit(limit).all()


def get_currency_pair_by_symbol(db: Session, symbol: str):
    return db.query(models.CurrencyPair).filter(models.CurrencyPair.symbol == symbol).first()


def create_currency_pair(db: Session, pair: schemas.CurrencyPairCreate):
    db_pair = models.CurrencyPair(**pair.dict())
    db.add(db_pair)
    db.commit()
    db.refresh(db_pair)
    return db_pair


# Time Period CRUD operations
def get_time_period(db: Session, period_id: int):
    return db.query(models.TimePeriod).filter(models.TimePeriod.id == period_id).first()


def get_time_periods(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.TimePeriod).offset(skip).limit(limit).all()


def create_time_period(db: Session, period: schemas.TimePeriodCreate):
    db_period = models.TimePeriod(**period.dict())
    db.add(db_period)
    db.commit()
    db.refresh(db_period)
    return db_period


# Candle CRUD operations
def get_candle(db: Session, candle_id: int):
    return db.query(models.Candle).filter(models.Candle.id == candle_id).first()


def get_candles(
    db: Session, 
    symbol: Optional[str] = None,
    currency_pair_id: Optional[int] = None,
    exchange_id: Optional[int] = None,
    time_period_id: Optional[int] = None,
    skip: int = 0, 
    limit: int = 100
):
    query = db.query(models.Candle)
    
    if symbol:
        # Конвертируем символ в currency_pair_id
        if '/' in symbol:
            base_symbol, quote_symbol = symbol.split('/')
            base_sym = db.query(models.Symbol).filter(models.Symbol.symbol == base_symbol).first()
            quote_sym = db.query(models.Symbol).filter(models.Symbol.symbol == quote_symbol).first()
            if base_sym and quote_sym:
                currency_pair = db.query(models.CurrencyPair).filter(
                    models.CurrencyPair.base_symbol_id == base_sym.id,
                    models.CurrencyPair.quote_symbol_id == quote_sym.id
                ).first()
                if currency_pair:
                    query = query.filter(models.Candle.currency_pair_id == currency_pair.id)
    
    if currency_pair_id:
        query = query.filter(models.Candle.currency_pair_id == currency_pair_id)
    if exchange_id:
        query = query.filter(models.Candle.exchange_id == exchange_id)
    if time_period_id:
        query = query.filter(models.Candle.time_period_id == time_period_id)
    
    return query.order_by(desc(models.Candle.open_time)).offset(skip).limit(limit).all()


def create_candle(db: Session, candle: schemas.CandleCreate):
    db_candle = models.Candle(**candle.dict())
    db.add(db_candle)
    db.commit()
    db.refresh(db_candle)
    return db_candle


# Exchange Configuration CRUD operations
def get_exchange_configuration(db: Session, config_id: int):
    return db.query(models.ExchangeConfiguration).filter(models.ExchangeConfiguration.id == config_id).first()


def get_exchange_configurations_by_user(db: Session, user_id: int):
    return db.query(models.ExchangeConfiguration).filter(models.ExchangeConfiguration.user_id == user_id).all()


def create_exchange_configuration(db: Session, config: schemas.ExchangeConfigurationCreate):
    db_config = models.ExchangeConfiguration(**config.dict())
    db.add(db_config)
    db.commit()
    db.refresh(db_config)
    return db_config