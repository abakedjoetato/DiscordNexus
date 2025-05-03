"""
Database connection and initialization module.
Handles MongoDB connection and operations.
"""
import logging
import motor.motor_asyncio
from config import MONGODB_URI, DATABASE_NAME

logger = logging.getLogger(__name__)

# MongoDB client instance
client = None
db = None

async def initialize():
    """Initialize the MongoDB connection."""
    global client, db
    
    try:
        logger.info(f"Connecting to MongoDB at {MONGODB_URI}")
        client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URI)
        db = client[DATABASE_NAME]
        
        # Check connection
        await client.admin.command('ping')
        logger.info("MongoDB connection successful")
        
        # Create indexes
        await create_indexes()
        logger.info("MongoDB indexes created")
        
        return db
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise

async def create_indexes():
    """Create necessary indexes for collections."""
    # Guild collection indexes
    await db.guilds.create_index("guild_id", unique=True)
    
    # Server collection indexes
    await db.servers.create_index([("guild_id", 1), ("server_id", 1)], unique=True)
    
    # Player collection indexes
    await db.players.create_index([("server_id", 1), ("player_name", 1)], unique=True)
    
    # Events collection indexes
    await db.events.create_index([("server_id", 1), ("event_type", 1), ("timestamp", 1)])
    
    # KillFeed collection indexes
    await db.killfeed.create_index([("server_id", 1), ("timestamp", 1)])
    await db.killfeed.create_index([("server_id", 1), ("killer", 1)])
    await db.killfeed.create_index([("server_id", 1), ("victim", 1)])

async def get_guild(guild_id):
    """
    Get guild document by Discord guild ID.
    
    Args:
        guild_id: Discord guild ID
        
    Returns:
        Guild document or None if not found
    """
    return await db.guilds.find_one({"guild_id": guild_id})

async def update_guild(guild_id, update_data):
    """
    Update guild document by Discord guild ID.
    
    Args:
        guild_id: Discord guild ID
        update_data: Dictionary with fields to update
        
    Returns:
        Result of the update operation
    """
    return await db.guilds.update_one(
        {"guild_id": guild_id},
        {"$set": update_data},
        upsert=True
    )

async def get_servers(guild_id):
    """
    Get all servers for a specific guild.
    
    Args:
        guild_id: Discord guild ID
        
    Returns:
        List of server documents
    """
    cursor = db.servers.find({"guild_id": guild_id})
    return await cursor.to_list(length=None)

async def add_server(server_data):
    """
    Add a new server to the database.
    
    Args:
        server_data: Dictionary with server information
        
    Returns:
        Result of the insert operation
    """
    return await db.servers.insert_one(server_data)

async def update_server(guild_id, server_id, update_data):
    """
    Update server document.
    
    Args:
        guild_id: Discord guild ID
        server_id: Server ID
        update_data: Dictionary with fields to update
        
    Returns:
        Result of the update operation
    """
    return await db.servers.update_one(
        {"guild_id": guild_id, "server_id": server_id},
        {"$set": update_data}
    )

async def delete_server(guild_id, server_id):
    """
    Delete a server from the database.
    
    Args:
        guild_id: Discord guild ID
        server_id: Server ID
        
    Returns:
        Result of the delete operation
    """
    # Delete the server
    server_result = await db.servers.delete_one({"guild_id": guild_id, "server_id": server_id})
    
    # Delete related player data
    player_result = await db.players.delete_many({"server_id": server_id})
    
    # Delete related events
    events_result = await db.events.delete_many({"server_id": server_id})
    
    # Delete related killfeed entries
    killfeed_result = await db.killfeed.delete_many({"server_id": server_id})
    
    return {
        "server": server_result.deleted_count,
        "players": player_result.deleted_count,
        "events": events_result.deleted_count,
        "killfeed": killfeed_result.deleted_count
    }

async def add_kill(kill_data):
    """
    Add a new kill to the killfeed collection.
    
    Args:
        kill_data: Dictionary with kill information
        
    Returns:
        Result of the insert operation
    """
    # Insert kill record
    result = await db.killfeed.insert_one(kill_data)
    
    # Update killer stats if not a suicide
    if kill_data["killer"] != kill_data["victim"]:
        await db.players.update_one(
            {"server_id": kill_data["server_id"], "player_name": kill_data["killer"]},
            {
                "$inc": {"kills": 1, "kill_streak": 1},
                "$set": {"death_streak": 0},
                "$max": {
                    "longest_shot": kill_data.get("distance", 0),
                    "max_kill_streak": {"$add": [{"$ifNull": ["$max_kill_streak", 0]}, 1]}
                }
            },
            upsert=True
        )
    
    # Update victim stats
    if kill_data["killer"] == kill_data["victim"]:
        # Suicide case
        await db.players.update_one(
            {"server_id": kill_data["server_id"], "player_name": kill_data["victim"]},
            {
                "$inc": {"suicides": 1, "death_streak": 1},
                "$set": {"kill_streak": 0}
            },
            upsert=True
        )
    else:
        # Normal death case
        await db.players.update_one(
            {"server_id": kill_data["server_id"], "player_name": kill_data["victim"]},
            {
                "$inc": {"deaths": 1, "death_streak": 1},
                "$set": {"kill_streak": 0},
                "$max": {"max_death_streak": {"$add": [{"$ifNull": ["$max_death_streak", 0]}, 1]}}
            },
            upsert=True
        )
    
    # Update weapon stats
    if "weapon" in kill_data:
        await db.players.update_one(
            {"server_id": kill_data["server_id"], "player_name": kill_data["killer"]},
            {"$inc": {f"weapons.{kill_data['weapon']}": 1}},
            upsert=True
        )
    
    return result

