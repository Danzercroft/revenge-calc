from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Numeric, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    email_verified_at = Column(DateTime)
    password = Column(String, nullable=False)
    remember_token = Column(String)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Exchange(Base):
    __tablename__ = "exchanges"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    code = Column(String, nullable=False)
    environment = Column(String, nullable=False)  # production/sandbox
    api_key = Column(String)
    api_secret = Column(String)
    api_passphrase = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Symbol(Base):
    __tablename__ = "symbols"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    symbol = Column(String, nullable=False, unique=True)
    description = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class CurrencyPair(Base):
    __tablename__ = "currency_pairs"

    id = Column(Integer, primary_key=True, index=True)
    base_symbol_id = Column(Integer, ForeignKey("symbols.id"))
    quote_symbol_id = Column(Integer, ForeignKey("symbols.id"))
    type = Column(String, nullable=False)  # spot/futures
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    base_symbol = relationship("Symbol", foreign_keys=[base_symbol_id])
    quote_symbol = relationship("Symbol", foreign_keys=[quote_symbol_id])


class TimePeriod(Base):
    __tablename__ = "time_periods"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    minutes = Column(Integer, nullable=False)
    description = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Candle(Base):
    __tablename__ = "candles"

    id = Column(Integer, primary_key=True, index=True)
    currency_pair_id = Column(Integer, ForeignKey("currency_pairs.id"))
    exchange_id = Column(Integer, ForeignKey("exchanges.id"))
    time_period_id = Column(Integer, ForeignKey("time_periods.id"))
    open_time = Column(DateTime, nullable=False)
    close_time = Column(DateTime, nullable=False)
    open_price = Column(Numeric(precision=18, scale=8))
    high_price = Column(Numeric(precision=18, scale=8))
    low_price = Column(Numeric(precision=18, scale=8))
    close_price = Column(Numeric(precision=18, scale=8))
    volume = Column(Numeric(precision=18, scale=8))
    quote_volume = Column(Numeric(precision=18, scale=8))
    trades_count = Column(Integer)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    currency_pair = relationship("CurrencyPair")
    exchange = relationship("Exchange")
    time_period = relationship("TimePeriod")


class ExchangeConfiguration(Base):
    __tablename__ = "exchange_configurations"

    id = Column(Integer, primary_key=True, index=True)
    exchange_id = Column(Integer, ForeignKey("exchanges.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    api_key = Column(String)
    api_secret = Column(String)
    sandbox_mode = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    exchange = relationship("Exchange")
    user = relationship("User")