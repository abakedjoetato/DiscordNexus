"""
SFTP client module for connecting to game servers and retrieving files.
"""
import logging
import os
import paramiko
import asyncio
from datetime import datetime
import config

logger = logging.getLogger(__name__)

class SFTPClient:
    """
    SFTP client for connecting to game servers and retrieving files.
    Handles recursive directory scanning to find CSV and log files.
    """
    
    def __init__(self, host, port, username, password, server_id):
        """
        Initialize SFTP client with connection parameters.
        
        Args:
            host: SFTP host address
            port: SFTP port
            username: SFTP username
            password: SFTP password
            server_id: Server ID for pattern matching
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.server_id = server_id
        self.ssh_client = None
        self.sftp_client = None
        self.connected = False
    
    async def connect(self):
        """
        Establish SFTP connection.
        
        Returns:
            Boolean indicating connection success
        """
        if self.connected:
            return True
            
        try:
            # Run SFTP connection in a thread pool
            loop = asyncio.get_event_loop()
            connected = await loop.run_in_executor(None, self._connect_sync)
            self.connected = connected
            return connected
        except Exception as e:
            logger.error(f"SFTP connection error for server {self.server_id}: {e}")
            return False
    
    def _connect_sync(self):
        """
        Synchronous SFTP connection method to run in thread pool.
        
        Returns:
            Boolean indicating connection success
        """
        try:
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh_client.connect(
                hostname=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                timeout=config.SFTP_TIMEOUT
            )
            self.sftp_client = self.ssh_client.open_sftp()
            logger.info(f"SFTP connection established for server {self.server_id}")
            return True
        except Exception as e:
            logger.error(f"SFTP connection error for server {self.server_id}: {e}")
            if self.ssh_client:
                self.ssh_client.close()
            self.ssh_client = None
            self.sftp_client = None
            return False
    
    async def disconnect(self):
        """Close SFTP connection."""
        if not self.connected:
            return
            
        try:
            # Run in thread pool
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._disconnect_sync)
        except Exception as e:
            logger.error(f"Error disconnecting SFTP for server {self.server_id}: {e}")
        finally:
            self.connected = False
    
    def _disconnect_sync(self):
        """Synchronous disconnect method to run in thread pool."""
        if self.sftp_client:
            self.sftp_client.close()
        if self.ssh_client:
            self.ssh_client.close()
        self.sftp_client = None
        self.ssh_client = None
    
    async def find_latest_csv(self, search_path="/"):
        """
        Recursively search for the latest CSV file by timestamp.
        
        Args:
            search_path: Starting directory path
            
        Returns:
            Path to the latest CSV file or None if not found
        """
        if not self.connected and not await self.connect():
            return None
            
        try:
            # Run in thread pool
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None, self._find_latest_csv_sync, search_path
            )
        except Exception as e:
            logger.error(f"Error finding latest CSV for server {self.server_id}: {e}")
            return None
    
    def _find_latest_csv_sync(self, search_path):
        """
        Synchronous method to find the latest CSV file.
        
        Args:
            search_path: Starting directory path
            
        Returns:
            Path to the latest CSV file or None if not found
        """
        latest_csv = None
        latest_time = datetime.min
        
        try:
            self._find_csv_recursive(search_path, lambda path, time: 
                self._update_latest(path, time, latest_csv, latest_time))
            return latest_csv
        except Exception as e:
            logger.error(f"Error in CSV recursive search for server {self.server_id}: {e}")
            return None
    
    def _update_latest(self, path, time, current_latest, current_time):
        """Update the latest file reference if the new file is more recent."""
        if time > current_time:
            return path, time
        return current_latest, current_time
    
    def _find_csv_recursive(self, path, callback, latest_csv=None, latest_time=datetime.min):
        """
        Recursively search for CSV files and call callback on each one.
        
        Args:
            path: Directory path to search
            callback: Function to call for each CSV file found
            latest_csv: Current latest CSV path
            latest_time: Current latest CSV timestamp
        
        Returns:
            Updated latest_csv and latest_time values
        """
        try:
            items = self.sftp_client.listdir_attr(path)
            
            for item in items:
                item_path = f"{path}/{item.filename}" if path != "/" else f"/{item.filename}"
                
                if stat.S_ISDIR(item.st_mode):
                    # This is a directory, recurse into it
                    latest_csv, latest_time = self._find_csv_recursive(
                        item_path, callback, latest_csv, latest_time
                    )
                elif item.filename.lower().endswith('.csv'):
                    # This is a CSV file, check if it's newer
                    file_time = datetime.fromtimestamp(item.st_mtime)
                    latest_csv, latest_time = callback(item_path, file_time)
            
            return latest_csv, latest_time
        except Exception as e:
            logger.error(f"Error searching directory {path}: {e}")
            return latest_csv, latest_time
    
    async def find_all_csv_files(self, search_path="/"):
        """
        Find all CSV files in the server.
        
        Args:
            search_path: Starting directory path
            
        Returns:
            List of CSV file paths
        """
        if not self.connected and not await self.connect():
            return []
            
        try:
            # Run in thread pool
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None, self._find_all_csv_files_sync, search_path
            )
        except Exception as e:
            logger.error(f"Error finding all CSV files for server {self.server_id}: {e}")
            return []
    
    def _find_all_csv_files_sync(self, search_path):
        """
        Synchronous method to find all CSV files.
        
        Args:
            search_path: Starting directory path
            
        Returns:
            List of CSV file paths
        """
        csv_files = []
        
        try:
            self._find_csv_files_recursive(search_path, csv_files)
            return sorted(csv_files)
        except Exception as e:
            logger.error(f"Error in finding all CSV files for server {self.server_id}: {e}")
            return []
    
    def _find_csv_files_recursive(self, path, csv_files):
        """
        Recursively search for CSV files and add them to the list.
        
        Args:
            path: Directory path to search
            csv_files: List to add found CSV files to
        """
        try:
            items = self.sftp_client.listdir_attr(path)
            
            for item in items:
                item_path = f"{path}/{item.filename}" if path != "/" else f"/{item.filename}"
                
                if stat.S_ISDIR(item.st_mode):
                    # This is a directory, recurse into it
                    self._find_csv_files_recursive(item_path, csv_files)
                elif item.filename.lower().endswith('.csv'):
                    # This is a CSV file, add it to the list
                    csv_files.append(item_path)
        except Exception as e:
            logger.error(f"Error searching directory {path}: {e}")
    
    async def find_log_file(self, search_path="/"):
        """
        Find the Deadside.log file.
        
        Args:
            search_path: Starting directory path
            
        Returns:
            Path to the log file or None if not found
        """
        if not self.connected and not await self.connect():
            return None
            
        try:
            # Run in thread pool
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None, self._find_log_file_sync, search_path
            )
        except Exception as e:
            logger.error(f"Error finding log file for server {self.server_id}: {e}")
            return None
    
    def _find_log_file_sync(self, search_path):
        """
        Synchronous method to find the Deadside.log file.
        
        Args:
            search_path: Starting directory path
            
        Returns:
            Path to the log file or None if not found
        """
        log_file = None
        
        try:
            self._find_log_recursive(search_path, log_file)
            return log_file
        except Exception as e:
            logger.error(f"Error in log file search for server {self.server_id}: {e}")
            return None
    
    def _find_log_recursive(self, path, log_file):
        """
        Recursively search for the log file.
        
        Args:
            path: Directory path to search
            log_file: Current log file path
        
        Returns:
            Updated log_file value
        """
        if log_file:
            return log_file
            
        try:
            items = self.sftp_client.listdir_attr(path)
            
            for item in items:
                item_path = f"{path}/{item.filename}" if path != "/" else f"/{item.filename}"
                
                if stat.S_ISDIR(item.st_mode):
                    # This is a directory, recurse into it
                    log_file = self._find_log_recursive(item_path, log_file)
                    if log_file:
                        return log_file
                elif item.filename.lower() == 'deadside.log':
                    # This is the log file, return its path
                    return item_path
            
            return log_file
        except Exception as e:
            logger.error(f"Error searching directory {path}: {e}")
            return log_file
    
    async def read_file(self, file_path, start_position=0):
        """
        Read file from the SFTP server, starting from a specific position.
        
        Args:
            file_path: Path to the file
            start_position: Starting position (line number) to read from
            
        Returns:
            Tuple of (lines, new_position) where lines is a list of strings
            and new_position is the updated position after reading
        """
        if not self.connected and not await self.connect():
            return [], start_position
            
        try:
            # Run in thread pool
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None, self._read_file_sync, file_path, start_position
            )
        except Exception as e:
            logger.error(f"Error reading file {file_path} for server {self.server_id}: {e}")
            return [], start_position
    
    def _read_file_sync(self, file_path, start_position):
        """
        Synchronous method to read a file from the SFTP server.
        
        Args:
            file_path: Path to the file
            start_position: Starting position (line number) to read from
            
        Returns:
            Tuple of (lines, new_position) where lines is a list of strings
            and new_position is the updated position after reading
        """
        try:
            with self.sftp_client.open(file_path, 'r') as f:
                # Skip to the starting position
                for _ in range(start_position):
                    line = f.readline()
                    if not line:
                        return [], start_position
                
                # Read the rest of the file
                lines = f.readlines()
                return lines, start_position + len(lines)
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return [], start_position
    
    async def check_file_exists(self, file_path):
        """
        Check if a file exists on the SFTP server.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Boolean indicating if the file exists
        """
        if not self.connected and not await self.connect():
            return False
            
        try:
            # Run in thread pool
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None, self._check_file_exists_sync, file_path
            )
        except Exception as e:
            logger.error(f"Error checking file {file_path} for server {self.server_id}: {e}")
            return False
    
    def _check_file_exists_sync(self, file_path):
        """
        Synchronous method to check if a file exists.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Boolean indicating if the file exists
        """
        try:
            self.sftp_client.stat(file_path)
            return True
        except FileNotFoundError:
            return False
        except Exception as e:
            logger.error(f"Error checking file {file_path}: {e}")
            return False
