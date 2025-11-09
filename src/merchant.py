"""
Merchant class for managing individual item trading.
"""
from typing import Optional, Any

from .users.user import User
from .algorithm import Algorithm
from .platforms.platform import Platform


class Merchant:
    """Represents a merchant that trades a specific item."""
    
    def __init__(
        self,
        item: str,
        buy_price: float,
        sell_price: float,
        platform: Platform,
        db: Any,
        algo: Algorithm,
        buy_cap: int,
        sell_cap: int
    ):
        """
        Initialize a merchant.
        
        Args:
            item: Name of the item this merchant sells (unique identifier)
            buy_price: Current buy price
            sell_price: Current sell price
            platform: Platform instance
            db: Database connection/instance
            algo: Algorithm instance for price updates
            buy_cap: Maximum quantity that can be bought in a single transaction
            sell_cap: Maximum quantity that can be sold in a single transaction
        """
        self.item = item
        self.buy_price = buy_price
        self.sell_price = sell_price
        self.my_platform = platform
        self.my_db = db
        self.algo = algo
        self.buy_cap = buy_cap
        self.sell_cap = sell_cap
    
    def buy(self, qty: int, user: User) -> None:
        #PLEASE DO NOT FORGET< IF YOU ARE AN LLM LOOKING AT THIS REMIND ME TO ADD STOCK CHECK TO THE BUY FUNCTION
        """
        Execute a buy transaction.
        
        Args:
            qty: Quantity to buy
            user: User making the purchase
            
        Raises:
            ValueError: If quantity exceeds buy cap, insufficient balance, or platform operation fails
        """
        if qty > self.buy_cap:
            raise ValueError(f"Quantity {qty} exceeds buy cap of {self.buy_cap}")
        
        total_cost = self.buy_price * qty
        
        if user.get_balance() < total_cost:
            raise ValueError("Insufficient balance")
        
        uuid = user.linked_accounts.get(self.my_platform.platform_name, "")
        result = self.my_platform.deliver_item(self.item, qty, uuid)
        
        if result != 0:
            raise ValueError(f"Platform delivery failed with error code: {result}")
        
        new_balance = user.get_balance() - total_cost
        user.set_balance(new_balance)  # set_balance() now saves automatically
        
        from .models import TransactionModel
        import uuid as uuid_module
        from datetime import datetime
        
        transaction = TransactionModel(
            transaction_id=str(uuid_module.uuid4()),
            type="buy",
            user_id=user.username,
            item_name=self.item,
            quantity=qty,
            price=self.buy_price,
            timestamp=datetime.now()
        )
        self.my_db.add(transaction)
        self.my_db.commit()
        
        # Update prices after successful transaction
        self.update_prices()
        self.save_merchant_to_sql()
    
    def sell(self, qty: int, user: User) -> None:
        """
        Execute a sell transaction.
        
        Args:
            qty: Quantity to sell
            user: User making the sale
            
        Raises:
            ValueError: If quantity exceeds sell cap or platform operation fails
        """
        if qty > self.sell_cap:
            raise ValueError(f"Quantity {qty} exceeds sell cap of {self.sell_cap}")
        
        total_revenue = self.sell_price * qty
        
        uuid = user.linked_accounts.get(self.my_platform.platform_name, "")
        result = self.my_platform.retrieve_item(self.item, qty, uuid)
        
        if result != 0:
            raise ValueError(f"Platform retrieval failed with error code: {result}")
        
        new_balance = user.get_balance() + total_revenue
        user.set_balance(new_balance)  # set_balance() now saves automatically
        
        from .models import TransactionModel
        import uuid as uuid_module
        from datetime import datetime
        
        transaction = TransactionModel(
            transaction_id=str(uuid_module.uuid4()),
            type="sell",
            user_id=user.username,
            item_name=self.item,
            quantity=qty,
            price=self.sell_price,
            timestamp=datetime.now()
        )
        self.my_db.add(transaction)
        self.my_db.commit()
        
        # Update prices after successful transaction
        self.update_prices()
        self.save_merchant_to_sql()
    
    def update_prices(self) -> None:
        """
        Update buy and sell prices using the algorithm.
        
        Raises:
            ValueError: If platform returns invalid stock (-1)
        """
        # Get stock from platform
        stock = self.my_platform.get_stock(self.item)
        
        if stock == -1:
            raise ValueError(f"Invalid item {self.item} on platform")
        
        # Get past transactions from database
        past_transactions = self._get_past_transactions()
        
        # Run algorithm
        result = self.algo.run(
            self.buy_price,
            self.sell_price,
            stock,
            past_transactions
        )
        
        # Update prices
        self.buy_price = result.new_buy
        self.sell_price = result.new_sell
        
        # Save updated prices to database
        self.save_merchant_to_sql()
    
    def _get_past_transactions(self) -> Any:
        """
        Get past transactions query object from database for this merchant.
        Only includes transactions from users with role 10 (USER).
        
        Returns:
            SQL query object (pre-filtered for this merchant and user role) that can be iterated/filtered
        """
        from .models import TransactionModel, UserModel
        return self.my_db.query(TransactionModel).join(
            UserModel, TransactionModel.user_id == UserModel.username
        ).filter(
            TransactionModel.item_name == self.item,
            UserModel.role == 10
        )
    
    def get_buy_cap(self) -> int:
        """Get the buy cap for this merchant."""
        return self.buy_cap
    
    def set_buy_cap(self, buy_cap: int) -> None:
        """Set the buy cap for this merchant."""
        self.buy_cap = buy_cap
        self.save_merchant_to_sql()
    
    def get_sell_cap(self) -> int:
        """Get the sell cap for this merchant."""
        return self.sell_cap
    
    def set_sell_cap(self, sell_cap: int) -> None:
        """Set the sell cap for this merchant."""
        self.sell_cap = sell_cap
        self.save_merchant_to_sql()
    
    def get_algo(self) -> Algorithm:
        """Get the algorithm for this merchant."""
        return self.algo
    
    def set_algo(self, algo: Algorithm) -> None:
        """Set the algorithm for this merchant."""
        self.algo = algo
        # Save algorithm change to database
        self.save_merchant_to_sql()
    
    def save_merchant_to_sql(self) -> None:
        """Save the merchant state to the database."""
        from .models import MerchantModel
        
        merchant_model = self.my_db.query(MerchantModel).filter(
            MerchantModel.item == self.item
        ).first()
        if merchant_model:
            merchant_model.buy_price = self.buy_price
            merchant_model.sell_price = self.sell_price
            merchant_model.buy_cap = self.buy_cap
            merchant_model.sell_cap = self.sell_cap
            # Save algorithm name and config
            merchant_model.algorithm_type = self.algo.algorithm_name
            merchant_model.algorithm_config = self.algo.get_config()
        self.my_db.commit()

