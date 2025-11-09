"""
Minecraft platform implementation.

IMPORTANT DESIGN PRINCIPLE:
Platform-specific code should NEVER modify files in the general source directory (src/).
All platform-specific models, database connections, utilities, and implementations
must be contained within the platform's own directory structure (src/platforms/minecraft/).

This ensures:
- Clean separation of concerns
- No conflicts between different platform implementations
- Easier maintenance and testing
- Platform code can be developed independently
"""

import os
import math
import yaml
from pathlib import Path
from typing import List, Optional, Dict, Any, Callable

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ..platform import Platform
from ..utils.logistics import StorageNetwork, Warehouse, Item, Inv

# Import Minecraft-specific models from local models file
# IMPORTANT: Platform-specific code should NEVER modify files in the general source
# directory (src/). All platform-specific models must be in the platform's directory.
from .models import MinecraftBase, MinecraftBotModel, MinecraftBotInventoryModel, MinecraftNetworkModel


class MinecraftInventory(Inv):
    """Concrete inventory implementation for Minecraft bots."""
    
    def __init__(self, capacity: int = 36 * 64, get_item_weight: Optional[Callable[[str], int]] = None):
        """
        Initialize Minecraft inventory.
        
        Args:
            capacity: Maximum number of items the inventory can hold (default: 36*64 = 2304)
            get_item_weight: Optional function to get item weight by item_name (default: returns 1)
        """
        self.capacity: int = capacity
        self.items: Dict[str, int] = {}
        self._get_item_weight: Callable[[str], int] = get_item_weight if get_item_weight else lambda _: 1
    
    def amount_of_item_that_can_be_added(self, item_name: str, item_weight: Optional[int] = None) -> int:
        """
        Returns how much of an item can be added before capacity is full.
        
        Calculates remaining space by:
        1. For each item in inventory: multiply amount by item weight, round up to nearest multiple of 64
        2. Sum all these values
        3. Subtract this sum from capacity
        4. Return the remainder divided by the weight of the item being added, rounded down
        
        Args:
            item_name: Name of the item
            item_weight: Weight of the item (if None, uses get_item_weight function)
            
        Returns:
            Amount that can be added
        """
        # Get item weight
        if item_weight is None:
            item_weight = self._get_item_weight(item_name)
        
        if item_weight <= 0:
            return 0
        
        # Calculate used space: for each item, multiply amount by weight, round up to nearest multiple of 64
        used_space = 0
        for existing_item_name, amount in self.items.items():
            existing_weight = self._get_item_weight(existing_item_name)
            weighted_amount = amount * existing_weight
            # Round up to nearest multiple of 64
            rounded_amount = math.ceil(weighted_amount / 64) * 64
            used_space += rounded_amount
        
        # Calculate remaining space
        remaining_space = self.capacity - used_space
        
        # Return remainder divided by item weight, rounded down
        if remaining_space <= 0:
            return 0
        
        return math.floor(remaining_space / item_weight)
    
    def add_item(self, item_name: str, amount: int) -> int:
        """
        Add an item to the inventory.
        
        Args:
            item_name: Name of the item to add
            amount: Amount to add
            
        Returns:
            0 if success, non-zero error code if failure
        """
        current_total = sum(self.items.values())
        if current_total + amount > self.capacity:
            return 1  # Capacity exceeded
        
        self.items[item_name] = self.items.get(item_name, 0) + amount
        return 0
    
    def remove_item(self, item_name: str, amount: int) -> int:
        """
        Remove an item from the inventory.
        
        Args:
            item_name: Name of the item to remove
            amount: Amount to remove
            
        Returns:
            0 if success, non-zero error code if failure
        """
        current_amount = self.items.get(item_name, 0)
        if current_amount < amount:
            return 1  # Not enough items
        
        self.items[item_name] = current_amount - amount
        if self.items[item_name] == 0:
            del self.items[item_name]
        
        return 0
    
    def get_quantity(self, item_name: str) -> int:
        """
        Get the quantity of an item in the inventory.
        
        Args:
            item_name: Name of the item
            
        Returns:
            Quantity of the item
        """
        return self.items.get(item_name, 0)


