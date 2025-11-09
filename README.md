# ModularMarkets

A market making system that allows hosting websites for buying and selling non-liquid commodities across various platforms (games, services, IRL items).

## Project Structure

```
src/
├── __init__.py
├── algorithm.py         # Algorithm interface and Result class
├── database.py         # Database connection and initialization functions
├── merchant.py         # Merchant class for item trading
├── models.py           # SQLAlchemy database models
├── shop.py             # Shop interface for managing merchants
├── plugins/
│   ├── __init__.py
│   ├── minecraft.py    # Minecraft platform implementation
│   └── platform.py     # Platform abstract base class
└── users/
    └── user.py         # User class for account management
```

## Core Classes

### User
Manages user accounts, authentication, balances, roles, and linked accounts.

### Merchant
Handles individual item trading with buy/sell operations, price caps, and price updates via algorithms.

### Shop
Manages collections of merchants and provides interface for merchant operations.

### Platform (Abstract)
Interface for external platforms (games, services) that provide items/services.

### Algorithm (Abstract)
Interface for market making algorithms that calculate buy/sell prices.

## Required Libraries

See `requirements.txt` for a list of dependencies. Key dependencies include:

- **Database**: SQLAlchemy (for ORM)
- **Environment**: python-dotenv (for loading .env files)

## Installation

### Using Nix (Recommended for NixOS)

```bash
nix develop
```

### Using pip

1. Install Python 3.12+
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set up environment variables:
   ```bash
   echo "DATABASE_URL=sqlite:///marketmaker.db" > .env
   ```

## Notes

- Database integration uses SQLAlchemy ORM
- Platform-specific plugins should inherit from the `Platform` abstract class
- Algorithms should inherit from the `Algorithm` abstract class
- User roles: 0 = GUEST, 10 = USER, 100 = ADMIN
