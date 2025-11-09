/**
 * Mineflayer API Server
 * 
 * Provides an HTTP API for managing Minecraft bots using mineflayer.
 * For now, this service only handles bot login functionality.
 */

import express from 'express';
import cors from 'cors';
import mineflayer from 'mineflayer';
import pathfinder from 'mineflayer-pathfinder';
import minecraftData from 'minecraft-data';
import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import yaml from 'js-yaml';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Load config from config.yml
function loadConfig() {
  try {
    const configPath = join(__dirname, '..', 'confs', 'config.yml');
    const configFile = readFileSync(configPath, 'utf8');
    const config = yaml.load(configFile) || {};
    return config;
  } catch (error) {
    console.warn('Could not load config.yml, using defaults:', error.message);
    return {};
  }
}

const config = loadConfig();

const app = express();
const PORT = process.env.MINEFLAYER_API_PORT || 3000;

// Enable CORS and JSON parsing
app.use(cors());
app.use(express.json());

// Store active bot connections
const activeBots = new Map();

/**
 * POST /api/bot/login
 * 
 * Logs a bot into a Minecraft server.
 * 
 * Request body:
 * {
 *   "bot_id": "unique_bot_identifier",
 *   "username": "bot_username",
 *   "password": "bot_password",  // Optional for offline mode
 *   "auth": "online" | "offline",
 *   "server": {
 *     "host": "server_address",
 *     "port": 25565
 *   }
 * }
 * 
 * Response:
 * {
 *   "success": true,
 *   "bot_id": "unique_bot_identifier",
 *   "status": "connected",
 *   "uuid": "bot_uuid"  // Only for online mode
 * }
 */
app.post('/api/bot/login', async (req, res) => {
  // Declare bot and bot_id outside try block so they're accessible in catch block
  let bot = null;
  const bot_id = req.body?.bot_id || null;
  
  try {
    const { username, password, auth, server } = req.body;

    // Validate required fields
    if (!bot_id || !username || !server || !server.host) {
      return res.status(400).json({
        success: false,
        error: 'Missing required fields: bot_id, username, and server.host are required'
      });
    }

    // Check if bot is already connected
    if (activeBots.has(bot_id)) {
      return res.status(409).json({
        success: false,
        error: `Bot ${bot_id} is already connected`
      });
    }

    // Validate auth mode
    if (auth === 'online' && !password) {
      return res.status(400).json({
        success: false,
        error: 'Password is required for online authentication'
      });
    }

    // Create bot options
    // Version priority: server.version in request > MINECRAFT_VERSION env var > config.yml > default 1.21.4
    const defaultVersion = process.env.MINECRAFT_VERSION || config.minecraft_version || '1.21.4';
    const botOptions = {
      host: server.host,
      port: server.port || 25565,
      username: username,
      version: server.version || defaultVersion,
    };

    // Set authentication based on mode
    if (auth === 'online') {
      botOptions.password = password;
    } else {
      // Offline mode - no password needed
      botOptions.auth = 'offline';
    }

    // Create and connect bot
    try {
      bot = mineflayer.createBot(botOptions);
      // Load pathfinder plugin
      bot.loadPlugin(pathfinder.pathfinder);
    } catch (err) {
      return res.status(500).json({
        success: false,
        error: `Failed to create bot: ${err.message}`
      });
    }

    // Set up event handlers
    bot.once('login', () => {
      console.log(`[${bot_id}] Bot logged in successfully`);
    });

    bot.once('spawn', () => {
      console.log(`[${bot_id}] Bot spawned in world`);
    });

    bot.on('error', (err) => {
      console.error(`[${bot_id}] Bot error:`, err.message);
      // Remove bot from active connections on error
      if (activeBots.has(bot_id)) {
        activeBots.delete(bot_id);
      }
    });

    bot.on('end', () => {
      console.log(`[${bot_id}] Bot disconnected`);
      activeBots.delete(bot_id);
    });

    // Wait for login event
    await new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        if (bot && typeof bot.end === 'function') {
          bot.end('Connection timeout');
        }
        // Ensure bot is removed from activeBots
        if (activeBots.has(bot_id)) {
          activeBots.delete(bot_id);
        }
        reject(new Error('Login timeout - bot failed to connect within 30 seconds'));
      }, 30000);

      bot.once('login', () => {
        clearTimeout(timeout);
        resolve();
      });

      bot.once('error', (err) => {
        clearTimeout(timeout);
        if (bot && typeof bot.end === 'function') {
          bot.end('Login failed');
        }
        // Ensure bot is removed from activeBots
        if (activeBots.has(bot_id)) {
          activeBots.delete(bot_id);
        }
        reject(err);
      });
    });

    // Store bot connection
    activeBots.set(bot_id, {
      bot: bot,
      username: username,
      auth: auth,
      server: server,
      connected_at: new Date().toISOString()
    });

    // Return success response
    res.json({
      success: true,
      bot_id: bot_id,
      status: 'connected',
      uuid: bot.player?.uuid || null,
      username: bot.username
    });

  } catch (error) {
    console.error('Login error:', error);
    
    // Clean up bot if it was created but login failed
    if (bot && bot_id) {
      try {
        if (typeof bot.end === 'function') {
          bot.end('Login error cleanup');
        }
        // Remove from activeBots if it was added
        if (activeBots.has(bot_id)) {
          activeBots.delete(bot_id);
        }
      } catch (cleanupErr) {
        console.error(`Error during bot cleanup for ${bot_id}:`, cleanupErr);
      }
    }
    
    res.status(500).json({
      success: false,
      error: error.message || 'Failed to login bot'
    });
  }
});

