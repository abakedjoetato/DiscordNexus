"""
Discord embed utilities for formatting bot responses.
"""
import logging
import random
from datetime import datetime

import discord

import config

logger = logging.getLogger(__name__)

def create_killfeed_embed(kill_entry):
    """
    Create a Discord embed for a kill event.
    
    Args:
        kill_entry: Dictionary with kill information
        
    Returns:
        discord.Embed object
    """
    embed = discord.Embed(
        title="PvP Kill Feed",
        color=config.EMBED_COLOR,
        timestamp=kill_entry.get("timestamp", datetime.now())
    )
    
    # Set author field as killer
    embed.set_author(name=kill_entry["killer"])
    
    # Determine embed details based on kill type
    if kill_entry["is_suicide"]:
        # This is a suicide
        suicide_message = random.choice(config.SUICIDE_MESSAGES)
        embed.description = f"**{kill_entry['victim']}** {suicide_message}"
        
        suicide_type = kill_entry.get("suicide_type", "other")
        if suicide_type == "menu":
            embed.add_field(name="Method", value="Menu Suicide", inline=True)
        elif suicide_type == "fall":
            embed.add_field(name="Method", value="Falling", inline=True)
        else:
            embed.add_field(name="Method", value=kill_entry["weapon"], inline=True)
    else:
        # This is a normal kill
        embed.description = f"**{kill_entry['killer']}** killed **{kill_entry['victim']}**"
        embed.add_field(name="Weapon", value=kill_entry["weapon"], inline=True)
        
        # Add distance if available
        if kill_entry.get("distance", 0) > 0:
            embed.add_field(
                name="Distance", 
                value=f"{kill_entry['distance']:.1f}m", 
                inline=True
            )
    
    # Set footer
    embed.set_footer(text="Tower of Temptation PvP Stats")
    
    return embed

def create_stats_embed(player_stats):
    """
    Create a Discord embed for player statistics.
    
    Args:
        player_stats: Dictionary with player statistics
        
    Returns:
        discord.Embed object
    """
    embed = discord.Embed(
        title=f"Player Statistics: {player_stats['player_name']}",
        color=config.EMBED_COLOR,
        timestamp=datetime.now()
    )
    
    # Calculate KDR
    kills = player_stats.get("kills", 0)
    deaths = player_stats.get("deaths", 0)
    
    if deaths == 0:
        kdr = kills
    else:
        kdr = kills / deaths
    
    # Add main stats
    embed.add_field(name="Kills", value=str(kills), inline=True)
    embed.add_field(name="Deaths", value=str(deaths), inline=True)
    embed.add_field(name="KDR", value=f"{kdr:.2f}", inline=True)
    
    # Add streaks
    embed.add_field(
        name="Current Streaks", 
        value=f"Kill: {player_stats.get('kill_streak', 0)} | Death: {player_stats.get('death_streak', 0)}", 
        inline=False
    )
    
    embed.add_field(
        name="Best Streaks", 
        value=f"Kill: {player_stats.get('max_kill_streak', 0)} | Death: {player_stats.get('max_death_streak', 0)}", 
        inline=False
    )
    
    # Add longest shot if available
    if player_stats.get("longest_shot", 0) > 0:
        embed.add_field(
            name="Longest Shot", 
            value=f"{player_stats['longest_shot']:.1f}m", 
            inline=False
        )
    
    # Add suicide count if available
    if player_stats.get("suicides", 0) > 0:
        embed.add_field(
            name="Suicides", 
            value=str(player_stats["suicides"]), 
            inline=True
        )
    
    # Set footer
    embed.set_footer(text="Tower of Temptation PvP Stats")
    
    return embed

def create_leaderboard_embed(leaderboard_data, stat_type, server_name):
    """
    Create a Discord embed for a leaderboard.
    
    Args:
        leaderboard_data: List of player statistics
        stat_type: Type of statistic for the leaderboard
        server_name: Name of the server
        
    Returns:
        discord.Embed object
    """
    title_map = {
        "kills": "Most Kills",
        "deaths": "Most Deaths",
        "kdr": "Highest KDR",
        "longest_shot": "Longest Shots",
        "max_kill_streak": "Best Kill Streaks",
        "max_death_streak": "Worst Death Streaks",
        "suicides": "Most Suicides"
    }
    
    title = title_map.get(stat_type, stat_type.title())
    
    embed = discord.Embed(
        title=f"Leaderboard: {title}",
        description=f"Server: {server_name}",
        color=config.EMBED_COLOR,
        timestamp=datetime.now()
    )
    
    # Format leaderboard entries
    for index, player in enumerate(leaderboard_data, start=1):
        name = player["player_name"]
        
        if stat_type == "kdr":
            # Special handling for KDR which is calculated
            kills = player.get("kills", 0)
            deaths = player.get("deaths", 0)
            
            if deaths == 0:
                value = kills
            else:
                value = kills / deaths
                
            value_str = f"{value:.2f}"
        elif stat_type == "longest_shot":
            # Format distance
            value_str = f"{player.get(stat_type, 0):.1f}m"
        else:
            # Standard numeric value
            value_str = str(player.get(stat_type, 0))
        
        embed.add_field(
            name=f"{index}. {name}",
            value=value_str,
            inline=False
        )
    
    # If no entries, add a message
    if not leaderboard_data:
        embed.description += "\n\nNo data available for this leaderboard yet."
    
    # Set footer
    embed.set_footer(text="Tower of Temptation PvP Stats")
    
    return embed

