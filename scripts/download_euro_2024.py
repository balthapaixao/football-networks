import os
import json
import pandas as pd
from pathlib import Path
import requests
from typing import List, Dict
import logging
from tqdm import tqdm
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# StatsBomb API endpoints for Euro 2024
BASE_URL = "https://raw.githubusercontent.com/statsbomb/open-data/master/data"
COMPETITION_URL = f"{BASE_URL}/competitions.json"
MATCHES_URL = f"{BASE_URL}/matches/55/282.json"  # Euro 2024 competition_id=55, season_id=282
EVENTS_BASE_URL = f"{BASE_URL}/events"

# Configure retry strategy
def create_session() -> requests.Session:
    """Create a requests session with retry strategy."""
    session = requests.Session()
    retries = Retry(
        total=5,  # number of retries
        backoff_factor=1,  # wait 1, 2, 4, 8, 16 seconds between retries
        status_forcelist=[408, 429, 500, 502, 503, 504],  # HTTP status codes to retry on
        allowed_methods=["GET"]
    )
    session.mount('https://', HTTPAdapter(max_retries=retries))
    return session

def create_directories(base_dir: str = "data/euro_2024") -> None:
    """Create necessary directories if they don't exist."""
    directories = [
        base_dir,
        f"{base_dir}/events",
        f"{base_dir}/360"
    ]
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        logging.info(f"Created directory: {directory}")

def download_json(url: str, session: requests.Session = None, max_retries: int = 3) -> List[Dict]:
    """Download JSON data from a URL with retries."""
    if session is None:
        session = create_session()
    
    for attempt in range(max_retries):
        try:
            response = session.get(url)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            if attempt == max_retries - 1:  # Last attempt
                logging.error(f"Error downloading data from {url}: {e}")
                raise
            else:
                wait_time = (attempt + 1) * 2  # Progressive delay
                logging.warning(f"Attempt {attempt + 1} failed. Retrying in {wait_time} seconds...")
                time.sleep(wait_time)

def download_matches() -> pd.DataFrame:
    """Download and process matches data."""
    logging.info("Downloading matches data...")
    session = create_session()
    matches = download_json(MATCHES_URL, session)
    
    # Convert to DataFrame and select relevant columns
    matches_df = pd.DataFrame(matches)
    
    # Flatten nested dictionaries
    matches_df['home_team_name'] = matches_df['home_team'].apply(lambda x: x.get('home_team_name'))
    matches_df['away_team_name'] = matches_df['away_team'].apply(lambda x: x.get('away_team_name'))
    matches_df['competition_stage_name'] = matches_df['competition_stage'].apply(lambda x: x.get('name'))
    matches_df['stadium_name'] = matches_df['stadium'].apply(lambda x: x.get('name'))
    matches_df['competition_name'] = matches_df['competition'].apply(lambda x: x.get('competition_name'))
    matches_df['season_name'] = matches_df['season'].apply(lambda x: x.get('season_name'))
    
    # Select final columns
    final_columns = [
        'match_id',
        'home_team_name',
        'away_team_name',
        'competition_stage_name',
        'stadium_name',
        'competition_name',
        'season_name'
    ]
    
    return matches_df[final_columns]

def download_match_events(match_id: int, base_dir: str, session: requests.Session = None) -> pd.DataFrame:
    """Download and process events data for a specific match."""
    events_url = f"{EVENTS_BASE_URL}/{match_id}.json"
    
    if session is None:
        session = create_session()
    
    try:
        events = download_json(events_url, session)
        events_df = pd.DataFrame(events)
        
        # Save raw events
        events_df.to_csv(f"{base_dir}/events/{match_id}.csv", index=False)
        return events_df
    
    except Exception as e:
        logging.error(f"Error processing events for match {match_id}: {e}")
        return pd.DataFrame()

