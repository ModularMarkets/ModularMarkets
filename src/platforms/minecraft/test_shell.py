#!/usr/bin/env python3
"""
Interactive test shell for Minecraft platform.

Allows testing of platform operations like:
- deposit/retrieve items
- check storage at various levels
- list bots
- manage bots
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.platforms.minecraft.platform import Minecraft
from src.platforms.minecraft.platform import MinecraftBot


class MinecraftTestShell:
    """Interactive shell for testing Minecraft platform."""
    
    def __init__(self):
        """Initialize the test shell."""
        print("Initializing Minecraft platform...")
        try:
            self.platform = Minecraft()
            print(f"✓ Platform initialized: {self.platform.platform_name}")
            print(f"✓ Trading mode: {self.platform._trading_mode}")
            print(f"✓ Server: {self.platform._server_address}:{self.platform._server_port}")
            print(f"✓ Network has {len(self.platform._network.warehouses)} bots")
            items = self.platform.get_item_list()
            print(f"✓ Available items: {', '.join(items[:5])}{'...' if len(items) > 5 else ''}")
        except Exception as e:
            print(f"✗ Error initializing platform: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    
    def cmd_help(self, args):
        """Show help message."""
        print("""
Available commands:
  help                          - Show this help message
  quit, exit                    - Exit the shell
  
  list-bots                     - List all bots in the network
  list-items                    - List all available items
  bot-info <bot_id>             - Show detailed info about a bot
  
  stock <item_name> [--no-cache] - Get stock at platform level (use --no-cache to fetch fresh data)
  stock-bot <bot_id> <item>     - Get stock for specific bot (always fetches fresh data)
  stock-network <item>          - Get stock at network level (always fetches fresh data)
  
  deposit <item> <amount>       - Deposit (retrieve) items (requires UUID)
  deposit-test <item> <amount>  - Deposit items with test UUID "test-user"
  
  deliver <item> <amount> <uuid>        - Deliver (withdraw) items to a user
  deliver-test <item> <amount> [uuid]   - Deliver items (defaults to "test-user" if uuid not provided)
  
  bot-inventory <bot_id>        - Show bot's current inventory
  network-summary               - Show summary of all bots and their inventories
  
  create-bot <username> <password> <auth> [bot_id]
                                  - Create a new bot (auth: online/offline)
  