/**
 * POST /api/bot/logout
 * 
 * Logs out a bot from the server.
 * 
 * Request body:
 * {
 *   "bot_id": "unique_bot_identifier"
 * }
 */
app.post('/api/bot/logout', (req, res) => {
  try {
    const { bot_id } = req.body;

    if (!bot_id) {
      return res.status(400).json({
        success: false,
        error: 'bot_id is required'
      });
    }

    const botData = activeBots.get(bot_id);
    if (!botData) {
      return res.status(404).json({
        success: false,
        error: `Bot ${bot_id} is not connected`
      });
    }

    // Disconnect bot
    if (botData.bot && typeof botData.bot.end === 'function') {
      botData.bot.end('Logout requested');
    }
    activeBots.delete(bot_id);

    res.json({
      success: true,
      bot_id: bot_id,
      status: 'disconnected'
    });

  } catch (error) {
    console.error('Logout error:', error);
    res.status(500).json({
      success: false,
      error: error.message || 'Failed to logout bot'
    });
  }
});

/**
 * GET /api/bot/status/:bot_id
 * 
 * Get the connection status of a bot.
 */
app.get('/api/bot/status/:bot_id', (req, res) => {
  try {
    const { bot_id } = req.params;
    const botData = activeBots.get(bot_id);

    if (!botData) {
      return res.status(404).json({
        success: false,
        error: `Bot ${bot_id} is not connected`
      });
    }

    res.json({
      success: true,
      bot_id: bot_id,
      status: 'connected',
      username: botData.username,
      auth: botData.auth,
      server: botData.server,
      connected_at: botData.connected_at,
      uuid: botData.bot.player?.uuid || null
    });

  } catch (error) {
    console.error('Status error:', error);
    res.status(500).json({
      success: false,
      error: error.message || 'Failed to get bot status'
    });
  }
});

/**
 * GET /api/bot/inventory/:bot_id
 * 
 * Get the current inventory of a bot.
 */
app.get('/api/bot/inventory/:bot_id', (req, res) => {
  try {
    const { bot_id } = req.params;
    const botData = activeBots.get(bot_id);
    
    if (!botData) {
      return res.status(404).json({
        success: false,
        error: `Bot ${bot_id} is not connected`
      });
    }
    
    const bot = botData.bot;
    const inventory = {};
    
    // Iterate through all inventory slots
    for (const item of Object.values(bot.inventory.items())) {
      if (item) {
        // Normalize item name (remove 'minecraft:' prefix if present)
        const itemName = item.name.replace(/^minecraft:/, '');
        inventory[itemName] = (inventory[itemName] || 0) + item.count;
      }
    }
    
    res.json({
      success: true,
      bot_id: bot_id,
      inventory: inventory
    });
    
  } catch (error) {
    console.error('Inventory error:', error);
    res.status(500).json({
      success: false,
      error: error.message || 'Failed to get inventory'
    });
  }
});

