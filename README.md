# Market Maker App

A market making system that allows hosting websites for buying and selling non-liquid commodities across various platforms (games, services, IRL items).

## Project Structure

```
src/
├── __init__.py
├── user.py              # User class for account management
├── merchant.py          # Merchant class for item trading
├── transaction.py       # Transaction data model
├── algorithm.py         # Algorithm interface and Result class
├── platform.py          # Platform abstract base class
├── shop.py              # Shop interface for managing merchants
├── database.py          # Database initialization functions
└── plugins/
    ├── __init__.py
    └── minecraft.py     # Minecraft platform implementation
```

## Core Classes

### User
Manages user accounts, authentication, balances, and linked accounts.

### Merchant
Handles individual item trading with buy/sell operations and price updates via algorithms.

### Shop
Manages collections of merchants and provides interface for merchant operations.

### Platform (Abstract)
Interface for external platforms (games, services) that provide items/services.

### Algorithm (Abstract)
Interface for market making algorithms that calculate buy/sell prices.

## Required Libraries

See `requirements.txt` for a list of suggested libraries. Key dependencies include:

- **Database**: SQLAlchemy (for ORM), database-specific adapters
- **Authentication**: Auth0 Python SDK
- **HTTP Clients**: requests, aiohttp (for platform API interactions)
- **Development**: mypy, pytest, black, flake8

## Installation

1. Install Python 3.12+
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set up environment variables (Auth0 credentials, database URLs, etc.)

## Notes

- All classes are currently interface definitions without full implementations
- Platform-specific plugins should inherit from the `Platform` abstract class
- Algorithms should inherit from the `Algorithm` abstract class
- Database integration is abstracted and needs to be implemented based on your chosen database