def retry_failed_downloads(failed_matches: List[int], base_dir: str) -> None:
    """Retry downloading failed matches with increased delays."""
    if not failed_matches:
        return
    
    logging.info(f"\nRetrying {len(failed_matches)} failed downloads...")
    session = create_session()
    
    for match_id in tqdm(failed_matches, desc="Retrying failed downloads"):
        events_df = download_match_events(match_id, base_dir, session)
        if not events_df.empty:
            logging.info(f"Successfully downloaded match {match_id} on retry")
        else:
            logging.error(f"Failed to download match {match_id} even after retry")

def combine_event_data(base_dir: str) -> None:
    """Combine all event data into a single file."""
    logging.info("\nCombining event data into a single file...")
    
    all_events = []
    event_files = [f for f in Path(f"{base_dir}/events").glob("*.csv") 
                  if f.stem.isdigit()]  # Only process files with numeric names (match IDs)
    
    for file in tqdm(event_files, desc="Processing event files"):
        try:
            df = pd.read_csv(file)
            match_id = int(file.stem)
            if 'match_id' not in df.columns:
                df['match_id'] = match_id
            all_events.append(df)
        except Exception as e:
            logging.error(f"Error processing file {file}: {e}")
            continue
    
    if all_events:
        try:
            combined_events = pd.concat(all_events, ignore_index=True)
            combined_events.to_csv(f"{base_dir}/all_events.csv", index=False)
            logging.info(f"Combined {len(event_files)} event files into all_events.csv")
            logging.info(f"Total events: {len(combined_events)}")
        except Exception as e:
            logging.error(f"Error combining events: {e}")
    else:
        logging.warning("No event files found to combine")

def check_data_availability() -> bool:
    """Check if Euro 2024 data is available."""
    try:
        competitions = download_json(COMPETITION_URL)
        euro_2024 = next(
            (c for c in competitions 
             if c.get('competition_name') == 'UEFA Euro' 
             and c.get('season_name') == '2024'), 
            None
        )
        
        if not euro_2024:
            logging.error("Euro 2024 competition not found in StatsBomb data")
            return False
            
        # Convert string dates to comparable format
        from datetime import datetime
        current_time = datetime.now()
        match_available = datetime.strptime(
            euro_2024['match_available'].split('.')[0],
            '%Y-%m-%dT%H:%M:%S'
        )
        
        if current_time < match_available:
            logging.error(f"Euro 2024 data will be available after {match_available}")
            return False
            
        return True
        
    except Exception as e:
        logging.error(f"Error checking data availability: {e}")
        return False

def main():
    """Main function to download and process all Euro 2024 data."""
    base_dir = "data/euro_2024"
    
    # Check if data is available
    if not check_data_availability():
        logging.error("Euro 2024 data is not yet available. The tournament hasn't started or data hasn't been released.")
        logging.info("Please try again after the tournament starts in June 2024.")
        return
    
    create_directories(base_dir)
    
    try:
        # Download matches data
        matches_df = download_matches()
        matches_df.to_csv(f"{base_dir}/matches.csv", index=False)
        logging.info(f"Saved matches data to {base_dir}/matches.csv")
        
        # Download events for each match
        failed_matches = []
        session = create_session()
        
        for match_id in tqdm(matches_df['match_id'], desc="Downloading match events"):
            events_df = download_match_events(match_id, base_dir, session)
            if events_df.empty:
                failed_matches.append(match_id)
        
        # Retry failed downloads
        if failed_matches:
            retry_failed_downloads(failed_matches, base_dir)
        
        # Combine all events
        combine_event_data(base_dir)
        
        # Final summary
        total_matches = len(matches_df)
        successful_matches = total_matches - len(failed_matches)
        logging.info("\nDownload Summary:")
        logging.info(f"Total matches: {total_matches}")
        logging.info(f"Successfully downloaded: {successful_matches}")
        logging.info(f"Failed to download: {len(failed_matches)}")
        if failed_matches:
            logging.info(f"Failed match IDs: {failed_matches}")
        
        logging.info("\nData download complete!")
        logging.info(f"Data saved in {base_dir}/")
        logging.info("Combined events data saved as all_events.csv")
        
    except Exception as e:
        logging.error(f"Error in main execution: {e}")
        raise

if __name__ == "__main__":
    main() 