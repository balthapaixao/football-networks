import json
import logging
from pathlib import Path
from typing import List, Dict, Set
import sqlite3
from load_historical_statsbomb_data import StatsbombDataLoader
from database_manager import FootballDatabaseManager
from datetime import datetime
import time

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/incremental_loading.log'),
        logging.StreamHandler()
    ]
)

class IncrementalStatsbombLoader:
    def __init__(self):
        self.db_manager = FootballDatabaseManager()
        self.historical_loader = StatsbombDataLoader()
        
    def get_database_matches(self) -> Set[str]:
        """Get all match IDs currently in the database."""
        conn = self.db_manager.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT match_id FROM DimMatch")
            return {str(row[0]) for row in cursor.fetchall()}
        finally:
            conn.close()
            
    def get_available_matches(self) -> Dict[str, dict]:
        """Get all available matches from Statsbomb."""
        available_matches = {}
        competitions = self.historical_loader.get_competitions()
        
        if not competitions:
            logging.error("Failed to fetch competitions")
            return available_matches
            
        for competition in competitions:
            try:
                matches = self.historical_loader.get_matches_batch([competition])
                if matches:
                    for match in matches:
                        match_id = str(match['match_id'])
                        available_matches[match_id] = match
                time.sleep(0.1)  # Small delay between requests
            except Exception as e:
                logging.error(f"Error fetching matches for competition {competition['competition_id']}: {str(e)}")
                continue
                
        return available_matches
        
    def identify_missing_matches(self) -> List[dict]:
        """Identify matches that are available but not in the database."""
        logging.info("Starting to identify missing matches...")
        
        # Get existing matches from database
        db_matches = self.get_database_matches()
        logging.info(f"Found {len(db_matches)} matches in database")
        
        # Get available matches from Statsbomb
        available_matches = self.get_available_matches()
        logging.info(f"Found {len(available_matches)} matches available from Statsbomb")
        
        # Identify missing matches
        missing_match_ids = set(available_matches.keys()) - db_matches
        missing_matches = [available_matches[match_id] for match_id in missing_match_ids]
        
        logging.info(f"Identified {len(missing_matches)} missing matches")
        return missing_matches
        
    def load_missing_matches(self):
        """Load any matches that are missing from the database."""
        try:
            # Get missing matches
            missing_matches = self.identify_missing_matches()
            
            if not missing_matches:
                logging.info("No missing matches found. Database is up to date!")
                return
                
            logging.info(f"Starting to load {len(missing_matches)} missing matches...")
            
            # Process missing matches in batches
            batch_size = 8  # Match batch size for processing
            total_processed = 0
            
            for i in range(0, len(missing_matches), batch_size):
                batch = missing_matches[i:i + batch_size]
                try:
                    results = self.historical_loader.process_matches_batch(batch)
                    if results:
                        total_processed += len(results)
                        logging.info(f"Successfully processed {len(results)} matches in current batch")
                except Exception as e:
                    logging.error(f"Error processing batch: {str(e)}")
                    continue
                    
                time.sleep(0.1)  # Small delay between batches
                
            logging.info(f"Incremental load completed. Processed {total_processed} new matches.")
            
        except Exception as e:
            logging.error(f"Error in incremental load: {str(e)}")
            raise

def main():
    # Create necessary directories
    Path("logs").mkdir(exist_ok=True)
    Path("data").mkdir(exist_ok=True)
    
    # Initialize and run the incremental loader
    loader = IncrementalStatsbombLoader()
    loader.load_missing_matches()

if __name__ == "__main__":
    main() 