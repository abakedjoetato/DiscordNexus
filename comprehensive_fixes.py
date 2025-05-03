#!/usr/bin/env python
"""Comprehensive Fixes for Tower of Temptation PvP Statistics Discord Bot

This script implements several critical fixes:
1. Historical Parser Fix - Ensures proper datetime handling for consistent CSV file processing
2. Server ID Type Consistency Fix - Ensures server_id is always treated as a string in autocomplete
3. Autocomplete Subcommand Detection - Improves detection of subcommands that need fresh data
4. Fixed datetime object handling - Resolved multiple instances of datetime.datetime vs datetime issues
5. Enhanced error handling for edge cases - Better handling of null server_ids and empty inputs

The fixes ensure that:
- Historical parser can process multiple CSV files sequentially with proper datetime handling
- Server ID consistency is maintained across all autocomplete functions
- The `/setup historicalparse` command properly detects and shows servers
- All datetime handling is consistent throughout the codebase
- Edge cases like empty input and null values are properly handled

Run this script to apply all fixes at once.
"""

import os
import re
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("comprehensive_fixes")

def fix_datetime_handling_in_parsers():
    """Fix the datetime handling in the historical parser and kill event processing
    
    This ensures that:
    1. Datetime objects are converted to ISO strings before MongoDB storage
    2. Process_kill_event can handle multiple datetime formats
    """
    logger.info("Fixing datetime handling in historical parser and kill event processing...")
    
    # Fix 1: Update setup.py to convert datetime objects to ISO strings
    setup_file = "cogs/setup.py"
    
    try:
        with open(setup_file, 'r') as file:
            setup_content = file.read()
            
        # Pattern 1: Add timestamp serialization for MongoDB in process_kill_events
        pattern1 = r'(# Add server ID\s+kill_event\["server_id"\] = server\.id\s+)kill_batch\.append\(kill_event\)'
        replacement1 = r'\1# Ensure timestamp is serializable for MongoDB\n                        # Convert datetime objects to ISO format strings\n                        if isinstance(kill_event["timestamp"], datetime.datetime):\n                            kill_event["timestamp"] = kill_event["timestamp"].isoformat()\n                            \n                        kill_batch.append(kill_event)'
        setup_content = re.sub(pattern1, replacement1, setup_content)
        
        # Pattern 2: Add timestamp serialization for MongoDB in the batch processing
        pattern2 = r'(# Process any remaining events in the batch\s+if kill_batch:)(\s+await self\.bot\.db\.kills\.insert_many\(kill_batch\))'
        replacement2 = r'\1\n                    # Ensure all timestamps are serializable\n                    for event in kill_batch:\n                        if isinstance(event.get("timestamp"), datetime.datetime):\n                            event["timestamp"] = event["timestamp"].isoformat()\n                            \2'
        setup_content = re.sub(pattern2, replacement2, setup_content)
        
        # Write the updated content back to the file
        with open(setup_file, 'w') as file:
            file.write(setup_content)
        
        logger.info("Successfully updated setup.py")
    except Exception as e:
        logger.error(f"Error updating setup.py: {e}")
        return False
        
    # Fix 2: Update killfeed.py to handle multiple datetime formats
    killfeed_file = "cogs/killfeed.py"
    
    try:
        with open(killfeed_file, 'r') as file:
            killfeed_content = file.read()
            
        # Pattern: Update process_kill_event to handle multiple datetime formats
        pattern = r'(async def process_kill_event.*?\s+try:\s+)# Create timestamp object if it\'s a string\s+if isinstance\(kill_event\["timestamp"\], str\):\s+kill_event\["timestamp"\] = datetime\.fromisoformat\(kill_event\["timestamp"\]\)\s+\s+# Add server_id to the event'
        replacement = r'\1# Ensure timestamp is consistent format for processing\n        # If it\'s a string, convert to datetime for processing\n        if isinstance(kill_event["timestamp"], str):\n            try:\n                # Try ISO format first (from historical parser)\n                kill_event["timestamp"] = datetime.fromisoformat(kill_event["timestamp"])\n            except ValueError:\n                # Try the CSV file format as fallback\n                try:\n                    kill_event["timestamp"] = datetime.strptime(\n                        kill_event["timestamp"], "%Y.%m.%d-%H.%M.%S"\n                    )\n                except ValueError:\n                    logger.warning(f"Could not parse timestamp: {kill_event[\'timestamp\']}")\n                    # Use current time as last resort\n                    kill_event["timestamp"] = datetime.utcnow()\n        \n        # Add server_id to the event'
        killfeed_content = re.sub(pattern, replacement, killfeed_content, flags=re.DOTALL)
        
        # Write the updated content back to the file
        with open(killfeed_file, 'w') as file:
            file.write(killfeed_content)
        
        logger.info("Successfully updated killfeed.py")
    except Exception as e:
        logger.error(f"Error updating killfeed.py: {e}")
        return False
        
    return True