/**
 * POST /api/bot/inventory/:bot_id/validate
 * 
 * Validate bot inventory against expected inventory.
 */
app.post('/api/bot/inventory/:bot_id/validate', (req, res) => {
  try {
    const { bot_id } = req.params;
    const { expected_inventory } = req.body;
    const botData = activeBots.get(bot_id);
    
    if (!botData) {
      return res.status(404).json({
        success: false,
        error: `Bot ${bot_id} is not connected`
      });
    }
    
    const bot = botData.bot;
    const actual_inventory = {};
    
    // Get actual inventory
    for (const item of Object.values(bot.inventory.items())) {
      if (item) {
        const itemName = item.name.replace(/^minecraft:/, '');
        actual_inventory[itemName] = (actual_inventory[itemName] || 0) + item.count;
      }
    }
    
    // Compare with expected if provided
    let is_accurate = true;
    const differences = {};
    
    if (expected_inventory) {
      // Check all expected items
      for (const [itemName, expectedQty] of Object.entries(expected_inventory)) {
        const normalizedName = itemName.replace(/^minecraft:/, '');
        const actualQty = actual_inventory[normalizedName] || 0;
        if (actualQty !== expectedQty) {
          is_accurate = false;
          differences[normalizedName] = actualQty - expectedQty;
        }
      }
      
      // Check for unexpected items (if expected_inventory is complete list)
      // For now, we only validate expected items exist in correct quantities
    }
    
    res.json({
      success: true,
      bot_id: bot_id,
      is_accurate: is_accurate,
      differences: differences,
      actual_inventory: actual_inventory
    });
    
  } catch (error) {
    console.error('Validate inventory error:', error);
    res.status(500).json({
      success: false,
      error: error.message || 'Failed to validate inventory'
    });
  }
});

/**
 * POST /api/bot/inventory/:bot_id/drop
 * 
 * Drop items from bot inventory that are not in the allowed list.
 */
app.post('/api/bot/inventory/:bot_id/drop', (req, res) => {
  try {
    const { bot_id } = req.params;
    const { allowed_items } = req.body;
    const botData = activeBots.get(bot_id);
    
    if (!botData) {
      return res.status(404).json({
        success: false,
        error: `Bot ${bot_id} is not connected`
      });
    }
    
    if (!Array.isArray(allowed_items)) {
      return res.status(400).json({
        success: false,
        error: 'allowed_items must be an array'
      });
    }
    
    const bot = botData.bot;
    let dropped_count = 0;
    
    // Normalize allowed items (remove minecraft: prefix)
    const normalized_allowed = allowed_items.map(item => item.replace(/^minecraft:/, ''));
    
    // Iterate through inventory and drop items not in allowed list
    for (let slot = 0; slot < bot.inventory.inventoryStart + bot.inventory.inventorySize; slot++) {
      const item = bot.inventory.slots[slot];
      if (item) {
        const itemName = item.name.replace(/^minecraft:/, '');
        if (!normalized_allowed.includes(itemName)) {
          bot.tossStack(item);
          dropped_count++;
        }
      }
    }
    
    res.json({
      success: true,
      bot_id: bot_id,
      dropped_count: dropped_count
    });
    
  } catch (error) {
    console.error('Drop items error:', error);
    res.status(500).json({
      success: false,
      error: error.message || 'Failed to drop items'
    });
  }
});

/**
 * POST /api/bot/inventory/:bot_id/drop-excess
 * 
 * Drop excess items of a specific type until we have exactly target_amount.
 */
