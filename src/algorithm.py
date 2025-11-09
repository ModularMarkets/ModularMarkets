"""
Algorithm interface and Result class for price calculation.
"""
from abc import ABC, abstractmethod
from typing import Any
from dataclasses import dataclass


@dataclass
class Result:
    """Result from algorithm execution containing new buy and sell prices."""
    new_buy: float
    new_sell: float


class Algorithm(ABC):
    """Abstract base class for market making algorithms."""
    
    @abstractmethod
    def run(
        self,
        buy_price: float,
        sell_price: float,
        stock: int,
        past_transactions: Any
    ) -> Result:
        """
        Run the algorithm to calculate new buy and sell prices.
        
        Args:
            buy_price: Current buy price
            sell_price: Current sell price
            stock: Current stock level
            past_transactions: SQL query object for past transactions (can be iterated/filtered)
            
        Returns:
            Result object with new_buy and new_sell prices
        """
        pass

