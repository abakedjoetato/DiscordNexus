"""
Parser for historical killfeed data from CSV files.
"""
import logging
import csv
import re
import asyncio
from datetime import datetime
import io

logger = logging.getLogger(__name__)

class HistoricalParser:
    """
    Parser for historical killfeed data from CSV files.
    Handles large-scale data parsing with progress updates.
    """
    
    def __init__(self, server_id, callback=None):
        """
        Initialize the parser.
        
        Args:
            server_id: Server ID for identification
            callback: Optional callback function for progress updates
        """
        self.server_id = server_id
        self.callback = callback
        self.last_update_time = datetime.now()
        self.total_files = 0
        self.processed_files = 0
        self.total_kills = 0
    
    async def parse_csv_files(self, csv_files_data):
        """
        Parse multiple CSV files for historical data.
        
        Args:
            csv_files_data: List of tuples (file_path, csv_data, last_position)
            
        Returns:
            Tuple of (all_kill_entries, parsing_positions)
        """
        all_kill_entries = []
        parsing_positions = {}
        
        self.total_files = len(csv_files_data)
        self.processed_files = 0
        self.total_kills = 0
        
        for file_path, csv_data, last_position in csv_files_data:
            # Parse the CSV file
            kill_entries, new_position = await self._parse_csv(
                file_path, csv_data, last_position
            )
            
            # Add kill entries to the list
            all_kill_entries.extend(kill_entries)
            
            # Update parsing position
            parsing_positions[file_path] = new_position
            
            # Update progress counter
            self.processed_files += 1
            self.total_kills += len(kill_entries)
            
            # Send progress update if enough time has passed
            await self._send_progress_update()
        
        # Send final progress update
        await self._send_progress_update(force=True)
        
        return all_kill_entries, parsing_positions
    
    async def _parse_csv(self, file_path, csv_data, last_position=0):
        """
        Parse a single CSV file.
        
        Args:
            file_path: Path to the CSV file
            csv_data: List of lines from the CSV file
            last_position: Last parsed position
            
        Returns:
            Tuple of (kill_entries, new_position)
        """
        kill_entries = []
        new_position = last_position
        
        try:
            # Process CSV data
            csv_reader = csv.reader(io.StringIO('\n'.join(csv_data)))
            
            for line_num, row in enumerate(csv_reader, start=1):
                # Skip already parsed lines
                if line_num <= last_position:
                    continue
                
                # Skip empty rows or header row
                if not row or len(row) < 5 or row[0] == "Time":
                    continue
                
                # Process kill entry
                kill_entry = self._process_row(row)
                if kill_entry:
                    kill_entries.append(kill_entry)
                
                new_position = line_num
        except Exception as e:
            logger.error(f"Error parsing historical CSV {file_path} for server {self.server_id}: {e}")
        
        return kill_entries, new_position
    
    def _process_row(self, row):
        """
        Process a CSV row into a kill entry.
        
        Args:
            row: CSV row data
            
        Returns:
            Dictionary with kill information or None if invalid
        """
        try:
            # Expected format: Time, Killer, Victim, Weapon, Distance
            if len(row) < 5:
                return None
            
            # Parse timestamp
            try:
                timestamp = datetime.strptime(row[0], "%Y.%m.%d-%H.%M.%S")
            except ValueError:
                timestamp = datetime.now()  # Fallback to current time
            
            killer = row[1].strip()
            victim = row[2].strip()
            weapon = row[3].strip()
            
            # Parse distance if available
            distance = 0
            if len(row) >= 5 and row[4]:
                try:
                    distance = float(row[4])
                except ValueError:
                    # Try to extract numeric value from string (e.g., "100m")
                    distance_match = re.search(r"(\d+\.?\d*)", row[4])
                    if distance_match:
                        distance = float(distance_match.group(1))
            
            # Create kill entry
            kill_entry = {
                "server_id": self.server_id,
                "timestamp": timestamp,
                "killer": killer,
                "victim": victim,
                "weapon": weapon,
                "distance": distance,
                "is_suicide": killer == victim
            }
            
            # Check for special suicide cases
            if killer == victim:
                if weapon.lower() == "suicide_by_relocation":
                    kill_entry["suicide_type"] = "menu"
                elif weapon.lower() == "falling":
                    kill_entry["suicide_type"] = "fall"
                else:
                    kill_entry["suicide_type"] = "other"
            
            return kill_entry
        except Exception as e:
            logger.error(f"Error processing historical row for server {self.server_id}: {e}")
            return None
    
    async def _send_progress_update(self, force=False):
        """
        Send progress update to the callback if enough time has passed.
        
        Args:
            force: Force sending update regardless of time passed
        """
        if not self.callback:
            return
            
        current_time = datetime.now()
        time_diff = (current_time - self.last_update_time).total_seconds()
        
        if force or time_diff >= 60:  # Send update every 60 seconds
            progress = {
                "server_id": self.server_id,
                "total_files": self.total_files,
                "processed_files": self.processed_files,
                "total_kills": self.total_kills,
                "percent_complete": (self.processed_files / max(1, self.total_files)) * 100,
                "timestamp": current_time
            }
            
            await self.callback(progress)
            self.last_update_time = current_time
