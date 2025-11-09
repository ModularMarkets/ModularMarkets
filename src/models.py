"""
Database models for persistence.
"""
from sqlalchemy import Column, String, Float, Integer, DateTime, JSON, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()


class UserModel(Base):
    __tablename__ = 'users'
    username = Column(String, primary_key=True)
    display_name = Column(String)
    balance = Column(Float)
    hashed_pass = Column(String)
    account_creation_time = Column(Integer)
    role = Column(Integer)
    linked_accounts = Column(JSON)


class ShopModel(Base):
    __tablename__ = 'shops'
    shop_id = Column(String, primary_key=True)
    platform_type = Column(String)
    platform_config = Column(JSON)


class MerchantModel(Base):
    __tablename__ = 'merchants'
    item = Column(String, primary_key=True)
    shop_id = Column(String)
    buy_price = Column(Float)
    sell_price = Column(Float)
    algorithm_type = Column(String)
    algorithm_config = Column(JSON)


class TransactionModel(Base):
    __tablename__ = 'transactions'
    transaction_id = Column(String, primary_key=True)
    type = Column(String)
    user_id = Column(String)
    item_name = Column(String)
    quantity = Column(Integer)
    price = Column(Float)
    timestamp = Column(DateTime)