async def add_event(event_data):
    """
    Add a new event to the events collection.
    
    Args:
        event_data: Dictionary with event information
        
    Returns:
        Result of the insert operation
    """
    return await db.events.insert_one(event_data)

async def update_player_connection(server_id, player_name, connected, is_console=False):
    """
    Update player connection status.
    
    Args:
        server_id: Server ID
        player_name: Player name
        connected: Boolean indicating if player connected or disconnected
        is_console: Boolean indicating if player is on console
        
    Returns:
        Result of the update operation
    """
    update_data = {
        "is_online": connected,
        "is_console": is_console,
        "last_updated": datetime.utcnow()
    }
    
    if connected:
        update_data["last_connected"] = datetime.utcnow()
    else:
        update_data["last_disconnected"] = datetime.utcnow()
    
    return await db.players.update_one(
        {"server_id": server_id, "player_name": player_name},
        {"$set": update_data},
        upsert=True
    )

async def get_player_stats(server_id, player_name):
    """
    Get player statistics.
    
    Args:
        server_id: Server ID
        player_name: Player name
        
    Returns:
        Player document or None if not found
    """
    return await db.players.find_one({"server_id": server_id, "player_name": player_name})

async def get_leaderboard(server_id, stat_field, limit=10):
    """
    Get leaderboard for a specific stat.
    
    Args:
        server_id: Server ID
        stat_field: Field to sort by (e.g., 'kills', 'deaths', 'kdr')
        limit: Maximum number of results
        
    Returns:
        List of player documents sorted by the specified stat
    """
    sort_field = stat_field
    
    # Special case for KDR which needs to be calculated
    if stat_field == "kdr":
        pipeline = [
            {"$match": {"server_id": server_id}},
            {"$addFields": {
                "kdr": {
                    "$cond": [
                        {"$eq": ["$deaths", 0]},
                        "$kills",
                        {"$divide": ["$kills", "$deaths"]}
                    ]
                }
            }},
            {"$sort": {"kdr": -1}},
            {"$limit": limit}
        ]
        cursor = db.players.aggregate(pipeline)
    else:
        cursor = db.players.find(
            {"server_id": server_id}, 
            sort=[(sort_field, -1)],
            limit=limit
        )
    
    return await cursor.to_list(length=limit)

async def get_weapon_stats(server_id, limit=10):
    """
    Get weapon usage statistics.
    
    Args:
        server_id: Server ID
        limit: Maximum number of weapons to return
        
    Returns:
        Aggregated weapon statistics
    """
    pipeline = [
        {"$match": {"server_id": server_id}},
        {"$project": {"_id": 0, "weapons": 1}},
        {"$unwind": "$weapons"},
        {"$group": {
            "_id": "$weapons.name",
            "total_kills": {"$sum": "$weapons.count"}
        }},
        {"$sort": {"total_kills": -1}},
        {"$limit": limit}
    ]
    
    cursor = db.players.aggregate(pipeline)
    return await cursor.to_list(length=limit)

async def get_events(server_id, event_type=None, limit=10):
    """
    Get recent events for a server.
    
    Args:
        server_id: Server ID
        event_type: Optional event type filter
        limit: Maximum number of events to return
        
    Returns:
        List of event documents
    """
    query = {"server_id": server_id}
    
    if event_type:
        query["event_type"] = event_type
    
    cursor = db.events.find(
        query,
        sort=[("timestamp", -1)],
        limit=limit
    )
    
    return await cursor.to_list(length=limit)

async def mark_parsing_position(server_id, file_path, position):
    """
    Update the last parsed position for a file.
    
    Args:
        server_id: Server ID
        file_path: Path of the parsed file
        position: Line position in the file
        
    Returns:
        Result of the update operation
    """
    return await db.parsing_state.update_one(
        {"server_id": server_id, "file_path": file_path},
        {"$set": {"position": position, "updated_at": datetime.utcnow()}},
        upsert=True
    )

async def get_parsing_position(server_id, file_path):
    """
    Get the last parsed position for a file.
    
    Args:
        server_id: Server ID
        file_path: Path of the parsed file
        
    Returns:
        Line position or 0 if not found
    """
    document = await db.parsing_state.find_one(
        {"server_id": server_id, "file_path": file_path}
    )
    
    return document["position"] if document else 0
