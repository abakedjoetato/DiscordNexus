"""
Parser for real-time killfeed data from CSV files.
"""
import logging
import csv
import re
from datetime import datetime
import io

logger = logging.getLogger(__name__)

class KillfeedParser:
    """
    Parser for killfeed data from CSV files.
    Handles real-time updates and new kill detection.
    """
    
    def __init__(self, server_id):
        """
        Initialize the parser.
        
        Args:
            server_id: Server ID for identification
        """
        self.server_id = server_id
        self.last_position = 0
    
    async def parse_csv(self, csv_data, last_position=0):
        """
        Parse CSV data for new kills.
        
        Args:
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
            logger.error(f"Error parsing killfeed CSV for server {self.server_id}: {e}")
        
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
            logger.error(f"Error processing killfeed row for server {self.server_id}: {e}")
            return None
