"""
Unit tests for Minecraft platform implementation.
"""
import pytest
from unittest.mock import Mock, patch
import yaml

from .platform import MinecraftBot, MinecraftBotNet, Minecraft
from .models import MinecraftBotModel, MinecraftBotInventoryModel, MinecraftNetworkModel
from ..utils.logistics import Item


class TestMinecraftBot:
    """Unit tests for MinecraftBot class."""
    
    @pytest.fixture
    def bot(self):
        """Create a MinecraftBot instance for testing."""
        return MinecraftBot(
            username="testbot",
            password="testpass",
            auth="offline",
            trading_mode="drop"
        )
    
    def test_bot_initialization(self, bot):
        """Test MinecraftBot initialization."""
        assert bot.username == "testbot"
        assert bot.password == "testpass"
        assert bot.auth == "offline"
        assert bot.trading_mode == "drop"
        assert bot.bot_id == "testbot"  # Defaults to username
        assert bot.inventory is None
        assert bot.stored_item_types == []
        assert bot._db_session is None
    
    def test_bot_initialization_with_bot_id(self):
        """Test MinecraftBot initialization with custom bot_id."""
        bot = MinecraftBot(
            username="testbot",
            password="testpass",
            auth="online",
            trading_mode="chat",
            bot_id="custom_id"
        )
        assert bot.bot_id == "custom_id"
        assert bot.username == "testbot"
    
    def test_deliver_item_not_implemented(self, bot):
        """Test deliver_item is not yet implemented."""
        result = bot.deliver_item("diamond", 5, "uuid123")
        assert result is None  # Currently returns None (pass statement)
    
    def test_transfer_item_not_implemented(self, bot):
        """Test transfer_item is not yet implemented."""
        mock_warehouse = Mock()
        result = bot.transfer_item("diamond", 5, mock_warehouse)
        assert result is None  # Currently returns None (pass statement)
    
    def test_retrieve_item_not_implemented(self, bot):
        """Test retrieve_item is not yet implemented."""
        result = bot.retrieve_item("diamond", 5, "uuid123")
        assert result is None  # Currently returns None (pass statement)
    
    def test_get_stock_not_implemented(self, bot):
        """Test get_stock is not yet implemented."""
        result = bot.get_stock("diamond")
        assert result is None  # Currently returns None (pass statement)
    
    def test_update_inv_not_implemented(self, bot):
        """Test _update_inv is not yet implemented."""
        result = bot._update_inv()
        assert result is None  # Currently returns None (pass statement)
    
    def test_save_to_sql_new_bot(self, bot):
        """Test save_to_sql creates new bot in database."""
        mock_db = Mock()
        mock_query = Mock()
        mock_filter = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = None  # Bot doesn't exist
        mock_filter.delete.return_value = None
        
        bot.save_to_sql(mock_db)
        
        # Should add new bot model
        mock_db.add.assert_called()
        mock_db.commit.assert_called_once()
    
    def test_save_to_sql_existing_bot(self, bot):
        """Test save_to_sql updates existing bot in database."""
        mock_db = Mock()
        mock_bot_model = Mock()
        mock_query = Mock()
        mock_filter = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = mock_bot_model  # Bot exists
        mock_filter.delete.return_value = None
        
        bot.save_to_sql(mock_db)
        
        # Should update existing bot model
        assert mock_bot_model.username == "testbot"
        assert mock_bot_model.auth == "offline"
        assert mock_bot_model.trading_mode == "drop"
        mock_db.commit.assert_called_once()
    
    def test_save_to_sql_with_inventory(self, bot):
        """Test save_to_sql saves inventory state."""
        # Create mock inventory
        mock_inventory = Mock()
        mock_inventory.items = {"diamond": 10, "emerald": 5}
        bot.inventory = mock_inventory
        
        mock_db = Mock()
        mock_query = Mock()
        mock_filter = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = None  # Bot doesn't exist
        mock_filter.delete.return_value = None
        
        bot.save_to_sql(mock_db)
        
        # Should add inventory entries
        assert mock_db.add.call_count >= 3  # Bot + 2 inventory items
        mock_db.commit.assert_called_once()
    
    def test_load_from_sql_not_found(self):
        """Test load_from_sql returns None when bot not found."""
        mock_db = Mock()
        mock_query = Mock()
        mock_filter = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = None  # Bot not found
        
        result = MinecraftBot.load_from_sql(mock_db, "nonexistent", "password")
        assert result is None
    
    def test_load_from_sql_success(self):
        """Test load_from_sql loads bot from database."""
        # Create mock bot model
        mock_bot_model = Mock()
        mock_bot_model.bot_id = "testbot"
        mock_bot_model.username = "testbot"
        mock_bot_model.auth = "offline"
        mock_bot_model.trading_mode = "drop"
        
        # Create mock inventory models
        mock_inv_model1 = Mock()
        mock_inv_model1.item_name = "diamond"
        mock_inv_model1.quantity = 10
        mock_inv_model2 = Mock()
        mock_inv_model2.item_name = "emerald"
        mock_inv_model2.quantity = 5
        
        mock_db = Mock()
        mock_query = Mock()
        mock_filter = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        
        # First query returns bot model, second returns inventory
        def query_side_effect(model):
            if model == MinecraftBotModel:
                mock_filter.first.return_value = mock_bot_model
                return mock_query
            elif model == MinecraftBotInventoryModel:
                mock_filter.all.return_value = [mock_inv_model1, mock_inv_model2]
                return mock_query
            return mock_query
        
        mock_db.query.side_effect = query_side_effect
        
        bot = MinecraftBot.load_from_sql(mock_db, "testbot", "password")
        
        assert bot is not None
        assert bot.username == "testbot"
        assert bot.auth == "offline"
        assert bot.trading_mode == "drop"
        assert bot.bot_id == "testbot"


