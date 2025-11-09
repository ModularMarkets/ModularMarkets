"""
Mineflayer API Service

This package provides a Node.js HTTP API service for managing Minecraft bots
using mineflayer, along with a Python client to interact with it.
"""

from .mineflayer_client import MineflayerClient, login_bot

__all__ = ['MineflayerClient', 'login_bot']

