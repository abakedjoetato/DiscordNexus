"""
Discord bot main module. Initializes the Pycord bot and loads extensions.
"""
import logging
import os
import sys
from datetime import datetime

import discord
from discord.ext import commands

import config

logger = logging.getLogger(__name__)

# Define intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

# Initialize bot
bot = commands.Bot(
    command_prefix=config.BOT_PREFIX,
    description=config.BOT_DESCRIPTION,
    intents=intents
)

@bot.event
async def on_ready():
    """Called when the bot is ready and connected to Discord."""
    logger.info(f"Logged in as {bot.user.name} (ID: {bot.user.id})")
    logger.info(f"Connected to {len(bot.guilds)} guilds")
    
    # Load all cogs
    await load_extensions()
    
    # Set bot presence
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="PvP Statistics"
        )
    )

async def load_extensions():
    """Load all bot extensions (cogs)."""
    try:
        # Core cogs
        await bot.load_extension("cogs.admin")
        await bot.load_extension("cogs.killfeed")
        await bot.load_extension("cogs.stats")
        await bot.load_extension("cogs.events")
        await bot.load_extension("cogs.premium")
        
        logger.info("All extensions loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load extensions: {e}")
        raise

@bot.event
async def on_guild_join(guild):
    """Called when the bot joins a new guild."""
    logger.info(f"Joined new guild: {guild.name} (ID: {guild.id})")
    
    # Create guild document in database with default settings
    from database import update_guild
    
    guild_data = {
        "guild_id": guild.id,
        "name": guild.name,
        "joined_at": datetime.utcnow(),
        "premium_tier": "free",
        "admin_role_id": None,
    }
    
    await update_guild(guild.id, guild_data)
    
    # Try to find the owner or an admin to message
    owner = guild.owner
    if owner:
        try:
            await owner.send(
                f"Thank you for adding the Tower of Temptation PvP Stats Bot to your server!\n\n"
                f"To get started, use `{config.BOT_PREFIX}setup` to configure your server settings and "
                f"`{config.BOT_PREFIX}addserver` to connect your game server.\n\n"
                f"For more information, use `{config.BOT_PREFIX}help`."
            )
        except discord.errors.Forbidden:
            # Can't message the owner, try to find a text channel to send to
            general_channel = discord.utils.get(guild.text_channels, name="general")
            if general_channel:
                await general_channel.send(
                    f"Thank you for adding the Tower of Temptation PvP Stats Bot!\n\n"
                    f"To get started, use `{config.BOT_PREFIX}setup` to configure your server settings and "
                    f"`{config.BOT_PREFIX}addserver` to connect your game server.\n\n"
                    f"For more information, use `{config.BOT_PREFIX}help`."
                )

@bot.event
async def on_guild_remove(guild):
    """Called when the bot is removed from a guild."""
    logger.info(f"Left guild: {guild.name} (ID: {guild.id})")
    
    # We'll keep the guild data in the database in case they add the bot back

@bot.event
async def on_command_error(ctx, error):
    """Global error handler for bot commands."""
    if isinstance(error, commands.CommandNotFound):
        return
    
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("You don't have the necessary permissions to use this command.")
        return
    
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"Missing required argument: {error.param.name}. Please use `{config.BOT_PREFIX}help {ctx.command}` for more information.")
        return
    
    if isinstance(error, commands.BadArgument):
        await ctx.send(f"Invalid argument provided. Please use `{config.BOT_PREFIX}help {ctx.command}` for more information.")
        return
    
    # For all other errors, log them and notify the user
    logger.error(f"Command error in {ctx.command}: {error}")
    await ctx.send("An error occurred while processing your command. Please try again later.")

# Help command customization
class PvPHelpCommand(commands.MinimalHelpCommand):
    """Custom help command for the PvP Stats bot."""
    
    async def send_bot_help(self, mapping):
        """Send help for all commands."""
        ctx = self.context
        embed = discord.Embed(
            title="Tower of Temptation PvP Stats Bot Help",
            color=config.EMBED_COLOR,
            description="Here are all the available commands:"
        )
        
        # Sort commands by cog
        for cog, commands in mapping.items():
            filtered = await self.filter_commands(commands, sort=True)
            if filtered:
                cog_name = getattr(cog, "qualified_name", "No Category")
                embed.add_field(
                    name=cog_name,
                    value="\n".join(f"`{config.BOT_PREFIX}{c.name}` - {c.short_doc}" for c in filtered),
                    inline=False
                )
        
        embed.set_footer(text=f"Use {config.BOT_PREFIX}help <command> for more info on a command.")
        await ctx.send(embed=embed)
    
    async def send_command_help(self, command):
        """Send help for a specific command."""
        ctx = self.context
        embed = discord.Embed(
            title=f"Command: {config.BOT_PREFIX}{command.qualified_name}",
            color=config.EMBED_COLOR,
            description=command.help or "No description available."
        )
        
        if command.aliases:
            embed.add_field(
                name="Aliases",
                value=", ".join(f"`{config.BOT_PREFIX}{alias}`" for alias in command.aliases),
                inline=False
            )
        
        if command.signature:
            embed.add_field(
                name="Usage",
                value=f"`{config.BOT_PREFIX}{command.qualified_name} {command.signature}`",
                inline=False
            )
        
        embed.set_footer(text=f"<> = required, [] = optional")
        await ctx.send(embed=embed)

# Set custom help command
bot.help_command = PvPHelpCommand()
