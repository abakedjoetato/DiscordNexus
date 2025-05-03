"""
Main entry point for the Tower of Temptation PvP Stats Discord Bot.
This file initializes the bot and database connection.
"""
import asyncio
import logging
import os
from bot import bot
import database

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

async def main():
    """Initialize the application and start the bot."""
    try:
        # Initialize database
        await database.initialize()
        logger.info("Database connection established")
        
        # Start the bot with token from environment
        token = os.getenv("DISCORD_TOKEN")
        if not token:
            raise ValueError("DISCORD_TOKEN environment variable not set")
        
        logger.info("Starting bot...")
        await bot.start(token)
    except Exception as e:
        logger.error(f"Error starting application: {e}")
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot shutting down...")