app.post('/api/bot/inventory/:bot_id/drop-excess', (req, res) => {
  try {
    const { bot_id } = req.params;
    const { item_name, target_amount } = req.body;
    const botData = activeBots.get(bot_id);
    
    if (!botData) {
      return res.status(404).json({
        success: false,
        error: `Bot ${bot_id} is not connected`
      });
    }
    
    if (!item_name || typeof item_name !== 'string') {
      return res.status(400).json({
        success: false,
        error: 'item_name is required and must be a string'
      });
    }
    
    if (!target_amount || typeof target_amount !== 'number' || target_amount < 0) {
      return res.status(400).json({
        success: false,
        error: 'target_amount is required and must be a non-negative number'
      });
    }
    
    const bot = botData.bot;
    const normalized_item_name = item_name.replace(/^minecraft:/, '');
    let dropped_count = 0;
    let current_total = 0;
    
    // Count current amount of this item
    for (const item of Object.values(bot.inventory.items())) {
      if (item) {
        const itemName = item.name.replace(/^minecraft:/, '');
        if (itemName === normalized_item_name) {
          current_total += item.count;
        }
      }
    }
    
    if (current_total <= target_amount) {
      return res.json({
        success: true,
        bot_id: bot_id,
        dropped_count: 0,
        message: `No excess to drop. Current: ${current_total}, Target: ${target_amount}`
      });
    }
    
    const excess = current_total - target_amount;
    let remaining_to_drop = excess;
    
    // Drop items until we have target_amount
    for (let slot = 0; slot < bot.inventory.inventoryStart + bot.inventory.inventorySize; slot++) {
      const item = bot.inventory.slots[slot];
      if (item && remaining_to_drop > 0) {
        const itemName = item.name.replace(/^minecraft:/, '');
        if (itemName === normalized_item_name) {
          // Calculate how much to drop from this stack
          const to_drop = Math.min(item.count, remaining_to_drop);
          if (to_drop > 0) {
            if (to_drop === item.count) {
              // Drop entire stack
              bot.tossStack(item);
              dropped_count += item.count;
              remaining_to_drop -= item.count;
            } else {
              // Drop partial stack using toss with count
              try {
                bot.toss(item, to_drop);
                dropped_count += to_drop;
                remaining_to_drop -= to_drop;
              } catch (err) {
                // If toss with count fails, fall back to dropping entire stack
                console.warn(`Failed to drop partial stack, dropping entire stack: ${err.message}`);
                bot.tossStack(item);
                dropped_count += item.count;
                remaining_to_drop -= item.count;
              }
            }
            
            if (remaining_to_drop <= 0) {
              break;
            }
          }
        }
      }
    }
    
    res.json({
      success: true,
      bot_id: bot_id,
      dropped_count: dropped_count,
      excess_dropped: dropped_count,
      target_amount: target_amount
    });
    
  } catch (error) {
    console.error('Drop excess items error:', error);
    res.status(500).json({
      success: false,
      error: error.message || 'Failed to drop excess items'
    });
  }
});

/**
 * POST /api/bot/:bot_id/chat
 * 
 * Send a chat message from the bot.
 */
app.post('/api/bot/:bot_id/chat', (req, res) => {
  try {
    const { bot_id } = req.params;
    const { message } = req.body;
    const botData = activeBots.get(bot_id);
    
    if (!botData) {
      return res.status(404).json({
        success: false,
        error: `Bot ${bot_id} is not connected`
      });
    }
    
    if (!message || typeof message !== 'string') {
      return res.status(400).json({
        success: false,
        error: 'message is required and must be a string'
      });
    }
    
    const bot = botData.bot;
    bot.chat(message);
    
    res.json({
      success: true,
      bot_id: bot_id,
      message: message
    });
    
  } catch (error) {
    console.error('Chat error:', error);
    res.status(500).json({
      success: false,
      error: error.message || 'Failed to send chat message'
    });
  }
});

/**
 * POST /api/bot/:bot_id/wait-for-items
 * 
 * Wait for items to appear in bot inventory with progress updates.
 */
