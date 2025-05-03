"""
SFTP utility functions for server connections and file operations
"""
import os
import re
import logging
import asyncio
import datetime
import time
from io import StringIO

import paramiko
from paramiko.ssh_exception import SSHException, AuthenticationException

from config import SFTP_CONNECTION_SETTINGS, CSV_FILENAME_PATTERN, LOG_FILENAME

logger = logging.getLogger(__name__)

class SFTPClient:
    """SFTP client for connecting to game servers and retrieving files"""

    def __init__(self, host, port, username, password, server_id):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.server_id = server_id
        self.client = None
        self.sftp = None
        self.root_path = None
        self.connected = False
        self.last_error = None

    async def connect(self):
        """Establish SFTP connection"""
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            self.client.connect(
                hostname=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                **SFTP_CONNECTION_SETTINGS
            )

            self.sftp = self.client.open_sftp()
            logger.info(f"Connected to SFTP server: {self.host}:{self.port} for server {self.server_id}")

            await self.find_root_path()

            self.connected = True
            self.last_error = None
            return True

        except Exception as e:
            self.last_error = str(e)
            logger.error(f"Connection error: {e}", exc_info=True)
            self.connected = False
            return False

    async def find_root_path(self):
        """Find the root path containing server directory"""
        try:
            current_path = '.'
            self.root_path = None

            # Create pattern for server directory
            ip_address = self.host.split(':')[0]
            server_pattern = f"{ip_address}_{self.server_id}"

            items = await self._list_dir_safe(current_path)
            logger.info(f"Searching for server directory matching pattern: {server_pattern}")
            logger.info(f"Found items in root: {items}")

            # Look for exact match first
            for item in items:
                if server_pattern.lower() in item.lower():
                    self.root_path = os.path.join(current_path, item)
                    logger.info(f"Found server directory: {self.root_path}")
                    return

            if not self.root_path:
                logger.warning(f"Could not find server directory matching {server_pattern}")
                self.root_path = current_path

        except Exception as e:
            logger.error(f"Error finding root path: {e}", exc_info=True)
            self.root_path = '.'

    async def get_latest_csv_file(self):
        """Get the most recent CSV file from any subdirectory"""
        if not self.connected:
            await self.connect()
            if not self.connected:
                return None

        try:
            # Construct base path to deathlogs
            server_dir = f"{self.host.split(':')[0]}_{self.server_id}"
            deathlogs_path = os.path.join(".", server_dir, "actual1", "deathlogs")

            logger.info(f"Searching for CSV files in {deathlogs_path}")

            # Find all CSV files recursively
            csv_files = await self._find_csv_files_recursive(deathlogs_path)

            if not csv_files:
                logger.warning(f"No CSV files found in {deathlogs_path}")
                return None

            # Sort by timestamp from filename
            sorted_files = []
            for file_path in csv_files:
                try:
                    filename = os.path.basename(file_path)
                    # Parse timestamp from filename (YYYY.MM.DD-HH.MM.SS)
                    timestamp_str = filename.split('.csv')[0]
                    dt = datetime.datetime.strptime(timestamp_str, '%Y.%m.%d-%H.%M.%S')
                    sorted_files.append((file_path, dt.timestamp(), filename))
                    logger.info(f"Parsed CSV file: {filename} with timestamp {dt}")
                except Exception as e:
                    logger.warning(f"Could not parse timestamp from {filename}: {e}")
                    # Use file modification time as fallback
                    try:
                        attrs = await asyncio.to_thread(lambda: self.sftp.stat(file_path))
                        sorted_files.append((file_path, attrs.st_mtime, filename))
                    except Exception:
                        sorted_files.append((file_path, 0, filename))

            # Sort by timestamp (newest first)
            sorted_files.sort(key=lambda x: float(x[1]), reverse=True)

            if sorted_files:
                latest_file = sorted_files[0][0]
                logger.info(f"Using latest CSV file: {latest_file}")
                return latest_file

            return None

        except Exception as e:
            logger.error(f"Error getting latest CSV file: {e}", exc_info=True)
            return None

    async def _find_csv_files_recursive(self, directory, max_depth=8, current_depth=0):
        """Find all CSV files recursively with improved error handling"""
        if current_depth > max_depth:
            return []

        csv_files = []
        try:
            items = await self._list_dir_safe(directory)
            if not items:
                return []

            logger.info(f"Checking directory: {directory} (depth: {current_depth})")
            logger.info(f"Found items: {items}")

            # Process all items
            for item in items:
                item_path = os.path.join(directory, item)

                # Check if it's a CSV file
                if item.lower().endswith('.csv'):
                    logger.info(f"Found CSV file: {item_path}")
                    csv_files.append(item_path)
                    continue

                # Check if it's a directory
                try:
                    if await self._is_dir_safe(item_path):
                        subdir_files = await self._find_csv_files_recursive(
                            item_path, max_depth, current_depth + 1
                        )
                        csv_files.extend(subdir_files)
                except Exception as e:
                    logger.warning(f"Error checking subdirectory {item_path}: {e}")

        except Exception as e:
            logger.error(f"Error scanning directory {directory}: {e}")

        return csv_files

    async def _list_dir_safe(self, path):
        """Safely list directory contents with timeout protection"""
        try:
            items = await asyncio.wait_for(
                asyncio.to_thread(lambda: self.sftp.listdir(path)),
                timeout=5.0
            )
            return items
        except Exception as e:
            logger.warning(f"Error listing directory {path}: {e}")
            return []

    async def _is_dir_safe(self, path):
        """Safely check if path is directory with timeout protection"""
        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(lambda: self.sftp.stat(path).st_mode & 0o40000 != 0),
                timeout=2.0
            )
            return result
        except Exception:
            return False

    async def disconnect(self):
        """Close SFTP connection"""
        try:
            if self.sftp:
                self.sftp.close()
            if self.client:
                self.client.close()
            self.connected = False
            logger.info(f"Disconnected from SFTP server: {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"Error disconnecting: {e}")

    async def get_log_file(self):
        """Get the path to the Deadside.log file"""
        if not self.connected:
            await self.connect()
        if not self.connected:
            return None

        try:
            # Record start time to prevent heartbeat blocks
            start_time = asyncio.get_event_loop().time()

            # First find the server directory using specific format {Host}_{serverid}/Logs
            target_directory = None

            # Direct path to the logs directory based on the provided structure
            server_dir_pattern = f"{self.host.split(':')[0]}_{self.server_id}"
            logs_dir = os.path.join(".", server_dir_pattern, "Logs")

            logger.info(f"Using direct log path: {logs_dir}")

            # Check if the logs directory exists with timeout protection
            try:
                async def dir_exists_with_timeout():
                    try:
                        # Try to list the directory to see if it exists
                        items = await asyncio.to_thread(lambda: self.sftp.listdir(logs_dir))
                        return True, items
                    except:
                        return False, None

                exists, logs_items = await asyncio.wait_for(dir_exists_with_timeout(), timeout=3.0)

                if exists and logs_items:
                    logger.info(f"'Logs' directory contains: {', '.join(logs_items)}")

                    # Check for Deadside.log in the logs directory
                    if LOG_FILENAME in logs_items:
                        log_path = os.path.join(logs_dir, LOG_FILENAME)
                        logger.info(f"Found log file at: {log_path}")
                        return log_path
                    else:
                        logger.warning(f"'{LOG_FILENAME}' not found in direct Logs directory path")

            except asyncio.TimeoutError:
                logger.warning(f"Timeout checking direct logs directory: {logs_dir}")
            except Exception as e:
                logger.warning(f"Error with direct logs path: {e}")

            # Fallback approach if direct path fails
            if asyncio.get_event_loop().time() - start_time > 15:
                logger.warning("Log file search is taking too long, stopping to prevent heartbeat timeout")
                return None

            # List root directory with timeout protection
            logger.info("Fallback: Searching for server directory in root...")
            try:
                async def list_root_with_timeout():
                    return await asyncio.to_thread(lambda: self.sftp.listdir("."))

                root_files = await asyncio.wait_for(list_root_with_timeout(), timeout=3.0)

                # Look for the server ID pattern
                for item in root_files:
                    if server_dir_pattern in item:
                        # Found matching directory
                        target_directory = os.path.join(".", item)
                        logger.info(f"Found server directory for logs: {target_directory}")

                        # Try to directly access the logs directory now
                        logs_dir = os.path.join(target_directory, "Logs")

                        try:
                            async def check_logs_dir():
                                return await asyncio.to_thread(lambda: self.sftp.listdir(logs_dir))

                            logs_items = await asyncio.wait_for(check_logs_dir(), timeout=3.0)

                            if LOG_FILENAME in logs_items:
                                log_path = os.path.join(logs_dir, LOG_FILENAME)
                                logger.info(f"Found log file at: {log_path}")
                                return log_path
                        except Exception:
                            logger.warning(f"Could not find {LOG_FILENAME} in {logs_dir}")

                        break

            except (asyncio.TimeoutError, Exception) as e:
                logger.error(f"Error in fallback log file search: {e}")

            # If we've tried everything and still don't have the file
            logger.error("Could not find the log file using any method")
            return None

        except Exception as e:
            logger.error(f"Error getting log file: {e}", exc_info=True)
            return None

    async def read_file(self, file_path, start_line=0, max_lines=None, chunk_size=1000):
        """Read a file from the SFTP server with timeout protection
        Args:
            file_path: Path to the file to read
            start_line: First line to read (0-indexed)
            max_lines: Maximum number of lines to read
            chunk_size: Number of lines to read in each chunk (to prevent timeout)
        Returns:
            List of lines read from the file
        """
        if not self.connected:
            await self.connect()
        if not self.connected:
            return []

        try:
            # Create a new task with timeout to prevent event loop blocking
            async def read_chunk(start, max_count):
                try:
                    # We'll create a new file handle for each chunk to avoid timeout issues
                    with self.sftp.file(file_path, 'r') as chunk_file:
                        # Skip to the starting position
                        for _ in range(start):
                            next(chunk_file, None)

                        # Read the requested chunk
                        chunk_lines = []
                        count = 0

                        # Use a separate thread for potentially blocking IO
                        # and add a timeout to prevent blocking the event loop
                        return await asyncio.wait_for(
                            asyncio.to_thread(self._read_chunk, chunk_file, max_count),
                            timeout=5.0  # 5 second timeout
                        )

                except asyncio.TimeoutError:
                    logger.warning(f"Timeout reading file {file_path} at position {start}")
                    # Try to reconnect on timeout
                    await self.disconnect()
                    await asyncio.sleep(1)
                    await self.connect()
                    return []
                except Exception as e:
                    logger.error(f"Error reading chunk at position {start}: {e}")
                    return []

            all_lines = []
            current_position = start_line
            remaining_lines = max_lines

            while True:
                # Determine how many lines to read in this chunk
                current_chunk_size = chunk_size
                if remaining_lines is not None:
                    if remaining_lines <= 0:
                        break
                    current_chunk_size = min(chunk_size, remaining_lines)

                # Read the next chunk with timeout protection
                chunk_data = await read_chunk(current_position, current_chunk_size)

                # Break if we got no data (end of file or error)
                if not chunk_data:
                    break

                # Update our tracking variables
                all_lines.extend([line.strip() for line in chunk_data])
                chunk_line_count = len(chunk_data)
                current_position += chunk_line_count

                if remaining_lines is not None:
                    remaining_lines -= chunk_line_count

                # If we got fewer lines than requested, we've reached the end of the file
                if chunk_line_count < current_chunk_size:
                    break

                # Add a small delay to prevent overloading the event loop
                await asyncio.sleep(0.01)

            return all_lines

        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}", exc_info=True)
            # Try to reconnect after an error
            await self.disconnect()
            await asyncio.sleep(1)
            await self.connect()
            return []

    def _read_chunk(self, file_obj, max_lines):
        """Read a chunk of lines from a file (runs in a separate thread)
        Args:
            file_obj: Open file object
            max_lines: Maximum number of lines to read
        Returns:
            List of lines read
        """
        try:
            lines = []
            for _ in range(max_lines):
                try:
                    line = next(file_obj)
                    lines.append(line)
                except StopIteration:
                    break
            return lines
        except Exception as e:
            logger.error(f"Error in _read_chunk: {e}")
            return []

    async def get_file_size(self, file_path, chunk_size=5000):
        """Get the size of a file in lines with timeout protection
        Args:
            file_path: Path to the file
            chunk_size: Number of lines to count in each chunk (to prevent timeout)
        Returns:
            Number of lines in the file
        """
        # Record start time to prevent heartbeat blocks
        start_time = asyncio.get_event_loop().time()

        if not self.connected:
            await self.connect()
        if not self.connected:
            return 0

        try:
            # Add global timeout protection for the entire method
            # Return an estimate if taking too long
            if asyncio.get_event_loop().time() - start_time > 20:
                logger.warning(f"get_file_size already taking too long, using default estimation")
                return 5000  # Default estimate to prevent heartbeat blocks

            # OPTIMIZATION: Use a more efficient method to count lines
            # This runs in a background thread to avoid blocking the event loop
            try:
                # We'll use Python's file iterator which is much faster for counting lines
                # This will be executed in a separate thread to prevent blocking
                def count_lines():
                    try:
                        with self.sftp.file(file_path, 'r') as f:
                            # Count lines in batches for very large files
                            count = 0
                            # Set a maximum number of lines to count to prevent extreme timeouts
                            # For very large files, we'll fall back to estimation anyway
                            max_count = 50000

                            for i, _ in enumerate(f):
                                count = i + 1
                                # Every chunk_size lines, yield to allow checking for timeout
                                if count % chunk_size == 0:
                                    # Just continue the loop
                                    pass

                                # Break early for extremely large files
                                if count >= max_count:
                                    # Add 10% to indicate it's larger
                                    logger.warning(f"File {file_path} exceeds {max_count} lines, using estimate")
                                    return int(count * 1.1)

                            return count
                    except Exception as e:
                        logger.error(f"Error counting lines in thread: {e}")
                        return 0

                # Run the counting function in a thread with a timeout
                logger.debug(f"Counting lines in {file_path} with timeout protection")
                return await asyncio.wait_for(
                    asyncio.to_thread(count_lines),
                    timeout=8.0  # Shorter timeout to prevent heartbeat blocks
                )

            except asyncio.TimeoutError:
                logger.warning(f"Timeout while counting lines in {file_path}, falling back to estimation")
                # Fall back to an estimation method on timeout

                # Add another heartbeat protection check
                if asyncio.get_event_loop().time() - start_time > 20:
                    logger.warning(f"get_file_size taking too long during estimation, using default value")
                    return 5000  # Default estimate to prevent heartbeat blocks

                try:
                    # Get file attributes with timeout protection
                    # Use run_in_executor to make sure SFTP stat operation doesn't block
                    async def get_stat_with_timeout():
                        return await asyncio.to_thread(lambda: self.sftp.stat(file_path))

                    # Add a timeout for the stat operation itself
                    try:
                        attrs = await asyncio.wait_for(get_stat_with_timeout(), timeout=3.0)
                        # Estimate based on file size - assume 100 bytes per line as a rough guess
                        # This is better than nothing if the full count times out
                        estimated_lines = attrs.st_size // 100
                        logger.info(f"File {file_path} has estimated {estimated_lines} lines based on size {attrs.st_size} bytes")
                        return estimated_lines
                    except asyncio.TimeoutError:
                        logger.warning(f"Timeout getting file stats for {file_path}, using default estimation")
                        return 5000  # Default if stat times out

                except Exception as est_error:
                    logger.error(f"Error estimating file size: {est_error}")
                    return 5000  # Arbitrary fallback if all else fails

        except Exception as e:
            logger.error(f"Error in get_file_size: {e}", exc_info=True)
            return 0

    @staticmethod
    def run_in_executor(func, *args, **kwargs):
        """Run a blocking function in an executor"""
        loop = asyncio.get_event_loop()
        return loop.run_in_executor(None, lambda: func(*args, **kwargs))