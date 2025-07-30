from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional
from decimal import Decimal


# User schemas
class UserBase(BaseModel):
    name: str
    email: EmailStr


class UserCreate(UserBase):
    password: str


class User(UserBase):
    id: int
    email_verified_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Exchange schemas
class ExchangeBase(BaseModel):
    name: str


class ExchangeCreate(ExchangeBase):
    api_key: Optional[str] = None
    api_secret: Optional[str] = None


class Exchange(ExchangeBase):
    id: int
    api_key: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Currency Pair schemas
class CurrencyPairBase(BaseModel):
    symbol: str
    base_currency: str
    quote_currency: str


class CurrencyPairCreate(CurrencyPairBase):
    pass


class CurrencyPair(CurrencyPairBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Time Period schemas
class TimePeriodBase(BaseModel):
    name: str
    interval: str


class TimePeriodCreate(TimePeriodBase):
    pass


class TimePeriod(TimePeriodBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Candle schemas
class CandleBase(BaseModel):
    currency_pair_id: int
    exchange_id: int
    time_period_id: int
    open_time: datetime
    close_time: datetime
    open_price: Decimal
    high_price: Decimal
    low_price: Decimal
    close_price: Decimal
    volume: Decimal
    quote_volume: Optional[Decimal] = None
    trades_count: Optional[int] = None


class CandleCreate(CandleBase):
    pass


class Candle(CandleBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Exchange Configuration schemas
class ExchangeConfigurationBase(BaseModel):
    exchange_id: int
    user_id: int
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    sandbox_mode: bool = False


class ExchangeConfigurationCreate(ExchangeConfigurationBase):
    pass


class ExchangeConfiguration(ExchangeConfigurationBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True