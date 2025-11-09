"""
FastAPI backend API for Market Maker App.
Exposes REST endpoints for frontend interaction.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List, Optional
from pydantic import BaseModel
import sys
from pathlib import Path

# Add src to path so we can import from it
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import get_db, load_all
from src.users.user import User
from src.shop import Shop
from src.merchant import Merchant


# Global application state (loaded on startup)
app_state: Dict = {
    'users': {},
    'shops': {},
    'db': None
}


# Pydantic models for request/response
class UserResponse(BaseModel):
    username: str
    display_name: str
    balance: float
    role: int
    linked_accounts: Dict[str, str]

    class Config:
        from_attributes = True


class MerchantInfo(BaseModel):
    item: str
    buy_price: float
    sell_price: float
    buy_cap: int
    sell_cap: int
    algorithm_name: str

    class Config:
        from_attributes = True


class ShopResponse(BaseModel):
    shop_id: str
    platform_type: str
    merchants: List[MerchantInfo]

    class Config:
        from_attributes = True


class BuyRequest(BaseModel):
    quantity: int
    username: str


class SellRequest(BaseModel):
    quantity: int
    username: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown."""
    # Startup
    print("Loading application state from database...")
    db = get_db()
    state = load_all(db)
    app_state['users'] = state['users']
    app_state['shops'] = state['shops']
    app_state['db'] = db
    print(f"Loaded {len(state['users'])} users and {len(state['shops'])} shops")
    
    yield
    
    # Shutdown
    if app_state.get('db'):
        app_state['db'].close()
        print("Database connection closed")


# Initialize FastAPI app
app = FastAPI(
    title="Market Maker API",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_app_state():
    """Dependency to get application state."""
    return app_state


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "users": len(app_state['users']), "shops": len(app_state['shops'])}


# User endpoints
@app.get("/api/users", response_model=List[UserResponse])
async def get_users(state: Dict = Depends(get_app_state)):
    """Get all users."""
    users = state['users']
    return [UserResponse(
        username=user.username,
        display_name=user.display_name,
        balance=user.balance,
        role=user.role,
        linked_accounts=user.linked_accounts
    ) for user in users.values()]


@app.get("/api/users/{username}", response_model=UserResponse)
async def get_user(username: str, state: Dict = Depends(get_app_state)):
    """Get a specific user by username."""
    users = state['users']
    if username not in users:
        raise HTTPException(status_code=404, detail="User not found")
    user = users[username]
    return UserResponse(
        username=user.username,
        display_name=user.display_name,
        balance=user.balance,
        role=user.role,
        linked_accounts=user.linked_accounts
    )


# Shop endpoints
@app.get("/api/shops", response_model=List[ShopResponse])
async def get_shops(state: Dict = Depends(get_app_state)):
    """Get all shops."""
    shops = state['shops']
    result = []
    for shop_id, shop in shops.items():
        merchants = []
        for item, merchant in shop.merchants.items():
            merchants.append(MerchantInfo(
                item=merchant.item,
                buy_price=merchant.buy_price,
                sell_price=merchant.sell_price,
                buy_cap=merchant.buy_cap,
                sell_cap=merchant.sell_cap,
                algorithm_name=merchant.algo.algorithm_name
            ))
        result.append(ShopResponse(
            shop_id=shop_id,
            platform_type=shop.platform_type or "Unknown",
            merchants=merchants
        ))
    return result


@app.get("/api/shops/{shop_id}", response_model=ShopResponse)
async def get_shop(shop_id: str, state: Dict = Depends(get_app_state)):
    """Get a specific shop by ID."""
    shops = state['shops']
    if shop_id not in shops:
        raise HTTPException(status_code=404, detail="Shop not found")
    shop = shops[shop_id]
    merchants = []
    for item, merchant in shop.merchants.items():
        merchants.append(MerchantInfo(
            item=merchant.item,
            buy_price=merchant.buy_price,
            sell_price=merchant.sell_price,
            buy_cap=merchant.buy_cap,
            sell_cap=merchant.sell_cap,
            algorithm_name=merchant.algo.algorithm_name
        ))
    return ShopResponse(
        shop_id=shop_id,
        platform_type=shop.platform_type or "Unknown",
        merchants=merchants
    )


# Merchant endpoints
@app.get("/api/shops/{shop_id}/merchants/{item}")
async def get_merchant(shop_id: str, item: str, state: Dict = Depends(get_app_state)):
    """Get a specific merchant."""
    shops = state['shops']
    if shop_id not in shops:
        raise HTTPException(status_code=404, detail="Shop not found")
    shop = shops[shop_id]
    merchant = shop.get_merchant(item)
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")
    return MerchantInfo(
        item=merchant.item,
        buy_price=merchant.buy_price,
        sell_price=merchant.sell_price,
        buy_cap=merchant.buy_cap,
        sell_cap=merchant.sell_cap,
        algorithm_name=merchant.algo.algorithm_name
    )


@app.post("/api/shops/{shop_id}/merchants/{item}/buy")
async def buy_item(shop_id: str, item: str, request: BuyRequest, state: Dict = Depends(get_app_state)):
    """Buy items from a merchant."""
    shops = state['shops']
    users = state['users']
    
    if shop_id not in shops:
        raise HTTPException(status_code=404, detail="Shop not found")
    if request.username not in users:
        raise HTTPException(status_code=404, detail="User not found")
    
    shop = shops[shop_id]
    merchant = shop.get_merchant(item)
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")
    
    user = users[request.username]
    
    try:
        merchant.buy(request.quantity, user)
        return {
            "success": True,
            "message": f"Bought {request.quantity} {item}",
            "new_balance": user.balance
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/shops/{shop_id}/merchants/{item}/sell")
async def sell_item(shop_id: str, item: str, request: SellRequest, state: Dict = Depends(get_app_state)):
    """Sell items to a merchant."""
    shops = state['shops']
    users = state['users']
    
    if shop_id not in shops:
        raise HTTPException(status_code=404, detail="Shop not found")
    if request.username not in users:
        raise HTTPException(status_code=404, detail="User not found")
    
    shop = shops[shop_id]
    merchant = shop.get_merchant(item)
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")
    
    user = users[request.username]
    
    try:
        merchant.sell(request.quantity, user)
        return {
            "success": True,
            "message": f"Sold {request.quantity} {item}",
            "new_balance": user.balance
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

