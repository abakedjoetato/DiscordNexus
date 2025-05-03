"""
Parser for game events and player connections from log files.
"""
import logging
import re
from datetime import datetime

logger = logging.getLogger(__name__)

class EventsParser:
    """
    Parser for game events and player connections from log files.
    Extracts mission events, airdrops, player connections, etc.
    """
    
    def __init__(self, server_id):
        """
        Initialize the parser.
        
        Args:
            server_id: Server ID for identification
        """
        self.server_id = server_id
        
        # Regular expressions for log parsing
        self.connection_pattern = re.compile(r"Player '(.+)' connected( \((.+)\))?")
        self.disconnection_pattern = re.compile(r"Player '(.+)' disconnected")
        self.mission_pattern = re.compile(r"Mission '(.+)' (started|completed|failed)")
        self.airdrop_pattern = re.compile(r"Airdrop (spawned|delivered) at (.+)")
        self.crash_pattern = re.compile(r"Helicopter crash (spawned|despawned) at (.+)")
        self.trader_pattern = re.compile(r"Trader (arrived|departed) at (.+)")
        self.convoy_pattern = re.compile(r"Convoy (spawned|completed|failed) at (.+)")
        self.encounter_pattern = re.compile(r"Encounter (started|completed) at (.+)")
    
    async def parse_log(self, log_data, last_position=0):
        """
        Parse log data for events and connections.
        
        Args:
            log_data: List of lines from the log file
            last_position: Last parsed position
            
        Returns:
            Tuple of (events, connections, new_position)
        """
        events = []
        connections = []
        new_position = last_position
        
        try:
            for line_num, line in enumerate(log_data, start=1):
                # Skip already parsed lines
                if line_num <= last_position:
                    continue
                
                # Skip empty lines
                if not line.strip():
                    continue
                
                # Process line for events and connections
                event = self._process_event_line(line)
                if event:
                    events.append(event)
                
                connection = self._process_connection_line(line)
                if connection:
                    connections.append(connection)
                
                new_position = line_num
        except Exception as e:
            logger.error(f"Error parsing log data for server {self.server_id}: {e}")
        
        return events, connections, new_position
    
    def _process_event_line(self, line):
        """
        Process a log line for game events.
        
        Args:
            line: Log line string
            
        Returns:
            Dictionary with event information or None if no event
        """
        try:
            # Extract timestamp if present (format: [HH:MM:SS])
            timestamp_match = re.match(r"\[(\d{2}:\d{2}:\d{2})\]", line)
            timestamp = None
            if timestamp_match:
                time_str = timestamp_match.group(1)
                now = datetime.now()
                timestamp = datetime(
                    now.year, now.month, now.day,
                    int(time_str.split(':')[0]),
                    int(time_str.split(':')[1]),
                    int(time_str.split(':')[2])
                )
                
                # Remove timestamp from line for further processing
                line = line[timestamp_match.end():].strip()
            else:
                timestamp = datetime.now()
            
            # Check for mission events
            mission_match = self.mission_pattern.search(line)
            if mission_match:
                return {
                    "server_id": self.server_id,
                    "event_type": "mission",
                    "name": mission_match.group(1),
                    "status": mission_match.group(2),
                    "timestamp": timestamp
                }
            
            # Check for airdrop events
            airdrop_match = self.airdrop_pattern.search(line)
            if airdrop_match:
                return {
                    "server_id": self.server_id,
                    "event_type": "airdrop",
                    "status": airdrop_match.group(1),
                    "location": airdrop_match.group(2),
                    "timestamp": timestamp
                }
            
            # Check for crash events
            crash_match = self.crash_pattern.search(line)
            if crash_match:
                return {
                    "server_id": self.server_id,
                    "event_type": "crash",
                    "status": crash_match.group(1),
                    "location": crash_match.group(2),
                    "timestamp": timestamp
                }
            
            # Check for trader events
            trader_match = self.trader_pattern.search(line)
            if trader_match:
                return {
                    "server_id": self.server_id,
                    "event_type": "trader",
                    "status": trader_match.group(1),
                    "location": trader_match.group(2),
                    "timestamp": timestamp
                }
            
            # Check for convoy events
            convoy_match = self.convoy_pattern.search(line)
            if convoy_match:
                return {
                    "server_id": self.server_id,
                    "event_type": "convoy",
                    "status": convoy_match.group(1),
                    "location": convoy_match.group(2),
                    "timestamp": timestamp
                }
            
            # Check for encounter events
            encounter_match = self.encounter_pattern.search(line)
            if encounter_match:
                return {
                    "server_id": self.server_id,
                    "event_type": "encounter",
                    "status": encounter_match.group(1),
                    "location": encounter_match.group(2),
                    "timestamp": timestamp
                }
            
            return None
        except Exception as e:
            logger.error(f"Error processing event line for server {self.server_id}: {e}")
            return None
    
    def _process_connection_line(self, line):
        """
        Process a log line for player connections.
        
        Args:
            line: Log line string
            
        Returns:
            Dictionary with connection information or None if no connection
        """
        try:
            # Extract timestamp if present (format: [HH:MM:SS])
            timestamp_match = re.match(r"\[(\d{2}:\d{2}:\d{2})\]", line)
            timestamp = None
            if timestamp_match:
                time_str = timestamp_match.group(1)
                now = datetime.now()
                timestamp = datetime(
                    now.year, now.month, now.day,
                    int(time_str.split(':')[0]),
                    int(time_str.split(':')[1]),
                    int(time_str.split(':')[2])
                )
                
                # Remove timestamp from line for further processing
                line = line[timestamp_match.end():].strip()
            else:
                timestamp = datetime.now()
            
            # Check for player connections
            connection_match = self.connection_pattern.search(line)
            if connection_match:
                platform = connection_match.group(3) if connection_match.group(3) else "pc"
                is_console = platform.lower() != "pc"
                
                return {
                    "server_id": self.server_id,
                    "player_name": connection_match.group(1),
                    "status": "connected",
                    "timestamp": timestamp,
                    "is_console": is_console,
                    "platform": platform
                }
            
            # Check for player disconnections
            disconnection_match = self.disconnection_pattern.search(line)
            if disconnection_match:
                return {
                    "server_id": self.server_id,
                    "player_name": disconnection_match.group(1),
                    "status": "disconnected",
                    "timestamp": timestamp
                }
            
            return None
        except Exception as e:
            logger.error(f"Error processing connection line for server {self.server_id}: {e}")
            return None
    
    def count_online_players(self, connections):
        """
        Count currently online players based on connection/disconnection events.
        
        Args:
            connections: List of connection events
            
        Returns:
            Dictionary with online player counts
        """
        online_players = set()
        console_players = set()
        pc_players = set()
        
        # Process connections chronologically
        for conn in sorted(connections, key=lambda x: x["timestamp"]):
            player_name = conn["player_name"]
            
            if conn["status"] == "connected":
                online_players.add(player_name)
                
                # Track platform
                if conn.get("is_console", False):
                    console_players.add(player_name)
                else:
                    pc_players.add(player_name)
            elif conn["status"] == "disconnected" and player_name in online_players:
                online_players.remove(player_name)
                
                # Remove from platform tracking
                if player_name in console_players:
                    console_players.remove(player_name)
                if player_name in pc_players:
                    pc_players.remove(player_name)
        
        return {
            "total": len(online_players),
            "console": len(console_players),
            "pc": len(pc_players)
        }
