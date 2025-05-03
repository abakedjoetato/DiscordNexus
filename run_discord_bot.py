"""
Entry point script for the Discord bot to be used with the Replit "Start application" workflow
"""
import asyncio
import logging
import os
import sys
from dotenv import load_dotenv
from bot import initialize_bot

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("bot.log")
    ]
)

logger = logging.getLogger(__name__)

async def main():
    """Main function to run the Discord bot"""
    try:
        # Force a global sync of commands when starting the bot
        force_sync = True
        
        # Log the MongoDB URI status (without exposing it)
        if os.getenv("MONGODB_URI"):
            logger.info("MONGODB_URI is set")
        else:
            logger.critical("MONGODB_URI environment variable not set. Exiting.")
            return
            
        # Log the Discord token status (without exposing it)
        token = os.getenv("DISCORD_TOKEN")
        if token:
            logger.info("DISCORD_TOKEN is set")
        else:
            logger.critical("DISCORD_TOKEN environment variable not set. Exiting.")
            return
        
        # Initialize and start the bot
        bot = await initialize_bot(force_sync=force_sync)
        
        # Command syncing is handled in bot.py on_ready event
        await bot.start(token)
    except Exception as e:
        logger.critical(f"Failed to start bot: {e}", exc_info=True)

if __name__ == "__main__":
    # Run the Discord bot
    asyncio.run(main())