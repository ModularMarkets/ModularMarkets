"""
Shop interface for managing merchants and items.
"""
from abc import ABC
from typing import Dict, Optional, Any

from .merchant import Merchant
from .platforms.platform import Platform
from .algorithm import Algorithm


class Shop(ABC):
    """Abstract base class for shops that manage merchants."""
    
    def __init__(self, platform: Platform, db: Any):
        """
        Initialize the shop.
        
        Args:
            platform: The platform instance this shop operates on
            db: Database connection/instance
        """
        self.my_platform = platform
        self.my_db = db
        self.merchants: Dict[str, Merchant] = {}
    
    def add_merchant(
        self,
        name: str,
        starting_price: int,
        algo: Algorithm,
        buy_cap: int,
        sell_cap: int
    ) -> None:
        """
        Create and register a new merchant.
        
        Args:
            name: Name of the item/merchant (should be checked against platform item list)
            starting_price: Initial price for the item
            algo: Algorithm instance to use for price calculation
            buy_cap: Maximum quantity that can be bought in a single transaction
            sell_cap: Maximum quantity that can be sold in a single transaction
        """
        if name not in self.my_platform.get_item_list():
            raise ValueError(f"Item {name} not available on platform")
        
        if name in self.merchants:
            raise ValueError(f"Merchant for {name} already exists")
        
        initial_buy_price = starting_price * 0.95
        initial_sell_price = starting_price * 1.05
        
        merchant = Merchant(
            item=name,
            buy_price=initial_buy_price,
            sell_price=initial_sell_price,
            platform=self.my_platform,
            db=self.my_db,
            algo=algo,
            buy_cap=buy_cap,
            sell_cap=sell_cap
        )
        
        self.merchants[name] = merchant
        
        from .models import MerchantModel
        merchant_model = MerchantModel(
            item=name,
            shop_id=getattr(self, 'shop_id', ''),
            buy_price=initial_buy_price,
            sell_price=initial_sell_price,
            algorithm_type=algo.__class__.__name__,
            algorithm_config={}
        )
        self.my_db.add(merchant_model)
        self.my_db.commit()
    
    def remove_merchant(self, name: str) -> None:
        """
        Remove a merchant by name.
        
        Args:
            name: Name of the merchant to remove
        """
        if name not in self.merchants:
            raise ValueError(f"Merchant {name} not found")
        
        merchant = self.merchants[name]
        
        from .models import MerchantModel
        merchant_model = self.my_db.query(MerchantModel).filter(
            MerchantModel.item == name
        ).first()
        if merchant_model:
            self.my_db.delete(merchant_model)
        
        del self.merchants[name]
        self.my_db.commit()
    
    def get_merchant(self, name: str) -> Optional[Merchant]:
        """
        Retrieve merchant by name.
        
        Args:
            name: Name of the merchant
            
        Returns:
            Merchant instance or None if not found
        """
        return self.merchants.get(name)
    
    def save_shop_to_sql(self) -> None:
        """Save the shop state to the database."""
        from .models import ShopModel
        
        shop_model = self.my_db.query(ShopModel).filter(
            ShopModel.shop_id == getattr(self, 'shop_id', None)
        ).first()
        if shop_model:
            shop_model.platform_type = getattr(self, 'platform_type', None)
            shop_model.platform_config = getattr(self, 'platform_config', {})
        self.my_db.commit()

