"""
Platform interface for external platforms (games, services, etc.).
"""
from abc import ABC, abstractmethod
from typing import List


class Platform(ABC):
    """Abstract base class for platforms that provide items/services."""
    
    platform_name: str
    
    @abstractmethod
    def get_item_list(self) -> List[str]:
        """Get a list of all available items on this platform."""
        pass
    
    @abstractmethod
    def deliver_item(self, item_name: str, amount: int, uuid: str) -> int:
        """
        Deliver an amount of items to a user on the platform.
        
        Args:
            item_name: Name of the item to deliver
            amount: Amount of items to deliver
            uuid: User's UUID on the platform
            
        Returns:
            0 if success, non-zero error code if failure
        """
        pass
    
    @abstractmethod
    def retrieve_item(self, item_name: str, amount: int, uuid: str) -> int:
        """
        Retrieve an amount of items from a user on the platform.
        
        Args:
            item_name: Name of the item to retrieve
            amount: Amount of items to retrieve
            uuid: User's UUID on the platform
            
        Returns:
            0 if success, non-zero error code if failure
        """
        pass
    
    @abstractmethod
    def get_stock(self, item_name: str) -> int:
        """
        Get the current stock level of an item.
        
        Args:
            item_name: Name of the item
            
        Returns:
            Current stock level, or -1 if invalid item
        """
        pass

