"""
Example usage of the Mineflayer API client.

This script demonstrates how to use the Python client to interact with
the mineflayer API service for logging bots into Minecraft servers.

Make sure the mineflayer API server is running before executing this script:
    cd src/platforms/minecraft/node_service
    npm install
    npm start
"""

from .mineflayer_client import MineflayerClient

def main():
    # Create client (defaults to http://localhost:3000)
    client = MineflayerClient()
    
    # Check if service is available
    if not client.is_available():
        print("Error: Mineflayer API service is not available.")
        print("Please start the service with: npm start")
        return
    
    print("Mineflayer API service is available!")
    
    # Example: Login a bot in offline mode
    try:
        print("\n--- Logging in bot (offline mode) ---")
        result = client.login(
            bot_id="example_bot_1",
            username="ExampleBot",
            auth="offline",
            server_host="localhost",
            server_port=25565
        )
        print(f"Login successful: {result}")
        
        # Get bot status
        print("\n--- Getting bot status ---")
        status = client.get_status("example_bot_1")
        print(f"Bot status: {status}")
        
        # List all bots
        print("\n--- Listing all bots ---")
        bots = client.list_bots()
        print(f"Connected bots: {bots}")
        
        # Logout bot
        print("\n--- Logging out bot ---")
        logout_result = client.logout("example_bot_1")
        print(f"Logout result: {logout_result}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()

