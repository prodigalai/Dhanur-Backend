#!/usr/bin/env python3
"""
Spotify Analytics Cron Job Script
Automated data collection and growth tracking for Spotify entities
"""

import os
import sys
import logging
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any
import json

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from providers.spotify.v1.analytics_ops import SpotifyAnalyticsOps
from core.db import get_db
from controllers.spotify_analytics_controller import SpotifyAnalyticsController

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("spotify_analytics_cron.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SpotifyAnalyticsCron:
    """Automated Spotify analytics data collection and processing."""
    
    def __init__(self):
        self.spotify_ops = None
        self.db = None
        self.analytics_controller = None
        
    async def initialize(self):
        """Initialize the cron job with database and Spotify operations."""
        try:
            # Initialize database
            self.db = next(get_db())
            self.analytics_controller = SpotifyAnalyticsController(self.db)
            
            # Initialize Spotify operations with client credentials
            self.spotify_ops = SpotifyAnalyticsOps()
            
            # Get client credentials from environment
            client_id = os.getenv("SPOTIFY_CLIENT_ID")
            client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
            
            if not client_id or not client_secret:
                raise Exception("Spotify client credentials not found in environment")
            
            # Get access token
            self.spotify_ops.get_client_credentials_token(client_id, client_secret)
            
            logger.info("Spotify Analytics Cron initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize cron job: {e}")
            raise
    
    async def collect_track_popularity_snapshots(self, track_ids: List[str] = None):
        """Collect popularity snapshots for tracks."""
        try:
            if not track_ids:
                # Get track IDs from database
                track_ids = self._get_track_ids_from_db()
            
            if not track_ids:
                logger.info("No tracks found for popularity snapshot collection")
                return
            
            logger.info(f"Collecting popularity snapshots for {len(track_ids)} tracks")
            
            # Get popularity data in batches
            batch_size = 50
            for i in range(0, len(track_ids), batch_size):
                batch = track_ids[i:i + batch_size]
                
                try:
                    tracks_data = self.spotify_ops.get_multiple_tracks_popularity(batch)
                    
                    # Store snapshots
                    for track in tracks_data['tracks']:
                        await self._store_track_popularity_snapshot(track)
                    
                    logger.info(f"Processed batch {i//batch_size + 1}: {len(batch)} tracks")
                    
                    # Rate limiting
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    logger.error(f"Error processing batch {i//batch_size + 1}: {e}")
                    continue
            
            logger.info("Track popularity snapshot collection completed")
            
        except Exception as e:
            logger.error(f"Error in track popularity collection: {e}")
    
    async def collect_artist_analytics_snapshots(self, artist_ids: List[str] = None):
        """Collect analytics snapshots for artists."""
        try:
            if not artist_ids:
                # Get artist IDs from database
                artist_ids = self._get_artist_ids_from_db()
            
            if not artist_ids:
                logger.info("No artists found for analytics snapshot collection")
                return
            
            logger.info(f"Collecting analytics snapshots for {len(artist_ids)} artists")
            
            # Get analytics data in batches
            batch_size = 50
            for i in range(0, len(artist_ids), batch_size):
                batch = artist_ids[i:i + batch_size]
                
                try:
                    artists_data = self.spotify_ops.get_multiple_artists_analytics(batch)
                    
                    # Store snapshots
                    for artist in artists_data['artists']:
                        await self._store_artist_analytics_snapshot(artist)
                    
                    logger.info(f"Processed batch {i//batch_size + 1}: {len(batch)} artists")
                    
                    # Rate limiting
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    logger.error(f"Error processing batch {i//batch_size + 1}: {e}")
                    continue
            
            logger.info("Artist analytics snapshot collection completed")
            
        except Exception as e:
            logger.error(f"Error in artist analytics collection: {e}")
    
    async def collect_playlist_analytics_snapshots(self, playlist_ids: List[str] = None):
        """Collect analytics snapshots for playlists."""
        try:
            if not playlist_ids:
                # Get playlist IDs from database
                playlist_ids = self._get_playlist_ids_from_db()
            
            if not playlist_ids:
                logger.info("No playlists found for analytics snapshot collection")
                return
            
            logger.info(f"Collecting analytics snapshots for {len(playlist_ids)} playlists")
            
            # Process playlists individually (they require separate API calls)
            for i, playlist_id in enumerate(playlist_ids):
                try:
                    playlist_data = self.spotify_ops.get_playlist_analytics(playlist_id)
                    
                    # Store snapshot
                    await self._store_playlist_analytics_snapshot(playlist_data)
                    
                    if (i + 1) % 10 == 0:
                        logger.info(f"Processed {i + 1}/{len(playlist_ids)} playlists")
                    
                    # Rate limiting
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    logger.error(f"Error processing playlist {playlist_id}: {e}")
                    continue
            
            logger.info("Playlist analytics snapshot collection completed")
            
        except Exception as e:
            logger.error(f"Error in playlist analytics collection: {e}")
    
    async def collect_audio_features(self, track_ids: List[str] = None):
        """Collect audio features for tracks."""
        try:
            if not track_ids:
                # Get track IDs that don't have audio features
                track_ids = self._get_tracks_without_audio_features()
            
            if not track_ids:
                logger.info("No tracks found for audio features collection")
                return
            
            logger.info(f"Collecting audio features for {len(track_ids)} tracks")
            
            # Get audio features in batches
            batch_size = 100
            for i in range(0, len(track_ids), batch_size):
                batch = track_ids[i:i + batch_size]
                
                try:
                    features_data = self.spotify_ops.get_multiple_tracks_audio_features(batch)
                    
                    # Store features
                    for track_features in features_data['tracks_features']:
                        await self._store_track_audio_features(track_features)
                    
                    logger.info(f"Processed batch {i//batch_size + 1}: {len(batch)} tracks")
                    
                    # Rate limiting
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    logger.error(f"Error processing batch {i//batch_size + 1}: {e}")
                    continue
            
            logger.info("Audio features collection completed")
            
        except Exception as e:
            logger.error(f"Error in audio features collection: {e}")
    
    async def calculate_growth_metrics(self):
        """Calculate and store growth metrics for all entities."""
        try:
            logger.info("Starting growth metrics calculation")
            
            # Get entities that have snapshots
            entities = self._get_entities_for_growth_calculation()
            
            for entity_type, entity_ids in entities.items():
                logger.info(f"Calculating growth metrics for {len(entity_ids)} {entity_type}s")
                
                for entity_id in entity_ids:
                    try:
                        await self._calculate_entity_growth_metrics(entity_type, entity_id)
                    except Exception as e:
                        logger.error(f"Error calculating growth metrics for {entity_type} {entity_id}: {e}")
                        continue
                
                logger.info(f"Completed growth metrics calculation for {entity_type}s")
            
            logger.info("Growth metrics calculation completed")
            
        except Exception as e:
            logger.error(f"Error in growth metrics calculation: {e}")
    
    async def run_full_analytics_collection(self):
        """Run complete analytics data collection."""
        try:
            logger.info("Starting full Spotify analytics collection")
            start_time = datetime.now()
            
            # Collect all types of data
            await self.collect_track_popularity_snapshots()
            await self.collect_artist_analytics_snapshots()
            await self.collect_playlist_analytics_snapshots()
            await self.collect_audio_features()
            
            # Calculate growth metrics
            await self.calculate_growth_metrics()
            
            end_time = datetime.now()
            duration = end_time - start_time
            
            logger.info(f"Full analytics collection completed in {duration}")
            
        except Exception as e:
            logger.error(f"Error in full analytics collection: {e}")
    
    # ===== HELPER METHODS =====
    
    def _get_track_ids_from_db(self) -> List[str]:
        """Get track IDs from database."""
        try:
            result = self.db.execute("SELECT id FROM spotify_tracks").fetchall()
            return [row[0] for row in result]
        except Exception as e:
            logger.error(f"Error getting track IDs from database: {e}")
            return []
    
    def _get_artist_ids_from_db(self) -> List[str]:
        """Get artist IDs from database."""
        try:
            result = self.db.execute("SELECT id FROM spotify_artists").fetchall()
            return [row[0] for row in result]
        except Exception as e:
            logger.error(f"Error getting artist IDs from database: {e}")
            return []
    
    def _get_playlist_ids_from_db(self) -> List[str]:
        """Get playlist IDs from database."""
        try:
            result = self.db.execute("SELECT id FROM spotify_playlists").fetchall()
            return [row[0] for row in result]
        except Exception as e:
            logger.error(f"Error getting playlist IDs from database: {e}")
            return []
    
    def _get_tracks_without_audio_features(self) -> List[str]:
        """Get track IDs that don't have audio features."""
        try:
            result = self.db.execute("""
                SELECT t.id FROM spotify_tracks t
                LEFT JOIN spotify_track_audio_features af ON t.id = af.track_id
                WHERE af.track_id IS NULL
            """).fetchall()
            return [row[0] for row in result]
        except Exception as e:
            logger.error(f"Error getting tracks without audio features: {e}")
            return []
    
    def _get_entities_for_growth_calculation(self) -> Dict[str, List[str]]:
        """Get entities that have snapshots for growth calculation."""
        try:
            entities = {}
            
            # Get tracks with snapshots
            track_result = self.db.execute("""
                SELECT DISTINCT track_id FROM spotify_track_popularity_snapshots
                WHERE snapshot_date >= CURRENT_DATE - INTERVAL '2 days'
            """).fetchall()
            entities['track'] = [row[0] for row in track_result]
            
            # Get artists with snapshots
            artist_result = self.db.execute("""
                SELECT DISTINCT artist_id FROM spotify_artist_analytics_snapshots
                WHERE snapshot_date >= CURRENT_DATE - INTERVAL '2 days'
            """).fetchall()
            entities['artist'] = [row[0] for row in artist_result]
            
            # Get playlists with snapshots
            playlist_result = self.db.execute("""
                SELECT DISTINCT playlist_id FROM spotify_playlist_analytics_snapshots
                WHERE snapshot_date >= CURRENT_DATE - INTERVAL '2 days'
            """).fetchall()
            entities['playlist'] = [row[0] for row in playlist_result]
            
            return entities
            
        except Exception as e:
            logger.error(f"Error getting entities for growth calculation: {e}")
            return {}
    
    async def _store_track_popularity_snapshot(self, track_data: Dict[str, Any]):
        """Store track popularity snapshot."""
        try:
            self.analytics_controller.store_track_popularity_snapshot(track_data)
        except Exception as e:
            logger.error(f"Error storing track popularity snapshot: {e}")
    
    async def _store_artist_analytics_snapshot(self, artist_data: Dict[str, Any]):
        """Store artist analytics snapshot."""
        try:
            self.analytics_controller.store_artist_analytics_snapshot(artist_data)
        except Exception as e:
            logger.error(f"Error storing artist analytics snapshot: {e}")
    
    async def _store_playlist_analytics_snapshot(self, playlist_data: Dict[str, Any]):
        """Store playlist analytics snapshot."""
        try:
            self.analytics_controller.store_playlist_analytics_snapshot(playlist_data)
        except Exception as e:
            logger.error(f"Error storing playlist analytics snapshot: {e}")
    
    async def _store_track_audio_features(self, features_data: Dict[str, Any]):
        """Store track audio features."""
        try:
            self.analytics_controller.store_track_audio_features(features_data)
        except Exception as e:
            logger.error(f"Error storing track audio features: {e}")
    
    async def _calculate_entity_growth_metrics(self, entity_type: str, entity_id: str):
        """Calculate growth metrics for an entity."""
        try:
            self.analytics_controller.calculate_and_store_growth_metrics(entity_type, entity_id)
        except Exception as e:
            logger.error(f"Error calculating growth metrics: {e}")

async def main():
    """Main function to run the cron job."""
    try:
        cron = SpotifyAnalyticsCron()
        await cron.initialize()
        
        # Run full analytics collection
        await cron.run_full_analytics_collection()
        
        logger.info("Spotify Analytics Cron job completed successfully")
        
    except Exception as e:
        logger.error(f"Spotify Analytics Cron job failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
