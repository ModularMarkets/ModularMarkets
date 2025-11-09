"""
Unit tests for Market Maker App classes and functions.
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

from src.users.user import User
from src.merchant import Merchant
from src.shop import Shop
from src.algorithm import Algorithm, Result
from src.plugins.platform import Platform
from src.database import get_db, load_all


class TestUser:
    """Unit tests for User class."""
    
    def test_user_initialization(self):
        """Test User initialization with all parameters."""
        mock_db = Mock()
        user = User(
            username="testuser",
            display_name="Test User",
            balance=100.0,
            hashed_pass="hashed123",
            account_creation_time=1234567890,
            db=mock_db,
            role=10,
            linked_accounts={"Minecraft": "uuid123"}
        )
        
        assert user.username == "testuser"
        assert user.display_name == "Test User"
        assert user.balance == 100.0
        assert user.hashed_pass == "hashed123"
        assert user.account_creation_time == 1234567890
        assert user.role == 10
        assert user.linked_accounts == {"Minecraft": "uuid123"}
    
    def test_get_balance(self):
        """Test get_balance returns correct balance."""
        mock_db = Mock()
        user = User(
            username="testuser",
            display_name="Test",
            balance=50.5,
            hashed_pass="hash",
            account_creation_time=1234567890,
            db=mock_db
        )
        
        assert user.get_balance() == 50.5
    
    def test_set_balance(self):
        """Test set_balance updates balance correctly."""
        mock_db = Mock()
        user = User(
            username="testuser",
            display_name="Test",
            balance=50.0,
            hashed_pass="hash",
            account_creation_time=1234567890,
            db=mock_db
        )
        
        user.set_balance(75.0)
        assert user.get_balance() == 75.0
        assert user.balance == 75.0
    
    def test_save_new_user(self):
        """Test save creates new user in database."""
        mock_db = Mock()
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value.first.return_value = None
        
        user = User(
            username="newuser",
            display_name="New User",
            balance=100.0,
            hashed_pass="hash",
            account_creation_time=1234567890,
            db=mock_db
        )
        
        user.save()
        
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
    
    def test_save_existing_user(self):
        """Test save updates existing user in database."""
        mock_db = Mock()
        mock_user_model = Mock()
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value.first.return_value = mock_user_model
        
        user = User(
            username="existing",
            display_name="Existing User",
            balance=200.0,
            hashed_pass="hash",
            account_creation_time=1234567890,
            db=mock_db,
            role=10
        )
        
        user.save()
        
        assert mock_user_model.balance == 200.0
        assert mock_user_model.role == 10
        mock_db.commit.assert_called_once()


class TestMerchant:
    """Unit tests for Merchant class."""
    
    @pytest.fixture
    def mock_platform(self):
        """Create a mock platform."""
        platform = Mock(spec=Platform)
        platform.platform_name = "TestPlatform"
        platform.get_item_list.return_value = ["item1", "item2"]
        platform.deliver_item.return_value = 0
        platform.retrieve_item.return_value = 0
        platform.get_stock.return_value = 100
        return platform
    
    @pytest.fixture
    def mock_algorithm(self):
        """Create a mock algorithm."""
        algo = Mock(spec=Algorithm)
        algo.run.return_value = Result(new_buy=10.0, new_sell=12.0)
        return algo
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database."""
        db = Mock()
        db.add = Mock()
        db.commit = Mock()
        db.query = Mock()
        return db
    
    @pytest.fixture
    def mock_user(self, mock_db):
        """Create a mock user."""
        user = Mock(spec=User)
        user.username = "testuser"
        user.get_balance.return_value = 1000.0
        user.save = Mock()
        # Make set_balance call save() to simulate real behavior
        def set_balance_side_effect(new_balance):
            user.balance = new_balance
            user.save()
        user.set_balance = Mock(side_effect=set_balance_side_effect)
        user.linked_accounts = {"TestPlatform": "uuid123"}
        return user
    
    @pytest.fixture
    def merchant(self, mock_platform, mock_db, mock_algorithm):
        """Create a merchant instance for testing."""
        return Merchant(
            item="test_item",
            buy_price=10.0,
            sell_price=12.0,
            platform=mock_platform,
            db=mock_db,
            algo=mock_algorithm,
            buy_cap=100,
            sell_cap=50
        )
    
    def test_merchant_initialization(self, merchant):
        """Test Merchant initialization."""
        assert merchant.item == "test_item"
        assert merchant.buy_price == 10.0
        assert merchant.sell_price == 12.0
        assert merchant.buy_cap == 100
        assert merchant.sell_cap == 50
    
    def test_buy_success(self, merchant, mock_user, mock_platform):
        """Test successful buy transaction."""
        merchant.buy(5, mock_user)
        
        mock_platform.deliver_item.assert_called_once_with("test_item", 5, "uuid123")
        mock_user.set_balance.assert_called_once()
        mock_user.save.assert_called_once()
        merchant.my_db.add.assert_called_once()
        merchant.my_db.commit.assert_called()
    
    def test_buy_exceeds_cap(self, merchant, mock_user):
        """Test buy fails when quantity exceeds buy cap."""
        with pytest.raises(ValueError, match="exceeds buy cap"):
            merchant.buy(150, mock_user)
    
    def test_buy_insufficient_balance(self, merchant, mock_user):
        """Test buy fails with insufficient balance."""
        mock_user.get_balance.return_value = 10.0
        
        with pytest.raises(ValueError, match="Insufficient balance"):
            merchant.buy(5, mock_user)
    
    def test_buy_platform_failure(self, merchant, mock_user, mock_platform):
        """Test buy fails when platform delivery fails."""
        mock_platform.deliver_item.return_value = 1
        
        with pytest.raises(ValueError, match="Platform delivery failed"):
            merchant.buy(5, mock_user)
    
    def test_sell_success(self, merchant, mock_user, mock_platform):
        """Test successful sell transaction."""
        merchant.sell(3, mock_user)
        
        mock_platform.retrieve_item.assert_called_once_with("test_item", 3, "uuid123")
        mock_user.set_balance.assert_called_once()
        mock_user.save.assert_called_once()
        merchant.my_db.add.assert_called_once()
        merchant.my_db.commit.assert_called()
    
    def test_sell_exceeds_cap(self, merchant, mock_user):
        """Test sell fails when quantity exceeds sell cap."""
        with pytest.raises(ValueError, match="exceeds sell cap"):
            merchant.sell(100, mock_user)
    
    def test_sell_platform_failure(self, merchant, mock_user, mock_platform):
        """Test sell fails when platform retrieval fails."""
        mock_platform.retrieve_item.return_value = 1
        
        with pytest.raises(ValueError, match="Platform retrieval failed"):
            merchant.sell(3, mock_user)
    
    def test_update_prices_success(self, merchant, mock_platform, mock_algorithm):
        """Test successful price update."""
        merchant.update_prices()
        
        mock_platform.get_stock.assert_called_once_with("test_item")
        mock_algorithm.run.assert_called_once()
        assert merchant.buy_price == 10.0
        assert merchant.sell_price == 12.0
    
    def test_update_prices_invalid_item(self, merchant, mock_platform):
        """Test update_prices fails with invalid item."""
        mock_platform.get_stock.return_value = -1
        
        with pytest.raises(ValueError, match="Invalid item"):
            merchant.update_prices()
    
    def test_get_buy_cap(self, merchant):
        """Test get_buy_cap returns correct value."""
        assert merchant.get_buy_cap() == 100
    
    def test_set_buy_cap(self, merchant):
        """Test set_buy_cap updates value."""
        merchant.set_buy_cap(200)
        assert merchant.get_buy_cap() == 200
        assert merchant.buy_cap == 200
    
    def test_get_sell_cap(self, merchant):
        """Test get_sell_cap returns correct value."""
        assert merchant.get_sell_cap() == 50
    
    def test_set_sell_cap(self, merchant):
        """Test set_sell_cap updates value."""
        merchant.set_sell_cap(75)
        assert merchant.get_sell_cap() == 75
        assert merchant.sell_cap == 75
    
    def test_get_algo(self, merchant, mock_algorithm):
        """Test get_algo returns algorithm."""
        assert merchant.get_algo() == mock_algorithm
    
    def test_set_algo(self, merchant):
        """Test set_algo updates algorithm."""
        new_algo = Mock(spec=Algorithm)
        merchant.set_algo(new_algo)
        assert merchant.get_algo() == new_algo
        assert merchant.algo == new_algo


