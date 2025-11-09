"""
Stub algorithm that maintains current prices.
Used as a default fallback algorithm.
"""
from typing import Any
from ..algorithm import Algorithm, Result


class StubAlgorithm(Algorithm):
    """Stub algorithm that maintains current prices."""
    
    @property
    def algorithm_name(self) -> str:
        return "stub"
    
    def run(self, buy_price: float, sell_price: float, stock: int, past_transactions: Any) -> Result:
        """Return current prices unchanged."""
        return Result(new_buy=buy_price, new_sell=sell_price)

