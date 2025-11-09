"""
Simple inventory-based market making algorithm.
Based on established MTGO bot strategies and simple market making principles.
"""
from typing import Any
from ..algorithm import Algorithm, Result


class InventoryMarketMaker(Algorithm):
    """
    Simple, robust market making algorithm.
    
    Core principles:
    1. Use current mid-price as reference (or recent transaction average)
    2. Adjust mid-price based on inventory: low stock = higher prices, high stock = lower prices
    3. Maintain minimum spread for profitability
    4. Widen spread when inventory deviates from target (makes it harder to move prices)
    
    This ensures:
    - When users buy (stock decreases): prices rise
    - When users sell (stock increases): prices fall
    - Bot always maintains profitable spread
    - Spread widens when inventory is far from target
    """
    
    @property
    def algorithm_name(self) -> str:
        return "inventory_mm"
    
    def __init__(self):
        # Target inventory level
        self.target_inventory = 10000
        
        # Minimum spread percentage (profit margin)
        self.min_spread_pct = 0.10  # 10% minimum spread
        
        # Maximum spread percentage (when inventory is far from target)
        self.max_spread_pct = 0.45  # 25% maximum spread
        
        # How aggressively to adjust mid-price based on inventory
        # Higher = prices move more when inventory deviates
        self.inventory_sensitivity = 0.30  # 20% price change per 100% inventory deviation
        
        # Number of recent transactions to use for reference price
        # Use fewer transactions for more responsive pricing
        self.lookback_window = 50
    
    def get_config(self) -> dict:
        """Get algorithm configuration."""
        return {
            "target_inventory": self.target_inventory,
            "min_spread_pct": self.min_spread_pct,
            "max_spread_pct": self.max_spread_pct,
            "inventory_sensitivity": self.inventory_sensitivity,
            "lookback_window": self.lookback_window
        }
    
    def set_config(self, config: dict) -> None:
        """Set algorithm configuration."""
        self.target_inventory = config.get("target_inventory", 100)
        self.min_spread_pct = config.get("min_spread_pct", 0.10)
        self.max_spread_pct = config.get("max_spread_pct", 0.25)
        self.inventory_sensitivity = config.get("inventory_sensitivity", 0.20)
        self.lookback_window = config.get("lookback_window", 50)
    
    def run(self, buy_price: float, sell_price: float, stock: int, 
            past_transactions: Any) -> Result:
        """
        Calculate new prices using simple, predictable logic.
        
        Args:
            buy_price: Current buy price (what users pay when buying)
            sell_price: Current sell price (what we pay when users sell)
            stock: Current inventory level
            past_transactions: SQLAlchemy query of past transactions
        
        Returns:
            Result with new buy and sell prices
        """
        from ..models import TransactionModel
        
        # STEP 1: Calculate reference price (fair market value)
        # Use simple average of recent transactions, weighted by quantity
        current_mid = (buy_price + sell_price) / 2
        reference_price = current_mid  # Default to current mid-price
        
        ordered_txns = past_transactions.order_by(TransactionModel.timestamp.desc()).all()
        if ordered_txns:
            recent_txns = ordered_txns[:self.lookback_window]
            if recent_txns:
                # Simple quantity-weighted average
                total_quantity = sum(txn.quantity for txn in recent_txns)
                if total_quantity > 0:
                    weighted_sum = sum(txn.price * txn.quantity for txn in recent_txns)
                    reference_price = weighted_sum / total_quantity
                else:
                    reference_price = recent_txns[0].price
                
                # Blend with current mid-price for stability (80% historical, 20% current)
                reference_price = 0.8 * reference_price + 0.2 * current_mid
        
        # STEP 2: Calculate inventory deviation
        inventory_deviation = stock - self.target_inventory
        inventory_ratio = inventory_deviation / max(self.target_inventory, 1)
        
        # STEP 3: Adjust mid-price based on inventory
        # Low stock (negative ratio) → raise prices
        # High stock (positive ratio) → lower prices
        price_adjustment = -inventory_ratio * self.inventory_sensitivity * reference_price
        new_mid = reference_price + price_adjustment
        
        # STEP 4: Calculate spread based on inventory deviation
        # When inventory is far from target, widen spread (makes it harder to move prices)
        # Spread ranges from min_spread_pct to max_spread_pct
        inventory_abs_ratio = abs(inventory_ratio)
        # Clamp inventory_abs_ratio to [0, 1] for spread calculation
        inventory_abs_ratio = min(inventory_abs_ratio, 1.0)
        
        # Linear interpolation: min_spread when at target, max_spread when far from target
        spread_pct = self.min_spread_pct + (self.max_spread_pct - self.min_spread_pct) * inventory_abs_ratio
        spread_amount = new_mid * spread_pct
        
        # STEP 5: Calculate buy and sell prices
        # Buy price = mid + spread/2 (what users pay when buying)
        # Sell price = mid - spread/2 (what we pay when users sell)
        # This ensures buy_price > sell_price always
        new_buy = new_mid + (spread_amount / 2)
        new_sell = new_mid - (spread_amount / 2)
        
        # STEP 6: Safety checks
        # Ensure minimum spread is maintained
        min_spread_amount = reference_price * self.min_spread_pct
        actual_spread = new_buy - new_sell
        if actual_spread < min_spread_amount:
            # Recalculate with minimum spread
            new_buy = new_mid + (min_spread_amount / 2)
            new_sell = new_mid - (min_spread_amount / 2)
        
        # Ensure prices are positive and buy_price > sell_price
        new_sell = max(new_sell, 0.01)
        new_buy = max(new_buy, new_sell + 0.01)
        
        return Result(new_buy=new_buy, new_sell=new_sell)