class TestShop:
    """Unit tests for Shop class."""
    
    @pytest.fixture
    def mock_platform(self):
        """Create a mock platform."""
        platform = Mock(spec=Platform)
        platform.get_item_list.return_value = ["item1", "item2", "item3"]
        return platform
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database."""
        db = Mock()
        db.add = Mock()
        db.commit = Mock()
        db.query = Mock()
        db.delete = Mock()
        return db
    
    @pytest.fixture
    def mock_algorithm(self):
        """Create a mock algorithm."""
        algo = Mock(spec=Algorithm)
        algo.algorithm_name = "test_algorithm"
        algo.get_config.return_value = {}
        return algo
    
    @pytest.fixture
    def shop(self, mock_platform, mock_db):
        """Create a shop instance for testing."""
        # Create a concrete shop class since Shop is abstract
        class ConcreteShop(Shop):
            pass
        
        shop_instance = ConcreteShop(mock_platform, mock_db)
        shop_instance.shop_id = "test_shop"  # Set shop_id so save_shop_to_sql() works
        return shop_instance
    
    def test_shop_initialization(self, shop, mock_platform, mock_db):
        """Test Shop initialization."""
        assert shop.my_platform == mock_platform
        assert shop.my_db == mock_db
        assert shop.merchants == {}
    
    def test_add_merchant_success(self, shop, mock_platform, mock_db, mock_algorithm):
        """Test successful merchant addition."""
        # Set up mock for shop save query (shop doesn't exist yet, so first() returns None)
        mock_shop_query = Mock()
        mock_shop_query.filter.return_value.first.return_value = None
        mock_db.query.return_value = mock_shop_query
        
        shop.add_merchant("item1", 100, mock_algorithm, 50, 30)
        
        assert "item1" in shop.merchants
        merchant = shop.merchants["item1"]
        assert merchant.item == "item1"
        assert merchant.buy_cap == 50
        assert merchant.sell_cap == 30
        # add is called twice: once for merchant, once for shop
        assert mock_db.add.call_count == 2
        # commit is called twice: once for merchant, once for shop save
        assert mock_db.commit.call_count == 2
    
    def test_add_merchant_item_not_available(self, shop, mock_platform, mock_algorithm):
        """Test add_merchant fails when item not on platform."""
        with pytest.raises(ValueError, match="not available on platform"):
            shop.add_merchant("nonexistent", 100, mock_algorithm, 50, 30)
    
    def test_add_merchant_already_exists(self, shop, mock_platform, mock_db, mock_algorithm):
        """Test add_merchant fails when merchant already exists."""
        shop.add_merchant("item1", 100, mock_algorithm, 50, 30)
        
        with pytest.raises(ValueError, match="already exists"):
            shop.add_merchant("item1", 100, mock_algorithm, 50, 30)
    
    def test_remove_merchant_success(self, shop, mock_platform, mock_db, mock_algorithm):
        """Test successful merchant removal."""
        shop.add_merchant("item1", 100, mock_algorithm, 50, 30)
        
        mock_query = Mock()
        mock_merchant_model = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value.first.return_value = mock_merchant_model
        
        shop.remove_merchant("item1")
        
        assert "item1" not in shop.merchants
        mock_db.delete.assert_called_once_with(mock_merchant_model)
        mock_db.commit.assert_called()
    
    def test_remove_merchant_not_found(self, shop):
        """Test remove_merchant fails when merchant doesn't exist."""
        with pytest.raises(ValueError, match="not found"):
            shop.remove_merchant("nonexistent")
    
    def test_get_merchant_exists(self, shop, mock_platform, mock_db, mock_algorithm):
        """Test get_merchant returns merchant when it exists."""
        shop.add_merchant("item1", 100, mock_algorithm, 50, 30)
        
        merchant = shop.get_merchant("item1")
        assert merchant is not None
        assert merchant.item == "item1"
    
    def test_get_merchant_not_found(self, shop):
        """Test get_merchant returns None when merchant doesn't exist."""
        merchant = shop.get_merchant("nonexistent")
        assert merchant is None


