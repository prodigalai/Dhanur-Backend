#!/usr/bin/env python3
"""
Spotify Analytics & Growth Controller
Manages analytics data collection, growth tracking, and automated insights
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text, desc, func
from datetime import datetime, timedelta
import json

from providers.spotify.v1.analytics_ops import SpotifyAnalyticsOps
from models.sqlalchemy_models import User, OAuthAccount
from utils.error_handler import (
    ValidationException, AuthenticationException, 
    DatabaseException, ContentCrewException
)

logger = logging.getLogger(__name__)

class SpotifyAnalyticsController:
    """Controller for Spotify analytics and growth tracking."""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    # ===== TRACK ANALYTICS =====
    
    def store_track_popularity_snapshot(self, track_data: Dict[str, Any]) -> Dict[str, Any]:
        """Store track popularity snapshot in database."""
        try:
            # First, ensure track exists in spotify_tracks table
            track_id = track_data['track_id']
            
            # Check if track exists
            existing_track = self.db.execute(
                text("SELECT id FROM spotify_tracks WHERE id = :track_id"),
                {"track_id": track_id}
            ).fetchone()
            
            if not existing_track:
                # Create track record
                self.db.execute(text("""
                    INSERT INTO spotify_tracks (id, name, album_name, isrc, duration_ms, explicit, release_date)
                    VALUES (:track_id, :name, :album_name, :isrc, :duration_ms, :explicit, :release_date)
                """), {
                    "track_id": track_id,
                    "name": track_data['name'],
                    "album_name": track_data['album']['name'],
                    "isrc": track_data.get('isrc'),
                    "duration_ms": track_data['duration_ms'],
                    "explicit": track_data['explicit'],
                    "release_date": track_data['album']['release_date']
                })
                
                # Create artist record if not exists
                for artist in track_data['artists']:
                    self.db.execute(text("""
                        INSERT INTO spotify_artists (id, name)
                        VALUES (:artist_id, :name)
                        ON CONFLICT (id) DO NOTHING
                    """), {
                        "artist_id": artist['id'],
                        "name": artist['name']
                    })
                
                # Update track with artist_id
                self.db.execute(text("""
                    UPDATE spotify_tracks 
                    SET artist_id = :artist_id 
                    WHERE id = :track_id
                """), {
                    "artist_id": track_data['artists'][0]['id'],
                    "track_id": track_id
                })
            
            # Store popularity snapshot
            self.db.execute(text("""
                INSERT INTO spotify_track_popularity_snapshots (track_id, popularity, snapshot_date)
                VALUES (:track_id, :popularity, :snapshot_date)
                ON CONFLICT (track_id, snapshot_date) DO UPDATE SET
                popularity = EXCLUDED.popularity
            """), {
                "track_id": track_id,
                "popularity": track_data['popularity'],
                "snapshot_date": datetime.now()
            })
            
            self.db.commit()
            
            logger.info(f"Stored popularity snapshot for track {track_id}: {track_data['popularity']}")
            return {"success": True, "track_id": track_id, "popularity": track_data['popularity']}
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error storing track popularity snapshot: {e}")
            raise ContentCrewException(f"Failed to store track popularity snapshot: {str(e)}")
    
    def get_track_popularity_trend(self, track_id: str, days: int = 30) -> Dict[str, Any]:
        """Get track popularity trend over specified days."""
        try:
            start_date = datetime.now() - timedelta(days=days)
            
            snapshots = self.db.execute(text("""
                SELECT popularity, snapshot_date
                FROM spotify_track_popularity_snapshots
                WHERE track_id = :track_id AND snapshot_date >= :start_date
                ORDER BY snapshot_date ASC
            """), {
                "track_id": track_id,
                "start_date": start_date
            }).fetchall()
            
            if not snapshots:
                return {"error": "No popularity data found for this track"}
            
            # Calculate trend metrics
            first_popularity = snapshots[0].popularity
            last_popularity = snapshots[-1].popularity
            change = last_popularity - first_popularity
            change_percent = (change / first_popularity * 100) if first_popularity > 0 else 0
            
            trend_data = {
                'track_id': track_id,
                'period_days': days,
                'first_popularity': first_popularity,
                'last_popularity': last_popularity,
                'change': change,
                'change_percent': round(change_percent, 2),
                'trend': 'growing' if change > 0 else 'declining' if change < 0 else 'stable',
                'snapshots': [
                    {
                        'popularity': s.popularity,
                        'date': s.snapshot_date.isoformat()
                    } for s in snapshots
                ]
            }
            
            return trend_data
            
        except Exception as e:
            logger.error(f"Error getting track popularity trend: {e}")
            raise ContentCrewException(f"Failed to get track popularity trend: {str(e)}")
    
    # ===== ARTIST ANALYTICS =====
    
    def store_artist_analytics_snapshot(self, artist_data: Dict[str, Any]) -> Dict[str, Any]:
        """Store artist analytics snapshot in database."""
        try:
            artist_id = artist_data['artist_id']
            
            # Ensure artist exists
            self.db.execute(text("""
                INSERT INTO spotify_artists (id, name, genres, images)
                VALUES (:artist_id, :name, :genres, :images)
                ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                genres = EXCLUDED.genres,
                images = EXCLUDED.images,
                updated_at = CURRENT_TIMESTAMP
            """), {
                "artist_id": artist_id,
                "name": artist_data['name'],
                "genres": artist_data['genres'],
                "images": json.dumps(artist_data['images'])
            })
            
            # Store analytics snapshot
            self.db.execute(text("""
                INSERT INTO spotify_artist_analytics_snapshots (artist_id, popularity, followers_total, snapshot_date)
                VALUES (:artist_id, :popularity, :followers_total, :snapshot_date)
                ON CONFLICT (artist_id, snapshot_date) DO UPDATE SET
                popularity = EXCLUDED.popularity,
                followers_total = EXCLUDED.followers_total
            """), {
                "artist_id": artist_id,
                "popularity": artist_data['popularity'],
                "followers_total": artist_data['followers'],
                "snapshot_date": datetime.now()
            })
            
            self.db.commit()
            
            logger.info(f"Stored analytics snapshot for artist {artist_id}")
            return {"success": True, "artist_id": artist_id}
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error storing artist analytics snapshot: {e}")
            raise ContentCrewException(f"Failed to store artist analytics snapshot: {str(e)}")
    
    def get_artist_growth_report(self, artist_id: str, days: int = 30) -> Dict[str, Any]:
        """Get comprehensive artist growth report."""
        try:
            start_date = datetime.now() - timedelta(days=days)
            
            # Get current and previous snapshots
            snapshots = self.db.execute(text("""
                SELECT popularity, followers_total, snapshot_date
                FROM spotify_artist_analytics_snapshots
                WHERE artist_id = :artist_id AND snapshot_date >= :start_date
                ORDER BY snapshot_date DESC
                LIMIT 2
            """), {
                "artist_id": artist_id,
                "start_date": start_date
            }).fetchall()
            
            if len(snapshots) < 2:
                return {"error": "Insufficient data for growth analysis"}
            
            current = snapshots[0]
            previous = snapshots[1]
            
            # Calculate growth metrics
            popularity_change = current.popularity - previous.popularity
            popularity_change_percent = (popularity_change / previous.popularity * 100) if previous.popularity > 0 else 0
            
            followers_change = current.followers_total - previous.followers_total
            followers_change_percent = (followers_change / previous.followers_total * 100) if previous.followers_total > 0 else 0
            
            # Get artist info
            artist_info = self.db.execute(text("""
                SELECT name, genres FROM spotify_artists WHERE id = :artist_id
            """), {"artist_id": artist_id}).fetchone()
            
            report = {
                'artist_id': artist_id,
                'artist_name': artist_info.name if artist_info else 'Unknown',
                'genres': artist_info.genres if artist_info else [],
                'analysis_period_days': days,
                'current_metrics': {
                    'popularity': current.popularity,
                    'followers': current.followers_total,
                    'date': current.snapshot_date.isoformat()
                },
                'previous_metrics': {
                    'popularity': previous.popularity,
                    'followers': previous.followers_total,
                    'date': previous.snapshot_date.isoformat()
                },
                'growth_metrics': {
                    'popularity_change': popularity_change,
                    'popularity_change_percent': round(popularity_change_percent, 2),
                    'followers_change': followers_change,
                    'followers_change_percent': round(followers_change_percent, 2)
                },
                'status': 'growing' if popularity_change > 0 or followers_change > 0 else 'declining',
                'insights': []
            }
            
            # Add insights
            if popularity_change_percent > 10:
                report['insights'].append("Strong popularity growth - consider capitalizing on momentum")
            elif popularity_change_percent < -5:
                report['insights'].append("Popularity declining - review content strategy")
            
            if followers_change_percent > 5:
                report['insights'].append("Growing follower base - engage with new followers")
            elif followers_change_percent < -2:
                report['insights'].append("Follower loss detected - investigate engagement strategies")
            
            return report
            
        except Exception as e:
            logger.error(f"Error getting artist growth report: {e}")
            raise ContentCrewException(f"Failed to get artist growth report: {str(e)}")
    
    # ===== PLAYLIST ANALYTICS =====
    
    def store_playlist_analytics_snapshot(self, playlist_data: Dict[str, Any]) -> Dict[str, Any]:
        """Store playlist analytics snapshot in database."""
        try:
            playlist_id = playlist_data['playlist_id']
            
            # Ensure playlist exists
            self.db.execute(text("""
                INSERT INTO spotify_playlists (id, name, description, owner_id, owner_display_name, public, collaborative)
                VALUES (:playlist_id, :name, :description, :owner_id, :owner_display_name, :public, :collaborative)
                ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                description = EXCLUDED.description,
                owner_display_name = EXCLUDED.owner_display_name,
                public = EXCLUDED.public,
                collaborative = EXCLUDED.collaborative,
                updated_at = CURRENT_TIMESTAMP
            """), {
                "playlist_id": playlist_id,
                "name": playlist_data['name'],
                "description": playlist_data.get('description', ''),
                "owner_id": playlist_data['owner']['id'],
                "owner_display_name": playlist_data['owner']['display_name'],
                "public": playlist_data['public'],
                "collaborative": playlist_data['collaborative']
            })
            
            # Store analytics snapshot
            self.db.execute(text("""
                INSERT INTO spotify_playlist_analytics_snapshots (playlist_id, followers_total, tracks_count, snapshot_date)
                VALUES (:playlist_id, :followers_total, :tracks_count, :snapshot_date)
                ON CONFLICT (playlist_id, snapshot_date) DO UPDATE SET
                followers_total = EXCLUDED.followers_total,
                tracks_count = EXCLUDED.tracks_count
            """), {
                "playlist_id": playlist_id,
                "followers_total": playlist_data['followers'],
                "tracks_count": playlist_data['tracks_count'],
                "snapshot_date": datetime.now()
            })
            
            # Store playlist tracks
            for track in playlist_data['tracks']:
                if track['track_id']:
                    self.db.execute(text("""
                        INSERT INTO spotify_playlist_tracks (playlist_id, track_id, added_at, added_by)
                        VALUES (:playlist_id, :track_id, :added_at, :added_by)
                        ON CONFLICT (playlist_id, track_id) DO UPDATE SET
                        position = EXCLUDED.position,
                        added_at = EXCLUDED.added_at
                    """), {
                        "playlist_id": playlist_id,
                        "track_id": track['track_id'],
                        "added_at": track['added_at'],
                        "added_by": track['added_by']
                    })
            
            self.db.commit()
            
            logger.info(f"Stored analytics snapshot for playlist {playlist_id}")
            return {"success": True, "playlist_id": playlist_id}
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error storing playlist analytics snapshot: {e}")
            raise ContentCrewException(f"Failed to store playlist analytics snapshot: {str(e)}")
    
    # ===== AUDIO FEATURES =====
    
    def store_track_audio_features(self, features_data: Dict[str, Any]) -> Dict[str, Any]:
        """Store track audio features in database."""
        try:
            track_id = features_data['track_id']
            features = features_data['audio_features']
            
            self.db.execute(text("""
                INSERT INTO spotify_track_audio_features (
                    track_id, danceability, energy, key, loudness, mode, speechiness,
                    acousticness, instrumentalness, liveness, valence, tempo, time_signature
                ) VALUES (
                    :track_id, :danceability, :energy, :key, :loudness, :mode, :speechiness,
                    :acousticness, :instrumentalness, :liveness, :valence, :tempo, :time_signature
                ) ON CONFLICT (track_id) DO UPDATE SET
                    danceability = EXCLUDED.danceability,
                    energy = EXCLUDED.energy,
                    key = EXCLUDED.key,
                    loudness = EXCLUDED.loudness,
                    mode = EXCLUDED.mode,
                    speechiness = EXCLUDED.speechiness,
                    acousticness = EXCLUDED.acousticness,
                    instrumentalness = EXCLUDED.instrumentalness,
                    liveness = EXCLUDED.liveness,
                    valence = EXCLUDED.valence,
                    tempo = EXCLUDED.tempo,
                    time_signature = EXCLUDED.time_signature,
                    updated_at = CURRENT_TIMESTAMP
            """), {
                "track_id": track_id,
                "danceability": features['danceability'],
                "energy": features['energy'],
                "key": features['key'],
                "loudness": features['loudness'],
                "mode": features['mode'],
                "speechiness": features['speechiness'],
                "acousticness": features['acousticness'],
                "instrumentalness": features['instrumentalness'],
                "liveness": features['liveness'],
                "valence": features['valence'],
                "tempo": features['tempo'],
                "time_signature": features['time_signature']
            })
            
            self.db.commit()
            
            logger.info(f"Stored audio features for track {track_id}")
            return {"success": True, "track_id": track_id}
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error storing track audio features: {e}")
            raise ContentCrewException(f"Failed to store track audio features: {str(e)}")
    
    # ===== GROWTH METRICS CALCULATION =====
    
    def calculate_and_store_growth_metrics(self, entity_type: str, entity_id: str) -> Dict[str, Any]:
        """Calculate and store growth metrics for an entity."""
        try:
            if entity_type == 'track':
                return self._calculate_track_growth_metrics(entity_id)
            elif entity_type == 'artist':
                return self._calculate_artist_growth_metrics(entity_id)
            elif entity_type == 'playlist':
                return self._calculate_playlist_growth_metrics(entity_id)
            else:
                raise ValidationException(f"Invalid entity type: {entity_type}")
                
        except Exception as e:
            logger.error(f"Error calculating growth metrics: {e}")
            raise ContentCrewException(f"Failed to calculate growth metrics: {str(e)}")
    
    def _calculate_track_growth_metrics(self, track_id: str) -> Dict[str, Any]:
        """Calculate growth metrics for a track."""
        try:
            # Get current and previous popularity snapshots
            snapshots = self.db.execute(text("""
                SELECT popularity, snapshot_date
                FROM spotify_track_popularity_snapshots
                WHERE track_id = :track_id
                ORDER BY snapshot_date DESC
                LIMIT 2
            """), {"track_id": track_id}).fetchall()
            
            if len(snapshots) < 2:
                return {"error": "Insufficient data for growth calculation"}
            
            current = snapshots[0]
            previous = snapshots[1]
            
            change_amount = current.popularity - previous.popularity
            change_percentage = (change_amount / previous.popularity * 100) if previous.popularity > 0 else 0
            
            # Store growth metrics
            self.db.execute(text("""
                INSERT INTO spotify_growth_metrics (
                    entity_type, entity_id, metric_type, current_value, previous_value,
                    change_amount, change_percentage, analysis_date
                ) VALUES (
                    'track', :entity_id, 'popularity', :current_value, :previous_value,
                    :change_amount, :change_percentage, :analysis_date
                )
            """), {
                "entity_id": track_id,
                "current_value": current.popularity,
                "previous_value": previous.popularity,
                "change_amount": change_amount,
                "change_percentage": round(change_percentage, 2),
                "analysis_date": datetime.now()
            })
            
            self.db.commit()
            
            return {
                "success": True,
                "entity_type": "track",
                "entity_id": track_id,
                "metric_type": "popularity",
                "change_amount": change_amount,
                "change_percentage": round(change_percentage, 2)
            }
            
        except Exception as e:
            self.db.rollback()
            raise e
    
    def _calculate_artist_growth_metrics(self, artist_id: str) -> Dict[str, Any]:
        """Calculate growth metrics for an artist."""
        try:
            # Get current and previous analytics snapshots
            snapshots = self.db.execute(text("""
                SELECT popularity, followers_total, snapshot_date
                FROM spotify_artist_analytics_snapshots
                WHERE artist_id = :artist_id
                ORDER BY snapshot_date DESC
                LIMIT 2
            """), {"artist_id": artist_id}).fetchall()
            
            if len(snapshots) < 2:
                return {"error": "Insufficient data for growth calculation"}
            
            current = snapshots[0]
            previous = snapshots[1]
            
            # Calculate popularity change
            pop_change = current.popularity - previous.popularity
            pop_change_percent = (pop_change / previous.popularity * 100) if previous.popularity > 0 else 0
            
            # Calculate followers change
            fol_change = current.followers_total - previous.followers_total
            fol_change_percent = (fol_change / previous.followers_total * 100) if previous.followers_total > 0 else 0
            
            # Store both metrics
            for metric_type, current_val, previous_val, change_amount, change_percent in [
                ('popularity', current.popularity, previous.popularity, pop_change, pop_change_percent),
                ('followers', current.followers_total, previous.followers_total, fol_change, fol_change_percent)
            ]:
                self.db.execute(text("""
                    INSERT INTO spotify_growth_metrics (
                        entity_type, entity_id, metric_type, current_value, previous_value,
                        change_amount, change_percentage, analysis_date
                    ) VALUES (
                        'artist', :entity_id, :metric_type, :current_value, :previous_value,
                        :change_amount, :change_percentage, :analysis_date
                    )
                """), {
                    "entity_id": artist_id,
                    "metric_type": metric_type,
                    "current_value": current_val,
                    "previous_value": previous_val,
                    "change_amount": change_amount,
                    "change_percentage": round(change_percent, 2),
                    "analysis_date": datetime.now()
                })
            
            self.db.commit()
            
            return {
                "success": True,
                "entity_type": "artist",
                "entity_id": artist_id,
                "metrics": {
                    "popularity": {"change": pop_change, "change_percent": round(pop_change_percent, 2)},
                    "followers": {"change": fol_change, "change_percent": round(fol_change_percent, 2)}
                }
            }
            
        except Exception as e:
            self.db.rollback()
            raise e
    
    def _calculate_playlist_growth_metrics(self, playlist_id: str) -> Dict[str, Any]:
        """Calculate growth metrics for a playlist."""
        try:
            # Get current and previous analytics snapshots
            snapshots = self.db.execute(text("""
                SELECT followers_total, tracks_count, snapshot_date
                FROM spotify_playlist_analytics_snapshots
                WHERE playlist_id = :playlist_id
                ORDER BY snapshot_date DESC
                LIMIT 2
            """), {"playlist_id": playlist_id}).fetchall()
            
            if len(snapshots) < 2:
                return {"error": "Insufficient data for growth calculation"}
            
            current = snapshots[0]
            previous = snapshots[1]
            
            # Calculate followers change
            fol_change = current.followers_total - previous.followers_total
            fol_change_percent = (fol_change / previous.followers_total * 100) if previous.followers_total > 0 else 0
            
            # Calculate tracks change
            tracks_change = current.tracks_count - previous.tracks_count
            tracks_change_percent = (tracks_change / previous.tracks_count * 100) if previous.tracks_count > 0 else 0
            
            # Store both metrics
            for metric_type, current_val, previous_val, change_amount, change_percent in [
                ('followers', current.followers_total, previous.followers_total, fol_change, fol_change_percent),
                ('tracks_count', current.tracks_count, previous.tracks_count, tracks_change, tracks_change_percent)
            ]:
                self.db.execute(text("""
                    INSERT INTO spotify_growth_metrics (
                        entity_type, entity_id, metric_type, current_value, previous_value,
                        change_amount, change_percentage, analysis_date
                    ) VALUES (
                        'playlist', :entity_id, :metric_type, :current_value, :previous_value,
                        :change_amount, :change_percentage, :analysis_date
                    )
                """), {
                    "entity_id": playlist_id,
                    "metric_type": metric_type,
                    "current_value": current_val,
                    "previous_value": previous_val,
                    "change_amount": change_amount,
                    "change_percentage": round(change_percent, 2),
                    "analysis_date": datetime.now()
                })
            
            self.db.commit()
            
            return {
                "success": True,
                "entity_type": "playlist",
                "entity_id": playlist_id,
                "metrics": {
                    "followers": {"change": fol_change, "change_percent": round(fol_change_percent, 2)},
                    "tracks_count": {"change": tracks_change, "change_percent": round(tracks_change_percent, 2)}
                }
            }
            
        except Exception as e:
            self.db.rollback()
            raise e
    
    # ===== DASHBOARD DATA =====
    
    def get_dashboard_summary(self) -> Dict[str, Any]:
        """Get summary data for analytics dashboard."""
        try:
            # Get total counts
            total_tracks = self.db.execute(text("SELECT COUNT(*) FROM spotify_tracks")).scalar()
            total_artists = self.db.execute(text("SELECT COUNT(*) FROM spotify_artists")).scalar()
            total_playlists = self.db.execute(text("SELECT COUNT(*) FROM spotify_playlists")).scalar()
            
            # Get recent growth
            recent_growth = self.db.execute(text("""
                SELECT entity_type, COUNT(*) as count
                FROM spotify_growth_metrics
                WHERE analysis_date >= CURRENT_DATE - INTERVAL '7 days'
                GROUP BY entity_type
            """)).fetchall()
            
            # Get top performing tracks
            top_tracks = self.db.execute(text("""
                SELECT t.name, a.name as artist_name, ts.popularity
                FROM spotify_current_track_popularity ts
                JOIN spotify_tracks t ON ts.track_id = t.id
                JOIN spotify_artists a ON t.artist_id = a.id
                ORDER BY ts.popularity DESC
                LIMIT 10
            """)).fetchall()
            
            # Get top growing artists
            top_growing_artists = self.db.execute(text("""
                SELECT a.name, gm.change_percentage
                FROM spotify_growth_metrics gm
                JOIN spotify_artists a ON gm.entity_id = a.id
                WHERE gm.entity_type = 'artist' 
                AND gm.metric_type = 'followers'
                AND gm.analysis_date >= CURRENT_DATE - INTERVAL '7 days'
                ORDER BY gm.change_percentage DESC
                LIMIT 10
            """)).fetchall()
            
            summary = {
                'total_counts': {
                    'tracks': total_tracks,
                    'artists': total_artists,
                    'playlists': total_playlists
                },
                'recent_growth': {
                    row.entity_type: row.count for row in recent_growth
                },
                'top_tracks': [
                    {
                        'name': row.name,
                        'artist': row.artist_name,
                        'popularity': row.popularity
                    } for row in top_tracks
                ],
                'top_growing_artists': [
                    {
                        'name': row.name,
                        'growth_percent': round(row.change_percentage, 2)
                    } for row in top_growing_artists
                ],
                'last_updated': datetime.now().isoformat()
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting dashboard summary: {e}")
            raise ContentCrewException(f"Failed to get dashboard summary: {str(e)}")
