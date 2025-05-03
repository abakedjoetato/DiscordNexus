"""
Configuration settings for the Tower of Temptation PvP Stats Discord Bot.
Loads configuration from environment variables with defaults.
"""
import os

# Bot Configuration
BOT_PREFIX = os.getenv("BOT_PREFIX", "!")
BOT_DESCRIPTION = "Tower of Temptation PvP Statistics Tracking Bot"
OWNER_ID = int(os.getenv("OWNER_ID", "0"))  # Discord ID of the bot owner
HOME_GUILD_ID = int(os.getenv("HOME_GUILD_ID", "0"))  # Main guild ID for bot administration

# Database Configuration
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "pvp_stats_bot")

# SFTP Configuration Defaults
SFTP_TIMEOUT = int(os.getenv("SFTP_TIMEOUT", "30"))  # Timeout in seconds

# Parser Configuration
CSV_UPDATE_INTERVAL = int(os.getenv("CSV_UPDATE_INTERVAL", "60"))  # Seconds between CSV checks
LOG_UPDATE_INTERVAL = int(os.getenv("LOG_UPDATE_INTERVAL", "30"))  # Seconds between log checks
PROGRESS_UPDATE_INTERVAL = int(os.getenv("PROGRESS_UPDATE_INTERVAL", "60"))  # Progress update interval

# Premium Tiers Configuration
PREMIUM_TIERS = {
    "free": {
        "name": "Free",
        "server_slots": 1,
        "features": ["killfeed"]
    },
    "basic": {
        "name": "Basic Premium",
        "server_slots": 3,
        "features": ["killfeed", "events", "connections"]
    },
    "advanced": {
        "name": "Advanced Premium",
        "server_slots": 5,
        "features": ["killfeed", "events", "connections", "stats"]
    },
    "pro": {
        "name": "Professional",
        "server_slots": 10,
        "features": ["killfeed", "events", "connections", "stats", "custom_embeds"]
    }
}

# Embed Configuration
EMBED_COLOR = 0x50C878  # Emerald green color for embeds

# Suicide Messages (for random selection in embeds)
SUICIDE_MESSAGES = [
    "decided that life was too hard",
    "ragequit in spectacular fashion",
    "got tired of living",
    "went to meet their maker",
    "chose the easy way out",
    "didn't want to give someone else the satisfaction",
    "thought the respawn screen looked nice",
    "wanted to test if fall damage was real",
    "found out gravity still works",
    "forgot that jumping from heights is dangerous",
    "decided to try flying without wings",
    "wanted to be one with the ground",
    "thought they could make that jump",
    "just couldn't take it anymore"
]