app.post('/api/bot/:bot_id/wait-for-items', async (req, res) => {
  try {
    const { bot_id } = req.params;
    const { item_name, target_amount, timeout_seconds } = req.body;
    const botData = activeBots.get(bot_id);
    
    if (!botData) {
      return res.status(404).json({
        success: false,
        error: `Bot ${bot_id} is not connected`
      });
    }
    
    if (!item_name || typeof item_name !== 'string') {
      return res.status(400).json({
        success: false,
        error: 'item_name is required and must be a string'
      });
    }
    
    if (!target_amount || typeof target_amount !== 'number' || target_amount <= 0) {
      return res.status(400).json({
        success: false,
        error: 'target_amount is required and must be a positive number'
      });
    }
    
    const timeout = timeout_seconds || 300;
    const normalized_item_name = item_name.replace(/^minecraft:/, '');
    const bot = botData.bot;
    const progress_messages = [];
    
    const startTime = Date.now();
    const checkInterval = 500; // Check every 500ms for responsiveness
    let last_amount = 0;
    
    const checkInventory = () => {
      let current_amount = 0;
      for (const item of Object.values(bot.inventory.items())) {
        if (item) {
          const itemName = item.name.replace(/^minecraft:/, '');
          if (itemName === normalized_item_name) {
            current_amount += item.count;
          }
        }
      }
      return current_amount;
    };
    
    // Set up inventory change listener to detect when items are added
    const onItemUpdate = () => {
      const current_amount = checkInventory();
      if (current_amount > last_amount) {
        // Items were added, send progress message
        const remaining = target_amount - current_amount;
        if (remaining > 0) {
          const progress_msg = `${remaining} left`;
          try {
            bot.chat(progress_msg);
            progress_messages.push(progress_msg);
          } catch (e) {
            // Ignore chat errors
          }
        }
        last_amount = current_amount;
      }
    };
    
    // Listen for inventory updates
    bot.inventory.on('updateSlot', onItemUpdate);
    
    // Also check initial inventory
    last_amount = checkInventory();
    if (last_amount > 0 && last_amount < target_amount) {
      const remaining = target_amount - last_amount;
      const progress_msg = `${remaining} left`;
      try {
        bot.chat(progress_msg);
        progress_messages.push(progress_msg);
      } catch (e) {
        // Ignore chat errors
      }
    }
    
    // Wait for items with progress updates
    return new Promise((resolve) => {
      const interval = setInterval(() => {
        const current_amount = checkInventory();
        
        if (current_amount >= target_amount) {
          bot.inventory.removeListener('updateSlot', onItemUpdate);
          clearInterval(interval);
          resolve(res.json({
            success: true,
            bot_id: bot_id,
            received_amount: current_amount,
            progress_messages: progress_messages
          }));
        } else if (Date.now() - startTime > timeout * 1000) {
          bot.inventory.removeListener('updateSlot', onItemUpdate);
          clearInterval(interval);
          resolve(res.status(408).json({
            success: false,
            error: `Timeout waiting for items. Received ${current_amount}/${target_amount}`,
            received_amount: current_amount,
            progress_messages: progress_messages
          }));
        }
      }, checkInterval);
    });
    
  } catch (error) {
    console.error('Wait for items error:', error);
    res.status(500).json({
      success: false,
      error: error.message || 'Failed to wait for items'
    });
  }
});

/**
 * POST /api/bot/{bot_id}/deliver-item
 * 
 * Deliver items to a player by navigating to them and dropping items.
 * 
 * Request body:
 * {
 *   "item_name": "diamond",
 *   "amount": 10,
 *   "target_uuid": "player_username_or_uuid"
 * }
 */
