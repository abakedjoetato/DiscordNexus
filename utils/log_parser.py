"""
Log parser for Deadside game server logs.

This module provides functions to parse and extract player lifecycle (queue, join, leave)
and game events (missions, helicrashes, airdrops, traders, convoys) from server logs.

The parser tracks:
1. Complete player lifecycle (queue, join, leave server)
2. Mission events (filtering for level 3-4 only)
3. Helicrash events
4. Airdrop events
5. Roaming trader events
6. Convoy events

Events are organized for output to appropriate Discord channels:
- Player joins/leaves -> connections channel
- Mission events -> events channel
- Airdrop, Helicrash, Trader, Convoy events -> events channel
"""

import re
import os
import logging
from datetime import datetime
from typing import Dict, List, Tuple, Set, Optional, Any

logger = logging.getLogger(__name__)

# Regular expressions for parsing different event types
TIMESTAMP_PATTERN = r'\[(\d{4}\.\d{2}\.\d{2}-\d{2}\.\d{2}\.\d{2}):(\d{3})\]\[\s*(\d+)\]'

# Max player count pattern - from command line arguments
MAX_PLAYERS_PATTERN = re.compile(r'-playersmaxcount=(\d+)')
SERVER_ID_PATTERN = re.compile(r'-serverid=([^\s]+)')

# Player lifecycle patterns
PLAYER_REGISTER_PATTERN = re.compile(
    rf'{TIMESTAMP_PATTERN}LogOnline: Warning: Player \|([a-f0-9]+) successfully registered!'
)
PLAYER_UNREGISTER_PATTERN = re.compile(
    rf'{TIMESTAMP_PATTERN}LogOnline: Warning: Player \|([a-f0-9]+) successfully unregistered from the session.'
)
PLAYER_KICK_PATTERN = re.compile(
    rf'{TIMESTAMP_PATTERN}LogSFPS: Error: \[ASFPSGameSession::KickPlayer\] Login = ([^,]+), SteamId = ([^,]*), Msg = (.+)'
)
PLAYER_NAME_PATTERN = re.compile(
    rf'{TIMESTAMP_PATTERN}LogSFPS: \[ASFPSGameSession::OnLogin\] Login = ([^,]+), ID = (\|[a-f0-9]+)'
)

# Mission patterns
MISSION_STATE_PATTERN = re.compile(
    rf'{TIMESTAMP_PATTERN}LogSFPS: Mission ([^\s]+) switched to ([A-Z]+)'
)
MISSION_RESPAWN_PATTERN = re.compile(
    rf'{TIMESTAMP_PATTERN}LogSFPS: Mission ([^\s]+) will respawn in (\d+)'
)

# Game event patterns
AIRDROP_PATTERN = re.compile(
    rf'{TIMESTAMP_PATTERN}LogSFPS: AirDrop switched to ([A-Za-z]+)'
)
HELICRASH_PATTERN = re.compile(
    rf'{TIMESTAMP_PATTERN}LogSFPS: GameplayEvent ([^_]+_[^_]+_HelicrashEvent[^\s]+) switched to ([A-Z]+)'
)
TRADER_PATTERN = re.compile(
    rf'{TIMESTAMP_PATTERN}LogSFPS: GameplayEvent ([^_]+_[^_]+_RoamingTraderEvent[^\s]+) switched to ([A-Z]+)'
)
CONVOY_PATTERN = re.compile(
    rf'{TIMESTAMP_PATTERN}LogSFPS: GameplayEvent ([^_]+_[^_]+_ConvoyEvent[^\s]+) switched to ([A-Z]+)'
)

# Mission level/difficulty regex pattern - looks for numbers that might indicate level
MISSION_LEVEL_PATTERN = re.compile(r'_0?([1-4])_|_0?([1-4])$|_([1-4])_|_([1-4])$|_([1-4])Mis')

