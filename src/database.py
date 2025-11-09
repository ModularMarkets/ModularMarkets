"""
Database connection, session management, and initialization functions.
"""
import os
import importlib
import inspect
from pathlib import Path
from typing import Dict, Any
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

from .models import Base, UserModel, ShopModel, MerchantModel
from .shop import Shop
from .users.user import User
from .algorithm import Algorithm, Result

load_dotenv()

# Platform registry: automatically discovered from src/platforms/
PLATFORM_REGISTRY: Dict[str, Any] = {}

# Algorithm registry: automatically discovered from src/algorithms/
ALGORITHM_REGISTRY: Dict[str, Any] = {}


def _discover_algorithms() -> None:
    """
    Automatically discover all algorithms from src/algorithms/ directory.
    Each Python file in the algorithms directory should contain an Algorithm class.
    The algorithm_name property is used as the registry key.
    """
    algorithms_dir = Path(__file__).parent / "algorithms"
    
    if not algorithms_dir.exists():
        return
    
    # Get all Python files in algorithms directory (excluding __init__.py)
    algorithm_files = [
        f for f in algorithms_dir.glob("*.py")
        if f.name != "__init__.py" and f.is_file()
    ]
    
    for algo_file in algorithm_files:
        try:
            # Import module: .algorithms.filename (relative import)
            module_name = f".algorithms.{algo_file.stem}"
            module = importlib.import_module(module_name, package="src")
            
            # Find all Algorithm subclasses in the module
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if (issubclass(obj, Algorithm) and 
                    obj is not Algorithm):
                    # Check if the class is from this module
                    obj_module = obj.__module__
                    expected_module = f"src.algorithms.{algo_file.stem}"
                    if obj_module == expected_module or obj_module.endswith(f".algorithms.{algo_file.stem}"):
                        # Create instance to get algorithm_name
                        try:
                            instance = obj()
                            algo_name = instance.algorithm_name
                            if algo_name:
                                ALGORITHM_REGISTRY[algo_name] = obj
                        except Exception as e:
                            print(f"Warning: Could not instantiate algorithm {name} from {algo_file.name}: {e}")
        except Exception as e:
            print(f"Warning: Could not load algorithm from {algo_file.name}: {e}")


def _discover_platforms() -> None:
    """
    Automatically discover all platforms from src/platforms/ directory.
    Each subdirectory in platforms/ is a platform.
    Import pattern: platforms."platformname" (lowercase) -> import PlatformName (PascalCase)
    Example: platforms/minecraft/ -> from .platforms.minecraft import Minecraft
    """
    platforms_dir = Path(__file__).parent / "platforms"
    
    if not platforms_dir.exists():
        return
    
    # Get all subdirectories in platforms directory
    platform_dirs = [
        d for d in platforms_dir.iterdir()
        if d.is_dir() and not d.name.startswith("__") and d.name != "utils"
    ]
    
    for platform_dir in platform_dirs:
        platform_name_lower = platform_dir.name.lower()
        # Convert folder name to PascalCase class name
        # e.g., "minecraft" -> "Minecraft", "cs_go" -> "CsGo"
        platform_name_pascal = ''.join(word.capitalize() for word in platform_name_lower.split('_'))
        
        try:
            # Import from .platforms.platformname (relative import)
            module_name = f".platforms.{platform_name_lower}"
            module = importlib.import_module(module_name, package="src")
            
            # Try to get the platform class (should match PascalCase name)
            platform_class = getattr(module, platform_name_pascal, None)
            
            if platform_class is None:
                # Try alternative: look for Platform subclass in the module
                from .platforms.platform import Platform
                expected_module_base = f"src.platforms.{platform_name_lower}"
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if (issubclass(obj, Platform) and 
                        obj is not Platform):
                        obj_module = obj.__module__
                        # Check if it's from this platform's module (could be in __init__ or platform.py)
                        if (obj_module.startswith(expected_module_base) or 
                            obj_module.endswith(f".platforms.{platform_name_lower}") or
                            obj_module.endswith(f".platforms.{platform_name_lower}.platform")):
                            platform_class = obj
                            platform_name_pascal = name  # Use actual class name
                            break
                
                # If still not found, try importing from platform.py directly
                if platform_class is None:
                    try:
                        platform_module_name = f".platforms.{platform_name_lower}.platform"
                        platform_module = importlib.import_module(platform_module_name, package="src")
                        platform_class = getattr(platform_module, platform_name_pascal, None)
                    except ImportError:
                        pass
            
            if platform_class:
                # Use the folder name (lowercase) as the registry key
                # But store it with first letter capitalized for display
                registry_key = platform_name_pascal
                PLATFORM_REGISTRY[registry_key] = platform_class
            else:
                print(f"Warning: Could not find platform class '{platform_name_pascal}' in {platform_name_lower}")
        except Exception as e:
            print(f"Warning: Could not load platform from {platform_name_lower}: {e}")


# Auto-discover algorithms and platforms on module import
_discover_algorithms()
_discover_platforms()


def get_db():
    """Get database session."""
    db_url = os.getenv('DATABASE_URL', 'sqlite:///marketmaker.db')
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def _create_platform(platform_type: str) -> Any:
    """
    Create platform instance from type using the platform registry.
    Platforms load their own configuration from environment variables or config files.
    
    Args:
        platform_type: Type of platform (e.g., "Minecraft")
        
    Returns:
        Platform instance
        
    Raises:
        ValueError: If platform_type is empty or platform is not found in registry
        RuntimeError: If platform creation fails
    """
    if not platform_type:
        raise ValueError("Cannot create platform: platform_type is empty")
    
    # Look up platform in registry
    if platform_type not in PLATFORM_REGISTRY:
        raise ValueError(
            f"Platform '{platform_type}' not found in registry. "
            f"Available platforms: {list(PLATFORM_REGISTRY.keys())}"
        )
    
    platform_class = PLATFORM_REGISTRY[platform_type]
    try:
        # Create platform instance (platforms load their own config from env/config files)
        return platform_class()
    except Exception as e:
        raise RuntimeError(
            f"Failed to create platform '{platform_type}': {str(e)}"
        ) from e


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
        # Recreate platform from stored type
        platform = _create_platform(
            shop_model.platform_type or "Minecraft"
        )
        
        # Create shop instance
        shop = Shop(platform, db)
        shop.shop_id = shop_model.shop_id
        shop.platform_type = shop_model.platform_type
        
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