class TestMinecraftBotNet:
    """Unit tests for MinecraftBotNet class."""
    
    @pytest.fixture
    def network(self):
        """Create a MinecraftBotNet instance for testing."""
        return MinecraftBotNet()
    
    def test_network_initialization(self, network):
        """Test MinecraftBotNet initialization."""
        assert network.warehouses == []
    
    def test_get_stock_not_implemented(self, network):
        """Test get_stock is not yet implemented."""
        result = network.get_stock("diamond")
        assert result is None  # Currently returns None (pass statement)
    
    def test_get_warehouse_for_retrieve_not_implemented(self, network):
        """Test get_warehouse_for_retrieve is not yet implemented."""
        result = network.get_warehouse_for_retrieve("diamond", 5)
        assert result is None  # Currently returns None (pass statement)
    
    def test_get_warehouse_for_store_not_implemented(self, network):
        """Test get_warehouse_for_store is not yet implemented."""
        result = network.get_warehouse_for_store("diamond", 5)
        assert result is None  # Currently returns None (pass statement)
    
    def test_prep_warehouse_for_retrieve_not_implemented(self, network):
        """Test _prep_warehouse_for_retrieve is not yet implemented."""
        result = network._prep_warehouse_for_retrieve("diamond", 5)
        assert result is None  # Currently returns None (pass statement)
    
    def test_save_to_sql(self, network):
        """Test save_to_sql saves all bots and network config."""
        # Add bots to network
        bot1 = MinecraftBot("bot1", "pass1", "offline", "drop")
        bot2 = MinecraftBot("bot2", "pass2", "online", "chat")
        network.warehouses = [bot1, bot2]
        
        mock_db = Mock()
        mock_query = Mock()
        mock_filter = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = None  # Network doesn't exist
        
        network.save_to_sql(mock_db)
        
        # Should save both bots and network config
        # Each bot.save_to_sql() calls commit once, and network.save_to_sql() calls commit once
        # So with 2 bots: 2 commits from bots + 1 commit from network = 3 total commits
        assert mock_db.add.call_count >= 1  # At least network model
        assert mock_db.commit.call_count == 3  # 2 from bots + 1 from network
    
    def test_load_from_sql(self, network):
        """Test load_from_sql loads bots from database."""
        # Create mock bot models
        mock_bot_model1 = Mock()
        mock_bot_model1.bot_id = "bot1"
        mock_bot_model1.username = "bot1"
        mock_bot_model1.auth = "offline"
        mock_bot_model1.trading_mode = "drop"
        
        mock_bot_model2 = Mock()
        mock_bot_model2.bot_id = "bot2"
        mock_bot_model2.username = "bot2"
        mock_bot_model2.auth = "online"
        mock_bot_model2.trading_mode = "chat"
        
        mock_db = Mock()
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.all.return_value = [mock_bot_model1, mock_bot_model2]
        
        # Mock load_from_sql for individual bots
        def get_bot_password(username):
            return f"pass_{username}"
        
        with patch.object(MinecraftBot, 'load_from_sql') as mock_load:
            mock_bot1 = MinecraftBot("bot1", "pass_bot1", "offline", "drop", "bot1")
            mock_bot2 = MinecraftBot("bot2", "pass_bot2", "online", "chat", "bot2")
            
            def load_side_effect(db, bot_id, password):
                if bot_id == "bot1":
                    return mock_bot1
                elif bot_id == "bot2":
                    return mock_bot2
                return None
            
            mock_load.side_effect = load_side_effect
            
            network.load_from_sql(mock_db, get_bot_password)
            
            assert len(network.warehouses) == 2