app.post('/api/bot/:bot_id/deliver-item', async (req, res) => {
  try {
    const bot_id = req.params.bot_id;
    const { item_name, amount, target_uuid } = req.body;

    // Validate required fields
    if (!item_name || !amount || !target_uuid) {
      return res.status(400).json({
        success: false,
        error: 'Missing required fields: item_name, amount, and target_uuid are required'
      });
    }

    // Get bot
    const botData = activeBots.get(bot_id);
    if (!botData) {
      return res.status(404).json({
        success: false,
        error: `Bot ${bot_id} not found`
      });
    }

    const bot = botData.bot;

    // Wait for bot to be fully spawned
    if (!bot.entity || !bot.entity.position) {
      // Wait for spawn event if not spawned yet
      await new Promise((resolve, reject) => {
        const timeout = setTimeout(() => {
          reject(new Error('Bot spawn timeout'));
        }, 10000);
        
        if (bot.entity && bot.entity.position) {
          clearTimeout(timeout);
          resolve();
        } else {
          bot.once('spawn', () => {
            clearTimeout(timeout);
            resolve();
          });
        }
      });
    }

    // Find target player by username or UUID
    let targetPlayer = null;
    
    // First try to find by username (case-insensitive)
    const players = Object.values(bot.players);
    for (const player of players) {
      if (player.username && player.username.toLowerCase() === target_uuid.toLowerCase()) {
        targetPlayer = player;
        break;
      }
      // Also check UUID if available
      if (player.uuid && player.uuid === target_uuid) {
        targetPlayer = player;
        break;
      }
    }

    // If not found in players list, try to find by entity UUID
    if (!targetPlayer) {
      const entities = Object.values(bot.entities);
      for (const entity of entities) {
        if (entity.type === 'player' && entity.username) {
          if (entity.username.toLowerCase() === target_uuid.toLowerCase() ||
              (entity.uuid && entity.uuid === target_uuid)) {
            targetPlayer = entity;
            break;
          }
        }
      }
    }

    if (!targetPlayer || !targetPlayer.entity) {
      return res.status(404).json({
        success: false,
        error: `Player ${target_uuid} not found`
      });
    }

    // Get target position
    const targetPos = targetPlayer.entity.position;
    if (!targetPos) {
      return res.status(400).json({
        success: false,
        error: 'Target player position not available'
      });
    }

    // Calculate position 3 blocks away from target
    const botPos = bot.entity.position;
    const direction = {
      x: targetPos.x - botPos.x,
      y: targetPos.y - botPos.y,
      z: targetPos.z - botPos.z
    };
    
    // Normalize direction and scale to 3 blocks
    const distance = Math.sqrt(direction.x * direction.x + direction.y * direction.y + direction.z * direction.z);
    if (distance > 0) {
      const scale = 3.0 / distance;
      direction.x *= scale;
      direction.y *= scale;
      direction.z *= scale;
    }

    const goalPos = {
      x: targetPos.x - direction.x,
      y: targetPos.y - direction.y,
      z: targetPos.z - direction.z
    };

    // Check if bot has the required items
    const item = bot.inventory.items().find(item => {
      const itemName = item.name.replace('minecraft:', '');
      return itemName === item_name.replace('minecraft:', '');
    });

    if (!item || item.count < amount) {
      return res.status(400).json({
        success: false,
        error: `Bot does not have enough ${item_name}. Has ${item ? item.count : 0}, needs ${amount}`
      });
    }

    // Set up pathfinder movements
    const mcData = minecraftData(bot.version);
    const movements = new pathfinder.Movements(bot, mcData);
    bot.pathfinder.setMovements(movements);

    // Use pathfinder to navigate to goal position
    const { GoalNear } = pathfinder.goals;
    const goal = new GoalNear(goalPos.x, goalPos.y, goalPos.z, 1);
    
    // Navigate to goal position
    try {
      await bot.pathfinder.goto(goal);
    } catch (pathError) {
      return res.status(500).json({
        success: false,
        error: `Pathfinding failed: ${pathError.message}`
      });
    }

    // Get current position after navigation
    const currentPos = bot.entity.position;
    const distanceToGoal = Math.sqrt(
      Math.pow(currentPos.x - goalPos.x, 2) +
      Math.pow(currentPos.y - goalPos.y, 2) +
      Math.pow(currentPos.z - goalPos.z, 2)
    );

    // If we're not close enough, return error
    if (distanceToGoal > 3) {
      return res.status(500).json({
        success: false,
        error: `Failed to reach target position. Distance: ${distanceToGoal.toFixed(2)} blocks`
      });
    }

    // Drop items towards the target player
    try {
      // Make bot look at the player before dropping
      // Look at player's eye level (position + height offset)
      let lookAtPos;
      if (targetPos.offset) {
        // Use offset method if available (Vec3-like object)
        lookAtPos = targetPos.offset(0, targetPlayer.entity.height || 1.6, 0);
      } else {
        // Fallback to manual calculation
        lookAtPos = {
          x: targetPos.x,
          y: targetPos.y + (targetPlayer.entity.height || 1.6),
          z: targetPos.z
        };
      }
      await bot.lookAt(lookAtPos);
      
      // Small delay to ensure look completes
      await new Promise(resolve => setTimeout(resolve, 200));
      
      // Drop items
      let dropped = 0;
      const itemsToDrop = bot.inventory.items().filter(invItem => {
        const invItemName = invItem.name.replace('minecraft:', '');
        return invItemName === item_name.replace('minecraft:', '');
      });

      for (const invItem of itemsToDrop) {
        if (dropped >= amount) break;
        
        const dropAmount = Math.min(invItem.count, amount - dropped);
        bot.toss(invItem.type, null, dropAmount);
        dropped += dropAmount;
        // Small delay between drops
        await new Promise(resolve => setTimeout(resolve, 100));
      }

      // Wait a moment for items to be dropped
      await new Promise(resolve => setTimeout(resolve, 500));

      // Logout the bot after delivery
      try {
        bot.end('Delivery complete');
        // Remove bot from active connections
        activeBots.delete(bot_id);
      } catch (logoutError) {
        console.warn(`[${bot_id}] Warning: Error during logout: ${logoutError.message}`);
        // Still remove from active connections even if logout fails
        activeBots.delete(bot_id);
      }

      return res.json({
        success: true,
        bot_id: bot_id,
        item_name: item_name,
        amount_dropped: dropped,
        target_uuid: target_uuid
      });
    } catch (dropError) {
      // Try to logout even on error
      try {
        bot.end('Delivery failed');
        activeBots.delete(bot_id);
      } catch (logoutError) {
        console.warn(`[${bot_id}] Warning: Error during logout after failure: ${logoutError.message}`);
        activeBots.delete(bot_id);
      }
      
      return res.status(500).json({
        success: false,
        error: `Failed to drop items: ${dropError.message}`
      });
    }

  } catch (error) {
    console.error('Deliver item error:', error);
    res.status(500).json({
      success: false,
      error: error.message || 'Failed to deliver item'
    });
  }
});