class PlayerLifecycleTracker:
    """Tracks player lifecycle events: queue, join, leave."""
    
    def __init__(self):
        self.registered_players: Set[str] = set()
        self.online_players: Dict[str, dict] = {}
        self.player_history: Dict[str, List[dict]] = {}
    
    def register_player(self, timestamp: str, player_id: str) -> dict:
        """Register a player (entering queue)."""
        self.registered_players.add(player_id)
        event = {
            'player_id': player_id,
            'timestamp': timestamp,
            'event_type': 'register',
            'status': 'queued'
        }
        if player_id not in self.player_history:
            self.player_history[player_id] = []
        self.player_history[player_id].append(event)
        return event
    
    def unregister_player(self, timestamp: str, player_id: str) -> dict:
        """Unregister a player (leaving server)."""
        if player_id in self.registered_players:
            self.registered_players.remove(player_id)
        if player_id in self.online_players:
            del self.online_players[player_id]
            
        event = {
            'player_id': player_id,
            'timestamp': timestamp,
            'event_type': 'unregister',
            'status': 'offline'
        }
        if player_id not in self.player_history:
            self.player_history[player_id] = []
        self.player_history[player_id].append(event)
        return event
    
    def kick_player(self, timestamp: str, player_name: str, steam_id: str, reason: str) -> dict:
        """Record player kick event."""
        # For kicks, we use player_name since player_id might not be in the kick message
        event = {
            'player_name': player_name,
            'steam_id': steam_id if steam_id else None,
            'timestamp': timestamp,
            'event_type': 'kick',
            'reason': reason,
            'status': 'offline'
        }
        
        # Add to history by name since we might not have ID
        player_key = f"name:{player_name}"
        if player_key not in self.player_history:
            self.player_history[player_key] = []
        self.player_history[player_key].append(event)
        return event
    
    def get_player_count(self) -> int:
        """Get current online player count."""
        return len(self.online_players)
    
    def get_player_history(self, player_id: str = None) -> List[dict]:
        """Get history for a specific player or all players."""
        if player_id:
            return self.player_history.get(player_id, [])
        
        # Flatten all history entries
        all_history = []
        for events in self.player_history.values():
            all_history.extend(events)
        
        # Sort by timestamp
        return sorted(all_history, key=lambda x: x['timestamp'])

class MissionTracker:
    """Tracks mission events and filters by level."""
    
    def __init__(self):
        self.active_missions: Dict[str, dict] = {}
        self.mission_history: List[dict] = []
        self.mission_states: Dict[str, str] = {}  # Track current state of each mission
    
    def _extract_mission_level(self, mission_name: str) -> Optional[int]:
        """Extract mission level from mission name."""
        match = MISSION_LEVEL_PATTERN.search(mission_name)
        if match:
            # Check each group and return the first non-None value
            for group in match.groups():
                if group is not None:
                    return int(group)
        return None
    
    def update_mission_state(self, timestamp: str, mission_name: str, state: str) -> dict:
        """Update mission state and record history."""
        # Extract mission level
        level = self._extract_mission_level(mission_name)
        
        # Only process ACTIVE state missions or state transitions from other states
        is_important = (state == "ACTIVE") or (
            mission_name in self.mission_states and 
            self.mission_states[mission_name] != state
        )
        
        # Update mission state
        self.mission_states[mission_name] = state
        
        # Create event record
        event = {
            'timestamp': timestamp,
            'mission_name': mission_name,
            'state': state,
            'level': level,
            'is_important': is_important
        }
        
        # For ACTIVE state, update active missions
        if state == "ACTIVE":
            self.active_missions[mission_name] = event
            # Only add to history if it's a level 3 or 4 mission
            if level is not None and level >= 3:
                self.mission_history.append(event)
                return event
        
        # For non-ACTIVE states, it's only important if the mission was previously active
        elif mission_name in self.active_missions and is_important:
            # Remove from active missions if it was there
            if mission_name in self.active_missions:
                del self.active_missions[mission_name]
            
            # Only add to history if it's a level 3 or 4 mission
            if level is not None and level >= 3:
                self.mission_history.append(event)
                return event
        
        return event if is_important else None
    
    def get_high_level_missions(self) -> List[dict]:
        """Get all recorded high-level (3-4) mission events."""
        return [
            event for event in self.mission_history 
            if event.get('level', 0) >= 3
        ]
    
    def get_active_high_level_missions(self) -> List[dict]:
        """Get currently active high-level (3-4) missions."""
        return [
            mission for mission in self.active_missions.values()
            if mission.get('level', 0) >= 3
        ]

