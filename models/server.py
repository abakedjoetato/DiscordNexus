"""
Server model for holding server-related data.
"""
from datetime import datetime

class Server:
    """
    Server model representing a game server.
    """
    
    def __init__(
        self,
        guild_id,
        server_id,
        name,
        host,
        port,
        username,
        password,
        added_at=None,
        is_online=False,
        online_players=0,
        last_check=None,
        csv_files=None,
        log_file=None,
        config=None
    ):
        """
        Initialize a server object.
        
        Args:
            guild_id: Discord guild ID this server belongs to
            server_id: Unique identifier for this server
            name: Display name for the server
            host: SFTP host address
            port: SFTP port
            username: SFTP username
            password: SFTP password
            added_at: Datetime when the server was added
            is_online: Boolean indicating if the server is online
            online_players: Number of players currently online
            last_check: Datetime of last status check
            csv_files: List of discovered CSV file paths
            log_file: Path to the server log file
            config: Additional server configuration
        """
        self.guild_id = guild_id
        self.server_id = server_id
        self.name = name
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.added_at = added_at or datetime.utcnow()
        self.is_online = is_online
        self.online_players = online_players
        self.last_check = last_check or datetime.utcnow()
        self.csv_files = csv_files or []
        self.log_file = log_file
        self.config = config or {}
    
    @classmethod
    def from_dict(cls, data):
        """
        Create a Server object from a dictionary.
        
        Args:
            data: Dictionary containing server data
            
        Returns:
            Server object
        """
        return cls(
            guild_id=data.get('guild_id'),
            server_id=data.get('server_id'),
            name=data.get('name'),
            host=data.get('host'),
            port=data.get('port'),
            username=data.get('username'),
            password=data.get('password'),
            added_at=data.get('added_at'),
            is_online=data.get('is_online', False),
            online_players=data.get('online_players', 0),
            last_check=data.get('last_check'),
            csv_files=data.get('csv_files', []),
            log_file=data.get('log_file'),
            config=data.get('config', {})
        )
    
    def to_dict(self):
        """
        Convert Server object to a dictionary.
        
        Returns:
            Dictionary with server data
        """
        return {
            'guild_id': self.guild_id,
            'server_id': self.server_id,
            'name': self.name,
            'host': self.host,
            'port': self.port,
            'username': self.username,
            'password': self.password,
            'added_at': self.added_at,
            'is_online': self.is_online,
            'online_players': self.online_players,
            'last_check': self.last_check,
            'csv_files': self.csv_files,
            'log_file': self.log_file,
            'config': self.config
        }
    
    def get_connection_string(self):
        """
        Get SFTP connection string.
        
        Returns:
            String with connection details (without password)
        """
        return f"sftp://{self.username}@{self.host}:{self.port}"
    
    def __str__(self):
        """String representation of the server."""
        status = "Online" if self.is_online else "Offline"
        return f"{self.name} ({self.server_id}) - {status}"