class MinecraftBot(Warehouse):
    """Minecraft bot that acts as a warehouse for item storage and delivery."""
    
    def __init__(self, username: str, password: str, auth: str, trading_mode: str, bot_id: Optional[str] = None):
        """
        Initialize a Minecraft bot.
        
        Args:
            username: Bot username
            password: Bot password
            auth: Authentication type ('online' or 'offline')
            trading_mode: Trading mode ('drop', 'chat', or 'plugin')
            bot_id: Unique bot identifier (defaults to username if not provided)
        """
        self.trading_mode: str = trading_mode
        self.username: str = username
        self.password: str = password
        self.auth: str = auth
        self.bot_id: str = bot_id if bot_id else username
        # Required Warehouse attributes
        # Initialize inventory with capacity of 36 slots * 64 items per slot = 2304
        # get_item_weight will be set by platform if available via set_item_weight_getter
        self.inventory: Inv = MinecraftInventory(capacity=36 * 64)
        self.stored_item_types: List[str] = []
        # Optional database session for SQL persistence (set by network/platform)
        self._db_session: Optional[Any] = None
        # Server connection info (set by platform when needed)
        self._server_address: Optional[str] = None
        self._server_port: Optional[int] = None
        self._minecraft_version: Optional[str] = None
        # Valid items list from platform (set by platform)
        self._valid_items: Optional[set] = None
    
    def _is_valid_item(self, item_name: str) -> bool:
        """
        Check if an item is in the valid items list.
        
        Args:
            item_name: Name of the item to check (normalized, without minecraft: prefix)
            
        Returns:
            True if item is valid, False otherwise
        """
        if self._valid_items is None:
            # If no valid items list is set, allow all items (backward compatibility)
            return True
        normalized_name = item_name.replace('minecraft:', '')
        return normalized_name in self._valid_items
    
    def _clean_stored_item_types(self) -> None:
        """
        Remove invalid items from stored_item_types.
        Only keeps items that are in the valid items list.
        """
        if self._valid_items is not None:
            self.stored_item_types = [item for item in self.stored_item_types if self._is_valid_item(item)]
    
    def _drop_excess_items(self, client: Any, item_name: str, target_amount: int) -> int:
        """
        Drop excess items of a specific type until we have exactly target_amount.
        
        Args:
            client: MineflayerClient instance
            item_name: Name of the item to drop excess of
            target_amount: Target amount to keep
            
        Returns:
            0 if success, non-zero error code if failure
        """
        try:
            # Use the drop_excess_items API
            result = client.drop_excess_items(self.bot_id, item_name, target_amount)
            
            if not result.get('success', False):
                print(f"Warning: drop_excess_items API returned failure for bot {self.bot_id}: {result}")
                return 1
            
            dropped_count = result.get('dropped_count', 0)
            if dropped_count > 0:
                print(f"Bot {self.bot_id} dropped {dropped_count} excess {item_name}")
                # Give a small delay for items to be dropped
                import time
                time.sleep(0.5)
            
            return 0
            
        except Exception as e:
            print(f"Error dropping excess items for bot {self.bot_id}: {e}")
            return 1
    
    def _clean_inv(self, additional_allowed_items: Optional[List[str]] = None) -> int:
        """
        Clean inventory by dropping items that the bot is not set to store.
        This function is generalized for use with both 'drop' and 'chat' trading modes.
        
        Args:
            additional_allowed_items: Optional list of item names to also allow (e.g., item being retrieved)
        
        Returns:
            0 if success, non-zero error code if failure
        """
        if self.trading_mode not in ('drop', 'chat'):
            return 0  # Not applicable for other modes
        
        from .node_service import MineflayerClient
        import time
        
        try:
            client = MineflayerClient()
            
            # Check if bot is connected
            status = client.get_status(self.bot_id)
            if not status.get('success') or status.get('status') != 'connected':
                return 1  # Bot not connected
            
            # Get allowed items (items the bot is set to store that are also valid)
            # Only include items that are both in stored_item_types AND in the valid items list
            allowed_items = [item for item in self.stored_item_types if self._is_valid_item(item)]
            
            # Add any additional allowed items (normalize minecraft: prefix)
            # Only add if they are valid items
            if additional_allowed_items:
                for item in additional_allowed_items:
                    normalized = item.replace('minecraft:', '')
                    if self._is_valid_item(normalized) and normalized not in allowed_items:
                        allowed_items.append(normalized)
            
            # Drop items not in allowed list
            drop_result = client.drop_items(self.bot_id, allowed_items)
            
            if not drop_result.get('success', False):
                print(f"Warning: drop_items API returned failure for bot {self.bot_id}: {drop_result}")
                return 1
            
            dropped_count = drop_result.get('dropped_count', 0)
            if dropped_count > 0:
                print(f"Bot {self.bot_id} dropped {dropped_count} unwanted item(s)")
                # Give a small delay for items to be dropped
                time.sleep(0.5)
            
            return 0
            
        except Exception as e:
            print(f"Error cleaning inventory for bot {self.bot_id}: {e}")
            return 1
    
    def deliver_item(self, item_name: str, amount: int, uuid: str) -> int:
        """
        Deliver an item to a user.
        
        Uses pathfinding to navigate to the player (3 blocks away), then drops items towards them.
        The uuid parameter accepts either a username or an actual UUID.
        
        Args:
            item_name: Name of the item to deliver
            amount: Amount to deliver
            uuid: User's UUID or username
            
        Returns:
            0 if success, non-zero error code if failure
        """
        from .node_service import MineflayerClient
        import requests
        import time
        
        client = None
        try:
            client = MineflayerClient()
            
            # Check if bot is connected
            try:
                status = client.get_status(self.bot_id)
                is_connected = status.get('success') and status.get('status') == 'connected'
            except requests.exceptions.HTTPError as e:
                # 404 means bot doesn't exist, not connected
                is_connected = False
            except Exception as e:
                print(f"Error checking bot status for {self.bot_id}: {e}")
                return 1
            
            if not is_connected:
                # Bot not connected, need server info - this should be set by platform
                if not self._server_address:
                    print(f"Error: Cannot login bot {self.bot_id} without server info")
                    return 1
                
                # Try to login
                try:
                    login_result = client.login(
                        bot_id=self.bot_id,
                        username=self.username,
                        password=self.password,
                        auth=self.auth,
                        server_host=self._server_address,
                        server_port=self._server_port or 25565,
                        version=self._minecraft_version
                    )
                    
                    if not login_result.get('success'):
                        print(f"Error: Login failed for bot {self.bot_id}: {login_result}")
                        return 1
                    
                    # Wait a bit for connection to establish
                    time.sleep(2)
                    
                    # Verify connection
                    status = client.get_status(self.bot_id)
                    if not status.get('success') or status.get('status') != 'connected':
                        print(f"Error: Bot {self.bot_id} not connected after login attempt")
                        return 1
                        
                except requests.exceptions.RequestException as e:
                    print(f"Error: Login request failed for bot {self.bot_id}: {e}")
                    return 1
                except Exception as e:
                    print(f"Error: Unexpected error during login for bot {self.bot_id}: {e}")
                    return 1
            
            # Normalize item name (remove minecraft: prefix if present)
            normalized_item_name = item_name.replace('minecraft:', '')
            
            # Call deliver_item API endpoint
            try:
                result = client.deliver_item(
                    bot_id=self.bot_id,
                    item_name=normalized_item_name,
                    amount=amount,
                    target_uuid=uuid,
                    timeout_seconds=60
                )
                
                if not result.get('success', False):
                    error_msg = result.get('error', 'Unknown error')
                    print(f"Error delivering item: {error_msg}")
                    return 1
                
                # Get actual amount dropped
                amount_dropped = result.get('amount_dropped', 0)
                
                if amount_dropped < amount:
                    print(f"Warning: Only dropped {amount_dropped} out of {amount} {item_name}")
                
                # Update inventory (remove item)
                if self.inventory and hasattr(self.inventory, 'remove_item'):
                    self.inventory.remove_item(normalized_item_name, amount_dropped)
                
                # Save to SQL if db session is available
                if self._db_session:
                    self.save_to_sql(self._db_session)
                
                return 0
                
            except requests.exceptions.RequestException as e:
                print(f"Error: Deliver item request failed for bot {self.bot_id}: {e}")
                return 1
            except ValueError as e:
                print(f"Error delivering item: {e}")
                return 1
            except Exception as e:
                print(f"Error: Unexpected error during delivery for bot {self.bot_id}: {e}")
                return 1
                
        except Exception as e:
            print(f"Error: Failed to deliver item {item_name} to {uuid}: {e}")
            return 1
    
    def transfer_item(self, item_name: str, amount: int, warehouse: Warehouse) -> int:
        """
        Transfer an item to another warehouse. Updates SQL DB if success.
        
        Args:
            item_name: Name of the item to transfer
            amount: Amount to transfer
            warehouse: Target warehouse
            
        Returns:
            0 if success, non-zero error code if failure
        """
        # TODO: Implement actual transfer logic
        # After successful transfer, update inventories and save to SQL:
        #   result = <perform transfer>
        #   if result == 0:
        #       # Update source inventory (remove item)
        #       if self.inventory and hasattr(self.inventory, 'remove_item'):
        #           self.inventory.remove_item(item_name, amount)
        #       # Update destination inventory (add item) if it's a MinecraftBot
        #       if isinstance(warehouse, MinecraftBot):
        #           if warehouse.inventory and hasattr(warehouse.inventory, 'add_item'):
        #               warehouse.inventory.add_item(item_name, amount)
        #       # Save both bots to SQL if db session is available
        #       if self._db_session:
        #           self.save_to_sql(self._db_session)
        #           if isinstance(warehouse, MinecraftBot) and warehouse._db_session:
        #               warehouse.save_to_sql(warehouse._db_session)
        #   return result
        pass
    
    def retrieve_item(self, item_name: str, amount: int, uuid: str) -> int:
        """
        Retrieve an item from a user. Updates stock in SQL DB if success.
        
        For 'drop' mode:
        1. Login (if not already connected)
        2. Immediately purge inventory of items not supposed to be carried
        3. Validate inventory
        4. Get current inventory and calculate target amount (current + deposit amount)
        5. Clean inventory (drop items not set to store, allow item being retrieved)
        6. Say in chat "seeking item_name, amount."
        7. Wait for item_name and amount to appear in inventory (with progress updates)
        8. Confirm inventory contents and drop any excess
        9. Clean inventory again
        10. Before leaving: Refund (drop) any items over the deposit amount
        11. Logout
        
        Args:
            item_name: Name of the item to retrieve
            amount: Amount to retrieve
            uuid: User's UUID
            
        Returns:
            0 if success, non-zero error code if failure
        """
        # Only implement for 'drop' mode for now
        if self.trading_mode != 'drop':
            return 1  # Not implemented for other modes yet
        
        from .node_service import MineflayerClient
        import requests
        import time
        
        client = None
        try:
            client = MineflayerClient()
            
            # Check if bot is connected
            try:
                status = client.get_status(self.bot_id)
                is_connected = status.get('success') and status.get('status') == 'connected'
            except requests.exceptions.HTTPError as e:
                # 404 means bot doesn't exist, not connected
                is_connected = False
            except Exception as e:
                print(f"Error checking bot status for {self.bot_id}: {e}")
                return 1
            
            if not is_connected:
                # Bot not connected, need server info - this should be set by platform
                if not self._server_address:
                    print(f"Error: Cannot login bot {self.bot_id} without server info")
                    return 1
                
                # Try to login
                try:
                    login_result = client.login(
                        bot_id=self.bot_id,
                        username=self.username,
                        password=self.password,
                        auth=self.auth,
                        server_host=self._server_address,
                        server_port=self._server_port or 25565,
                        version=self._minecraft_version
                    )
                    
                    if not login_result.get('success'):
                        print(f"Error: Login failed for bot {self.bot_id}: {login_result}")
                        return 1
                    
                    # Wait a bit for connection to establish
                    time.sleep(2)
                    
                    # Verify connection
                    status = client.get_status(self.bot_id)
                    if not status.get('success') or status.get('status') != 'connected':
                        print(f"Error: Bot {self.bot_id} not connected after login attempt")
                        return 1
                    
                    # Immediately after login: Purge inventory of items not supposed to be carried
                    # This ensures the bot starts with a clean inventory before receiving deposits
                    # Clean stored_item_types to remove any invalid items
                    self._clean_stored_item_types()
                    purge_result = self._clean_inv()
                    if purge_result != 0:
                        print(f"Warning: Failed to purge inventory for bot {self.bot_id} after login")
                    else:
                        # Give a small delay for drops to process
                        time.sleep(0.5)
                        
                except requests.exceptions.RequestException as e:
                    print(f"Error: Login request failed for bot {self.bot_id}: {e}")
                    return 1
                except Exception as e:
                    print(f"Error: Unexpected error during login for bot {self.bot_id}: {e}")
                    return 1
            else:
                # Bot was already connected - still purge inventory on entry
                # Clean stored_item_types to remove any invalid items
                self._clean_stored_item_types()
                purge_result = self._clean_inv()
                if purge_result != 0:
                    print(f"Warning: Failed to purge inventory for bot {self.bot_id}")
                else:
                    time.sleep(0.5)
            
            # 1. Validate inventory - see if it is more or less than expected
            try:
                # Get expected inventory from bot's stored state
                expected_inventory = {}
                if isinstance(self.inventory, MinecraftInventory):
                    # Normalize item names (remove minecraft: prefix if present)
                    for item_name_key, quantity in self.inventory.items.items():
                        normalized_key = item_name_key.replace('minecraft:', '')
                        expected_inventory[normalized_key] = quantity
                
                validation = client.validate_inventory(self.bot_id, expected_inventory=expected_inventory if expected_inventory else None)
                if not validation.get('success'):
                    print(f"Warning: Bot {self.bot_id} inventory validation API call failed: {validation}")
                elif not validation.get('is_accurate', True):
                    differences = validation.get('differences', {})
                    print(f"Warning: Bot {self.bot_id} inventory validation showed differences: {differences}")
                    # Log whether inventory is more or less than expected
                    for item, diff in differences.items():
                        if diff > 0:
                            print(f"  - {item}: {diff} more than expected")
                        elif diff < 0:
                            print(f"  - {item}: {abs(diff)} less than expected")
            except requests.exceptions.RequestException as e:
                print(f"Error: Inventory validation request failed for bot {self.bot_id}: {e}")
                return 1
            
            # 2. Get current inventory to calculate target amount
            normalized_item_name = item_name.replace('minecraft:', '')
            current_amount = 0
            try:
                inv_result = client.get_inventory(self.bot_id)
                if inv_result.get('success'):
                    actual_inventory = inv_result.get('inventory', {})
                    current_amount = actual_inventory.get(normalized_item_name, 0)
            except requests.exceptions.RequestException as e:
                print(f"Warning: Could not get current inventory for bot {self.bot_id}: {e}")
                # Continue anyway, assume 0 current amount
            
            # Calculate target amount (current + new)
            target_amount = current_amount + amount
            
            # 3. Clean inventory (drop items not set to store)
            # Include the item we're about to receive in allowed items
            # Try cleaning multiple times to ensure it works
            max_clean_attempts = 3
            for clean_attempt in range(max_clean_attempts):
                clean_result = self._clean_inv(additional_allowed_items=[normalized_item_name])
                if clean_result != 0:
                    if clean_attempt == max_clean_attempts - 1:
                        print(f"Error: Failed to clean inventory for bot {self.bot_id} after {max_clean_attempts} attempts")
                        return clean_result
                    else:
                        print(f"Warning: Cleaning attempt {clean_attempt + 1} failed, retrying...")
                        time.sleep(0.5)
                        continue
                
                # Verify cleaning worked by checking inventory again
                try:
                    time.sleep(0.5)  # Wait for drops to process
                    inv_after_clean = client.get_inventory(self.bot_id)
                    if inv_after_clean.get('success'):
                        cleaned_inventory = inv_after_clean.get('inventory', {})
                        # Check for items that shouldn't be there
                        allowed_items = set(self.stored_item_types + [normalized_item_name])
                        unwanted_items = []
                        for inv_item_name, quantity in cleaned_inventory.items():
                            if quantity > 0 and inv_item_name not in allowed_items:
                                unwanted_items.append(f"{inv_item_name}:{quantity}")
                        if unwanted_items:
                            if clean_attempt < max_clean_attempts - 1:
                                print(f"Warning: Bot {self.bot_id} still has unwanted items after cleaning (attempt {clean_attempt + 1}): {', '.join(unwanted_items)}")
                                time.sleep(0.5)
                                continue  # Try cleaning again
                            else:
                                print(f"Warning: Bot {self.bot_id} still has unwanted items after {max_clean_attempts} cleaning attempts: {', '.join(unwanted_items)}")
                        else:
                            break  # Clean inventory, exit loop
                except Exception as e:
                    print(f"Warning: Could not verify inventory cleaning for bot {self.bot_id}: {e}")
                    break  # Can't verify, assume it worked
            
            # 4. Say in chat "seeking item_name, amount."
            try:
                chat_result = client.send_chat(self.bot_id, f"seeking {normalized_item_name}, {amount}.")
                if not chat_result.get('success'):
                    print(f"Error: Failed to send chat message for bot {self.bot_id}: {chat_result}")
                    return 1
            except requests.exceptions.RequestException as e:
                print(f"Error: Chat request failed for bot {self.bot_id}: {e}")
                return 1
            
            # 5. Wait for items with progress updates (wait for target_amount total)
            try:
                wait_result = client.wait_for_items(
                    bot_id=self.bot_id,
                    item_name=normalized_item_name,
                    target_amount=target_amount,
                    timeout_seconds=300
                )
                
                if not wait_result.get('success'):
                    print(f"Error: wait_for_items failed for bot {self.bot_id}: {wait_result}")
                    return 1
                
                received_amount = wait_result.get('received_amount', 0)
                if received_amount < target_amount:
                    print(f"Error: Bot {self.bot_id} only received {received_amount}/{target_amount} {normalized_item_name} (expected {amount} new items on top of {current_amount} existing)")
                    return 1
                    
            except requests.exceptions.RequestException as e:
                print(f"Error: wait_for_items request failed for bot {self.bot_id}: {e}")
                return 1
            
            # 6. Confirm inventory contents and sync local cache
            # Get actual inventory from game to sync local cache
            try:
                inv_result = client.get_inventory(self.bot_id)
                if not inv_result.get('success'):
                    print(f"Error: Failed to get inventory for bot {self.bot_id}: {inv_result}")
                    return 1
                
                actual_inventory = inv_result.get('inventory', {})
                
                # Verify we actually have the target amount (current + new)
                actual_amount = actual_inventory.get(normalized_item_name, 0)
                if actual_amount < target_amount:
                    print(f"Error: Bot {self.bot_id} inventory shows only {actual_amount}/{target_amount} {normalized_item_name} (expected {amount} new items on top of {current_amount} existing)")
                    return 1
                
                # Check for excess items - if we received more than target, we need to drop the excess
                excess_amount = actual_amount - target_amount
                if excess_amount > 0:
                    print(f"Bot {self.bot_id} received {excess_amount} excess {normalized_item_name}, dropping excess...")
                    # Drop excess items - we'll need to drop specific amount
                    # For now, we'll drop all and then wait for the target amount again
                    # But actually, we should drop just the excess
                    # Let's use a helper to drop specific amount
                    try:
                        # Get all items of this type and drop excess
                        # We'll need to iterate through slots and drop the excess
                        # For simplicity, drop all of this item type, then the final clean will handle it
                        # Actually, better approach: drop items until we have exactly target_amount
                        drop_excess_result = self._drop_excess_items(client, normalized_item_name, target_amount)
                        if drop_excess_result != 0:
                            print(f"Warning: Failed to drop excess items for bot {self.bot_id}")
                        else:
                            # Re-check inventory after dropping excess
                            time.sleep(0.5)
                            inv_after_drop = client.get_inventory(self.bot_id)
                            if inv_after_drop.get('success'):
                                actual_inventory = inv_after_drop.get('inventory', {})
                                actual_amount = actual_inventory.get(normalized_item_name, 0)
                                if actual_amount > target_amount:
                                    print(f"Warning: Bot {self.bot_id} still has {actual_amount - target_amount} excess {normalized_item_name} after drop attempt")
                    except Exception as e:
                        print(f"Warning: Error dropping excess items for bot {self.bot_id}: {e}")
                
                # Update local inventory cache to match game inventory
                # Only include valid items in the cache
                if isinstance(self.inventory, MinecraftInventory):
                    # Clear and rebuild from actual game inventory, filtering invalid items
                    self.inventory.items = {}
                    for inv_item_name, quantity in actual_inventory.items():
                        if quantity > 0:
                            if self._is_valid_item(inv_item_name):
                                self.inventory.items[inv_item_name] = quantity
                            else:
                                # Invalid item found - log warning
                                print(f"Warning: Bot {self.bot_id} has invalid item {inv_item_name}:{quantity} in inventory, will be purged")
                else:
                    print(f"Warning: Bot {self.bot_id} inventory is not MinecraftInventory instance")
                
            except requests.exceptions.RequestException as e:
                print(f"Error: get_inventory request failed for bot {self.bot_id}: {e}")
                return 1
            
            # Validate against expected (target amount)
            try:
                expected_inv = {normalized_item_name: target_amount}
                validation = client.validate_inventory(self.bot_id, expected_inventory=expected_inv)
                if not validation.get('success'):
                    print(f"Warning: Bot {self.bot_id} inventory confirmation API call failed: {validation}")
                elif not validation.get('is_accurate', False):
                    print(f"Warning: Bot {self.bot_id} inventory confirmation failed: {validation.get('differences', {})}")
                    # Still continue, but log the issue
            except requests.exceptions.RequestException as e:
                print(f"Warning: Inventory confirmation request failed for bot {self.bot_id}: {e}")
                # Don't fail here, we already verified the inventory above
            
            # Update stored_item_types if needed - ONLY if item is valid
            if normalized_item_name not in self.stored_item_types:
                if self._is_valid_item(normalized_item_name):
                    self.stored_item_types.append(normalized_item_name)
                else:
                    print(f"Warning: Bot {self.bot_id} received invalid item {normalized_item_name}, will be purged")
            
            # 7. Clean inventory again (drop any items that shouldn't be there)
            # Give a small delay to ensure any excess drops are processed
            time.sleep(0.5)
            clean_result = self._clean_inv()
            if clean_result != 0:
                print(f"Warning: Failed to clean inventory after retrieval for bot {self.bot_id}")
                # Don't fail here, items were already received
            else:
                # Verify cleaning worked - try multiple times if needed
                max_clean_attempts = 3
                for attempt in range(max_clean_attempts):
                    try:
                        time.sleep(0.5)  # Wait for drops to process
                        inv_after_final_clean = client.get_inventory(self.bot_id)
                        if inv_after_final_clean.get('success'):
                            final_inventory = inv_after_final_clean.get('inventory', {})
                            allowed_items = set(self.stored_item_types)
                            unwanted_items = []
                            for inv_item_name, quantity in final_inventory.items():
                                if quantity > 0 and inv_item_name not in allowed_items:
                                    unwanted_items.append(f"{inv_item_name}:{quantity}")
                            
                            # Also check for excess of the item we just received
                            final_item_amount = final_inventory.get(normalized_item_name, 0)
                            if final_item_amount > target_amount:
                                excess = final_item_amount - target_amount
                                unwanted_items.append(f"{normalized_item_name}:{excess} (excess)")
                            
                            if unwanted_items:
                                if attempt < max_clean_attempts - 1:
                                    print(f"Warning: Bot {self.bot_id} still has unwanted items after cleaning (attempt {attempt + 1}): {', '.join(unwanted_items)}")
                                    # Try cleaning again
                                    self._clean_inv()
                                    # Also drop excess of the target item if needed
                                    if final_item_amount > target_amount:
                                        self._drop_excess_items(client, normalized_item_name, target_amount)
                                else:
                                    print(f"Warning: Bot {self.bot_id} still has unwanted items after {max_clean_attempts} cleaning attempts: {', '.join(unwanted_items)}")
                            else:
                                break  # Clean inventory, exit loop
                    except Exception as e:
                        print(f"Warning: Could not verify final inventory cleaning for bot {self.bot_id}: {e}")
                        break
            
            # 8. Before leaving: Refund any items over the deposit amount
            # The deposit amount is 'amount', so target_amount = current_amount + amount
            # Any excess should be dropped (refunded) before logout
            try:
                # Get final inventory check before logout
                time.sleep(0.5)  # Wait for any previous operations to complete
                final_inv_check = client.get_inventory(self.bot_id)
                if final_inv_check.get('success'):
                    final_inv = final_inv_check.get('inventory', {})
                    final_item_amount = final_inv.get(normalized_item_name, 0)
                    
                    # Refund (drop) any excess over the target amount
                    if final_item_amount > target_amount:
                        excess_to_refund = final_item_amount - target_amount
                        refund_result = self._drop_excess_items(client, normalized_item_name, target_amount)
                        if refund_result != 0:
                            print(f"Warning: Failed to refund excess items for bot {self.bot_id}")
                        else:
                            time.sleep(0.5)  # Wait for drops to process
                    
                    # Also ensure no other unwanted items remain
                    allowed_items = set(self.stored_item_types)
                    for inv_item_name, quantity in final_inv.items():
                        if quantity > 0 and inv_item_name not in allowed_items:
                            # Drop unwanted items
                            self._clean_inv()
                            time.sleep(0.5)
                            break  # Clean once, then re-check if needed
            except Exception as e:
                print(f"Warning: Error during final inventory check before logout for bot {self.bot_id}: {e}")
                # Continue to logout anyway
            
            # 9. Logout
            try:
                logout_result = client.logout(self.bot_id)
                if not logout_result.get('success'):
                    print(f"Warning: Logout failed for bot {self.bot_id}: {logout_result}")
            except requests.exceptions.RequestException as e:
                print(f"Warning: Logout request failed for bot {self.bot_id}: {e}")
                # Don't fail here, items were already received
            
            # Save to SQL if db session is available
            if self._db_session:
                try:
                    self.save_to_sql(self._db_session)
                except Exception as e:
                    print(f"Warning: Failed to save bot {self.bot_id} to SQL: {e}")
                    # Don't fail here, items were already received
            
            return 0
            
        except requests.exceptions.RequestException as e:
            print(f"Error: API request failed for bot {self.bot_id}: {e}")
            # Try to logout on error
            if client:
                try:
                    client.logout(self.bot_id)
                except:
                    pass
            return 1
        except Exception as e:
            print(f"Error retrieving item {item_name} from bot {self.bot_id}: {e}")
            import traceback
            traceback.print_exc()
            # Try to logout on error
            if client:
                try:
                    client.logout(self.bot_id)
                except:
                    pass
            return 1
    
    def get_stock(self, item_name: str, cached: bool = True) -> int:
        """
        Get the current stock level of an item.
        
        Currently only supports 'drop' and 'chat' trading modes.
        Plugin mode requires different implementation via server plugin API.
        
        Args:
            item_name: Name of the item
            cached: Whether to use cached data
            
        Returns:
            Current stock level, or -1 if invalid item
            
        Raises:
            ValueError: If trading mode is 'plugin' or bot is not connected
            requests.RequestException: If the API request fails
        """
        # Only support drop and chat trading modes
        if self.trading_mode == 'plugin':
            raise ValueError(
                f"get_stock is not supported for 'plugin' trading mode. "
                f"Plugin mode requires server plugin API integration."
            )
        
        from .node_service import MineflayerClient
        
        # Normalize item name (remove 'minecraft:' prefix if present)
        normalized_name = item_name.replace('minecraft:', '')
        
        # If using cache, check local inventory first
        if cached:
            if hasattr(self.inventory, 'get_quantity'):
                quantity = self.inventory.get_quantity(normalized_name)
                if quantity is not None:
                    return quantity
        
        # Fetch from mineflayer service
        client = MineflayerClient()
        import requests
        import time
        
        # Track if we auto-logged in (so we can logout after fetching)
        auto_logged_in = False
        
        # Check if bot is connected
        is_connected = False
        try:
            status = client.get_status(self.bot_id)
            is_connected = status.get('success') and status.get('status') == 'connected'
        except requests.exceptions.HTTPError as e:
            # 404 means bot doesn't exist, not connected
            is_connected = False
        except Exception as e:
            # If we can't check status and cached data is available, fall back to it
            if cached or not hasattr(self.inventory, 'get_quantity'):
                raise ValueError(f"Failed to check bot status for {self.bot_id}: {e}")
            # Fall back to cached data
            print(f"Warning: Could not check bot status for {self.bot_id}, using cached data: {e}")
            quantity = self.inventory.get_quantity(normalized_name)
            return quantity if quantity is not None else 0
        
        # If not connected, try to auto-login
        if not is_connected:
            if not self._server_address:
                # No server info, fall back to cached data if available
                if hasattr(self.inventory, 'get_quantity'):
                    print(f"Warning: Bot {self.bot_id} is not connected and no server info available, using cached data")
                    quantity = self.inventory.get_quantity(normalized_name)
                    return quantity if quantity is not None else 0
                else:
                    raise ValueError(f"Bot {self.bot_id} is not connected and no server info available")
            
            # Try to login
            try:
                login_result = client.login(
                    bot_id=self.bot_id,
                    username=self.username,
                    password=self.password,
                    auth=self.auth,
                    server_host=self._server_address,
                    server_port=self._server_port or 25565,
                    version=self._minecraft_version
                )
                
                if not login_result.get('success'):
                    # Login failed, fall back to cached data if available
                    if hasattr(self.inventory, 'get_quantity'):
                        print(f"Warning: Login failed for bot {self.bot_id}, using cached data")
                        quantity = self.inventory.get_quantity(normalized_name)
                        return quantity if quantity is not None else 0
                    else:
                        raise ValueError(f"Login failed for bot {self.bot_id}: {login_result}")
                
                # Wait a bit for connection to establish
                time.sleep(2)
                
                # Verify connection
                status = client.get_status(self.bot_id)
                if not status.get('success') or status.get('status') != 'connected':
                    # Connection failed, fall back to cached data if available
                    if hasattr(self.inventory, 'get_quantity'):
                        print(f"Warning: Bot {self.bot_id} not connected after login attempt, using cached data")
                        quantity = self.inventory.get_quantity(normalized_name)
                        return quantity if quantity is not None else 0
                    else:
                        raise ValueError(f"Bot {self.bot_id} not connected after login attempt")
                
                is_connected = True
                auto_logged_in = True  # Mark that we auto-logged in
            except requests.exceptions.RequestException as e:
                # Login request failed, fall back to cached data if available
                if hasattr(self.inventory, 'get_quantity'):
                    print(f"Warning: Login request failed for bot {self.bot_id}, using cached data: {e}")
                    quantity = self.inventory.get_quantity(normalized_name)
                    return quantity if quantity is not None else 0
                else:
                    raise ValueError(f"Login request failed for bot {self.bot_id}: {e}")
            except Exception as e:
                # Unexpected error during login, fall back to cached data if available
                if hasattr(self.inventory, 'get_quantity'):
                    print(f"Warning: Unexpected error during login for bot {self.bot_id}, using cached data: {e}")
                    quantity = self.inventory.get_quantity(normalized_name)
                    return quantity if quantity is not None else 0
                else:
                    raise ValueError(f"Unexpected error during login for bot {self.bot_id}: {e}")
        
        # Bot is connected, get fresh inventory data
        try:
            result = client.get_inventory(self.bot_id)
            inventory_data = result.get('inventory', {})
            quantity = inventory_data.get(normalized_name, 0)
            
            # Update local inventory cache
            if hasattr(self.inventory, 'items'):
                if normalized_name not in self.inventory.items:
                    self.inventory.items[normalized_name] = 0
                self.inventory.items[normalized_name] = quantity
            
            # Save to SQL if db session is available
            if self._db_session:
                try:
                    self.save_to_sql(self._db_session)
                except Exception as e:
                    print(f"Warning: Failed to save bot {self.bot_id} inventory to SQL: {e}")
                    # Don't fail here, inventory was already updated in cache
            
            # If we auto-logged in, logout to prevent bot accumulation
            if auto_logged_in:
                try:
                    client.logout(self.bot_id)
                except Exception as logout_err:
                    # Don't fail if logout fails, just log warning
                    print(f"Warning: Failed to logout bot {self.bot_id} after get_stock: {logout_err}")
            
            return quantity
        except Exception as e:
            # If fetching fails, fall back to cached data if available
            # If we auto-logged in, try to logout before returning
            if auto_logged_in:
                try:
                    client.logout(self.bot_id)
                except Exception as logout_err:
                    print(f"Warning: Failed to logout bot {self.bot_id} after get_stock error: {logout_err}")
            
            if hasattr(self.inventory, 'get_quantity'):
                print(f"Warning: Failed to fetch inventory for bot {self.bot_id}, using cached data: {e}")
                quantity = self.inventory.get_quantity(normalized_name)
                return quantity if quantity is not None else 0
            else:
                raise ValueError(f"Failed to fetch inventory for bot {self.bot_id}: {e}")
    
    def _update_inv(self) -> int:
        """
        Update inventory. Private method for internal use.
        Saves inventory state to SQL after update if db session is available.
        
        Returns:
            0 if inventory was accurate,
            -1 if inventory was inaccurate,
            other values for failure
        """
        # TODO: Implement actual inventory update logic
        # After updating inventory, save to SQL:
        #   result = <update inventory from game state>
        #   if result == 0 or result == -1:  # Save even if inaccurate (for tracking)
        #       # Update stored_item_types based on current inventory
        #       if self.inventory and hasattr(self.inventory, 'items'):
        #           self.stored_item_types = [item for item, qty in self.inventory.items.items() if qty > 0]
        #       # Save to SQL if db session is available
        #       if self._db_session:
        #           self.save_to_sql(self._db_session)
        #   return result
        pass
    
    def save_to_sql(self, db: Any) -> None:
        """
        Save bot configuration and current inventory state to database.
        
        Args:
            db: Database session
        """
        # Save or update bot configuration
        bot_model = db.query(MinecraftBotModel).filter(
            MinecraftBotModel.bot_id == self.bot_id
        ).first()
        
        if bot_model:
            # Update existing bot
            bot_model.username = self.username
            bot_model.auth = self.auth
            bot_model.trading_mode = self.trading_mode
        else:
            # Create new bot
            bot_model = MinecraftBotModel(
                bot_id=self.bot_id,
                username=self.username,
                auth=self.auth,
                trading_mode=self.trading_mode
            )
            db.add(bot_model)
        
        # Always clear existing inventory entries for this bot to ensure clean state
        db.query(MinecraftBotInventoryModel).filter(
            MinecraftBotInventoryModel.bot_id == self.bot_id
        ).delete()
        
        # Save current inventory state
        if hasattr(self.inventory, 'items'):
            # Save current inventory
            for item_name, quantity in self.inventory.items.items():
                if quantity > 0:  # Only save items with quantity > 0
                    inv_model = MinecraftBotInventoryModel(
                        bot_id=self.bot_id,
                        item_name=item_name,
                        quantity=quantity
                    )
                    db.add(inv_model)
        
        db.commit()
    
    @classmethod
    def load_from_sql(cls, db: Any, bot_id: str, password: str) -> Optional['MinecraftBot']:
        """
        Load bot from database.
        
        Args:
            db: Database session
            bot_id: Bot identifier
            password: Bot password (must be provided, not stored in DB)
            
        Returns:
            MinecraftBot instance or None if not found
        """
        bot_model = db.query(MinecraftBotModel).filter(
            MinecraftBotModel.bot_id == bot_id
        ).first()
        
        if not bot_model:
            return None
        
        # Create bot instance
        bot = cls(
            username=bot_model.username,
            password=password,
            auth=bot_model.auth,
            trading_mode=bot_model.trading_mode,
            bot_id=bot_model.bot_id
        )
        
        # Load inventory
        inv_models = db.query(MinecraftBotInventoryModel).filter(
            MinecraftBotInventoryModel.bot_id == bot_id
        ).all()
        
        # Reconstruct inventory if we have inventory data
        if inv_models:
            # Load inventory data into the bot's inventory
            # Only load valid items
            if hasattr(bot.inventory, 'items'):
                valid_inventory = {}
                valid_stored_types = []
                for inv in inv_models:
                    if bot._is_valid_item(inv.item_name):
                        valid_inventory[inv.item_name] = inv.quantity
                        if inv.quantity > 0:
                            valid_stored_types.append(inv.item_name)
                    else:
                        print(f"Warning: Bot {bot.bot_id} has invalid item {inv.item_name} in database, skipping")
                
                bot.inventory.items = valid_inventory
                bot.stored_item_types = valid_stored_types
        
        # Note: _db_session should be set by the network/platform after loading
        return bot