/**
 * GET /api/bots
 * 
 * List all connected bots.
 */
app.get('/api/bots', (req, res) => {
  try {
    const bots = Array.from(activeBots.entries()).map(([bot_id, data]) => ({
      bot_id: bot_id,
      username: data.username,
      auth: data.auth,
      server: data.server,
      connected_at: data.connected_at,
      uuid: data.bot.player?.uuid || null
    }));

    res.json({
      success: true,
      bots: bots,
      count: bots.length
    });

  } catch (error) {
    console.error('List bots error:', error);
    res.status(500).json({
      success: false,
      error: error.message || 'Failed to list bots'
    });
  }
});

/**
 * Health check endpoint
 */
app.get('/health', (req, res) => {
  res.json({
    status: 'ok',
    service: 'mineflayer-api',
    active_bots: activeBots.size
  });
});

// Start server
app.listen(PORT, () => {
  console.log(`Mineflayer API server running on port ${PORT}`);
  console.log(`Health check: http://localhost:${PORT}/health`);
});

// Graceful shutdown
process.on('SIGTERM', () => {
  console.log('SIGTERM received, shutting down gracefully...');
  // Disconnect all bots
  for (const [bot_id, botData] of activeBots.entries()) {
    if (botData.bot && typeof botData.bot.end === 'function') {
      botData.bot.end('Server shutdown');
    }
  }
  process.exit(0);
});

process.on('SIGINT', () => {
  console.log('SIGINT received, shutting down gracefully...');
  // Disconnect all bots
  for (const [bot_id, botData] of activeBots.entries()) {
    if (botData.bot && typeof botData.bot.end === 'function') {
      botData.bot.end('Server shutdown');
    }
  }
  process.exit(0);
});