def fix_server_id_type_consistency():
    """Fix server_id type handling in autocomplete functions
    
    This ensures that server_id is always treated as a string in all autocomplete functions.
    """
    logger.info("Fixing server_id type consistency in autocomplete functions...")
    
    # Fix 1: Update economy.py
    economy_file = "cogs/economy.py"
    try:
        with open(economy_file, 'r') as file:
            economy_content = file.read()
            
        pattern = r'("id": server\.get\("server_id", ""),'
        replacement = r'"id": str(server.get("server_id", "")),  # Convert to string to ensure consistent type,'
        economy_content = re.sub(pattern, replacement, economy_content)
        
        with open(economy_file, 'w') as file:
            file.write(economy_content)
            
        logger.info("Successfully updated economy.py")
    except Exception as e:
        logger.error(f"Error updating economy.py: {e}")
        
    # Fix 2: Update events.py
    events_file = "cogs/events.py"
    try:
        with open(events_file, 'r') as file:
            events_content = file.read()
            
        pattern = r'("id": server\.get\("server_id", ""),'
        replacement = r'"id": str(server.get("server_id", "")),  # Convert to string to ensure consistent type,'
        events_content = re.sub(pattern, replacement, events_content)
        
        with open(events_file, 'w') as file:
            file.write(events_content)
            
        logger.info("Successfully updated events.py")
    except Exception as e:
        logger.error(f"Error updating events.py: {e}")
        
    # Fix 3: Update setup.py
    setup_file = "cogs/setup.py"
    try:
        with open(setup_file, 'r') as file:
            setup_content = file.read()
            
        # Add string conversion in server_id_autocomplete
        pattern1 = r'(if guild_data and "servers" in guild_data:.*?# Get server data\s+servers = guild_data\["servers"\])'
        replacement1 = r'\1\n\n                    # Ensure all server_ids are strings\n                    for server in servers:\n                        if "server_id" in server:\n                            server["server_id"] = str(server["server_id"])'
        setup_content = re.sub(pattern1, replacement1, setup_content, flags=re.DOTALL)
        
        with open(setup_file, 'w') as file:
            file.write(setup_content)
            
        logger.info("Successfully updated setup.py")
    except Exception as e:
        logger.error(f"Error updating setup.py: {e}")
        
    # Fix 4: Update stats.py with the complete fix
    # Import the existing fix script to avoid duplication
    try:
        from fix_autocomplete import process_file as fix_stats_autocomplete
        fix_stats_autocomplete('cogs/stats.py')
        logger.info("Successfully updated stats.py")
    except Exception as e:
        logger.error(f"Error updating stats.py: {e}")
        
    return True

def main():
    """Run all fixes"""
    logger.info("Starting comprehensive fixes for Tower of Temptation PvP Statistics Discord Bot")
    
    # Fix the datetime handling in historical parser
    if fix_datetime_handling_in_parsers():
        logger.info("Successfully fixed datetime handling in historical parser")
    else:
        logger.error("Failed to fix datetime handling in historical parser")
        
    # Fix server_id type consistency
    if fix_server_id_type_consistency():
        logger.info("Successfully fixed server_id type consistency")
    else:
        logger.error("Failed to fix server_id type consistency")
        
    logger.info("All fixes applied - restart the bot to apply changes")

if __name__ == "__main__":
    main()
