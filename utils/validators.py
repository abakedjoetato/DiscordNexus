"""
Validation utilities for command inputs and server connections.
"""
import logging
import re
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)

async def validate_sftp_credentials(host, port, username, password, server_id):
    """
    Validate SFTP credentials by attempting to connect.
    
    Args:
        host: SFTP host address
        port: SFTP port
        username: SFTP username
        password: SFTP password
        server_id: Server ID for pattern matching
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    from utils.sftp_client import SFTPClient
    
    try:
        # Create SFTP client and try to connect
        sftp_client = SFTPClient(host, port, username, password, server_id)
        connected = await sftp_client.connect()
        
        if connected:
            # Test finding the files we need
            csv_found = await sftp_client.find_latest_csv()
            log_found = await sftp_client.find_log_file()
            
            await sftp_client.disconnect()
            
            if not csv_found:
                return False, "Connected, but could not find any CSV files. Please check the server structure."
            
            if not log_found:
                return False, "Connected, but could not find Deadside.log file. Please check the server structure."
            
            return True, None
        else:
            return False, "Failed to connect with the provided credentials."
    except Exception as e:
        logger.error(f"SFTP validation error for server {server_id}: {e}")
        return False, f"Error validating SFTP credentials: {str(e)}"

def validate_server_id(server_id):
    """
    Validate server ID format.
    
    Args:
        server_id: Server ID to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Server ID should be alphanumeric with underscores, no spaces
    if not re.match(r'^[a-zA-Z0-9_]+$', server_id):
        return False, "Server ID should contain only letters, numbers, and underscores."
    
    # Check length
    if len(server_id) < 3 or len(server_id) > 32:
        return False, "Server ID should be between 3 and 32 characters."
    
    return True, None

def validate_server_name(server_name):
    """
    Validate server name.
    
    Args:
        server_name: Server name to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not server_name or server_name.strip() == "":
        return False, "Server name cannot be empty."
    
    if len(server_name) > 100:
        return False, "Server name is too long (maximum 100 characters)."
    
    return True, None

async def is_admin(ctx):
    """
    Check if a user has admin permissions in the guild.
    
    Args:
        ctx: Discord command context
        
    Returns:
        Boolean indicating if the user is an admin
    """
    # Always allow bot owner
    if ctx.author.id == int(ctx.bot.application_id):
        return True
    
    # Check if user is guild owner
    if ctx.guild and ctx.author.id == ctx.guild.owner_id:
        return True
    
    # Check if user has administrator permission
    if ctx.guild and ctx.author.guild_permissions.administrator:
        return True
    
    # Check if user has the admin role set for the guild
    from database import get_guild
    guild_data = await get_guild(ctx.guild.id)
    
    if guild_data and guild_data.get("admin_role_id"):
        admin_role_id = guild_data["admin_role_id"]
        return any(role.id == admin_role_id for role in ctx.author.roles)
    
    return False

async def is_home_guild_admin(ctx):
    """
    Check if a user is an admin in the home guild.
    
    Args:
        ctx: Discord command context
        
    Returns:
        Boolean indicating if the user is a home guild admin
    """
    import config
    
    # Always allow bot owner
    if ctx.author.id == int(ctx.bot.application_id):
        return True
    
    # Check if this is the home guild
    if ctx.guild and ctx.guild.id == config.HOME_GUILD_ID:
        return await is_admin(ctx)
    
    return False

def validate_premium_tier(tier):
    """
    Validate premium tier.
    
    Args:
        tier: Premium tier to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    import config
    
    if tier not in config.PREMIUM_TIERS:
        return False, f"Invalid premium tier. Available tiers: {', '.join(config.PREMIUM_TIERS.keys())}"
    
    return True, None

def check_feature_access(guild_data, feature):
    """
    Check if a guild has access to a specific premium feature.
    
    Args:
        guild_data: Guild data dictionary
        feature: Feature to check access for
        
    Returns:
        Boolean indicating if the guild has access to the feature
    """
    import config
    
    premium_tier = guild_data.get("premium_tier", "free")
    tier_info = config.PREMIUM_TIERS.get(premium_tier, config.PREMIUM_TIERS["free"])
    
    return feature in tier_info["features"]

def check_server_limit(guild_data):
    """
    Check if a guild has reached its server limit.
    
    Args:
        guild_data: Guild data dictionary
        
    Returns:
        Tuple of (has_reached_limit, servers_count, max_servers)
    """
    import config
    
    premium_tier = guild_data.get("premium_tier", "free")
    tier_info = config.PREMIUM_TIERS.get(premium_tier, config.PREMIUM_TIERS["free"])
    
    servers_count = len(guild_data.get("servers", []))
    max_servers = tier_info["server_slots"]
    
    return servers_count >= max_servers, servers_count, max_servers