class MinecraftBotNet(StorageNetwork):
    """Network of Minecraft bots that act as a storage network."""
    
    def __init__(self):
        """Initialize the Minecraft bot network."""
        self.warehouses: List[MinecraftBot] = []
    
    def get_stock(self, item_name: str, cached: bool = True) -> int:
        """
        Get the total stock level of an item across all warehouses.
        
        Currently only supports bots with 'drop' and 'chat' trading modes.
        Bots with 'plugin' trading mode will raise ValueError.
        
        Args:
            item_name: Name of the item
            cached: Whether to use cached data
            
        Returns:
            Total stock level across all warehouses, or -1 if invalid item
            
        Raises:
            requests.RequestException: If any API request fails
            ValueError: If any bot has 'plugin' trading mode, is not connected, or API response indicates failure
        """
        total_stock = 0
        
        for bot in self.warehouses:
            if isinstance(bot, MinecraftBot):
                stock = bot.get_stock(item_name, cached)
                if stock < 0:
                    return -1  # Invalid item
                total_stock += stock
        
        return total_stock
    
    def get_warehouse_for_retrieve(self, item_name: str, amount: int) -> MinecraftBot:
        """
        Find which warehouse should be used for retrieving an item.
        
        Priority:
        1. First check if any bots are set to store this item type (stored_item_types contains item_name)
        2. If not, assign to bot with least items currently in inventory
        3. Check if bot can handle the amount (using amount_of_item_that_can_be_added)
        4. If not, try to find another bot or create new one (handled by platform)
        
        Args:
            item_name: Name of the item
            amount: Amount to retrieve
            
        Returns:
            Warehouse (MinecraftBot) to use for retrieval
            
        Raises:
            ValueError: If no bot can fit the item
        """
        # Normalize item name
        normalized_item_name = item_name.replace('minecraft:', '')
        
        # First, check if any bots are set to store this item type
        bots_with_item = [
            bot for bot in self.warehouses
            if isinstance(bot, MinecraftBot) and normalized_item_name in bot.stored_item_types
        ]
        
        if bots_with_item:
            # Find the one with least items that can handle the amount
            best_bot = None
            min_items = float('inf')
            
            for bot in bots_with_item:
                if isinstance(bot.inventory, MinecraftInventory):
                    current_item_count = sum(bot.inventory.items.values())
                    can_add = bot.inventory.amount_of_item_that_can_be_added(normalized_item_name)
                    
                    if can_add >= amount and current_item_count < min_items:
                        min_items = current_item_count
                        best_bot = bot
            
            if best_bot:
                return best_bot
        
        # No bots set to store this item, find bot with least items
        if not self.warehouses:
            raise ValueError("No bots available in network")
        
        # Find bot with least items that can handle the amount
        best_bot = None
        min_items = float('inf')
        
        for bot in self.warehouses:
            if isinstance(bot, MinecraftBot) and isinstance(bot.inventory, MinecraftInventory):
                current_item_count = sum(bot.inventory.items.values())
                can_add = bot.inventory.amount_of_item_that_can_be_added(normalized_item_name)
                
                if can_add >= amount and current_item_count < min_items:
                    min_items = current_item_count
                    best_bot = bot
        
        if best_bot:
            return best_bot
        
        # No bot can fit the item
        raise ValueError(
            f"No bot in network can fit {amount} of {item_name}. "
            f"All bots are at capacity or cannot handle this amount."
        )
    
    def get_warehouse_for_store(self, item_name: str, amount: int) -> MinecraftBot:
        """
        Out of the warehouses that store each item, try to minimize the amount
        of items in each warehouse. Prefer warehouses that already have the item.
        Bots can now store multiple different item types thanks to proper inventory management.
        
        Args:
            item_name: Name of the item
            amount: Amount to store
            
        Returns:
            Warehouse to use for storage
        """
        pass
    
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
    
    def save_to_sql(self, db: Any) -> None:
        """
        Save all bots in network and their inventories to database.
        
        Args:
            db: Database session
        """
        for bot in self.warehouses:
            if isinstance(bot, MinecraftBot):
                bot.save_to_sql(db)
        
        # Save network-level configuration if needed
        network_model = db.query(MinecraftNetworkModel).filter(
            MinecraftNetworkModel.network_id == 'default'
        ).first()
        
        if not network_model:
            network_model = MinecraftNetworkModel(
                network_id='default',
                config={}
            )
            db.add(network_model)
        
        db.commit()
    
    def load_from_sql(self, db: Any, get_bot_password: Callable[[str], str]) -> None:
        """
        Load all bots from database, reconstruct network, and populate inventories.
        
        Args:
            db: Database session
            get_bot_password: Callable that takes (username: str) -> str to retrieve bot password
        """
        bot_models = db.query(MinecraftBotModel).all()
        
        self.warehouses = []
        
        for bot_model in bot_models:
            # Get password for this bot
            password = get_bot_password(bot_model.username)
            
            if password:
                bot = MinecraftBot.load_from_sql(db, bot_model.bot_id, password)
                if bot:
                    # Set db session reference so bot can save to SQL automatically
                    bot._db_session = db
                    # Note: Item weight getter should be set by platform after loading
                    self.warehouses.append(bot)
            else:
                print(f"Warning: Password not found for bot {bot_model.username}, skipping load")