class TestMinecraftPlatform:
    """Unit tests for Minecraft Platform class."""
    
    @pytest.fixture
    def temp_config_dir(self, tmp_path):
        """Create a temporary config directory with test files."""
        config_dir = tmp_path / "confs"
        config_dir.mkdir()
        
        # Create config.yml
        config_data = {
            'trading_mode': 'drop',
            'server_address': 'test.server.com',
            'server_port': 25565,
            'offline': False
        }
        with open(config_dir / 'config.yml', 'w') as f:
            yaml.dump(config_data, f)
        
        # Create items.yml
        items_data = {
            'items': [
                {'name': 'diamond', 'weight': 1, 'info': {}},
                {'name': 'emerald', 'weight': 1, 'info': {}},
                {'name': 'gold_ingot', 'weight': 1, 'info': {}}
            ]
        }
        with open(config_dir / 'items.yml', 'w') as f:
            yaml.dump(items_data, f)
        
        # Create bots.yml
        bots_data = {
            'bots': [
                {'username': 'testbot1', 'password': 'pass1', 'auth': 'offline', 'bot_id': 'bot1'},
                {'username': 'testbot2', 'auth': 'online', 'bot_id': 'bot2'}
            ]
        }
        with open(config_dir / 'bots.yml', 'w') as f:
            yaml.dump(bots_data, f)
        
        return config_dir
    
    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        mock_db = Mock()
        mock_query = Mock()
        mock_filter = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_query.count.return_value = 0  # No existing bots
        mock_filter.first.return_value = None
        mock_filter.all.return_value = []
        mock_db.add = Mock()
        mock_db.commit = Mock()
        mock_db.rollback = Mock()
        return mock_db
    
    @patch('src.platforms.minecraft.platform.create_engine')
    @patch('src.platforms.minecraft.platform.sessionmaker')
    @patch('src.platforms.minecraft.platform.os.getenv')
    @patch('src.platforms.minecraft.platform.Path')
    def test_platform_initialization(
        self, mock_path, mock_getenv, mock_sessionmaker, mock_create_engine, temp_config_dir
    ):
        """Test Minecraft platform initialization."""
        # Mock Path to return our temp config dir
        mock_path_instance = Mock()
        mock_path_instance.parent = Mock()
        mock_path_instance.parent.__truediv__ = Mock(return_value=temp_config_dir)
        mock_path.return_value = mock_path_instance
        
        # Mock environment variables
        mock_getenv.side_effect = lambda key, default=None: default
        
        # Mock database setup
        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine
        mock_session = Mock()
        mock_sessionmaker.return_value = mock_session
        mock_db = Mock()
        mock_query = Mock()
        mock_filter = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_query.count.return_value = 0
        mock_filter.first.return_value = None
        mock_filter.all.return_value = []
        mock_db.add = Mock()
        mock_db.commit = Mock()
        mock_session.return_value = mock_db
        
        platform = Minecraft()
        
        assert platform._trading_mode == 'drop'
        assert platform._server_address == 'test.server.com'
        assert platform._server_port == 25565
        assert len(platform._possible_items) == 3
        assert platform._network is not None
    
    @patch('src.platforms.minecraft.platform.os.getenv')
    def test_get_bot_password(self, mock_getenv):
        """Test _get_bot_password retrieves password from env."""
        mock_getenv.return_value = "test_password"
        
        # We need to create a minimal platform instance
        # Since __init__ does a lot, we'll test the method directly
        platform = Mock(spec=Minecraft)
        platform._get_bot_password = Minecraft._get_bot_password.__get__(platform, Minecraft)
        
        password = platform._get_bot_password("testbot")
        
        mock_getenv.assert_called_once_with('MINECRAFT_BOT_PASSWORD_TESTBOT')
        assert password == "test_password"
    
    def test_load_config_file_exists(self, temp_config_dir):
        """Test _load_config loads from existing config file."""
        platform = Mock(spec=Minecraft)
        platform._load_config = Minecraft._load_config.__get__(platform, Minecraft)
        
        config = platform._load_config(temp_config_dir)
        
        assert config['trading_mode'] == 'drop'
        assert config['server_address'] == 'test.server.com'
        assert config['server_port'] == 25565
    
    def test_load_config_file_not_exists(self, tmp_path):
        """Test _load_config returns empty dict when file doesn't exist."""
        platform = Mock(spec=Minecraft)
        platform._load_config = Minecraft._load_config.__get__(platform, Minecraft)
        
        config = platform._load_config(tmp_path)
        
        assert config == {}
    
    def test_load_items(self, temp_config_dir):
        """Test _load_items loads items from items.yml."""
        platform = Mock(spec=Minecraft)
        platform._load_items = Minecraft._load_items.__get__(platform, Minecraft)
        
        items = platform._load_items(temp_config_dir)
        
        assert len(items) == 3
        assert items[0].item_name == 'diamond'
        assert items[1].item_name == 'emerald'
        assert items[2].item_name == 'gold_ingot'
        assert all(item.item_weight == 1 for item in items)
    
    def test_load_items_file_not_exists(self, tmp_path):
        """Test _load_items returns empty list when file doesn't exist."""
        platform = Mock(spec=Minecraft)
        platform._load_items = Minecraft._load_items.__get__(platform, Minecraft)
        
        items = platform._load_items(tmp_path)
        
        assert items == []
    
    @patch('src.platforms.minecraft.platform.MinecraftBot')
    def test_load_bots_from_config(self, mock_bot_class, temp_config_dir, mock_db_session):
        """Test _load_bots_from_config loads bots from bots.yml."""
        # Mock bot creation
        mock_bot = Mock()
        mock_bot_class.return_value = mock_bot
        
        platform = Mock(spec=Minecraft)
        platform._db = mock_db_session
        # Mock _get_bot_password to return None for bot2 (no password available)
        # This tests that bot2 is skipped when no password is found
        def get_bot_password_side_effect(username):
            if username == "testbot2":
                return None  # No password available for bot2
            return "env_pass"  # Password available for other bots
        platform._get_bot_password = Mock(side_effect=get_bot_password_side_effect)
        platform.create_bot = Mock(return_value=mock_bot)
        platform._load_bots_from_config = Minecraft._load_bots_from_config.__get__(platform, Minecraft)
        
        platform._load_bots_from_config(temp_config_dir)
        
        # Should create bot1 (has password in config) and skip bot2 (no password)
        assert platform.create_bot.call_count == 1
    
    def test_load_bots_from_config_file_not_exists(self, tmp_path, mock_db_session):
        """Test _load_bots_from_config handles missing file gracefully."""
        platform = Mock(spec=Minecraft)
        platform._db = mock_db_session
        platform._load_bots_from_config = Minecraft._load_bots_from_config.__get__(platform, Minecraft)
        
        # Should not raise exception
        platform._load_bots_from_config(tmp_path)
    
    def test_get_item_list(self):
        """Test get_item_list returns list of item names."""
        platform = Mock(spec=Minecraft)
        item1 = Item()
        item1.item_name = "diamond"
        item2 = Item()
        item2.item_name = "emerald"
        platform._possible_items = [item1, item2]
        platform.get_item_list = Minecraft.get_item_list.__get__(platform, Minecraft)
        
        result = platform.get_item_list()
        
        assert result == ["diamond", "emerald"]
    
    def test_deliver_item_not_implemented(self):
        """Test deliver_item is not yet fully implemented."""
        platform = Mock(spec=Minecraft)
        platform._network = Mock()
        platform.deliver_item = Minecraft.deliver_item.__get__(platform, Minecraft)
        
        result = platform.deliver_item("diamond", 5, "uuid123")
        
        assert result == 0  # Currently returns dummy value
    
    def test_retrieve_item_not_implemented(self):
        """Test retrieve_item is not yet fully implemented."""
        platform = Mock(spec=Minecraft)
        platform._network = Mock()
        platform.retrieve_item = Minecraft.retrieve_item.__get__(platform, Minecraft)
        
        result = platform.retrieve_item("diamond", 5, "uuid123")
        
        assert result == 0  # Currently returns dummy value
    
    def test_get_stock_not_implemented(self):
        """Test get_stock is not yet fully implemented."""
        platform = Mock(spec=Minecraft)
        platform._network = Mock()
        platform.get_stock = Minecraft.get_stock.__get__(platform, Minecraft)
        
        result = platform.get_stock("diamond")
        
        assert result == 0  # Currently returns dummy value
    
    def test_create_bot(self, mock_db_session):
        """Test create_bot creates and saves bot."""
        platform = Mock(spec=Minecraft)
        platform._trading_mode = "drop"
        platform._db = mock_db_session
        platform._network = Mock()
        platform._network.warehouses = []
        platform.create_bot = Minecraft.create_bot.__get__(platform, Minecraft)
        
        bot = platform.create_bot("testbot", "password", "offline", "bot_id_1")
        
        assert isinstance(bot, MinecraftBot)
        assert bot.username == "testbot"
        assert bot.auth == "offline"
        assert bot.trading_mode == "drop"
        assert bot.bot_id == "bot_id_1"
        assert bot in platform._network.warehouses
        mock_db_session.commit.assert_called()
    
    def test_create_bot_default_bot_id(self, mock_db_session):
        """Test create_bot uses username as bot_id when not provided."""
        platform = Mock(spec=Minecraft)
        platform._trading_mode = "drop"
        platform._db = mock_db_session
        platform._network = Mock()
        platform._network.warehouses = []
        platform.create_bot = Minecraft.create_bot.__get__(platform, Minecraft)
        
        bot = platform.create_bot("testbot", "password", "offline")
        
        assert bot.bot_id == "testbot"

