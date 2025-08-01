"""
Pydantic схемы для валидации и сериализации данных API.

Этот модуль содержит схемы для всех моделей данных,
используемые для валидации входящих запросов и сериализации ответов API.
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, EmailStr


# User schemas
class UserBase(BaseModel):
    """Базовая схема пользователя."""

    name: str
    email: EmailStr


class UserCreate(UserBase):
    """Схема для создания пользователя."""

    password: str


class User(UserBase):
    """Схема пользователя для ответов API."""

    id: int
    email_verified_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        """Конфигурация Pydantic модели."""

        from_attributes = True


# Exchange schemas
class ExchangeBase(BaseModel):
    """Базовая схема биржи."""

    name: str


class ExchangeCreate(ExchangeBase):
    """Схема для создания биржи."""

    api_key: Optional[str] = None
    api_secret: Optional[str] = None


class Exchange(ExchangeBase):
    """Схема биржи для ответов API."""

    id: int
    api_key: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        """Конфигурация Pydantic модели."""

        from_attributes = True


# Currency Pair schemas
class CurrencyPairBase(BaseModel):
    """Базовая схема валютной пары."""

    symbol: str
    base_currency: str
    quote_currency: str


class CurrencyPairCreate(CurrencyPairBase):
    """Схема для создания валютной пары."""


class CurrencyPair(CurrencyPairBase):
    """Схема валютной пары для ответов API."""

    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        """Конфигурация Pydantic модели."""

        from_attributes = True


# Time Period schemas
class TimePeriodBase(BaseModel):
    """Базовая схема временного периода."""

    name: str
    interval: str


class TimePeriodCreate(TimePeriodBase):
    """Схема для создания временного периода."""


class TimePeriod(TimePeriodBase):
    """Схема временного периода для ответов API."""

    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        """Конфигурация Pydantic модели."""

        from_attributes = True


# Candle schemas
class CandleBase(BaseModel):
    """Базовая схема свечи."""

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
    """Схема для создания свечи."""


class Candle(CandleBase):
    """Схема свечи для ответов API."""

    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        """Конфигурация Pydantic модели."""

        from_attributes = True


# Exchange Configuration schemas
class ExchangeConfigurationBase(BaseModel):
    """Базовая схема конфигурации биржи."""

    exchange_id: int
    user_id: int
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    sandbox_mode: bool = False


class ExchangeConfigurationCreate(ExchangeConfigurationBase):
    """Схема для создания конфигурации биржи."""


class ExchangeConfiguration(ExchangeConfigurationBase):
    """Схема конфигурации биржи для ответов API."""

    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        """Конфигурация Pydantic модели."""

        from_attributes = True