def create_event_embed(event):
    """
    Create a Discord embed for a game event.
    
    Args:
        event: Dictionary with event information
        
    Returns:
        discord.Embed object
    """
    event_type = event["event_type"]
    event_status = event.get("status", "")
    
    # Define title based on event type
    title_map = {
        "mission": "Mission Event",
        "airdrop": "Airdrop Event",
        "crash": "Helicopter Crash",
        "trader": "Trader Event",
        "convoy": "Convoy Event",
        "encounter": "Encounter Event"
    }
    
    title = title_map.get(event_type, "Server Event")
    
    embed = discord.Embed(
        title=title,
        color=config.EMBED_COLOR,
        timestamp=event.get("timestamp", datetime.now())
    )
    
    # Format description based on event type
    if event_type == "mission":
        embed.description = f"Mission **{event['name']}** has {event_status}!"
    elif event_type == "airdrop":
        embed.description = f"Airdrop has {event_status} at {event.get('location', 'unknown location')}!"
    elif event_type == "crash":
        embed.description = f"Helicopter crash has {event_status} at {event.get('location', 'unknown location')}!"
    elif event_type == "trader":
        embed.description = f"Trader has {event_status} at {event.get('location', 'unknown location')}!"
    elif event_type == "convoy":
        embed.description = f"Convoy has {event_status} at {event.get('location', 'unknown location')}!"
    elif event_type == "encounter":
        embed.description = f"Encounter has {event_status} at {event.get('location', 'unknown location')}!"
    else:
        embed.description = f"Unknown event of type {event_type} has occurred."
    
    # Set footer
    embed.set_footer(text="Tower of Temptation PvP Stats")
    
    return embed

def create_player_count_embed(server_name, player_counts):
    """
    Create a Discord embed for player counts.
    
    Args:
        server_name: Name of the server
        player_counts: Dictionary with player count information
        
    Returns:
        discord.Embed object
    """
    embed = discord.Embed(
        title=f"Online Players: {server_name}",
        color=config.EMBED_COLOR,
        timestamp=datetime.now()
    )
    
    total = player_counts.get("total", 0)
    pc = player_counts.get("pc", 0)
    console = player_counts.get("console", 0)
    
    embed.add_field(name="Total", value=str(total), inline=True)
    embed.add_field(name="PC", value=str(pc), inline=True)
    embed.add_field(name="Console", value=str(console), inline=True)
    
    # Set footer
    embed.set_footer(text="Tower of Temptation PvP Stats")
    
    return embed

def create_historical_progress_embed(progress):
    """
    Create a Discord embed for historical parsing progress.
    
    Args:
        progress: Dictionary with progress information
        
    Returns:
        discord.Embed object
    """
    embed = discord.Embed(
        title="Historical Data Parsing Progress",
        color=config.EMBED_COLOR,
        timestamp=progress.get("timestamp", datetime.now())
    )
    
    embed.description = (
        f"Processed {progress['processed_files']} of {progress['total_files']} files "
        f"({progress['percent_complete']:.1f}%)"
    )
    
    embed.add_field(
        name="Kills Processed", 
        value=str(progress["total_kills"]), 
        inline=True
    )
    
    # Set footer
    embed.set_footer(text="Tower of Temptation PvP Stats")
    
    return embed

def create_server_list_embed(servers, guild_name):
    """
    Create a Discord embed for listing registered servers.
    
    Args:
        servers: List of server information dictionaries
        guild_name: Name of the Discord guild
        
    Returns:
        discord.Embed object
    """
    embed = discord.Embed(
        title=f"Registered Servers for {guild_name}",
        color=config.EMBED_COLOR,
        timestamp=datetime.now()
    )
    
    if not servers:
        embed.description = "No servers registered yet. Use the addserver command to add a server."
        return embed
    
    for server in servers:
        status = "🟢 Online" if server.get("is_online", False) else "🔴 Offline"
        field_value = (
            f"ID: {server['server_id']}\n"
            f"Status: {status}\n"
            f"Players: {server.get('online_players', 0)}\n"
            f"Added: {server['added_at'].strftime('%Y-%m-%d')}"
        )
        
        embed.add_field(
            name=server["name"],
            value=field_value,
            inline=False
        )
    
    # Set footer
    embed.set_footer(text="Tower of Temptation PvP Stats")
    
    return embed

def create_premium_status_embed(guild_data):
    """
    Create a Discord embed showing premium status.
    
    Args:
        guild_data: Dictionary with guild information
        
    Returns:
        discord.Embed object
    """
    premium_tier = guild_data.get("premium_tier", "free")
    tier_info = config.PREMIUM_TIERS.get(premium_tier, config.PREMIUM_TIERS["free"])
    
    embed = discord.Embed(
        title="Premium Status",
        color=config.EMBED_COLOR,
        timestamp=datetime.now()
    )
    
    embed.add_field(
        name="Current Tier", 
        value=tier_info["name"], 
        inline=False
    )
    
    embed.add_field(
        name="Server Slots", 
        value=f"{len(guild_data.get('servers', []))} / {tier_info['server_slots']}", 
        inline=True
    )
    
    features_list = "\n".join([f"✅ {feature.title()}" for feature in tier_info["features"]])
    embed.add_field(
        name="Features", 
        value=features_list, 
        inline=False
    )
    
    # If not on the highest tier, show upgrade info
    if premium_tier != "pro":
        embed.add_field(
            name="Want More?", 
            value="Contact the bot owner to upgrade your premium tier for more features!", 
            inline=False
        )
    
    # Set footer
    embed.set_footer(text="Tower of Temptation PvP Stats")
    
    return embed
