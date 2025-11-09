"""
Logistics system interfaces for storage networks, warehouses, and inventory management.

This is a generalized logistics implementation designed to work across diverse use cases:
- Physical warehouses storing real-world goods
- Digital assets like carbon credits or cryptocurrency
- In-game logistics using player accounts as storage (e.g., Minecraft items)
- Any other platform where items need to be stored, transferred, and managed

The system provides abstract interfaces that can be implemented for any platform,
allowing for flexible item storage and retrieval across different contexts.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any


class Item:
    """
    Represents an item in the logistics system.
    
    This is a generalized item representation that can be used across different
    platforms and contexts. The item_info field contains platform-specific
    metadata needed to identify and handle the item within its context.
    
    Examples:
    - For physical warehouses: item_info might contain serial numbers, batch IDs, or location data
    - For carbon credits: item_info might contain certification details, issuance dates, or registry info
    - For in-game items: item_info might contain game-specific metadata (e.g., NBT data for Minecraft)
    - For digital assets: item_info might contain blockchain addresses, token IDs, or smart contract data
    
    The structure and content of item_info is determined by the platform implementation.
    """
    
    item_name: str
    item_weight: int
    item_info: Dict[str, Any]


class Inv(ABC):
    """Abstract base class for inventory management."""
    
    capacity: int
    items: Dict[str, int]  # item_name -> amount
    
    @abstractmethod
    def amount_of_item_that_can_be_added(self, item_name: str) -> int:
        """
        Returns how much of an item can be added before capacity is full.
        
        Args:
            item_name: Name of the item
            
        Returns:
            Amount that can be added
        """
        pass
    
    @abstractmethod
    def add_item(self, item_name: str, amount: int) -> int:
        """
        Add an item to the inventory.
        
        Args:
            item_name: Name of the item to add
            amount: Amount to add
            
        Returns:
            0 if success, non-zero error code if failure
        """
        pass
    
    @abstractmethod
    def remove_item(self, item_name: str, amount: int) -> int:
        """
        Remove an item from the inventory.
        
        Args:
            item_name: Name of the item to remove
            amount: Amount to remove
            
        Returns:
            0 if success, non-zero error code if failure
        """
        pass
    
    @abstractmethod
    def get_quantity(self, item_name: str) -> int:
        """
        Get the quantity of an item in the inventory.
        
        Args:
            item_name: Name of the item
            
        Returns:
            Quantity of the item
        """
        pass


class Warehouse(ABC):
    """Abstract base class for warehouse management."""
    
    inventory: Inv
    stored_item_types: List[str]  # item names stored in warehouse
    
    @abstractmethod
    def deliver_item(self, item_name: str, amount: int, uuid: str) -> int:
        """
        Deliver an item to a user.
        
        Args:
            item_name: Name of the item to deliver
            amount: Amount to deliver
            uuid: User's UUID
            
        Returns:
            0 if success, non-zero error code if failure
        """
        pass
    
    @abstractmethod
    def transfer_item(self, item_name: str, amount: int, warehouse: 'Warehouse') -> int:
        """
        Transfer an item to another warehouse. Updates SQL DB if success.
        
        Args:
            item_name: Name of the item to transfer
            amount: Amount to transfer
            warehouse: Target warehouse
            
        Returns:
            0 if success, non-zero error code if failure
        """
        pass
    
    @abstractmethod
    def retrieve_item(self, item_name: str, amount: int, uuid: str) -> int:
        """
        Retrieve an item from a user. Updates stock in SQL DB if success.
        
        Args:
            item_name: Name of the item to retrieve
            amount: Amount to retrieve
            uuid: User's UUID
            
        Returns:
            0 if success, non-zero error code if failure
        """
        pass
    
    @abstractmethod
    def get_stock(self, item_name: str, cached: bool = True) -> int:
        """
        Get the current stock level of an item.
        
        Args:
            item_name: Name of the item
            cached: Whether to use cached data
            
        Returns:
            Current stock level, or -1 if invalid item
        """
        pass
    
    @abstractmethod
    def _update_inv(self) -> int:
        """
        Update inventory. Private method for internal use.
        
        Returns:
            0 if inventory was accurate,
            -1 if inventory was inaccurate,
            other values for failure
        """
        pass


class StorageNetwork(ABC):
    """Abstract base class for storage network management."""
    
    warehouses: List[Warehouse]
    
    @abstractmethod
    def get_stock(self, item_name: str, cached: bool = True) -> int:
        """
        Get the total stock level of an item across all warehouses.
        
        Args:
            item_name: Name of the item
            cached: Whether to use cached data
            
        Returns:
            Total stock level across all warehouses, or -1 if invalid item
        """
        pass
    
    @abstractmethod
    def get_warehouse_for_retrieve(self, item_name: str, amount: int) -> Warehouse:
        """
        Get the warehouse that should be used for retrieving an item.
        
        Args:
            item_name: Name of the item
            amount: Amount to retrieve
            
        Returns:
            Warehouse to use for retrieval
        """
        pass
    
    @abstractmethod
    def get_warehouse_for_store(self, item_name: str, amount: int) -> Warehouse:
        """
        Get the warehouse that should be used for storing an item.
        
        Args:
            item_name: Name of the item
            amount: Amount to store
            
        Returns:
            Warehouse to use for storage
        """
        pass
    
    @abstractmethod
    def _prep_warehouse_for_retrieve(self, item_name: str, amount: int) -> int:
        """
        Prepare a warehouse for retrieval by moving stock from other warehouses
        if needed. If a retrieve is beyond what is in a single warehouse, move
        stock from other warehouses so a single warehouse may fulfill the order.
        
        Args:
            item_name: Name of the item
            amount: Amount to retrieve
            
        Returns:
            0 for success. Return 1 if it is impossible for any warehouse in
            the network to hold enough for the order.
        """
        pass

