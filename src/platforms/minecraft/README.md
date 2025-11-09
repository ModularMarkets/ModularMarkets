# Minecraft Platform

A platform implementation for ModularMarkets that enables automated trading of Minecraft items through a network of bot warehouses. This platform is designed to work with Minecraft servers (including The Pit and other custom servers) by managing item storage, delivery, and retrieval through automated bot accounts.

## Overview

The Minecraft platform provides:

- **Bot Network Management**: A distributed network of Minecraft bot accounts that act as warehouses for item storage
- **Item Trading**: Automated delivery and retrieval of items to/from players
- **Inventory Tracking**: Real-time inventory management across multiple bot warehouses
- **Database Persistence**: SQL-based storage for bot configurations and inventory state
- **Flexible Trading Modes**: Support for different trading methods (drop, chat, plugin)

## Architecture

### Core Components

1. **Minecraft Platform** (`Minecraft` class)
   - Main platform interface implementing the `Platform` abstract class
   - Manages bot network, item configuration, and trading operations
   - Handles configuration loading and database connections

2. **Minecraft Bot** (`MinecraftBot` class)
   - Individual bot account that acts as a warehouse
   - Implements the `Warehouse` interface for item storage and delivery
   - Manages its own inventory and can transfer items between warehouses

3. **Minecraft Bot Network** (`MinecraftBotNet` class)
   - Manages a collection of Minecraft bots as a storage network
   - Implements the `StorageNetwork` interface
   - Handles warehouse selection for optimal item storage/retrieval

### Design Principles

**IMPORTANT**: Platform-specific code should NEVER modify files in the general source directory (`src/`). All platform-specific models, database connections, utilities, and implementations must be contained within the platform's own directory structure (`src/platforms/minecraft/`).

This ensures:
- Clean separation of concerns
- No conflicts between different platform implementations
- Easier maintenance and testing
- Platform code can be developed independently

## Installation

### Prerequisites

- Python 3.12+
- Access to a Minecraft server (for online authentication) or offline mode support
- SQLite or PostgreSQL database (for bot network persistence)

### Using Nix (Recommended)

```bash
# Enter development environment with Minecraft platform
nix develop .#minecraft-only
```

### Using pip

1. Install core dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Install Minecraft platform dependencies:
   ```bash
   pip install -r src/platforms/minecraft/requirements.txt
   ```

3. Set up environment variables (optional):
   ```bash
   export MINECRAFT_DATABASE_URL="sqlite:///minecraft_network.db"
   export MINECRAFT_TRADING_MODE="drop"
   export MINECRAFT_SERVER_ADDRESS="localhost"
   export MINECRAFT_SERVER_PORT="25565"
   ```

## Configuration

The Minecraft platform uses YAML configuration files located in `src/platforms/minecraft/confs/`:

### config.yml

Main platform configuration file. Values can be overridden by environment variables.

```yaml
# Trading mode: 'drop', 'chat', or 'plugin'
trading_mode: drop

# Server connection settings (for drop & chat modes)
server_address: localhost
server_port: 25565
offline: false
```

**Environment Variable Overrides:**
- `MINECRAFT_TRADING_MODE`: Overrides `trading_mode`
- `MINECRAFT_SERVER_ADDRESS`: Overrides `server_address`
- `MINECRAFT_SERVER_PORT`: Overrides `server_port`
- `MINECRAFT_OFFLINE`: Overrides `offline` (set to 'true', '1', or 'yes')
- `MINECRAFT_DATABASE_URL`: Database connection URL (default: `sqlite:///minecraft_network.db`)

### items.yml

Defines all tradeable items on the platform.

```yaml
items:
  - name: diamond
    weight: 1
    info: {}  # NBT data for item identification (if needed)
  
  - name: emerald
    weight: 1
    info: {}
```

**Fields:**
- `name`: Item identifier (required)
- `weight`: Item weight for logistics calculations (required)
- `info`: Minecraft NBT data for item identification (optional, use `{}` for standard items)

**NBT Data Format:**
The `info` field should ONLY contain in-game NBT data relevant for identifying items in trading (e.g., custom names, lore, enchantments). It must follow the Minecraft NBT specification.

Example with custom NBT:
```yaml
- name: custom_diamond
  weight: 1
  info:
    display:
      Name: '{"text":"Premium Diamond","color":"gold"}'
      Lore:
        - '{"text":"A special diamond with custom properties"}'
```

See: https://minecraft.wiki/w/Item_format

### bots.yml

**WARNING**: This file contains passwords and should NOT be committed to version control!**

Defines Minecraft bot accounts that act as warehouses.

```yaml
bots:
  - username: warehouse1
    password: "change_me"
    auth: online
    bot_id: "warehouse-001"  # Optional, defaults to username
```

**Fields:**
- `username`: Bot's Minecraft username (required)
- `password`: Bot password (required, or use environment variable)
- `auth`: Authentication type - `online` (Mojang/Microsoft) or `offline` (required)
- `bot_id`: Optional unique identifier (defaults to username if not provided)

**Password via Environment Variable:**
Instead of storing passwords in `bots.yml`, you can use environment variables:
```bash
export MINECRAFT_BOT_PASSWORD_WAREHOUSE1="your_password_here"
```
The format is: `MINECRAFT_BOT_PASSWORD_{USERNAME}` (where USERNAME is uppercase).

## Usage

### Basic Setup

1. **Configure Items**: Edit `confs/items.yml` to define tradeable items
2. **Configure Bots**: Edit `confs/bots.yml` or set environment variables for bot passwords
3. **Configure Platform**: Edit `confs/config.yml` or set environment variables

### Creating a Platform Instance

