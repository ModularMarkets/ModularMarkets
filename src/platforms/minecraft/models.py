"""
Minecraft platform-specific database models.

IMPORTANT: Platform-specific code should NEVER modify files in the general source
directory (src/). All platform-specific models, utilities, and implementations
must be contained within the platform's own directory structure.

This file contains SQLAlchemy models for the Minecraft platform's separate database,
used to persist bot network state, bot configurations, and inventory data.
"""
from sqlalchemy import Column, String, Integer, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base

# Separate Base for Minecraft database to avoid conflicts with main database
MinecraftBase = declarative_base()


class MinecraftBotModel(MinecraftBase):
    """Model for storing Minecraft bot configuration."""
    __tablename__ = 'minecraft_bots'
    bot_id = Column(String, primary_key=True)  # Use username as bot_id
    username = Column(String, unique=True, nullable=False)
    auth = Column(String, nullable=False)  # 'online' or 'offline'
    trading_mode = Column(String, nullable=False)  # 'drop', 'chat', or 'plugin'
    # Note: password is NOT stored for security reasons
    # Note: UUID is automatically assigned by Minecraft during authentication and not stored


class MinecraftBotInventoryModel(MinecraftBase):
    """Model for storing Minecraft bot inventory state."""
    __tablename__ = 'minecraft_bot_inventory'
    bot_id = Column(String, ForeignKey('minecraft_bots.bot_id', ondelete='CASCADE'), primary_key=True)
    item_name = Column(String, primary_key=True)
    quantity = Column(Integer, nullable=False, default=0)


class MinecraftNetworkModel(MinecraftBase):
    """Model for storing Minecraft network-level configuration."""
    __tablename__ = 'minecraft_network'
    network_id = Column(String, primary_key=True, default='default')
    config = Column(JSON)  # Store network-level configuration