Examples:
  stock diamond
  stock-bot bot1 diamond
  deposit-test diamond 72
  deliver-test diamond 5
  list-bots
  bot-info bot1
        """)
    
    def cmd_list_bots(self, args):
        """List all bots in the network."""
        bots = self.platform._network.warehouses
        if not bots:
            print("No bots in network.")
            return
        
        print(f"\nBots in network ({len(bots)}):")
        print("-" * 80)
        for bot in bots:
            if isinstance(bot, MinecraftBot):
                item_count = sum(bot.inventory.items.values()) if hasattr(bot.inventory, 'items') else 0
                stored_types = ', '.join(bot.stored_item_types) if bot.stored_item_types else 'none'
                print(f"  Bot ID: {bot.bot_id}")
                print(f"    Username: {bot.username}")
                print(f"    Trading Mode: {bot.trading_mode}")
                print(f"    Auth: {bot.auth}")
                print(f"    Items in inventory: {item_count}")
                print(f"    Stored item types: {stored_types}")
                print()
    
    def cmd_list_items(self, args):
        """List all available items."""
        items = self.platform.get_item_list()
        print(f"\nAvailable items ({len(items)}):")
        print(", ".join(items))
    
    def cmd_bot_info(self, args):
        """Show detailed info about a bot."""
        if not args:
            print("Usage: bot-info <bot_id>")
            return
        
        bot_id = args[0]
        bot = None
        for b in self.platform._network.warehouses:
            if isinstance(b, MinecraftBot) and b.bot_id == bot_id:
                bot = b
                break
        
        if not bot:
            print(f"Bot '{bot_id}' not found")
            return
        
        print(f"\nBot Info: {bot_id}")
        print("-" * 80)
        print(f"Username: {bot.username}")
        print(f"Trading Mode: {bot.trading_mode}")
        print(f"Auth: {bot.auth}")
        print(f"Server: {bot._server_address}:{bot._server_port}")
        print(f"Version: {bot._minecraft_version}")
        
        if hasattr(bot.inventory, 'items'):
            print(f"\nInventory ({sum(bot.inventory.items.values())} items):")
            if bot.inventory.items:
                for item_name, quantity in sorted(bot.inventory.items.items()):
                    print(f"  {item_name}: {quantity}")
            else:
                print("  (empty)")
            
            if hasattr(bot.inventory, 'capacity'):
                used = sum(bot.inventory.items.values())
                print(f"\nCapacity: {used}/{bot.inventory.capacity}")
        
        print(f"\nStored Item Types: {', '.join(bot.stored_item_types) if bot.stored_item_types else 'none'}")
    
    def cmd_stock(self, args):
        """Get stock at platform level."""
        if not args:
            print("Usage: stock <item_name> [--no-cache]")
            return
        
        # Check for --no-cache flag
        use_cache = True
        if '--no-cache' in args:
            use_cache = False
            args = [arg for arg in args if arg != '--no-cache']
        
        item_name = args[0]
        try:
            stock = self.platform.get_stock(item_name, cached=use_cache)
            cache_status = "cached" if use_cache else "fresh"
            print(f"Platform stock of {item_name} ({cache_status}): {stock}")
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
    
    def cmd_stock_bot(self, args):
        """Get stock for specific bot."""
        if len(args) < 2:
            print("Usage: stock-bot <bot_id> <item_name>")
            return
        
        bot_id = args[0]
        item_name = args[1]
        
        bot = None
        for b in self.platform._network.warehouses:
            if isinstance(b, MinecraftBot) and b.bot_id == bot_id:
                bot = b
                break
        
        if not bot:
            print(f"Bot '{bot_id}' not found")
            return
        
        try:
            stock = bot.get_stock(item_name, cached=False)
            print(f"Bot {bot_id} stock of {item_name}: {stock}")
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
    
    def cmd_stock_network(self, args):
        """Get stock at network level."""
        if not args:
            print("Usage: stock-network <item_name>")
            return
        
        item_name = args[0]
        try:
            stock = self.platform._network.get_stock(item_name, cached=False)
            print(f"Network stock of {item_name}: {stock}")
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
    
    def cmd_deposit(self, args):
        """Deposit (retrieve) items."""
        if len(args) < 3:
            print("Usage: deposit <item_name> <amount> <uuid>")
            return
        
        item_name = args[0]
        try:
            amount = int(args[1])
        except ValueError:
            print(f"Error: amount must be a number, got '{args[1]}'")
            return
        
        uuid = args[2]
        
        print(f"Retrieving {amount} {item_name} from user {uuid}...")
        try:
            result = self.platform.retrieve_item(item_name, amount, uuid)
            if result == 0:
                print(f"✓ Successfully retrieved {amount} {item_name}")
            else:
                print(f"✗ Failed to retrieve items (error code: {result})")
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
    
    def cmd_deposit_test(self, args):
        """Deposit items with test UUID."""
        if len(args) < 2:
            print("Usage: deposit-test <item_name> <amount>")
            return
        
        item_name = args[0]
        try:
            amount = int(args[1])
        except ValueError:
            print(f"Error: amount must be a number, got '{args[1]}'")
            return
        
        uuid = "test-user"
        self.cmd_deposit([item_name, str(amount), uuid])
    
    def cmd_deliver(self, args):
        """Deliver (withdraw) items to a user."""
        if len(args) < 3:
            print("Usage: deliver <item_name> <amount> <uuid>")
            return
        
        item_name = args[0]
        try:
            amount = int(args[1])
        except ValueError:
            print(f"Error: amount must be a number, got '{args[1]}'")
            return
        
        uuid = args[2]
        
        print(f"Delivering {amount} {item_name} to user {uuid}...")
        try:
            result = self.platform.deliver_item(item_name, amount, uuid)
            if result == 0:
                print(f"✓ Successfully delivered {amount} {item_name}")
            else:
                print(f"✗ Failed to deliver items (error code: {result})")
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
    
    def cmd_deliver_test(self, args):
        """Deliver items with test UUID (or specified username/UUID)."""
        if len(args) < 2:
            print("Usage: deliver-test <item_name> <amount> [uuid/username]")
            print("  If uuid/username is not provided, defaults to 'test-user'")
            return
        
        item_name = args[0]
        try:
            amount = int(args[1])
        except ValueError:
            print(f"Error: amount must be a number, got '{args[1]}'")
            return
        
        # Use provided UUID/username or default to "test-user"
        uuid = args[2] if len(args) > 2 else "test-user"
        self.cmd_deliver([item_name, str(amount), uuid])
    
    def cmd_bot_inventory(self, args):
        """Show bot's current inventory."""
        if not args:
            print("Usage: bot-inventory <bot_id>")
            return
        
        bot_id = args[0]
        bot = None
        for b in self.platform._network.warehouses:
            if isinstance(b, MinecraftBot) and b.bot_id == bot_id:
                bot = b
                break
        
        if not bot:
            print(f"Bot '{bot_id}' not found")
            return
        
        print(f"\nBot {bot_id} Inventory:")
        print("-" * 80)
        
        if hasattr(bot.inventory, 'items'):
            if bot.inventory.items:
                total = 0
                for item_name, quantity in sorted(bot.inventory.items.items()):
                    print(f"  {item_name}: {quantity}")
                    total += quantity
                print(f"\nTotal items: {total}")
                if hasattr(bot.inventory, 'capacity'):
                    print(f"Capacity: {total}/{bot.inventory.capacity}")
            else:
                print("  (empty)")
        else:
            print("  (inventory not initialized)")
    
    def cmd_network_summary(self, args):
        """Show summary of all bots and their inventories."""
        bots = self.platform._network.warehouses
        if not bots:
            print("No bots in network.")
            return
        
        print("\nNetwork Summary:")
        print("=" * 80)
        
        for bot in bots:
            if isinstance(bot, MinecraftBot):
                item_count = sum(bot.inventory.items.values()) if hasattr(bot.inventory, 'items') else 0
                capacity = bot.inventory.capacity if hasattr(bot.inventory, 'capacity') else 0
                
                print(f"\nBot: {bot.bot_id} ({bot.username})")
                print(f"  Items: {item_count}/{capacity}")
                print(f"  Stored types: {', '.join(bot.stored_item_types) if bot.stored_item_types else 'none'}")
                
                if hasattr(bot.inventory, 'items') and bot.inventory.items:
                    print("  Inventory breakdown:")
                    for item_name, quantity in sorted(bot.inventory.items.items()):
                        print(f"    {item_name}: {quantity}")
    
    def cmd_create_bot(self, args):
        """Create a new bot."""
        if len(args) < 3:
            print("Usage: create-bot <username> <password> <auth> [bot_id]")
            print("  auth: 'online' or 'offline'")
            return
        
        username = args[0]
        password = args[1]
        auth = args[2]
        bot_id = args[3] if len(args) > 3 else None
        
        if auth not in ('online', 'offline'):
            print(f"Error: auth must be 'online' or 'offline', got '{auth}'")
            return
        
        print(f"Creating bot: {username} (auth: {auth})...")
        try:
            bot = self.platform.create_bot(username, password, auth, bot_id)
            print(f"✓ Bot created: {bot.bot_id}")
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
    
    def run(self):
        """Run the interactive shell."""
        print("\n" + "=" * 80)
        print("Minecraft Platform Test Shell")
        print("=" * 80)
        print("Type 'help' for available commands, 'quit' to exit")
        print()
        
        commands = {
            'help': self.cmd_help,
            'quit': lambda args: None,
            'exit': lambda args: None,
            'list-bots': self.cmd_list_bots,
            'list-items': self.cmd_list_items,
            'bot-info': self.cmd_bot_info,
            'stock': self.cmd_stock,
            'stock-bot': self.cmd_stock_bot,
            'stock-network': self.cmd_stock_network,
            'deposit': self.cmd_deposit,
            'deposit-test': self.cmd_deposit_test,
            'deliver': self.cmd_deliver,
            'deliver-test': self.cmd_deliver_test,
            'bot-inventory': self.cmd_bot_inventory,
            'network-summary': self.cmd_network_summary,
            'create-bot': self.cmd_create_bot,
        }
        
        while True:
            try:
                line = input("minecraft> ").strip()
                if not line:
                    continue
                
                parts = line.split()
                cmd = parts[0].lower()
                args = parts[1:] if len(parts) > 1 else []
                
                if cmd in ('quit', 'exit'):
                    print("Goodbye!")
                    break
                
                if cmd in commands:
                    commands[cmd](args)
                else:
                    print(f"Unknown command: {cmd}. Type 'help' for available commands.")
                
            except KeyboardInterrupt:
                print("\nGoodbye!")
                break
            except EOFError:
                print("\nGoodbye!")
                break
            except Exception as e:
                print(f"Error: {e}")
                import traceback
                traceback.print_exc()


if __name__ == '__main__':
    shell = MinecraftTestShell()
    shell.run()