class GameEventTracker:
    """Tracks game events like airdrops, helicrashes, traders, and convoys."""
    
    def __init__(self):
        self.active_events: Dict[str, dict] = {}
        self.event_history: List[dict] = []
        self.event_states: Dict[str, str] = {}  # Track current state of each event
    
    def track_airdrop(self, timestamp: str, state: str) -> dict:
        """Track airdrop event state changes."""
        event_id = "AirDrop"
        
        # Determine if this is an important state change
        is_important = (state in ["Flying", "Dropping"]) or (
            event_id in self.event_states and 
            self.event_states[event_id] != state
        )
        
        # Update event state
        self.event_states[event_id] = state
        
        # Create event record
        event = {
            'timestamp': timestamp,
            'event_type': 'airdrop',
            'state': state,
            'is_important': is_important
        }
        
        # For important states, update tracking
        if is_important:
            if state in ["Flying", "Dropping"]:
                self.active_events[event_id] = event
            elif event_id in self.active_events:
                del self.active_events[event_id]
            
            self.event_history.append(event)
            return event
        
        return None
    
    def track_gameplay_event(self, timestamp: str, event_id: str, state: str, event_type: str) -> dict:
        """Track gameplay events like helicrashes, traders, and convoys."""
        # Determine if this is an important state change
        is_important = (state == "ACTIVE") or (
            event_id in self.event_states and 
            self.event_states[event_id] != state
        )
        
        # Update event state
        self.event_states[event_id] = state
        
        # Create event record
        event = {
            'timestamp': timestamp,
            'event_id': event_id,
            'event_type': event_type,
            'state': state,
            'is_important': is_important
        }
        
        # For important states, update tracking
        if is_important:
            if state == "ACTIVE":
                self.active_events[event_id] = event
            elif event_id in self.active_events:
                del self.active_events[event_id]
            
            self.event_history.append(event)
            return event
        
        return None
    
    def get_active_events(self, event_type: Optional[str] = None) -> List[dict]:
        """Get active events, optionally filtered by type."""
        if event_type:
            return [
                event for event in self.active_events.values()
                if event['event_type'] == event_type
            ]
        return list(self.active_events.values())
    
    def get_event_history(self, event_type: Optional[str] = None) -> List[dict]:
        """Get event history, optionally filtered by type."""
        if event_type:
            return [
                event for event in self.event_history
                if event['event_type'] == event_type
            ]
        return self.event_history

