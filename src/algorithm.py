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
    
    @property
    @abstractmethod
    def algorithm_name(self) -> str:
        """
        Get the unique name/identifier for this algorithm.
        This should be a stable identifier used for loading from the database.
        
        Returns:
            Unique algorithm name (e.g., "simple_mm", "volatility_adjusted", etc.)
        """
        pass
    
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
    
    def get_config(self) -> dict:
        """
        Get the configuration dictionary for this algorithm.
        Override this method if your algorithm has configurable parameters.
        
        Returns:
            Dictionary of algorithm configuration parameters
        """
        return {}
    
    def set_config(self, config: dict) -> None:
        """
        Set the configuration for this algorithm from a dictionary.
        Override this method if your algorithm has configurable parameters.
        
        Args:
            config: Dictionary of algorithm configuration parameters
        """
        pass