class Minecraft(Platform):
    """Minecraft platform implementation for The Pit and other servers."""
    
    platform_name: str = "minecraft"
    
    def __init__(self, *args, **kwargs):
        """
        Initialize Minecraft platform connection.
        Read env variables or a config.yml for getting configs.
        possibleItems should be read from an items.yml.
        Update the MinecraftBotNet from SQL database or create it.
        
        Args:
            *args: Variable length argument list
            **kwargs: Arbitrary keyword arguments
        """
        # Get config directory (platforms/minecraft/confs/)
        config_dir = Path(__file__).parent / 'confs'
        
        # Load configuration from environment variables or config.yml
        config = self._load_config(config_dir)
        
        # Set configuration attributes (env vars take precedence over config file)
        self._trading_mode: str = os.getenv(
            'MINECRAFT_TRADING_MODE',
            config.get('trading_mode', 'drop')
        )
        self._server_address: str = os.getenv(
            'MINECRAFT_SERVER_ADDRESS',
            config.get('server_address', 'localhost')
        )
        self._server_port: int = int(os.getenv(
            'MINECRAFT_SERVER_PORT',
            config.get('server_port', 25565)
        ))
        self._offline: bool = os.getenv(
            'MINECRAFT_OFFLINE',
            str(config.get('offline', False))
        ).lower() in ('true', '1', 'yes')
        self._minecraft_version: str = os.getenv(
            'MINECRAFT_VERSION',
            config.get('minecraft_version', '1.21.4')
        )
        
        # Load items from items.yml
        self._possible_items: List[Item] = self._load_items(config_dir)
        
        # Initialize database connection
        self._db = self._get_minecraft_db()
        
        # Initialize network - load from SQL if exists, otherwise create new
        self._network: Optional[MinecraftBotNet] = MinecraftBotNet()
        self._load_network_from_sql()
        
        # Load bots from bots.yml config file (creates any missing bots)
        self._load_bots_from_config(config_dir)
    
    def _get_minecraft_db(self) -> Any:
        """
        Create separate database connection for Minecraft platform.
        
        Returns:
            Database session
        """
        db_url = os.getenv('MINECRAFT_DATABASE_URL', 'sqlite:///minecraft_network.db')
        engine = create_engine(db_url)
        
        # Create tables if they don't exist
        MinecraftBase.metadata.create_all(engine)
        
        Session = sessionmaker(bind=engine)
        return Session()
    
    def _get_bot_password(self, username: str) -> Optional[str]:
        """
        Retrieve bot password from environment variables.
        
        Args:
            username: Bot username
            
        Returns:
            Password if found, None otherwise
        """
        env_var = f'MINECRAFT_BOT_PASSWORD_{username.upper()}'
        return os.getenv(env_var)
    
    def _load_network_from_sql(self) -> None:
        """
        Load network from SQL database if data exists.
        If no data exists, network remains empty.
        """
        try:
            # Check if any bots exist in database
            bot_count = self._db.query(MinecraftBotModel).count()
            
            if bot_count > 0:
                # Load network from database
                self._network.load_from_sql(self._db, self._get_bot_password)
                
                # Set valid items list for all loaded bots
                valid_item_names = set(item.item_name for item in self._possible_items)
                
                # Set item weight getter for all loaded bots
                def get_item_weight(item_name: str) -> int:
                    for item in self._possible_items:
                        if item.item_name == item_name:
                            return item.item_weight
                    return 1  # Default weight if item not found
                
                for bot in self._network.warehouses:
                    if isinstance(bot, MinecraftBot):
                        # Set valid items list
                        bot._valid_items = valid_item_names
                        # Filter stored_item_types to only include valid items
                        bot.stored_item_types = [item for item in bot.stored_item_types if bot._is_valid_item(item)]
                        
                        if isinstance(bot.inventory, MinecraftInventory):
                            bot.inventory._get_item_weight = get_item_weight
                        # Set server connection info for loaded bots
                        bot._server_address = self._server_address
                        bot._server_port = self._server_port
                        bot._minecraft_version = self._minecraft_version
            # If no bots exist, network remains empty (already initialized)
        except Exception as e:
            print(f"Warning: Could not load network from database: {e}")
            # Continue with empty network
    
    def save_network_to_sql(self) -> None:
        """
        Save entire network state to database.
        """
        try:
            self._network.save_to_sql(self._db)
        except Exception as e:
            print(f"Error saving network to database: {e}")
            self._db.rollback()
    
    def _load_config(self, config_dir: Path) -> Dict[str, Any]:
        """
        Load configuration from config.yml file.
        
        Args: config_dir: Path to config directory (platforms/minecraft/confs/) Returns: Dictionary containing configuration values
        """
        config_path = config_dir / 'config.yml'
        config = {}
        
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f) or {}
            except Exception as e:
                # If config file exists but can't be read, use defaults
                print(f"Warning: Could not load config.yml: {e}")
        
        return config
    
    def _load_items(self, config_dir: Path) -> List[Item]:
        """
        Load items from items.yml file.
        
        The item_info field should ONLY contain in-game NBT data relevant for
        identifying items in trading (e.g., custom names, lore, enchantments).
        It must follow the Minecraft NBT specification.
        
        Common NBT fields for item identification:
        - display.Name: Custom item name (JSON text component)
        - display.Lore: Custom lore/description (array of JSON text components)
        - Enchantments: List of enchantments (if relevant for trading)
        
        Args:
            config_dir: Path to config directory (platforms/minecraft/confs/)
            
        Returns:
            List of Item objects
        """
        items_path = config_dir / 'items.yml'
        items = []
        
        if items_path.exists():
            try:
                with open(items_path, 'r') as f:
                    data = yaml.safe_load(f) or {}
                    items_data = data.get('items', [])
                    
                    for item_data in items_data:
                        item = Item()
                        item.item_name = item_data.get('name', '')
                        item.item_weight = item_data.get('weight', 1)
                        # item_info should only contain Minecraft NBT data for item identification
                        # See: https://minecraft.wiki/w/Item_format
                        item.item_info = item_data.get('info', {})
                        items.append(item)
            except Exception as e:
                print(f"Warning: Could not load items.yml: {e}")
        
        return items
    
    def _load_bots_from_config(self, config_dir: Path) -> None:
        """
        Load bots from bots.yml file and ensure they are in the network.
        
        bots.yml is ALWAYS prioritized over the SQL database. For each bot in bots.yml:
        - If bot exists in database, update its configuration from bots.yml (username, auth, etc.)
          but preserve inventory from database
        - If bot doesn't exist in database, create it
        - Always ensure bot is in network with bots.yml configuration
        
        Passwords can be provided either:
        - Directly in bots.yml file (password field)
        - Via environment variables: MINECRAFT_BOT_PASSWORD_{USERNAME} (where USERNAME is uppercase)
        
        Args:
            config_dir: Path to config directory (platforms/minecraft/confs/)
        """
        bots_path = config_dir / 'bots.yml'
        
        if not bots_path.exists():
            # bots.yml is optional - if it doesn't exist, just return
            return
        
        try:
            with open(bots_path, 'r') as f:
                data = yaml.safe_load(f) or {}
                bots_data = data.get('bots', [])
                
                for bot_data in bots_data:
                    username = bot_data.get('username')
                    if not username:
                        print(f"Warning: Bot entry missing username, skipping")
                        continue
                    
                    auth = bot_data.get('auth', 'offline')
                    bot_id = bot_data.get('bot_id', username)
                    
                    # Get password from config file, fallback to environment variable
                    password = bot_data.get('password')
                    if not password:
                        password = self._get_bot_password(username)
                    if not password:
                        print(f"Warning: Password not found for bot {username} (set in bots.yml or MINECRAFT_BOT_PASSWORD_{username.upper()} env var), skipping")
                        continue
                    
                    # Check if bot is already in the network
                    existing_bot_in_network = None
                    for w in self._network.warehouses:
                        if isinstance(w, MinecraftBot) and w.bot_id == bot_id:
                            existing_bot_in_network = w
                            break
                    
                    # Check if bot exists in database
                    existing_bot_model = self._db.query(MinecraftBotModel).filter(
                        MinecraftBotModel.bot_id == bot_id
                    ).first()
                    
                    # Set valid items list for all bots
                    valid_item_names = set(item.item_name for item in self._possible_items)
                    
                    if existing_bot_in_network:
                        # Bot is already in network - update its configuration from bots.yml
                        bot = existing_bot_in_network
                        # Update configuration from bots.yml (prioritize bots.yml)
                        bot.username = username
                        bot.auth = auth
                        bot.password = password  # Update password
                        # Note: trading_mode comes from platform config, not bots.yml
                        
                        # Set valid items list
                        bot._valid_items = valid_item_names
                        # Filter stored_item_types to only include valid items
                        bot.stored_item_types = [item for item in bot.stored_item_types if bot._is_valid_item(item)]
                        
                        # Update database to match bots.yml
                        if existing_bot_model:
                            existing_bot_model.username = username
                            existing_bot_model.auth = auth
                            self._db.commit()
                        
                        print(f"Updated bot configuration from bots.yml: {username} (bot_id: {bot_id})")
                    elif existing_bot_model:
                        # Bot exists in database but not in network - load it and update from bots.yml
                        try:
                            bot = MinecraftBot.load_from_sql(self._db, bot_id, password)
                            if bot:
                                # Update configuration from bots.yml (prioritize bots.yml)
                                bot.username = username
                                bot.auth = auth
                                bot.password = password
                                
                                # Update database to match bots.yml
                                existing_bot_model.username = username
                                existing_bot_model.auth = auth
                                self._db.commit()
                                
                                # Set valid items list
                                bot._valid_items = valid_item_names
                                # Filter stored_item_types to only include valid items
                                bot.stored_item_types = [item for item in bot.stored_item_types if bot._is_valid_item(item)]
                                
                                # Set item weight getter
                                def get_item_weight(item_name: str) -> int:
                                    for item in self._possible_items:
                                        if item.item_name == item_name:
                                            return item.item_weight
                                    return 1
                                
                                if isinstance(bot.inventory, MinecraftInventory):
                                    bot.inventory._get_item_weight = get_item_weight
                                
                                # Set server connection info
                                bot._server_address = self._server_address
                                bot._server_port = self._server_port
                                bot._minecraft_version = self._minecraft_version
                                
                                # Set db session reference
                                bot._db_session = self._db
                                
                                # Add to network
                                self._network.warehouses.append(bot)
                                print(f"Loaded and updated bot from database with bots.yml config: {username} (bot_id: {bot_id})")
                            else:
                                print(f"Warning: Could not load bot {username} from database")
                        except Exception as e:
                            print(f"Error loading bot {username} from database: {e}")
                    else:
                        # Bot doesn't exist, create it (this will add it to network and save to SQL)
                        try:
                            self.create_bot(username=username, password=password, auth=auth, bot_id=bot_id)
                            print(f"Created bot: {username} (bot_id: {bot_id})")
                        except Exception as e:
                            print(f"Error creating bot {username}: {e}")
                        
        except Exception as e:
            print(f"Warning: Could not load bots.yml: {e}")
    
    def get_item_list(self) -> List[str]:
        """
        Lists items on the platform, iterate through possibleItems and return the ItemNames.
        
        Returns:
            List of item names
        """
        return [item.item_name for item in self._possible_items]
    
    def deliver_item(self, item_name: str, amount: int, uuid: str) -> int:
        """
        Sends amount of itemName to UUID.
        Find which minecraftBot has the item, then have it deliver the item.
        
        Args:
            item_name: Name of the item to deliver
            amount: Amount to deliver
            uuid: User's UUID or username
            
        Returns:
            0 if success, non-zero error code if failure
        """
        # Validate that the item is in the list of possible items
        normalized_item_name = item_name.replace('minecraft:', '')
        valid_item_names = self.get_item_list()
        if normalized_item_name not in valid_item_names:
            print(f"Error: Item '{item_name}' is not a valid item. Valid items: {', '.join(valid_item_names)}")
            return 1  # Invalid item
        
        if not self._network:
            return 1  # No network available
        
        try:
            # Find a bot that has enough of the item
            bot = None
            for warehouse in self._network.warehouses:
                if isinstance(warehouse, MinecraftBot):
                    # Check if bot has enough stock
                    try:
                        stock = warehouse.get_stock(normalized_item_name, cached=True)
                        if stock >= amount:
                            bot = warehouse
                            break
                    except Exception as e:
                        # Skip bots that can't provide stock info
                        print(f"Warning: Could not check stock for bot {warehouse.bot_id}: {e}")
                        continue
            
            if not bot:
                # No bot has enough stock - check total network stock
                total_stock = self._network.get_stock(normalized_item_name, cached=True)
                if total_stock < amount:
                    print(f"Error: Not enough stock. Network has {total_stock}, need {amount}")
                    return 1
                else:
                    # Stock exists but might be spread across multiple bots
                    # For now, try to find the bot with the most stock
                    best_bot = None
                    max_stock = 0
                    for warehouse in self._network.warehouses:
                        if isinstance(warehouse, MinecraftBot):
                            try:
                                stock = warehouse.get_stock(normalized_item_name, cached=True)
                                if stock > max_stock:
                                    max_stock = stock
                                    best_bot = warehouse
                            except Exception:
                                continue
                    
                    if best_bot:
                        bot = best_bot
                        print(f"Warning: Item spread across multiple bots. Using bot {bot.bot_id} with {max_stock} items")
                    else:
                        print(f"Error: Could not find a bot with the item")
                        return 1
            
            # Set server connection info for bot if not already set
            if not bot._server_address:
                bot._server_address = self._server_address
                bot._server_port = self._server_port
                bot._minecraft_version = self._minecraft_version
            
            # Have the bot deliver the item
            return bot.deliver_item(normalized_item_name, amount, uuid)
            
        except ValueError as e:
            print(f"Error finding warehouse for delivery: {e}")
            return 1
        except Exception as e:
            print(f"Error delivering item {item_name}: {e}")
            import traceback
            traceback.print_exc()
            return 1
    
    def retrieve_item(self, item_name: str, amount: int, uuid: str) -> int:
        """
        Gets itemName from UUID.
        Find which minecraftBot is best suited to storing an item, and then have it retrieve the item.
        
        Flow:
        1. Check BotNet for which bot should retrieve (get_warehouse_for_retrieve)
        2. BotNet will:
           - First check if any bots are set to store this item type
           - If not, assign to bot with least items
           - Check if bot can handle the amount
           - If not, try to create a new bot or error
        3. Have the selected bot actually retrieve the item (calls bot.retrieve_item)
        
        Args:
            item_name: Name of the item to retrieve
            amount: Amount to retrieve
            uuid: User's UUID
            
        Returns:
            0 if success, non-zero error code if failure
        """
        # Validate that the item is in the list of possible items
        normalized_item_name = item_name.replace('minecraft:', '')
        valid_item_names = self.get_item_list()
        if normalized_item_name not in valid_item_names:
            print(f"Error: Item '{item_name}' is not a valid item. Valid items: {', '.join(valid_item_names)}")
            return 1  # Invalid item
        
        if not self._network:
            return 1  # No network available
        
        try:
            # Get warehouse for retrieve
            bot = self._network.get_warehouse_for_retrieve(item_name, amount)
            
            # Check if bot can handle the amount
            if isinstance(bot.inventory, MinecraftInventory):
                normalized_item_name = item_name.replace('minecraft:', '')
                can_add = bot.inventory.amount_of_item_that_can_be_added(normalized_item_name)
                if can_add < amount:
                    # Try to find another bot or create new one
                    # First, try to find another bot
                    try:
                        # Remove current bot from consideration and try again
                        original_warehouses = self._network.warehouses.copy()
                        self._network.warehouses = [b for b in original_warehouses if b != bot]
                        bot = self._network.get_warehouse_for_retrieve(item_name, amount)
                        self._network.warehouses = original_warehouses
                    except ValueError:
                        # No other bot can fit, would need to create new bot
                        # For now, return error - can be enhanced later
                        return 1
            
            # Set server connection info for bot if not already set
            if not bot._server_address:
                bot._server_address = self._server_address
                bot._server_port = self._server_port
                bot._minecraft_version = self._minecraft_version
            
            # Have the bot retrieve the item
            return bot.retrieve_item(item_name, amount, uuid)
            
        except ValueError as e:
            print(f"Error finding warehouse for retrieve: {e}")
            return 1
        except Exception as e:
            print(f"Error retrieving item {item_name}: {e}")
            return 1
    
    def get_stock(self, item_name: str, cached: bool = True) -> int:
        """
        Returns item stock.
        
        Currently only supports bots with 'drop' and 'chat' trading modes.
        Bots with 'plugin' trading mode will raise ValueError.
        
        Args:
            item_name: Name of the item
            cached: If True, use cached inventory data. If False, fetch fresh data from API.
            
        Returns:
            Current stock level
            
        Raises:
            requests.RequestException: If any API request fails
            ValueError: If any bot has 'plugin' trading mode, is not connected, or API response indicates failure
        """
        if self._network:
            return self._network.get_stock(item_name, cached=cached)
        return 0
    
    def create_bot(self, username: str, password: str, auth: str, bot_id: Optional[str] = None) -> MinecraftBot:
        """
        Create the bot, add it to the network, and save to SQL.
        
        Args:
            username: Bot username
            password: Bot password
            auth: Authentication type ('online' or 'offline')
            bot_id: Optional unique bot identifier (defaults to username if not provided)
            
        Returns:
            Created MinecraftBot instance
        """
        # Create function to get item weight from platform's possible items
        def get_item_weight(item_name: str) -> int:
            for item in self._possible_items:
                if item.item_name == item_name:
                    return item.item_weight
            return 1  # Default weight if item not found
        
        # Create bot with trading mode from platform config
        bot = MinecraftBot(
            username=username,
            password=password,
            auth=auth,
            trading_mode=self._trading_mode,
            bot_id=bot_id
        )
        
        # Set valid items list from platform
        valid_item_names = set(item.item_name for item in self._possible_items)
        bot._valid_items = valid_item_names
        
        # Set item weight getter for inventory
        if isinstance(bot.inventory, MinecraftInventory):
            bot.inventory._get_item_weight = get_item_weight
        
        # Set server connection info for bot
        bot._server_address = self._server_address
        bot._server_port = self._server_port
        bot._minecraft_version = self._minecraft_version
        
        # Set db session reference so bot can save to SQL automatically
        bot._db_session = self._db
        
        # Add to network
        self._network.warehouses.append(bot)
        
        # Save to SQL immediately
        try:
            bot.save_to_sql(self._db)
        except Exception as e:
            print(f"Error saving bot to database: {e}")
            self._db.rollback()
        
        return bot

