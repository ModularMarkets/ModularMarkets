"""
Integration tests for the Market Maker App database persistence system.
Tests the full save/load cycle to ensure all data is properly persisted and restored.
"""
import pytest
import os
import tempfile
from datetime import datetime

from src.database import get_db, load_all
from src.users.user import User
from src.shop import Shop
from src.merchant import Merchant
from src.platforms.minecraft import Minecraft
from src.algorithm import Algorithm, Result


class StubAlgorithm(Algorithm):
    """Simple stub algorithm for testing."""
    
    def __init__(self, multiplier: float = 1.0):
        self.multiplier = multiplier
    
    @property
    def algorithm_name(self) -> str:
        return "stub_test"
    
    def run(self, buy_price: float, sell_price: float, stock: int, past_transactions) -> Result:
        """Simple algorithm that adjusts prices based on multiplier."""
        return Result(
            new_buy=buy_price * self.multiplier,
            new_sell=sell_price * self.multiplier
        )
    
    def get_config(self) -> dict:
        """Get algorithm configuration."""
        return {"multiplier": self.multiplier}
    
    def set_config(self, config: dict) -> None:
        """Set algorithm configuration."""
        self.multiplier = config.get("multiplier", 1.0)


class TestDatabaseIntegration:
    """Integration tests for database save/load functionality."""
    
    @pytest.fixture(autouse=True)
    def register_test_algorithm(self):
        """Register the test algorithm in the registry before each test."""
        from src.database import ALGORITHM_REGISTRY
        # Register the test algorithm
        ALGORITHM_REGISTRY["stub_test"] = StubAlgorithm
        yield
        # Cleanup: remove test algorithm after test
        if "stub_test" in ALGORITHM_REGISTRY:
            del ALGORITHM_REGISTRY["stub_test"]
    
    @pytest.fixture
    def test_db_path(self):
        """Create a temporary database file for testing."""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        yield path
        # Cleanup
        if os.path.exists(path):
            os.remove(path)
    
    @pytest.fixture
    def test_db(self, test_db_path, monkeypatch):
        """Create a test database session."""
        # Set the database URL to use the test database
        monkeypatch.setenv('DATABASE_URL', f'sqlite:///{test_db_path}')
        db = get_db()
        yield db
        db.close()
    
    def test_initialize_empty_database(self, test_db):
        """Test that we can initialize and load from an empty database."""
        state = load_all(test_db)
        
        assert 'users' in state
        assert 'shops' in state
        assert len(state['users']) == 0
        assert len(state['shops']) == 0
    
    def test_save_and_load_user(self, test_db):
        """Test saving and loading a user."""
        # Create and save a user
        user = User(
            username="testuser",
            display_name="Test User",
            balance=100.5,
            hashed_pass="hashed_password_123",
            account_creation_time=1234567890,
            db=test_db,
            role=10,
            linked_accounts={"Minecraft": "uuid-123-456"}
        )
        user.save()
        
        # Load from database
        state = load_all(test_db)
        
        # Verify user was loaded
        assert "testuser" in state['users']
        loaded_user = state['users']["testuser"]
        assert loaded_user.username == "testuser"
        assert loaded_user.display_name == "Test User"
        assert loaded_user.balance == 100.5
        assert loaded_user.hashed_pass == "hashed_password_123"
        assert loaded_user.account_creation_time == 1234567890
        assert loaded_user.role == 10
        assert loaded_user.linked_accounts == {"Minecraft": "uuid-123-456"}
    
    def test_save_and_load_multiple_users(self, test_db):
        """Test saving and loading multiple users."""
        # Create multiple users
        users_data = [
            ("user1", "User One", 50.0, 10),
            ("user2", "User Two", 200.0, 10),
            ("admin", "Admin User", 1000.0, 100),
        ]
        
        for username, display_name, balance, role in users_data:
            user = User(
                username=username,
                display_name=display_name,
                balance=balance,
                hashed_pass=f"hash_{username}",
                account_creation_time=1234567890,
                db=test_db,
                role=role
            )
            user.save()
        
        # Load from database
        state = load_all(test_db)
        
        # Verify all users were loaded
        assert len(state['users']) == 3
        assert state['users']["user1"].balance == 50.0
        assert state['users']["user2"].balance == 200.0
        assert state['users']["admin"].balance == 1000.0
        assert state['users']["admin"].role == 100
    
    def test_save_and_load_shop(self, test_db):
        """Test saving and loading a shop with platform."""
        # Create platform (new Minecraft class loads config from env/config files)
        platform = Minecraft()
        
        # Create shop
        shop = Shop(platform, test_db)
        shop.shop_id = "test_shop_1"
        shop.platform_type = "Minecraft"
        shop.save_shop_to_sql()
        
        # Load from database
        state = load_all(test_db)
        
        # Verify shop was loaded
        assert "test_shop_1" in state['shops']
        loaded_shop = state['shops']["test_shop_1"]
        assert loaded_shop.shop_id == "test_shop_1"
        assert loaded_shop.platform_type == "Minecraft"
        assert isinstance(loaded_shop.my_platform, Minecraft)
        # New Minecraft class loads config from env/config files, not stored attributes
    
    def test_save_and_load_merchant(self, test_db):
        """Test saving and loading a merchant."""
        # Create platform and shop
        platform = Minecraft()
        shop = Shop(platform, test_db)
        shop.shop_id = "test_shop_1"
        shop.platform_type = "Minecraft"
        shop.save_shop_to_sql()
        
        # Create algorithm
        algo = StubAlgorithm(multiplier=1.1)
        
        # Create merchant via shop
        shop.add_merchant("diamond", 100, algo, buy_cap=50, sell_cap=30)
        
        # Load from database
        state = load_all(test_db)
        
        # Verify shop and merchant were loaded
        assert "test_shop_1" in state['shops']
        loaded_shop = state['shops']["test_shop_1"]
        assert "diamond" in loaded_shop.merchants
        
        loaded_merchant = loaded_shop.merchants["diamond"]
        assert loaded_merchant.item == "diamond"
        assert loaded_merchant.buy_price == 95.0  # 100 * 0.95
        assert loaded_merchant.sell_price == 105.0  # 100 * 1.05
        assert loaded_merchant.buy_cap == 50
        assert loaded_merchant.sell_cap == 30
        assert isinstance(loaded_merchant.algo, Algorithm)
    
    def test_save_and_load_complete_system(self, test_db):
        """Test saving and loading a complete system with users, shops, and merchants."""
        # Create users
        user1 = User(
            username="trader1",
            display_name="Trader One",
            balance=500.0,
            hashed_pass="hash1",
            account_creation_time=1234567890,
            db=test_db,
            role=10,
            linked_accounts={"Minecraft": "uuid-111"}
        )
        user1.save()
        
        user2 = User(
            username="trader2",
            display_name="Trader Two",
            balance=750.0,
            hashed_pass="hash2",
            account_creation_time=1234567890,
            db=test_db,
            role=10,
            linked_accounts={"Minecraft": "uuid-222"}
        )
        user2.save()
        
        # Create shop with platform
        platform = Minecraft()
        shop = Shop(platform, test_db)
        shop.shop_id = "main_shop"
        shop.platform_type = "Minecraft"
        shop.save_shop_to_sql()
        
        # Create merchants
        algo1 = StubAlgorithm(multiplier=1.05)
        algo2 = StubAlgorithm(multiplier=0.95)
        
        shop.add_merchant("diamond", 100, algo1, buy_cap=100, sell_cap=50)
        shop.add_merchant("gold_ingot", 50, algo2, buy_cap=200, sell_cap=100)
        
        # Perform some transactions
        merchant1 = shop.get_merchant("diamond")
        merchant2 = shop.get_merchant("gold_ingot")
        
        # User1 buys diamond (5 items at 95.0 each = 475.0, within 500.0 balance)
        merchant1.buy(5, user1)
        
        # User2 sells gold_ingot
        merchant2.sell(5, user2)
        
        # Load everything from database
        state = load_all(test_db)
        
        # Verify users
        assert len(state['users']) == 2
        loaded_user1 = state['users']["trader1"]
        loaded_user2 = state['users']["trader2"]
        
        # User1 should have less balance (bought diamonds)
        assert loaded_user1.balance < 500.0
        # User2 should have more balance (sold gold)
        assert loaded_user2.balance > 750.0
        
        # Verify shop
        assert "main_shop" in state['shops']
        loaded_shop = state['shops']["main_shop"]
        
        # Verify merchants
        assert "diamond" in loaded_shop.merchants
        assert "gold_ingot" in loaded_shop.merchants
        
        loaded_merchant1 = loaded_shop.merchants["diamond"]
        loaded_merchant2 = loaded_shop.merchants["gold_ingot"]
        
        # Verify merchant data
        assert loaded_merchant1.item == "diamond"
        assert loaded_merchant1.buy_cap == 100
        assert loaded_merchant1.sell_cap == 50
        
        assert loaded_merchant2.item == "gold_ingot"
        assert loaded_merchant2.buy_cap == 200
        assert loaded_merchant2.sell_cap == 100
        
        # Verify prices were updated (algorithm ran)
        # Prices should have changed from initial values due to algorithm
        assert loaded_merchant1.buy_price != 95.0 or loaded_merchant1.sell_price != 105.0
        assert loaded_merchant2.buy_price != 47.5 or loaded_merchant2.sell_price != 52.5
    
    def test_user_balance_persistence(self, test_db):
        """Test that user balance changes are persisted correctly."""
        # Create user
        user = User(
            username="balance_test",
            display_name="Balance Test",
            balance=1000.0,
            hashed_pass="hash",
            account_creation_time=1234567890,
            db=test_db,
            role=10
        )
        user.save()
        
        # Change balance
        user.set_balance(500.0)
        
        # Load from database
        state = load_all(test_db)
        loaded_user = state['users']["balance_test"]
        
        assert loaded_user.balance == 500.0
    
    def test_merchant_price_persistence(self, test_db):
        """Test that merchant price changes are persisted correctly."""
        # Create shop and merchant
        platform = Minecraft()
        shop = Shop(platform, test_db)
        shop.shop_id = "price_test_shop"
        shop.platform_type = "Minecraft"
        shop.save_shop_to_sql()
        
        algo = StubAlgorithm(multiplier=1.0)
        shop.add_merchant("emerald", 100, algo, buy_cap=50, sell_cap=50)
        
        # Get merchant and update prices
        merchant = shop.get_merchant("emerald")
        initial_buy = merchant.buy_price
        initial_sell = merchant.sell_price
        
        # Update prices (this should save automatically)
        merchant.update_prices()
        
        # Load from database
        state = load_all(test_db)
        loaded_shop = state['shops']["price_test_shop"]
        loaded_merchant = loaded_shop.merchants["emerald"]
        
        # Prices should be updated (algorithm ran)
        assert loaded_merchant.buy_price == merchant.buy_price
        assert loaded_merchant.sell_price == merchant.sell_price
    
    def test_merchant_cap_persistence(self, test_db):
        """Test that merchant cap changes are persisted correctly."""
        # Create shop and merchant
        platform = Minecraft()
        shop = Shop(platform, test_db)
        shop.shop_id = "cap_test_shop"
        shop.platform_type = "Minecraft"
        shop.save_shop_to_sql()
        
        algo = StubAlgorithm(multiplier=1.0)
        shop.add_merchant("iron_ingot", 50, algo, buy_cap=100, sell_cap=50)
        
        # Get merchant and change caps
        merchant = shop.get_merchant("iron_ingot")
        merchant.set_buy_cap(200)
        merchant.set_sell_cap(100)
        
        # Load from database
        state = load_all(test_db)
        loaded_shop = state['shops']["cap_test_shop"]
        loaded_merchant = loaded_shop.merchants["iron_ingot"]
        
        assert loaded_merchant.buy_cap == 200
        assert loaded_merchant.sell_cap == 100
    
    def test_transaction_persistence(self, test_db):
        """Test that transactions are saved and can be queried."""
        # Create user, shop, and merchant
        user = User(
            username="txn_user",
            display_name="Txn User",
            balance=1000.0,
            hashed_pass="hash",
            account_creation_time=1234567890,
            db=test_db,
            role=10,
            linked_accounts={"Minecraft": "uuid-txn"}
        )
        user.save()
        
        platform = Minecraft()
        shop = Shop(platform, test_db)
        shop.shop_id = "txn_shop"
        shop.platform_type = "Minecraft"
        shop.save_shop_to_sql()
        
        algo = StubAlgorithm(multiplier=1.0)
        shop.add_merchant("diamond", 100, algo, buy_cap=100, sell_cap=100)
        
        merchant = shop.get_merchant("diamond")
        
        # Perform transactions
        merchant.buy(5, user)
        merchant.sell(2, user)
        
        # Query transactions from database
        from src.models import TransactionModel
        transactions = test_db.query(TransactionModel).filter(
            TransactionModel.user_id == "txn_user"
        ).all()
        
        assert len(transactions) == 2
        
        # Verify transaction details
        buy_txn = next(t for t in transactions if t.type == "buy")
        sell_txn = next(t for t in transactions if t.type == "sell")
        
        assert buy_txn.item_name == "diamond"
        assert buy_txn.quantity == 5
        assert buy_txn.user_id == "txn_user"
        
        assert sell_txn.item_name == "diamond"
        assert sell_txn.quantity == 2
        assert sell_txn.user_id == "txn_user"
    
    def test_algorithm_persistence(self, test_db):
        """Test that algorithm type and config are saved and loaded correctly."""
        # Create shop and merchant with algorithm
        platform = Minecraft()
        shop = Shop(platform, test_db)
        shop.shop_id = "algo_test_shop"
        shop.platform_type = "Minecraft"
        shop.save_shop_to_sql()
        
        # Create algorithm with specific config
        algo = StubAlgorithm(multiplier=1.5)
        shop.add_merchant("emerald", 100, algo, buy_cap=50, sell_cap=50)
        
        # Verify algorithm was saved in database
        from src.models import MerchantModel
        merchant_model = test_db.query(MerchantModel).filter(
            MerchantModel.item == "emerald"
        ).first()
        
        assert merchant_model.algorithm_type == "stub_test"
        assert merchant_model.algorithm_config == {"multiplier": 1.5}
        
        # Load from database
        state = load_all(test_db)
        loaded_shop = state['shops']["algo_test_shop"]
        loaded_merchant = loaded_shop.merchants["emerald"]
        
        # Verify algorithm was loaded correctly
        assert loaded_merchant.algo.algorithm_name == "stub_test"
        assert loaded_merchant.algo.get_config() == {"multiplier": 1.5}
        assert loaded_merchant.algo.multiplier == 1.5
    
    def test_algorithm_swap_persistence(self, test_db):
        """Test that swapping algorithms persists correctly."""
        # Create shop and merchant
        platform = Minecraft()
        shop = Shop(platform, test_db)
        shop.shop_id = "swap_test_shop"
        shop.platform_type = "Minecraft"
        shop.save_shop_to_sql()
        
        # Create initial algorithm
        algo1 = StubAlgorithm(multiplier=1.0)
        shop.add_merchant("gold_ingot", 50, algo1, buy_cap=100, sell_cap=100)
        
        merchant = shop.get_merchant("gold_ingot")
        assert merchant.algo.multiplier == 1.0
        
        # Swap to different algorithm
        algo2 = StubAlgorithm(multiplier=2.0)
        merchant.set_algo(algo2)
        
        # Verify algorithm was saved
        from src.models import MerchantModel
        merchant_model = test_db.query(MerchantModel).filter(
            MerchantModel.item == "gold_ingot"
        ).first()
        assert merchant_model.algorithm_type == "stub_test"
        assert merchant_model.algorithm_config == {"multiplier": 2.0}
        
        # Load from database and verify
        state = load_all(test_db)
        loaded_shop = state['shops']["swap_test_shop"]
        loaded_merchant = loaded_shop.merchants["gold_ingot"]
        
        assert loaded_merchant.algo.algorithm_name == "stub_test"
        assert loaded_merchant.algo.multiplier == 2.0
        assert loaded_merchant.algo.get_config() == {"multiplier": 2.0}
    
    def test_algorithm_config_update_persistence(self, test_db):
        """Test that algorithm config changes persist when merchant is saved."""
        # Create shop and merchant
        platform = Minecraft()
        shop = Shop(platform, test_db)
        shop.shop_id = "config_test_shop"
        shop.platform_type = "Minecraft"
        shop.save_shop_to_sql()
        
        algo = StubAlgorithm(multiplier=1.0)
        shop.add_merchant("iron_ingot", 30, algo, buy_cap=200, sell_cap=100)
        
        merchant = shop.get_merchant("iron_ingot")
        
        # Change algorithm config
        merchant.algo.multiplier = 1.25
        # Trigger save by updating prices (which calls save_merchant_to_sql)
        merchant.update_prices()
        
        # Verify config was saved
        from src.models import MerchantModel
        merchant_model = test_db.query(MerchantModel).filter(
            MerchantModel.item == "iron_ingot"
        ).first()
        assert merchant_model.algorithm_config == {"multiplier": 1.25}
        
        # Load and verify
        state = load_all(test_db)
        loaded_shop = state['shops']["config_test_shop"]
        loaded_merchant = loaded_shop.merchants["iron_ingot"]
        
        assert loaded_merchant.algo.multiplier == 1.25
    
    def test_algorithm_missing_error(self, test_db):
        """Test that loading fails when algorithm is not in registry."""
        # Create shop and merchant with algorithm
        platform = Minecraft()
        shop = Shop(platform, test_db)
        shop.shop_id = "error_test_shop"
        shop.platform_type = "Minecraft"
        shop.save_shop_to_sql()
        
        algo = StubAlgorithm(multiplier=1.0)
        shop.add_merchant("diamond", 100, algo, buy_cap=50, sell_cap=50)
        
        # Manually change algorithm_type in database to non-existent algorithm
        from src.models import MerchantModel
        merchant_model = test_db.query(MerchantModel).filter(
            MerchantModel.item == "diamond"
        ).first()
        merchant_model.algorithm_type = "nonexistent_algorithm"
        test_db.commit()
        
        # Try to load - should raise error
        with pytest.raises(ValueError, match="Algorithm 'nonexistent_algorithm' not found"):
            load_all(test_db)

