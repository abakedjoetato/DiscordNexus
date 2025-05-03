"""
Player model for holding player statistics and data.
"""
from datetime import datetime

class Player:
    """
    Player model representing a game player and their statistics.
    """
    
    def __init__(
        self,
        server_id,
        player_name,
        kills=0,
        deaths=0,
        suicides=0,
        longest_shot=0,
        kill_streak=0,
        death_streak=0,
        max_kill_streak=0,
        max_death_streak=0,
        weapons=None,
        is_online=False,
        is_console=False,
        last_connected=None,
        last_disconnected=None,
        first_seen=None,
        last_updated=None
    ):
        """
        Initialize a player object.
        
        Args:
            server_id: Server ID this player belongs to
            player_name: Player's in-game name
            kills: Total kills count
            deaths: Total deaths count
            suicides: Total suicides count
            longest_shot: Longest kill distance in meters
            kill_streak: Current kill streak
            death_streak: Current death streak
            max_kill_streak: Highest kill streak
            max_death_streak: Highest death streak
            weapons: Dictionary mapping weapon names to kill counts
            is_online: Boolean indicating if player is currently online
            is_console: Boolean indicating if player is on console
            last_connected: Datetime of last connection
            last_disconnected: Datetime of last disconnection
            first_seen: Datetime when player was first seen
            last_updated: Datetime of last stats update
        """
        self.server_id = server_id
        self.player_name = player_name
        self.kills = kills
        self.deaths = deaths
        self.suicides = suicides
        self.longest_shot = longest_shot
        self.kill_streak = kill_streak
        self.death_streak = death_streak
        self.max_kill_streak = max_kill_streak
        self.max_death_streak = max_death_streak
        self.weapons = weapons or {}
        self.is_online = is_online
        self.is_console = is_console
        self.last_connected = last_connected
        self.last_disconnected = last_disconnected
        self.first_seen = first_seen or datetime.utcnow()
        self.last_updated = last_updated or datetime.utcnow()
    
    @classmethod
    def from_dict(cls, data):
        """
        Create a Player object from a dictionary.
        
        Args:
            data: Dictionary containing player data
            
        Returns:
            Player object
        """
        return cls(
            server_id=data.get('server_id'),
            player_name=data.get('player_name'),
            kills=data.get('kills', 0),
            deaths=data.get('deaths', 0),
            suicides=data.get('suicides', 0),
            longest_shot=data.get('longest_shot', 0),
            kill_streak=data.get('kill_streak', 0),
            death_streak=data.get('death_streak', 0),
            max_kill_streak=data.get('max_kill_streak', 0),
            max_death_streak=data.get('max_death_streak', 0),
            weapons=data.get('weapons', {}),
            is_online=data.get('is_online', False),
            is_console=data.get('is_console', False),
            last_connected=data.get('last_connected'),
            last_disconnected=data.get('last_disconnected'),
            first_seen=data.get('first_seen'),
            last_updated=data.get('last_updated')
        )
    
    def to_dict(self):
        """
        Convert Player object to a dictionary.
        
        Returns:
            Dictionary with player data
        """
        return {
            'server_id': self.server_id,
            'player_name': self.player_name,
            'kills': self.kills,
            'deaths': self.deaths,
            'suicides': self.suicides,
            'longest_shot': self.longest_shot,
            'kill_streak': self.kill_streak,
            'death_streak': self.death_streak,
            'max_kill_streak': self.max_kill_streak,
            'max_death_streak': self.max_death_streak,
            'weapons': self.weapons,
            'is_online': self.is_online,
            'is_console': self.is_console,
            'last_connected': self.last_connected,
            'last_disconnected': self.last_disconnected,
            'first_seen': self.first_seen,
            'last_updated': self.last_updated
        }
    
    def get_kdr(self):
        """
        Calculate Kill/Death Ratio.
        
        Returns:
            Float KDR value (kills if deaths is 0)
        """
        if self.deaths == 0:
            return self.kills
        return self.kills / self.deaths
    
    def get_top_weapons(self, limit=5):
        """
        Get player's most used weapons.
        
        Args:
            limit: Maximum number of weapons to return
            
        Returns:
            List of (weapon_name, kill_count) tuples
        """
        sorted_weapons = sorted(
            self.weapons.items(),
            key=lambda x: x[1],
            reverse=True
        )
        return sorted_weapons[:limit]
    
    def get_online_time(self):
        """
        Calculate total online time if connection data is available.
        
        Returns:
            Total seconds online or None if data unavailable
        """
        if not self.last_connected or not self.last_disconnected:
            return None
        
        total_time = 0
        if self.is_online:
            # Player is online, calculate time since last connection
            online_time = (datetime.utcnow() - self.last_connected).total_seconds()
            total_time += online_time
        
        # Add historical online time
        # This would require tracking connection sessions, not implemented in this model
        
        return total_time
    
    def __str__(self):
        """String representation of the player."""
        status = "Online" if self.is_online else "Offline"
        platform = "Console" if self.is_console else "PC"
        return f"{self.player_name} - {status} ({platform}) - K/D: {self.get_kdr():.2f}"
