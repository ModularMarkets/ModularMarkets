"""
Carbon Credit platform implementation.
A dummy platform that tracks internal supply of carbon credits.
"""
import json
from pathlib import Path
from typing import List
from ..platform import Platform


class CarbonCredit(Platform):
    """
    Carbon Credit platform - tracks internal supply of carbon credits.
    
    When users buy: supply decreases (we deliver credits to them)
    When users sell: supply increases (we retrieve credits from them)
    """
    
    platform_name: str = "carboncredit"
    
    # The only item available on this platform
    ITEM_NAME = "carbon credit"
    
    # Default supply if no saved state exists
    DEFAULT_SUPPLY = 100
    
    def __init__(self, *args, **kwargs):
        """
        Initialize Carbon Credit platform.
        Sets up internal supply tracking with persistence.
        
        Args:
            *args: Variable length argument list
            **kwargs: Arbitrary keyword arguments
        """
        # Path to supply state file
        self._state_file = Path(__file__).parent / "supply.json"
        
        # Load supply from file, or use default
        self._supply: int = self._load_supply()
    
    def _load_supply(self) -> int:
        """
        Load supply from persistent storage.
        
        Returns:
            Supply level (defaults to DEFAULT_SUPPLY if file doesn't exist)
        """
        if self._state_file.exists():
            try:
                with open(self._state_file, 'r') as f:
                    data = json.load(f)
                    return data.get('supply', self.DEFAULT_SUPPLY)
            except Exception as e:
                print(f"Warning: Could not load supply from {self._state_file}: {e}")
                return self.DEFAULT_SUPPLY
        return self.DEFAULT_SUPPLY
    
    def _save_supply(self) -> None:
        """
        Save current supply to persistent storage.
        """
        try:
            with open(self._state_file, 'w') as f:
                json.dump({'supply': self._supply}, f)
        except Exception as e:
            print(f"Warning: Could not save supply to {self._state_file}: {e}")
    
    def get_item_list(self) -> List[str]:
        """
        Get a list of all available items on this platform.
        
        Returns:
            List containing "carbon credit"
        """
        return [self.ITEM_NAME]
    
    def deliver_item(self, item_name: str, amount: int, uuid: str) -> int:
        """
        Deliver carbon credits to a user (when they buy from us).
        This decreases our internal supply.
        
        Args:
            item_name: Name of the item (should be "carbon credit")
            amount: Amount of credits to deliver
            uuid: User's UUID (not used in dummy implementation)
            
        Returns:
            0 if success, non-zero error code if failure
        """
        if item_name != self.ITEM_NAME:
            return -1  # Invalid item
        
        if amount <= 0:
            return -2  # Invalid amount
        
        # Check if we have enough supply
        if self._supply < amount:
            return -3  # Insufficient supply
        
        # Decrease supply (we're delivering to the user)
        self._supply -= amount
        self._save_supply()  # Persist the change
        
        return 0  # Success
    
    def retrieve_item(self, item_name: str, amount: int, uuid: str) -> int:
        """
        Retrieve carbon credits from a user (when they sell to us).
        This increases our internal supply.
        
        Args:
            item_name: Name of the item (should be "carbon credit")
            amount: Amount of credits to retrieve
            uuid: User's UUID (not used in dummy implementation)
            
        Returns:
            0 if success, non-zero error code if failure
        """
        if item_name != self.ITEM_NAME:
            return -1  # Invalid item
        
        if amount <= 0:
            return -2  # Invalid amount
        
        # Increase supply (we're retrieving from the user)
        self._supply += amount
        self._save_supply()  # Persist the change
        
        return 0  # Success
    
    def get_stock(self, item_name: str) -> int:
        """
        Get the current stock level of carbon credits.
        
        Args:
            item_name: Name of the item (should be "carbon credit")
            
        Returns:
            Current stock level, or -1 if invalid item
        """
        if item_name != self.ITEM_NAME:
            return -1  # Invalid item
        
        return self._supply
    
    def get_supply(self) -> int:
        """
        Get the current internal supply of carbon credits.
        
        Returns:
            Current supply level
        """
        return self._supply
    
    def set_supply(self, supply: int) -> None:
        """
        Set the internal supply of carbon credits.
        
        Args:
            supply: New supply level (must be >= 0)
        """
        if supply < 0:
            raise ValueError("Supply cannot be negative")
        self._supply = supply
        self._save_supply()  # Persist the change

