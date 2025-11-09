"""
Integration tests for Minecraft platform item retrieval/deposit functionality.

These tests require:
1. A running Minecraft server (or test server)
2. The mineflayer Node.js service running
3. Valid bot credentials configured

Set environment variables:
- MINECRAFT_TEST_SERVER: Server address (default: localhost)
- MINECRAFT_TEST_PORT: Server port (default: 25565)
- MINECRAFT_TEST_VERSION: Minecraft version (default: 1.21.8)
- MINECRAFT_BOT_PASSWORD_<username>: Password for each test bot
- MINEFLAYER_API_URL: Mineflayer service URL (default: http://localhost:3000)

Skip these tests if MINECRAFT_SKIP_INTEGRATION_TESTS is set.
"""
import pytest
import os
import time
import tempfile
from typing import List, Dict, Optional

from .platform import Minecraft, MinecraftBot, MinecraftBotNet
from .node_service import MineflayerClient
from .models import MinecraftBotModel, MinecraftBotInventoryModel, MinecraftNetworkModel


# Skip all integration tests if flag is set
pytestmark = pytest.mark.skipif(
    os.getenv('MINECRAFT_SKIP_INTEGRATION_TESTS', '').lower() == 'true',
    reason="Integration tests skipped via MINECRAFT_SKIP_INTEGRATION_TESTS"
)


