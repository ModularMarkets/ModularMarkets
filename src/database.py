"""
Database connection, session management, and initialization functions.
"""
import os
from typing import Dict, Any
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

from .models import Base, UserModel, ShopModel, MerchantModel
from .shop import Shop
from .users.user import User

load_dotenv()


def get_db():
    """Get database session."""
    db_url = os.getenv('DATABASE_URL', 'sqlite:///marketmaker.db')
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def load_all(db: Any) -> Dict:
    """
    Load all classes from database and return state.
    
    Args:
        db: Database session
        
    Returns:
        Dictionary with 'users' and 'shops' keys
    """
    users = {}
    shops = {}
    
    user_models = db.query(UserModel).all()
    for user_model in user_models:
        users[user_model.username] = User(
            username=user_model.username,
            display_name=user_model.display_name,
            balance=user_model.balance,
            hashed_pass=user_model.hashed_pass,
            account_creation_time=user_model.account_creation_time,
            db=db,
            role=user_model.role if hasattr(user_model, 'role') and user_model.role is not None else 10,
            linked_accounts=user_model.linked_accounts or {}
        )
    
    shop_models = db.query(ShopModel).all()
    for shop_model in shop_models:
        # Shop creation will be handled by concrete implementation
        shops[shop_model.shop_id] = shop_model
    
    merchant_models = db.query(MerchantModel).all()
    for merchant_model in merchant_models:
        if merchant_model.shop_id in shops:
            # Merchant loading will be handled by shop
            pass
    
    return {'users': users, 'shops': shops}