```python
from src.platforms.minecraft import Minecraft

# Platform automatically loads configuration from confs/ directory
platform = Minecraft()

# Get list of available items
items = platform.get_item_list()
print(items)  # ['diamond', 'emerald', 'gold_ingot', ...]

# Get stock level for an item
stock = platform.get_stock("diamond")
print(f"Diamond stock: {stock}")

# Deliver items to a player
result = platform.deliver_item("diamond", 5, "player_uuid_here")
if result == 0:
    print("Delivery successful!")
else:
    print(f"Delivery failed with error code: {result}")

# Retrieve items from a player
result = platform.retrieve_item("emerald", 10, "player_uuid_here")
if result == 0:
    print("Retrieval successful!")
```

### Managing Bots

```python
# Create a new bot programmatically
bot = platform.create_bot(
    username="new_bot",
    password="password123",
    auth="offline",
    bot_id="custom_id"  # Optional
)

# Bot is automatically added to the network and saved to database
```

### Bot Network Operations

```python
# Access the bot network
network = platform._network

# Get total stock across all warehouses
total_stock = network.get_stock("diamond", cached=True)

# Find best warehouse for retrieving an item
warehouse = network.get_warehouse_for_retrieve("diamond", 10)

# Find best warehouse for storing an item
warehouse = network.get_warehouse_for_store("diamond", 50)

# Save network state to database
platform.save_network_to_sql()
```

## Trading Modes

The platform supports three trading modes:

1. **drop**: Items are dropped on the ground for players to pick up
2. **chat**: Items are traded via chat commands (requires server plugin/mod)
3. **plugin**: Items are managed through a server plugin API

**Note**: Trading mode implementations are currently in development. The platform structure is ready, but actual game interaction logic needs to be implemented.

## Database

The Minecraft platform uses a separate database from the main ModularMarkets database to store:

- **Bot Configurations**: Username, authentication type, trading mode
- **Bot Inventories**: Current inventory state for each bot
- **Network Configuration**: Network-level settings

### Database Models

- `MinecraftBotModel`: Stores bot configuration
- `MinecraftBotInventoryModel`: Stores inventory items per bot
- `MinecraftNetworkModel`: Stores network-level configuration

### Database URL

Set the `MINECRAFT_DATABASE_URL` environment variable to specify the database connection:
```bash
export MINECRAFT_DATABASE_URL="sqlite:///minecraft_network.db"  # SQLite (default)
# or
export MINECRAFT_DATABASE_URL="postgresql://user:pass@localhost/minecraft_db"  # PostgreSQL
```

## Testing

Unit tests for the Minecraft platform are located in `src/platforms/minecraft/test_platform.py`.

Run tests with:
```bash
# Run all Minecraft platform tests
pytest src/platforms/minecraft/test_platform.py

# Run with verbose output
pytest src/platforms/minecraft/test_platform.py -v

# Run specific test class
pytest src/platforms/minecraft/test_platform.py::TestMinecraftBot
```

### Test Coverage

The test suite covers:
- Bot initialization and configuration
- SQL persistence (save/load)
- Network operations
- Platform initialization and configuration loading
- Item list management
- Bot creation and management

## Development

### Project Structure

```
src/platforms/minecraft/
├── __init__.py              # Platform exports
├── platform.py              # Main platform implementation
├── models.py                # Database models
├── test_platform.py         # Unit tests
├── requirements.txt         # Platform-specific dependencies
├── confs/                   # Configuration files
│   ├── config.yml          # Platform configuration
│   ├── items.yml           # Item definitions
│   └── bots.yml            # Bot configurations (gitignored)
├── trading/                # Trading mode implementations
└── utils/                  # Platform-specific utilities
```

### Adding New Items

1. Edit `confs/items.yml`
2. Add item entry with name, weight, and optional NBT info
3. Restart the platform to load new items

### Adding New Bots

1. Edit `confs/bots.yml` or use environment variables
2. Restart the platform - bots are automatically created if they don't exist in the database
3. Or create bots programmatically using `platform.create_bot()`

### Implementing Trading Modes

Trading mode implementations should be added in the `trading/` directory. Each mode should handle:
- Item delivery to players
- Item retrieval from players
- Inventory synchronization
- Error handling and retry logic

### Database Migrations

The platform automatically creates database tables on first run. For schema changes:
1. Update models in `models.py`
2. The platform will attempt to create new tables/columns on startup
3. For production, use proper migration tools (Alembic, etc.)

## Security Considerations

1. **Bot Passwords**: Never commit `bots.yml` to version control. Use environment variables for production.
2. **Database Access**: Secure your database connection string. Use environment variables.
3. **Server Access**: Ensure bot accounts have appropriate permissions and are not admin accounts.
4. **Rate Limiting**: Implement rate limiting for trading operations to avoid server bans.

## Troubleshooting

### Bots Not Loading

- Check that `bots.yml` exists and is properly formatted
- Verify passwords are set (either in file or environment variables)
- Check database connection and permissions
- Review error messages in console output

### Items Not Found

- Verify `items.yml` is properly formatted
- Check that item names match exactly (case-sensitive)
- Ensure platform has been restarted after editing `items.yml`

### Database Errors

- Verify database URL is correct
- Check database file permissions (for SQLite)
- Ensure database user has CREATE TABLE permissions
- Review SQLAlchemy error messages

## License

This platform implementation follows the same license as the main ModularMarkets project.

## Contributing

When contributing to the Minecraft platform:

1. Keep all changes within `src/platforms/minecraft/`
2. Never modify files in the general `src/` directory
3. Add tests for new functionality in `test_platform.py`
4. Update this README for significant changes
5. Follow the existing code style and patterns