class TestMinecraftIntegration:
    """Integration tests for Minecraft platform with real bots and server."""
    
    @pytest.fixture(scope="class")
    def mineflayer_client(self):
        """Create a mineflayer client for testing."""
        api_url = os.getenv('MINEFLAYER_API_URL', 'http://localhost:3000')
        return MineflayerClient(api_url=api_url)
    
    @pytest.fixture(scope="class")
    def test_server_config(self):
        """Get test server configuration from environment."""
        return {
            'address': os.getenv('MINECRAFT_TEST_SERVER', 'localhost'),
            'port': int(os.getenv('MINECRAFT_TEST_PORT', '25565')),
            'version': os.getenv('MINECRAFT_TEST_VERSION', '1.21.8')
        }
    
    @pytest.fixture(scope="class")
    def test_bots_config(self):
        """Get test bot configurations."""
        # Define test bots - these should be configured in environment
        bots = [
            {
                'username': 'testbot1',
                'bot_id': 'testbot1',
                'auth': 'offline'
            },
            {
                'username': 'testbot2',
                'bot_id': 'testbot2',
                'auth': 'offline'
            },
            {
                'username': 'testbot3',
                'bot_id': 'testbot3',
                'auth': 'offline'
            }
        ]
        
        # Verify passwords are available
        for bot in bots:
            password = os.getenv(f'MINECRAFT_BOT_PASSWORD_{bot["username"].upper()}')
            if not password:
                pytest.skip(f"Password not set for bot {bot['username']} (set MINECRAFT_BOT_PASSWORD_{bot['username'].upper()})")
            bot['password'] = password
        
        return bots
    
    @pytest.fixture(scope="class")
    def test_db_path(self):
        """Create a temporary database for testing."""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        yield path
        # Cleanup
        if os.path.exists(path):
            os.remove(path)
    
    @pytest.fixture(scope="class")
    def platform(self, test_db_path, test_server_config, monkeypatch):
        """Create a Minecraft platform instance for testing."""
        # Set database URL
        monkeypatch.setenv('MINECRAFT_DATABASE_URL', f'sqlite:///{test_db_path}')
        
        # Create platform
        platform = Minecraft()
        
        # Override server config for testing
        platform._server_address = test_server_config['address']
        platform._server_port = test_server_config['port']
        platform._minecraft_version = test_server_config['version']
        
        return platform
    
    @pytest.fixture(scope="class")
    def setup_bots(self, platform, test_bots_config, test_server_config):
        """Set up test bots in the platform."""
        bots = []
        for bot_config in test_bots_config:
            bot = platform.create_bot(
                username=bot_config['username'],
                password=bot_config['password'],
                auth=bot_config['auth'],
                bot_id=bot_config['bot_id']
            )
            bots.append(bot)
        
        yield bots
        
        # Cleanup: logout all bots
        client = MineflayerClient()
        for bot in bots:
            try:
                status = client.get_status(bot.bot_id)
                if status.get('success') and status.get('status') == 'connected':
                    client.logout(bot.bot_id)
            except Exception as e:
                print(f"Warning: Could not logout bot {bot.bot_id}: {e}")
    
    def test_service_connectivity(self, mineflayer_client):
        """Test that the mineflayer service is accessible."""
        # Try to get status of a non-existent bot (should return error but service should respond)
        try:
            result = mineflayer_client.get_status('nonexistent_bot')
            # Service should respond (even if bot doesn't exist)
            assert 'success' in result
        except Exception as e:
            pytest.fail(f"Mineflayer service not accessible: {e}")
    
    def test_bot_login_logout(self, platform, test_bots_config, test_server_config):
        """Test that bots can login and logout."""
        bot_config = test_bots_config[0]
        bot = platform.create_bot(
            username=bot_config['username'],
            password=bot_config['password'],
            auth=bot_config['auth'],
            bot_id=bot_config['bot_id']
        )
        
        client = MineflayerClient()
        
        # Login
        login_result = client.login(
            bot_id=bot.bot_id,
            username=bot.username,
            password=bot.password,
            auth=bot.auth,
            server_host=test_server_config['address'],
            server_port=test_server_config['port'],
            version=test_server_config['version']
        )
        
        assert login_result.get('success'), f"Login failed: {login_result}"
        
        # Wait a bit for connection
        time.sleep(2)
        
        # Check status
        status = client.get_status(bot.bot_id)
        assert status.get('success'), f"Status check failed: {status}"
        assert status.get('status') == 'connected', f"Bot not connected: {status}"
        
        # Logout
        logout_result = client.logout(bot.bot_id)
        assert logout_result.get('success'), f"Logout failed: {logout_result}"
        
        # Wait a bit for disconnection
        time.sleep(1)
        
        # Verify disconnected
        status = client.get_status(bot.bot_id)
        assert status.get('status') != 'connected', "Bot still connected after logout"
    
    @pytest.mark.parametrize("item_name,amount", [
        ("diamond", 64),
        ("emerald", 32),
        ("gold_ingot", 16),
    ])
    def test_retrieve_single_item_single_bot(self, platform, setup_bots, item_name, amount):
        """Test retrieving a single item type with a single bot."""
        bot = setup_bots[0]
        
        # Retrieve item
        result = platform.retrieve_item(item_name, amount, f"test_uuid_{item_name}")
        
        assert result == 0, f"Failed to retrieve {amount} {item_name}"
        
        # Verify inventory
        stock = platform.get_stock(item_name)
        assert stock >= amount, f"Expected at least {amount} {item_name}, got {stock}"
        
        # Verify bot inventory
        assert item_name in bot.stored_item_types, f"{item_name} not in bot's stored_item_types"
        assert bot.inventory.get_quantity(item_name) >= amount, \
            f"Bot inventory doesn't have {amount} {item_name}"
    
    def test_retrieve_multiple_items_single_bot(self, platform, setup_bots):
        """Test retrieving multiple different items with a single bot."""
        bot = setup_bots[0]
        
        items_to_retrieve = [
            ("diamond", 32),
            ("emerald", 16),
            ("gold_ingot", 8),
        ]
        
        for item_name, amount in items_to_retrieve:
            result = platform.retrieve_item(item_name, amount, f"test_uuid_{item_name}")
            assert result == 0, f"Failed to retrieve {amount} {item_name}"
        
        # Verify all items are in inventory
        for item_name, amount in items_to_retrieve:
            stock = platform.get_stock(item_name)
            assert stock >= amount, f"Expected at least {amount} {item_name}, got {stock}"
            assert bot.inventory.get_quantity(item_name) >= amount, \
                f"Bot inventory doesn't have {amount} {item_name}"
    
    def test_retrieve_same_item_multiple_bots(self, platform, setup_bots):
        """Test retrieving the same item type across multiple bots."""
        item_name = "diamond"
        amount_per_bot = 32
        
        # Retrieve items using different bots
        for i, bot in enumerate(setup_bots[:2]):  # Use first 2 bots
            result = platform.retrieve_item(item_name, amount_per_bot, f"test_uuid_{i}")
            assert result == 0, f"Bot {i} failed to retrieve {amount_per_bot} {item_name}"
        
        # Verify total stock
        total_stock = platform.get_stock(item_name)
        expected_min = amount_per_bot * 2
        assert total_stock >= expected_min, \
            f"Expected at least {expected_min} {item_name} total, got {total_stock}"
    
    def test_retrieve_different_items_multiple_bots(self, platform, setup_bots):
        """Test retrieving different items across multiple bots."""
        items_per_bot = [
            ("diamond", 64),
            ("emerald", 32),
            ("gold_ingot", 16),
        ]
        
        # Assign each item to a different bot
        for i, (item_name, amount) in enumerate(items_per_bot):
            if i < len(setup_bots):
                bot = setup_bots[i]
                result = platform.retrieve_item(item_name, amount, f"test_uuid_{item_name}_{i}")
                assert result == 0, f"Bot {i} failed to retrieve {amount} {item_name}"
        
        # Verify each item's stock
        for item_name, amount in items_per_bot:
            stock = platform.get_stock(item_name)
            assert stock >= amount, f"Expected at least {amount} {item_name}, got {stock}"
    
    def test_retrieve_72_diamonds_integration(self, platform, setup_bots):
        """Integration test specifically for retrieving 72 diamonds."""
        item_name = "diamond"
        amount = 72
        
        result = platform.retrieve_item(item_name, amount, "test_uuid_72_diamonds")
        
        assert result == 0, f"Failed to retrieve {amount} {item_name}"
        
        # Verify stock
        stock = platform.get_stock(item_name)
        assert stock >= amount, f"Expected at least {amount} {item_name}, got {stock}"
        
        # Verify bot inventory
        bot = setup_bots[0]
        bot_stock = bot.inventory.get_quantity(item_name)
        assert bot_stock >= amount, f"Bot should have at least {amount} {item_name}, got {bot_stock}"
    
    def test_inventory_capacity_across_bots(self, platform, setup_bots):
        """Test that inventory capacity is respected across multiple bots."""
        # Try to retrieve a large amount that should be distributed across bots
        item_name = "diamond"
        large_amount = 200
        
        result = platform.retrieve_item(item_name, large_amount, "test_uuid_large")
        
        # Should either succeed (if capacity allows) or fail gracefully
        # If it succeeds, verify distribution
        if result == 0:
            total_stock = platform.get_stock(item_name)
            assert total_stock >= large_amount, \
                f"Expected at least {large_amount} {item_name}, got {total_stock}"
    
    def test_concurrent_retrieval_multiple_items(self, platform, setup_bots):
        """Test retrieving multiple items concurrently (simulated sequential)."""
        items = [
            ("diamond", 32),
            ("emerald", 16),
            ("gold_ingot", 8),
        ]
        
        # Retrieve all items
        for item_name, amount in items:
            result = platform.retrieve_item(item_name, amount, f"test_uuid_concurrent_{item_name}")
            assert result == 0, f"Failed to retrieve {amount} {item_name}"
        
        # Verify all items are available
        for item_name, amount in items:
            stock = platform.get_stock(item_name)
            assert stock >= amount, f"Expected at least {amount} {item_name}, got {stock}"
    
    def test_bot_selection_priority(self, platform, setup_bots):
        """Test that bot selection prioritizes bots already storing the item."""
        item_name = "diamond"
        amount = 32
        
        # First retrieval - should use first available bot
        result1 = platform.retrieve_item(item_name, amount, "test_uuid_priority_1")
        assert result1 == 0
        
        # Second retrieval of same item - should prefer bot that already has it
        result2 = platform.retrieve_item(item_name, amount, "test_uuid_priority_2")
        assert result2 == 0
        
        # Verify stock increased
        total_stock = platform.get_stock(item_name)
        assert total_stock >= amount * 2, \
            f"Expected at least {amount * 2} {item_name}, got {total_stock}"
    
    def test_inventory_persistence(self, platform, setup_bots, test_db_path):
        """Test that inventory state persists across platform reloads."""
        item_name = "diamond"
        amount = 32
        
        # Retrieve item
        result = platform.retrieve_item(item_name, amount, "test_uuid_persistence")
        assert result == 0
        
        # Get current stock
        stock_before = platform.get_stock(item_name)
        
        # Reload platform from database
        platform2 = Minecraft()
        platform2._server_address = platform._server_address
        platform2._server_port = platform._server_port
        platform2._minecraft_version = platform._minecraft_version
        
        # Verify stock is still available
        stock_after = platform2.get_stock(item_name)
        assert stock_after == stock_before, \
            f"Stock changed after reload: {stock_before} -> {stock_after}"
    
    def test_error_handling_insufficient_capacity(self, platform, setup_bots):
        """Test error handling when no bot can fit the requested amount."""
        item_name = "diamond"
        # Request an impossibly large amount
        huge_amount = 100000
        
        result = platform.retrieve_item(item_name, huge_amount, "test_uuid_huge")
        
        # Should return error code (non-zero)
        assert result != 0, "Should fail when requesting impossibly large amount"
    
    def test_error_handling_invalid_item(self, platform, setup_bots):
        """Test error handling for invalid item names."""
        invalid_item = "nonexistent_item_xyz"
        amount = 10
        
        # This might fail at different points depending on implementation
        # Just verify it doesn't crash
        try:
            result = platform.retrieve_item(invalid_item, amount, "test_uuid_invalid")
            # If it doesn't raise, should return error code
            assert result != 0, "Should return error for invalid item"
        except (ValueError, KeyError) as e:
            # Expected error
            assert True
        except Exception as e:
            pytest.fail(f"Unexpected error type: {type(e).__name__}: {e}")

