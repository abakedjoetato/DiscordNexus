"""
Guild model for holding Discord guild-related data.
"""
from datetime import datetime

class Guild:
    """
    Guild model representing a Discord guild (server).
    """
    
    def __init__(
        self,
        guild_id,
        name,
        premium_tier="free",
        admin_role_id=None,
        killfeed_channel_id=None,
        events_channel_id=None,
        connections_channel_id=None,
        voice_channel_id=None,
        joined_at=None,
        config=None
    ):
        """
        Initialize a guild object.
        
        Args:
            guild_id: Discord guild ID
            name: Discord guild name
            premium_tier: Premium tier level
            admin_role_id: Role ID for administration commands
            killfeed_channel_id: Channel ID for killfeed messages
            events_channel_id: Channel ID for event messages
            connections_channel_id: Channel ID for connection messages
            voice_channel_id: Voice channel ID for player count updates
            joined_at: Datetime when the bot joined this guild
            config: Additional guild configuration
        """
        self.guild_id = guild_id
        self.name = name
        self.premium_tier = premium_tier
        self.admin_role_id = admin_role_id
        self.killfeed_channel_id = killfeed_channel_id
        self.events_channel_id = events_channel_id
        self.connections_channel_id = connections_channel_id
        self.voice_channel_id = voice_channel_id
        self.joined_at = joined_at or datetime.utcnow()
        self.config = config or {}
    
    @classmethod
    def from_dict(cls, data):
        """
        Create a Guild object from a dictionary.
        
        Args:
            data: Dictionary containing guild data
            
        Returns:
            Guild object
        """
        return cls(
            guild_id=data.get('guild_id'),
            name=data.get('name'),
            premium_tier=data.get('premium_tier', 'free'),
            admin_role_id=data.get('admin_role_id'),
            killfeed_channel_id=data.get('killfeed_channel_id'),
            events_channel_id=data.get('events_channel_id'),
            connections_channel_id=data.get('connections_channel_id'),
            voice_channel_id=data.get('voice_channel_id'),
            joined_at=data.get('joined_at'),
            config=data.get('config', {})
        )
    
    def to_dict(self):
        """
        Convert Guild object to a dictionary.
        
        Returns:
            Dictionary with guild data
        """
        return {
            'guild_id': self.guild_id,
            'name': self.name,
            'premium_tier': self.premium_tier,
            'admin_role_id': self.admin_role_id,
            'killfeed_channel_id': self.killfeed_channel_id,
            'events_channel_id': self.events_channel_id,
            'connections_channel_id': self.connections_channel_id,
            'voice_channel_id': self.voice_channel_id,
            'joined_at': self.joined_at,
            'config': self.config
        }
    
    def has_feature(self, feature):
        """
        Check if the guild has access to a specific feature.
        
        Args:
            feature: Feature name to check
            
        Returns:
            Boolean indicating access
        """
        import config
        
        tier_info = config.PREMIUM_TIERS.get(self.premium_tier, config.PREMIUM_TIERS["free"])
        return feature in tier_info["features"]
    
    def get_max_servers(self):
        """
        Get maximum number of servers allowed for this guild.
        
        Returns:
            Integer with max server count
        """
        import config
        
        tier_info = config.PREMIUM_TIERS.get(self.premium_tier, config.PREMIUM_TIERS["free"])
        return tier_info["server_slots"]
    
    def __str__(self):
        """String representation of the guild."""
        return f"{self.name} (ID: {self.guild_id}, Tier: {self.premium_tier})"
