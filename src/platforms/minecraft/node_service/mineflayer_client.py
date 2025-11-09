"""
Python client for the Mineflayer API service.

This module provides a Python interface to interact with the Node.js mineflayer
service for managing Minecraft bot connections.
"""

import requests
from typing import Optional, Dict, Any, List
import json


class MineflayerClient:
    """Client for interacting with the Mineflayer API service."""
    
    def __init__(self, api_url: str = "http://localhost:3000"):
        """
        Initialize the Mineflayer API client.
        
        Args:
            api_url: Base URL of the mineflayer API service
        """
        self.api_url = api_url.rstrip('/')
        self.session = requests.Session()
    
    def login(
        self,
        bot_id: str,
        username: str,
        password: Optional[str] = None,
        auth: str = "offline",
        server_host: str = "localhost",
        server_port: int = 25565,
        version: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Log a bot into a Minecraft server.
        
        Args:
            bot_id: Unique identifier for the bot
            username: Minecraft username
            password: Password for online authentication (required if auth='online')
            auth: Authentication mode ('online' or 'offline')
            server_host: Minecraft server address
            server_port: Minecraft server port
            version: Minecraft version (e.g., '1.21.4'). Defaults to '1.21.4' if not specified
            
        Returns:
            Dictionary with login result containing:
            - success: bool
            - bot_id: str
            - status: str
            - uuid: Optional[str] (only for online mode)
            - username: str
            
        Raises:
            requests.RequestException: If the API request fails
        """
        url = f"{self.api_url}/api/bot/login"
        
        payload = {
            "bot_id": bot_id,
            "username": username,
            "auth": auth,
            "server": {
                "host": server_host,
                "port": server_port
            }
        }
        
        # Add version if specified
        if version:
            payload["server"]["version"] = version
        
        # Add password for online authentication
        if auth == "online":
            if not password:
                raise ValueError("Password is required for online authentication")
            payload["password"] = password
        
        response = self.session.post(url, json=payload, timeout=35)
        response.raise_for_status()
        return response.json()
    
    def logout(self, bot_id: str) -> Dict[str, Any]:
        """
        Log out a bot from the server.
        
        Args:
            bot_id: Unique identifier for the bot
            
        Returns:
            Dictionary with logout result
            
        Raises:
            requests.RequestException: If the API request fails
        """
        url = f"{self.api_url}/api/bot/logout"
        
        payload = {"bot_id": bot_id}
        
        response = self.session.post(url, json=payload)
        response.raise_for_status()
        return response.json()
    
    def get_status(self, bot_id: str) -> Dict[str, Any]:
        """
        Get the connection status of a bot.
        
        Args:
            bot_id: Unique identifier for the bot
            
        Returns:
            Dictionary with bot status information
            
        Raises:
            requests.RequestException: If the API request fails
        """
        url = f"{self.api_url}/api/bot/status/{bot_id}"
        
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()
    
    def list_bots(self) -> Dict[str, Any]:
        """
        List all connected bots.
        
        Returns:
            Dictionary with list of connected bots
            
        Raises:
            requests.RequestException: If the API request fails
        """
        url = f"{self.api_url}/api/bots"
        
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check the health of the API service.
        
        Returns:
            Dictionary with service health status
            
        Raises:
            requests.RequestException: If the API request fails
        """
        url = f"{self.api_url}/health"
        
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()
    
    def get_inventory(self, bot_id: str) -> Dict[str, Any]:
        """
        Get the current inventory of a bot.
        
        Args:
            bot_id: Unique identifier for the bot
            
        Returns:
            Dictionary with inventory data containing:
            - success: bool
            - bot_id: str
            - inventory: Dict[str, int] (item_name -> quantity)
            
        Raises:
            requests.RequestException: If the API request fails
            ValueError: If the API response indicates failure
        """
        url = f"{self.api_url}/api/bot/inventory/{bot_id}"
        
        response = self.session.get(url, timeout=10)
        response.raise_for_status()
        result = response.json()
        
        if not result.get('success', False):
            error_msg = result.get('error', 'Unknown error')
            raise ValueError(f"API returned failure: {error_msg}")
        
        return result
    
    def validate_inventory(self, bot_id: str, expected_inventory: Optional[Dict[str, int]] = None) -> Dict[str, Any]:
        """
        Validate bot inventory against expected inventory.
        
        Args:
            bot_id: Unique identifier for the bot
            expected_inventory: Optional dict of item_name -> quantity to validate against
            
        Returns:
            Dictionary with validation result containing:
            - success: bool
            - is_accurate: bool
            - differences: Dict[str, int] (item_name -> difference)
            
        Raises:
            requests.RequestException: If the API request fails
            ValueError: If the API response indicates failure
        """
        url = f"{self.api_url}/api/bot/inventory/{bot_id}/validate"
        
        payload = {}
        if expected_inventory:
            payload["expected_inventory"] = expected_inventory
        
        response = self.session.post(url, json=payload, timeout=10)
        response.raise_for_status()
        result = response.json()
        
        if not result.get('success', False):
            error_msg = result.get('error', 'Unknown error')
            raise ValueError(f"API returned failure: {error_msg}")
        
        return result
    
    def drop_items(self, bot_id: str, allowed_items: List[str]) -> Dict[str, Any]:
        """
        Drop items from bot inventory that are not in the allowed list.
        
        Args:
            bot_id: Unique identifier for the bot
            allowed_items: List of item names to keep (all others will be dropped)
            
        Returns:
            Dictionary with drop result containing:
            - success: bool
            - dropped_count: int
            
        Raises:
            requests.RequestException: If the API request fails
            ValueError: If the API response indicates failure
        """
        url = f"{self.api_url}/api/bot/inventory/{bot_id}/drop"
        
        payload = {"allowed_items": allowed_items}
        
        response = self.session.post(url, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()
        
        if not result.get('success', False):
            error_msg = result.get('error', 'Unknown error')
            raise ValueError(f"API returned failure: {error_msg}")
        
        return result
    
    def drop_excess_items(self, bot_id: str, item_name: str, target_amount: int) -> Dict[str, Any]:
        """
        Drop excess items of a specific type until we have exactly target_amount.
        
        Args:
            bot_id: Unique identifier for the bot
            item_name: Name of the item to drop excess of
            target_amount: Target amount to keep
            
        Returns:
            Dictionary with drop result containing:
            - success: bool
            - dropped_count: int
            - excess_dropped: int
            
        Raises:
            requests.RequestException: If the API request fails
            ValueError: If the API response indicates failure
        """
        url = f"{self.api_url}/api/bot/inventory/{bot_id}/drop-excess"
        
        payload = {
            "item_name": item_name,
            "target_amount": target_amount
        }
        
        response = self.session.post(url, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()
        
        if not result.get('success', False):
            error_msg = result.get('error', 'Unknown error')
            raise ValueError(f"API returned failure: {error_msg}")
        
        return result
    
    def send_chat(self, bot_id: str, message: str) -> Dict[str, Any]:
        """
        Send a chat message from the bot.
        
        Args:
            bot_id: Unique identifier for the bot
            message: Chat message to send
            
        Returns:
            Dictionary with result containing:
            - success: bool
            
        Raises:
            requests.RequestException: If the API request fails
            ValueError: If the API response indicates failure
        """
        url = f"{self.api_url}/api/bot/{bot_id}/chat"
        
        payload = {"message": message}
        
        response = self.session.post(url, json=payload, timeout=10)
        response.raise_for_status()
        result = response.json()
        
        if not result.get('success', False):
            error_msg = result.get('error', 'Unknown error')
            raise ValueError(f"API returned failure: {error_msg}")
        
        return result
    
    def wait_for_items(
        self,
        bot_id: str,
        item_name: str,
        target_amount: int,
        timeout_seconds: int = 300
    ) -> Dict[str, Any]:
        """
        Wait for items to appear in bot inventory with progress updates.
        
        Args:
            bot_id: Unique identifier for the bot
            item_name: Name of the item to wait for
            target_amount: Target amount of items to wait for
            timeout_seconds: Maximum time to wait in seconds (default: 300)
            
        Returns:
            Dictionary with result containing:
            - success: bool
            - received_amount: int
            - progress_messages: List[str] (chat messages sent during wait)
            
        Raises:
            requests.RequestException: If the API request fails
            ValueError: If the API response indicates failure
        """
        url = f"{self.api_url}/api/bot/{bot_id}/wait-for-items"
        
        payload = {
            "item_name": item_name,
            "target_amount": target_amount,
            "timeout_seconds": timeout_seconds
        }
        
        response = self.session.post(url, json=payload, timeout=timeout_seconds + 10)
        response.raise_for_status()
        result = response.json()
        
        if not result.get('success', False):
            error_msg = result.get('error', 'Unknown error')
            raise ValueError(f"API returned failure: {error_msg}")
        
        return result
    
    def deliver_item(
        self,
        bot_id: str,
        item_name: str,
        amount: int,
        target_uuid: str,
        timeout_seconds: int = 60
    ) -> Dict[str, Any]:
        """
        Deliver items to a player by navigating to them and dropping items.
        
        Args:
            bot_id: Unique identifier for the bot
            item_name: Name of the item to deliver
            amount: Amount to deliver
            target_uuid: Target player's username or UUID
            timeout_seconds: Maximum time to wait for delivery in seconds (default: 60)
            
        Returns:
            Dictionary with result containing:
            - success: bool
            - item_name: str
            - amount_dropped: int
            - target_uuid: str
            
        Raises:
            requests.RequestException: If the API request fails
            ValueError: If the API response indicates failure
        """
        url = f"{self.api_url}/api/bot/{bot_id}/deliver-item"
        
        payload = {
            "item_name": item_name,
            "amount": amount,
            "target_uuid": target_uuid
        }
        
        response = self.session.post(url, json=payload, timeout=timeout_seconds + 10)
        response.raise_for_status()
        result = response.json()
        
        if not result.get('success', False):
            error_msg = result.get('error', 'Unknown error')
            raise ValueError(f"API returned failure: {error_msg}")
        
        return result
    
    def is_available(self) -> bool:
        """
        Check if the API service is available.
        
        Returns:
            True if the service is available, False otherwise
        """
        try:
            health = self.health_check()
            return health.get('status') == 'ok'
        except Exception:
            return False


# Convenience function for quick bot login
def login_bot(
    bot_id: str,
    username: str,
    password: Optional[str] = None,
    auth: str = "offline",
    server_host: str = "localhost",
    server_port: int = 25565,
    version: Optional[str] = None,
    api_url: str = "http://localhost:3000"
) -> Dict[str, Any]:
    """
    Convenience function to log in a bot.
    
    Args:
        bot_id: Unique identifier for the bot
        username: Minecraft username
        password: Password for online authentication (required if auth='online')
        auth: Authentication mode ('online' or 'offline')
        server_host: Minecraft server address
        server_port: Minecraft server port
        version: Minecraft version (e.g., '1.21.4'). Defaults to '1.21.4' if not specified
        api_url: Base URL of the mineflayer API service
        
    Returns:
        Dictionary with login result
    """
    client = MineflayerClient(api_url)
    return client.login(
        bot_id=bot_id,
        username=username,
        password=password,
        auth=auth,
        server_host=server_host,
        server_port=server_port,
        version=version
    )

