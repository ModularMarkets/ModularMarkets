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


class MinecraftBot(Warehouse):
    """Minecraft bot that acts as a warehouse for item storage and delivery."""
    
    def __init__(self, username: str, password: str, uuid: str, auth: str, trading_mode: str, bot_id: Optional[str] = None):
        """
        Initialize a Minecraft bot.
        
        Args:
            username: Bot username
            password: Bot password
            uuid: Bot UUID
            auth: Authentication type ('online' or 'offline')
            trading_mode: Trading mode ('drop', 'chat', or 'plugin')
            bot_id: Unique bot identifier (defaults to username if not provided)
        """
        self.trading_mode: str = trading_mode
        self.username: str = username
        self.password: str = password
        self.uuid: str = uuid
        self.auth: str = auth
        self.bot_id: str = bot_id if bot_id else username
        # Required Warehouse attributes
        self.inventory: Optional[Inv] = None
        self.stored_item_types: List[str] = []
        # Optional database session for SQL persistence (set by network/platform)
        self._db_session: Optional[Any] = None
    
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
        # TODO: Implement actual delivery logic
        # After successful delivery, update inventory and save to SQL:
        #   result = <perform delivery>
        #   if result == 0:
        #       # Update inventory (remove item)
        #       if self.inventory and hasattr(self.inventory, 'remove_item'):
        #           self.inventory.remove_item(item_name, amount)
        #       # Save to SQL if db session is available
        #       if self._db_session:
        #           self.save_to_sql(self._db_session)
        #   return result
        pass
    
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
        
        Args:
            item_name: Name of the item to retrieve
            amount: Amount to retrieve
            uuid: User's UUID
            
        Returns:
            0 if success, non-zero error code if failure
        """
        # TODO: Implement actual retrieval logic
        # After successful retrieval, update inventory and save to SQL:
        #   result = <perform retrieval>
        #   if result == 0:
        #       # Update inventory (add item)
        #       if self.inventory and hasattr(self.inventory, 'add_item'):
        #           self.inventory.add_item(item_name, amount)
        #       # Update stored_item_types if needed
        #       if item_name not in self.stored_item_types:
        #           self.stored_item_types.append(item_name)
        #       # Save to SQL if db session is available
        #       if self._db_session:
        #           self.save_to_sql(self._db_session)
        #   return result
        pass
    
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
            bot_model.uuid = self.uuid
            bot_model.auth = self.auth
            bot_model.trading_mode = self.trading_mode
        else:
            # Create new bot
            bot_model = MinecraftBotModel(
                bot_id=self.bot_id,
                username=self.username,
                uuid=self.uuid,
                auth=self.auth,
                trading_mode=self.trading_mode
            )
            db.add(bot_model)
        
        # Save inventory state
        if self.inventory is not None and hasattr(self.inventory, 'items'):
            # Clear existing inventory entries for this bot
            db.query(MinecraftBotInventoryModel).filter(
                MinecraftBotInventoryModel.bot_id == self.bot_id
            ).delete()
            
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
            uuid=bot_model.uuid,
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
            # Note: This assumes inventory is a dict-like object
            # The actual implementation depends on the Inv class structure
            if bot.inventory is None:
                # Initialize inventory - this depends on the actual Inv implementation
                # For now, we'll store the data and let _update_inv handle it
                pass
            elif hasattr(bot.inventory, 'items'):
                bot.inventory.items = {inv.item_name: inv.quantity for inv in inv_models}
                bot.stored_item_types = [inv.item_name for inv in inv_models if inv.quantity > 0]
        
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
        
        Args:
            item_name: Name of the item
            cached: Whether to use cached data
            
        Returns:
            Total stock level across all warehouses, or -1 if invalid item
        """
        pass
    
    def get_warehouse_for_retrieve(self, item_name: str, amount: int) -> MinecraftBot:
        """
        Find which warehouse has the most of an item, and cache from it.
        
        Args:
            item_name: Name of the item
            amount: Amount to retrieve
            
        Returns:
            Warehouse to use for retrieval
        """
        pass
    
    def get_warehouse_for_store(self, item_name: str, amount: int) -> MinecraftBot:
        """
        Out of the warehouses that store each item, try to minimize the amount
        of items in each warehouse. Prefer warehouses that already have an item.
        One item should be per MinecraftBot.
        
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
                    self.warehouses.append(bot)
            else:
                print(f"Warning: Password not found for bot {bot_model.username}, skipping load")


class Minecraft(Platform):
    """Minecraft platform implementation for The Pit and other servers."""
    
    platform_name: str = "minecrap"
    
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
        
        # Load items from items.yml
        self._possible_items: List[Item] = self._load_items(config_dir)
        
        # Initialize database connection
        self._db = self._get_minecraft_db()
        
        # Initialize network - load from SQL if exists, otherwise create new
        self._network: Optional[MinecraftBotNet] = MinecraftBotNet()
        self._load_network_from_sql()
    
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
        
        Args:
            config_dir: Path to config directory (platforms/minecraft/confs/)
            
        Returns:
            Dictionary containing configuration values
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
            uuid: User's UUID
            
        Returns:
            0 if success, non-zero error code if failure
        """
        pass
    
    def retrieve_item(self, item_name: str, amount: int, uuid: str) -> int:
        """
        Gets itemName from UUID.
        Find which minecraftBot is best suited to storing an item, and then have it store the item.
        
        Args:
            item_name: Name of the item to retrieve
            amount: Amount to retrieve
            uuid: User's UUID
            
        Returns:
            0 if success, non-zero error code if failure
        """
        pass
    
    def get_stock(self, item_name: str) -> int:
        """
        Returns item stock.
        
        Args:
            item_name: Name of the item
            
        Returns:
            Current stock level
        """
        pass
    
    def create_bot(self, username: str, password: str, uuid: str, auth: str) -> MinecraftBot:
        """
        Create the bot, add it to the network, and save to SQL.
        
        Args:
            username: Bot username
            password: Bot password
            uuid: Bot UUID
            auth: Authentication type ('online' or 'offline')
            
        Returns:
            Created MinecraftBot instance
        """
        # Create bot with trading mode from platform config
        bot = MinecraftBot(
            username=username,
            password=password,
            uuid=uuid,
            auth=auth,
            trading_mode=self._trading_mode
        )
        
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