class TestAlgorithm:
    """Unit tests for Algorithm and Result classes."""
    
    def test_result_dataclass(self):
        """Test Result dataclass creation."""
        result = Result(new_buy=10.5, new_sell=12.5)
        
        assert result.new_buy == 10.5
        assert result.new_sell == 12.5
    
    def test_algorithm_is_abstract(self):
        """Test Algorithm is abstract and cannot be instantiated."""
        with pytest.raises(TypeError):
            Algorithm()


class TestDatabase:
    """Unit tests for database functions."""
    
    @patch('src.database.create_engine')
    @patch('src.database.sessionmaker')
    @patch('src.database.os.getenv')
    def test_get_db(self, mock_getenv, mock_sessionmaker, mock_create_engine):
        """Test get_db creates database session."""
        mock_getenv.return_value = "sqlite:///test.db"
        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine
        mock_session = Mock()
        mock_sessionmaker.return_value = mock_session
        
        db = get_db()
        
        mock_create_engine.assert_called_once_with("sqlite:///test.db")
        mock_sessionmaker.assert_called_once_with(bind=mock_engine)
        assert db == mock_session()
    
    def test_load_all_empty_database(self):
        """Test load_all with empty database."""
        mock_db = Mock()
        mock_db.query.return_value.all.return_value = []
        
        result = load_all(mock_db)
        
        assert result == {'users': {}, 'shops': {}}
    
    def test_load_all_with_users(self):
        """Test load_all loads users from database."""
        mock_db = Mock()
        
        mock_user_model = Mock()
        mock_user_model.username = "user1"
        mock_user_model.display_name = "User 1"
        mock_user_model.balance = 100.0
        mock_user_model.hashed_pass = "hash"
        mock_user_model.account_creation_time = 1234567890
        mock_user_model.role = 10
        mock_user_model.linked_accounts = {}
        
        # Mock user query
        mock_user_query = Mock()
        mock_user_query.all.return_value = [mock_user_model]
        
        # Mock shop query (return empty list)
        mock_shop_query = Mock()
        mock_shop_query.all.return_value = []
        
        # Mock merchant query (return empty list)
        mock_merchant_query = Mock()
        mock_merchant_query.all.return_value = []
        
        # Set up query to return different results based on model
        def query_side_effect(model):
            if model.__name__ == 'UserModel':
                return mock_user_query
            elif model.__name__ == 'ShopModel':
                return mock_shop_query
            elif model.__name__ == 'MerchantModel':
                return mock_merchant_query
            return Mock()
        
        mock_db.query.side_effect = query_side_effect
        
        result = load_all(mock_db)
        
        assert "user1" in result['users']
        user = result['users']["user1"]
        assert user.username == "user1"
        assert user.balance == 100.0
        assert user.role == 10

