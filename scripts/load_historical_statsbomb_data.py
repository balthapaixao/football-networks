import json
import requests
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from database_manager import FootballDatabaseManager
from tqdm import tqdm
import pandas as pd
import logging
from datetime import datetime
import time
import asyncio
import aiohttp
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from itertools import islice
import concurrent.futures
import backoff

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/data_loading.log'),
        logging.StreamHandler()
    ]
)

class StatsbombDataLoader:
    def __init__(self, base_url="https://raw.githubusercontent.com/statsbomb/open-data/master/data"):
        self.base_url = base_url
        self.db_manager = FootballDatabaseManager()
        self.db_manager.initialize_database()
        
        # Configure session with retries and backoff
        self.session = requests.Session()
        retries = Retry(
            total=5,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
            respect_retry_after_header=True
        )
        # Configure pool size for concurrent requests
        adapter = HTTPAdapter(
            max_retries=retries,
            pool_connections=8,
            pool_maxsize=16  # Double the worker count to handle connection reuse
        )
        self.session.mount('https://', adapter)
        self.session.mount('http://', adapter)
        
        # Create thread pool for concurrent HTTP requests
        self.thread_pool = ThreadPoolExecutor(max_workers=8)
        
    @backoff.on_exception(backoff.expo, 
                         (requests.exceptions.RequestException,
                          requests.exceptions.ConnectionError),
                         max_tries=5)
    def fetch_json(self, url, timeout=30):
        """Fetch JSON data from URL with exponential backoff retry."""
        try:
            response = self.session.get(url, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logging.error(f"Error fetching data from {url}: {str(e)}")
            raise

    def fetch_urls_concurrent(self, urls):
        """Fetch multiple URLs concurrently using thread pool."""
        results = []
        
        with ThreadPoolExecutor(max_workers=8) as executor:
            # Submit all requests
            future_to_url = {executor.submit(self.fetch_json, url): url for url in urls}
            
            # Process results as they complete
            for future in concurrent.futures.as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    result = future.result()
                    if result is not None:
                        results.append(result)
                except Exception as e:
                    logging.error(f"Error fetching {url}: {str(e)}")
                    continue
        
        return results

    def get_competitions(self):
        """Get list of available competitions."""
        url = f"{self.base_url}/competitions.json"
        return self.fetch_json(url)

    def get_matches_batch(self, competition_batches):
        """Get matches for multiple competitions concurrently."""
        urls = [
            f"{self.base_url}/matches/{comp['competition_id']}/{comp['season_id']}.json"
            for comp in competition_batches
        ]
        results = self.fetch_urls_concurrent(urls)
        matches = []
        for result in results:
            if result:
                matches.extend(result)
        return matches

    def get_events_batch(self, match_ids):
        """Get events for multiple matches concurrently."""
        urls = [f"{self.base_url}/events/{match_id}.json" for match_id in match_ids]
        return self.fetch_urls_concurrent(urls)

    def validate_match_data(self, match_data):
        """Validate required match data fields."""
        required_fields = [
            'match_id', 'match_date', 'kick_off',
            'competition', 'season',
            'home_team', 'away_team'
        ]
        if not all(field in match_data for field in required_fields):
            return False
        
        # Validate nested structures
        if not all(key in match_data['competition'] for key in ['competition_id', 'competition_name']):
            return False
        if not all(key in match_data['season'] for key in ['season_id', 'season_name']):
            return False
        if not all(key in match_data['home_team'] for key in ['home_team_id', 'home_team_name']):
            return False
        if not all(key in match_data['away_team'] for key in ['away_team_id', 'away_team_name']):
            return False
            
        return True

    def validate_event_data(self, event):
        """Validate required event data fields."""
        required_fields = ['id', 'period', 'timestamp', 'type']
        if not isinstance(event, dict) or not all(field in event for field in required_fields):
            return False
        return True

    def process_matches_batch(self, matches_batch):
        """Process a batch of matches with concurrent event fetching."""
        try:
            match_ids = [str(match['match_id']) for match in matches_batch if self.validate_match_data(match)]
            if not match_ids:
                return []

            # Split match IDs into smaller sub-batches to reduce concurrent load
            sub_batch_size = 4
            results = []
            
            for i in range(0, len(match_ids), sub_batch_size):
                sub_batch = match_ids[i:i + sub_batch_size]
                
                # Fetch events for sub-batch
                events_list = self.get_events_batch(sub_batch)
                if not events_list:
                    continue
                    
                # Create a mapping of match_id to events
                events_map = {str(match_id): events for match_id, events in zip(sub_batch, events_list) if events}
                
                # Process each match in the sub-batch
                for match in matches_batch:
                    if str(match['match_id']) not in sub_batch:
                        continue
                        
                    try:
                        if not self.validate_match_data(match):
                            continue

                        match_id = str(match['match_id'])
                        
                        # Prepare and insert match data
                        match_data = {
                            'match_id': match_id,
                            'match_date': match['match_date'],
                            'kick_off': match['kick_off'],
                            'competition_id': match['competition']['competition_id'],
                            'competition_name': match['competition']['competition_name'],
                            'season_id': match['season']['season_id'],
                            'season_name': match['season']['season_name'],
                            'home_team_id': str(match['home_team']['home_team_id']),
                            'home_team_name': match['home_team']['home_team_name'],
                            'away_team_id': str(match['away_team']['away_team_id']),
                            'away_team_name': match['away_team']['away_team_name']
                        }
                        self.db_manager.batch_insert_dimension_data('DimMatch', [match_data])

                        # Prepare and insert team data
                        teams_data = []
                        for team_type, team in [('home_team', match['home_team']), ('away_team', match['away_team'])]:
                            teams_data.append({
                                'team_id': str(team[f'{team_type}_id']),
                                'team_name': team[f'{team_type}_name'],
                                'team_gender': team.get(f'{team_type}_gender'),
                                'team_group': team.get(f'{team_type}_group'),
                                'country_id': team.get('country', {}).get('id'),
                                'country_name': team.get('country', {}).get('name')
                            })
                        self.db_manager.batch_insert_dimension_data('DimTeam', teams_data)

                        # Process events if available
                        events = events_map.get(match_id, [])
                        if not events:
                            continue

                        # Batch process events
                        event_batch_size = 100
                        player_data_batch = []
                        event_data_batch = []
                        
                        for event in events:
                            if not self.validate_event_data(event):
                                continue

                            # Collect player data
                            if 'player' in event and event['player']:
                                player_data_batch.append({
                                    'player_id': str(event['player']['id']),
                                    'player_name': event['player']['name'],
                                    'current_team_id': str(event.get('possession_team', {}).get('id')) if event.get('possession_team') else None
                                })

                            # Get location coordinates
                            location = event.get('location', [])
                            location_x = location[0] if len(location) > 0 else None
                            location_y = location[1] if len(location) > 1 else None

                            # Collect event data
                            event_data_batch.append({
                                'event_id': f"{match_id}_{event['id']}",
                                'match_id': match_id,
                                'player_id': str(event['player']['id']) if event.get('player') else None,
                                'team_id': str(event['possession_team']['id']) if event.get('possession_team') else None,
                                'timestamp': event['timestamp'],
                                'period_id': event['period'],
                                'location_x': location_x,
                                'location_y': location_y,
                                'event_type': event['type']['name'],
                                'possession_id': event.get('possession'),
                                'duration': event.get('duration')
                            })

                            # Insert batches when they reach the batch size
                            if len(player_data_batch) >= event_batch_size:
                                self.db_manager.batch_insert_dimension_data('DimPlayer', player_data_batch)
                                player_data_batch = []
                            
                            if len(event_data_batch) >= event_batch_size:
                                self.db_manager.batch_insert_events(event_data_batch)
                                event_data_batch = []

                        # Insert any remaining batches
                        if player_data_batch:
                            self.db_manager.batch_insert_dimension_data('DimPlayer', player_data_batch)
                        if event_data_batch:
                            self.db_manager.batch_insert_events(event_data_batch)

                        results.append(match_id)
                        logging.info(f"Processed match {match_id}")

                    except Exception as e:
                        logging.error(f"Error processing match {match.get('match_id')}: {str(e)}")
                        continue

                # Add a small delay between sub-batches to prevent overwhelming the connection pool
                time.sleep(0.1)

            return results

        except Exception as e:
            logging.error(f"Error processing match batch: {str(e)}")
            return []

    def load_all_data(self):
        """Load all available data using parallel processing."""
        try:
            # Get competitions
            competitions = self.get_competitions()
            if not competitions:
                logging.error("Failed to fetch competitions")
                return

            # Initialize period dimension data
            periods = [
                {'period_id': 1, 'period_name': 'First Half'},
                {'period_id': 2, 'period_name': 'Second Half'},
                {'period_id': 3, 'period_name': 'First Extra'},
                {'period_id': 4, 'period_name': 'Second Extra'},
                {'period_id': 5, 'period_name': 'Penalties'}
            ]
            self.db_manager.batch_insert_dimension_data('DimPeriod', periods)

            # Process competitions in smaller batches
            comp_batch_size = 4
            all_matches = []
            
            for i in range(0, len(competitions), comp_batch_size):
                comp_batch = competitions[i:i + comp_batch_size]
                matches = self.get_matches_batch(comp_batch)
                if matches:
                    all_matches.extend(matches)
                time.sleep(0.1)  # Add small delay between competition batches

            logging.info(f"Found {len(all_matches)} matches to process")

            # Process matches in batches
            batch_size = 8
            completed = 0
            start_time = time.time()
            
            with tqdm(total=len(all_matches), desc="Processing matches") as pbar:
                for i in range(0, len(all_matches), batch_size):
                    batch = all_matches[i:i + batch_size]
                    try:
                        results = self.process_matches_batch(batch)
                        if results:
                            num_processed = len(results)
                            completed += num_processed
                            elapsed = time.time() - start_time
                            rate = completed / elapsed if elapsed > 0 else 0
                            
                            pbar.set_postfix({
                                'matches/s': f'{rate:.2f}',
                                'completed': completed
                            })
                            pbar.update(num_processed)
                            
                    except Exception as e:
                        logging.error(f"Error processing batch: {str(e)}")
                        continue
                    
                    # Add small delay between batches
                    time.sleep(0.1)

            logging.info("Data loading completed successfully!")

        except Exception as e:
            logging.error(f"Error in load_all_data: {str(e)}")

if __name__ == "__main__":
    # Create necessary directories
    Path("logs").mkdir(exist_ok=True)
    Path("data").mkdir(exist_ok=True)
    
    # Initialize and run the loader
    loader = StatsbombDataLoader()
    loader.load_all_data() 