class LogParser:
    """Main log parser class that coordinates all trackers."""
    
    def __init__(self):
        self.player_tracker = PlayerLifecycleTracker()
        self.mission_tracker = MissionTracker()
        self.event_tracker = GameEventTracker()
        self.processed_lines = 0
        self.last_processed_timestamp = None
        self.max_player_count = None
        self.server_id = None
        self.server_name = None
        self.player_names = {}  # Map player_id to player_name
    
    def parse_line(self, line: str) -> Dict[str, Any]:
        """Parse a single log line and update appropriate trackers."""
        self.processed_lines += 1
        result = {}
        
        # Check for server configuration info
        if self.max_player_count is None:
            max_players_match = MAX_PLAYERS_PATTERN.search(line)
            if max_players_match:
                self.max_player_count = int(max_players_match.group(1))
                result['server_config'] = {'max_player_count': self.max_player_count}
                
        if self.server_id is None:
            server_id_match = SERVER_ID_PATTERN.search(line)
            if server_id_match:
                self.server_id = server_id_match.group(1)
                # Extract the server name from the server ID
                parts = self.server_id.split('__l_')
                if parts and len(parts) > 0:
                    self.server_name = parts[0].replace('_', ' ')
                result['server_config'] = {
                    'server_id': self.server_id,
                    'server_name': self.server_name
                }
        
        # Check player name mapping
        match = PLAYER_NAME_PATTERN.search(line)
        if match:
            timestamp = f"{match.group(1)}:{match.group(2)}"
            player_name = match.group(4)
            player_id = match.group(5)
            
            # Store the player name mapping
            self.player_names[player_id] = player_name
            
            # Add player to online players
            self.player_tracker.online_players[player_id] = {
                'player_id': player_id,
                'player_name': player_name,
                'timestamp': timestamp,
                'status': 'online'
            }
            
            result['player_join'] = {
                'player_id': player_id,
                'player_name': player_name,
                'timestamp': timestamp,
                'event_type': 'join',
                'status': 'online'
            }
            
            self.last_processed_timestamp = timestamp
            return result
        
        # Check player lifecycle events
        match = PLAYER_REGISTER_PATTERN.search(line)
        if match:
            timestamp = f"{match.group(1)}:{match.group(2)}"
            player_id = match.group(4)
            result['player_register'] = self.player_tracker.register_player(timestamp, player_id)
            
            # If we know this player's name, add it to the event
            if player_id in self.player_names:
                result['player_register']['player_name'] = self.player_names[player_id]
                
            self.last_processed_timestamp = timestamp
            return result
        
        match = PLAYER_UNREGISTER_PATTERN.search(line)
        if match:
            timestamp = f"{match.group(1)}:{match.group(2)}"
            player_id = match.group(4)
            result['player_unregister'] = self.player_tracker.unregister_player(timestamp, player_id)
            
            # If we know this player's name, add it to the event
            if player_id in self.player_names:
                result['player_unregister']['player_name'] = self.player_names[player_id]
                
            self.last_processed_timestamp = timestamp
            return result
        
        match = PLAYER_KICK_PATTERN.search(line)
        if match:
            timestamp = f"{match.group(1)}:{match.group(2)}"
            player_name = match.group(4)
            steam_id = match.group(5)
            reason = match.group(6)
            result['player_kick'] = self.player_tracker.kick_player(timestamp, player_name, steam_id, reason)
            self.last_processed_timestamp = timestamp
            return result
        
        # Check mission events
        match = MISSION_STATE_PATTERN.search(line)
        if match:
            timestamp = f"{match.group(1)}:{match.group(2)}"
            mission_name = match.group(4)
            state = match.group(5)
            mission_event = self.mission_tracker.update_mission_state(timestamp, mission_name, state)
            if mission_event and mission_event.get('is_important', False):
                result['mission'] = mission_event
            self.last_processed_timestamp = timestamp
            return result
        
        # Check airdrop events
        match = AIRDROP_PATTERN.search(line)
        if match:
            timestamp = f"{match.group(1)}:{match.group(2)}"
            state = match.group(4)
            airdrop_event = self.event_tracker.track_airdrop(timestamp, state)
            if airdrop_event and airdrop_event.get('is_important', False):
                result['airdrop'] = airdrop_event
            self.last_processed_timestamp = timestamp
            return result
        
        # Check helicrash events
        match = HELICRASH_PATTERN.search(line)
        if match:
            timestamp = f"{match.group(1)}:{match.group(2)}"
            event_id = match.group(4)
            state = match.group(5)
            helicrash_event = self.event_tracker.track_gameplay_event(timestamp, event_id, state, 'helicrash')
            if helicrash_event and helicrash_event.get('is_important', False):
                result['helicrash'] = helicrash_event
            self.last_processed_timestamp = timestamp
            return result
        
        # Check trader events
        match = TRADER_PATTERN.search(line)
        if match:
            timestamp = f"{match.group(1)}:{match.group(2)}"
            event_id = match.group(4)
            state = match.group(5)
            trader_event = self.event_tracker.track_gameplay_event(timestamp, event_id, state, 'trader')
            if trader_event and trader_event.get('is_important', False):
                result['trader'] = trader_event
            self.last_processed_timestamp = timestamp
            return result
        
        # Check convoy events
        match = CONVOY_PATTERN.search(line)
        if match:
            timestamp = f"{match.group(1)}:{match.group(2)}"
            event_id = match.group(4)
            state = match.group(5)
            convoy_event = self.event_tracker.track_gameplay_event(timestamp, event_id, state, 'convoy')
            if convoy_event and convoy_event.get('is_important', False):
                result['convoy'] = convoy_event
            self.last_processed_timestamp = timestamp
            return result
        
        return result
    
    def parse_file(self, file_path: str, start_line: int = 0, max_lines: Optional[int] = None) -> List[Dict[str, Any]]:
        """Parse a log file and return all important events."""
        important_events = []
        
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            # Skip lines if needed
            if start_line > 0:
                for _ in range(start_line):
                    next(f, None)
            
            # Process lines
            for i, line in enumerate(f):
                if max_lines and i >= max_lines:
                    break
                
                event = self.parse_line(line)
                if any(key in event for key in ['player_register', 'player_unregister', 'player_kick', 
                                               'mission', 'airdrop', 'helicrash', 'trader', 'convoy']):
                    important_events.append(event)
        
        return important_events
    
    def get_player_count(self) -> int:
        """Get current online player count."""
        return self.player_tracker.get_player_count()
    
    def get_player_history(self, player_id: Optional[str] = None) -> List[dict]:
        """Get player history."""
        return self.player_tracker.get_player_history(player_id)
    
    def get_active_high_level_missions(self) -> List[dict]:
        """Get active high-level missions (level 3-4)."""
        return self.mission_tracker.get_active_high_level_missions()
    
    def get_active_events(self, event_type: Optional[str] = None) -> List[dict]:
        """Get active game events."""
        return self.event_tracker.get_active_events(event_type)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get parser statistics."""
        return {
            'processed_lines': self.processed_lines,
            'last_timestamp': self.last_processed_timestamp,
            'player_count': self.player_tracker.get_player_count(),
            'max_player_count': self.max_player_count,
            'server_id': self.server_id,
            'server_name': self.server_name,
            'active_high_level_missions': len(self.mission_tracker.get_active_high_level_missions()),
            'active_events': {
                'airdrop': len(self.event_tracker.get_active_events('airdrop')),
                'helicrash': len(self.event_tracker.get_active_events('helicrash')),
                'trader': len(self.event_tracker.get_active_events('trader')),
                'convoy': len(self.event_tracker.get_active_events('convoy'))
            }
        }
        
    def get_formatted_player_count(self) -> str:
        """Get formatted player count for voice channel name."""
        if self.max_player_count:
            return f"Online: {self.player_tracker.get_player_count()}/{self.max_player_count}"
        return f"Online: {self.player_tracker.get_player_count()}"
        
    def get_connections_events(self) -> List[Dict[str, Any]]:
        """Get player connection events for the connections channel."""
        events = []
        for player_id, history in self.player_tracker.player_history.items():
            for event in history:
                if event['event_type'] in ['register', 'unregister', 'kick', 'join']:
                    # Add player name if available
                    if player_id in self.player_names and 'player_name' not in event:
                        event['player_name'] = self.player_names[player_id]
                    events.append(event)
        return sorted(events, key=lambda x: x['timestamp'])
    
    def get_game_events(self) -> List[Dict[str, Any]]:
        """Get game events for the events channel."""
        events = []
        
        # Add high-level mission events
        for mission in self.mission_tracker.get_high_level_missions():
            if mission['state'] == 'ACTIVE' and mission.get('level', 0) >= 3:
                events.append({
                    'timestamp': mission['timestamp'],
                    'event_type': 'mission',
                    'mission_name': mission['mission_name'],
                    'mission_level': mission['level'],
                    'state': mission['state']
                })
        
        # Add airdrop events
        for event in self.event_tracker.get_event_history('airdrop'):
            if event['state'] in ['Flying', 'Dropping']:
                events.append({
                    'timestamp': event['timestamp'],
                    'event_type': 'airdrop',
                    'state': event['state']
                })
        
        # Add helicrash, trader, convoy events
        for event_type in ['helicrash', 'trader', 'convoy']:
            for event in self.event_tracker.get_event_history(event_type):
                if event['state'] == 'ACTIVE':
                    events.append({
                        'timestamp': event['timestamp'],
                        'event_type': event_type,
                        'event_id': event['event_id'],
                        'state': event['state']
                    })
        
        return sorted(events, key=lambda x: x['timestamp'])


# Function to create a parser and process a log file
def parse_log_file(file_path: str, start_line: int = 0, max_lines: Optional[int] = None) -> Tuple[LogParser, List[Dict[str, Any]]]:
    """Parse a log file and return the parser and important events."""
    parser = LogParser()
    events = parser.parse_file(file_path, start_line, max_lines)
    return parser, events