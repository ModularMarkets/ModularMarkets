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
from .algorithm import Algorithm, Result

load_dotenv()

# Algorithm registry: maps algorithm names to their classes
# Add new algorithms here as they are implemented
ALGORITHM_REGISTRY: Dict[str, Any] = {
    # Stub algorithm (default fallback)
    "stub": None,  # Will be set to StubAlgorithm class below
    # Example entries (uncomment when algorithms are implemented):
    # "simple_mm": SimpleMarketMaker,
    # "volatility_adjusted": VolatilityAdjusted,
    # Add your algorithm classes here
}


def get_db():
    """Get database session."""
    db_url = os.getenv('DATABASE_URL', 'sqlite:///marketmaker.db')
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def _create_platform(platform_type: str, config: dict) -> Any:
    """
    Create platform instance from type and config.
    
    Args:
        platform_type: Type of platform (e.g., "Minecraft")
        config: Configuration dictionary for the platform
        
    Returns:
        Platform instance
    """
    if platform_type == "Minecraft":
        from .plugins.minecraft import Minecraft
        return Minecraft(
            api_key=config.get('api_key'),
            server_url=config.get('server_url')
        )
    else:
        raise ValueError(f"Unknown platform type: {platform_type}")


def _create_algorithm(algorithm_name: str, config: dict) -> Any:
    """
    Create algorithm instance from name and config using the algorithm registry.
    
    Args:
        algorithm_name: Unique name/identifier of the algorithm (from ALGORITHM_REGISTRY)
        config: Configuration dictionary for the algorithm
        
    Returns:
        Algorithm instance
        
    Raises:
        ValueError: If algorithm_name is empty or algorithm is not found in registry
        RuntimeError: If algorithm creation fails
    """
    if not algorithm_name:
        raise ValueError("Cannot create algorithm: algorithm_name is empty")
    
    # Look up algorithm in registry
    if algorithm_name not in ALGORITHM_REGISTRY:
        raise ValueError(
            f"Algorithm '{algorithm_name}' not found in registry. "
            f"Available algorithms: {list(ALGORITHM_REGISTRY.keys())}"
        )
    
    algorithm_class = ALGORITHM_REGISTRY[algorithm_name]
    try:
        # Create algorithm instance with config
        algo = algorithm_class()
        if config:
            algo.set_config(config)
        return algo
    except Exception as e:
        raise RuntimeError(
            f"Failed to create algorithm '{algorithm_name}': {str(e)}"
        ) from e


# Define StubAlgorithm class for the registry
class StubAlgorithm(Algorithm):
    """Stub algorithm that maintains current prices."""
    
    @property
    def algorithm_name(self) -> str:
        return "stub"
    
    def run(self, buy_price: float, sell_price: float, stock: int, past_transactions: Any) -> Result:
        """Return current prices unchanged."""
        return Result(new_buy=buy_price, new_sell=sell_price)


# Register the stub algorithm
ALGORITHM_REGISTRY["stub"] = StubAlgorithm


def _create_stub_algorithm() -> Any:
    """
    Create a stub algorithm that maintains current prices.
    This is used when algorithm implementations are not available.
    
    Returns:
        Stub Algorithm instance
    """
    return StubAlgorithm()


def load_all(db: Any) -> Dict:
    """
    Load all classes from database and return state.
    
    Args:
        db: Database session
        
    Returns:
        Dictionary with 'users' and 'shops' keys, where shops contain loaded merchants
    """
    users = {}
    shops = {}
    
    # Load all users
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
    
    # Load all shops and recreate platform instances
    shop_models = db.query(ShopModel).all()
    for shop_model in shop_models:
        # Recreate platform from stored config
        platform = _create_platform(
            shop_model.platform_type or "Minecraft",
            shop_model.platform_config or {}
        )
        
        # Create shop instance
        shop = Shop(platform, db)
        shop.shop_id = shop_model.shop_id
        shop.platform_type = shop_model.platform_type
        shop.platform_config = shop_model.platform_config or {}
        
        shops[shop_model.shop_id] = shop
    
    # Load all merchants and attach them to their shops
    merchant_models = db.query(MerchantModel).all()
    for merchant_model in merchant_models:
        shop_id = merchant_model.shop_id
        if shop_id not in shops:
            # Skip merchants for shops that don't exist
            continue
        
        shop = shops[shop_id]
        
        # Recreate algorithm instance (raises error if algorithm not found)
        algo = _create_algorithm(
            merchant_model.algorithm_type or "",
            merchant_model.algorithm_config or {}
        )
        
        # Create merchant instance with loaded data
        from .merchant import Merchant
        
        merchant = Merchant(
            item=merchant_model.item,
            buy_price=merchant_model.buy_price,
            sell_price=merchant_model.sell_price,
            platform=shop.my_platform,
            db=db,
            algo=algo,
            buy_cap=merchant_model.buy_cap if merchant_model.buy_cap is not None else 0,
            sell_cap=merchant_model.sell_cap if merchant_model.sell_cap is not None else 0
        )
        
        # Add merchant to shop
        shop.merchants[merchant_model.item] = merchant
    
    return {'users': users, 'shops': shops}

