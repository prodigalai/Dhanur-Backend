-- Migration 011: Spotify Analytics & Growth Schema
-- Comprehensive analytics system for tracks, artists, playlists, and user engagement

-- ===== SPOTIFY ENTITIES =====

-- Artists table
CREATE TABLE IF NOT EXISTS spotify_artists (
    id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(500) NOT NULL,
    spotify_uri VARCHAR(255),
    genres TEXT[], -- Array of genres
    images JSONB, -- Profile images
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tracks table
CREATE TABLE IF NOT EXISTS spotify_tracks (
    id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(500) NOT NULL,
    artist_id VARCHAR(255) REFERENCES spotify_artists(id),
    album_id VARCHAR(255),
    album_name VARCHAR(500),
    isrc VARCHAR(50), -- International Standard Recording Code
    duration_ms INTEGER,
    explicit BOOLEAN DEFAULT FALSE,
    spotify_uri VARCHAR(255),
    release_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Playlists table
CREATE TABLE IF NOT EXISTS spotify_playlists (
    id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(500) NOT NULL,
    description TEXT,
    owner_id VARCHAR(255),
    owner_display_name VARCHAR(255),
    public BOOLEAN DEFAULT FALSE,
    collaborative BOOLEAN DEFAULT FALSE,
    spotify_uri VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ===== ANALYTICS SNAPSHOTS =====

-- Track popularity snapshots
CREATE TABLE IF NOT EXISTS spotify_track_popularity_snapshots (
    id SERIAL PRIMARY KEY,
    track_id VARCHAR(255) REFERENCES spotify_tracks(id),
    popularity INTEGER CHECK (popularity >= 0 AND popularity <= 100),
    snapshot_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(track_id, snapshot_date)
);

-- Artist analytics snapshots
CREATE TABLE IF NOT EXISTS spotify_artist_analytics_snapshots (
    id SERIAL PRIMARY KEY,
    artist_id VARCHAR(255) REFERENCES spotify_artists(id),
    popularity INTEGER CHECK (popularity >= 0 AND popularity <= 100),
    followers_total INTEGER DEFAULT 0,
    snapshot_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(artist_id, snapshot_date)
);

-- Playlist analytics snapshots
CREATE TABLE IF NOT EXISTS spotify_playlist_analytics_snapshots (
    id SERIAL PRIMARY KEY,
    playlist_id VARCHAR(255) REFERENCES spotify_playlists(id),
    followers_total INTEGER DEFAULT 0,
    tracks_count INTEGER DEFAULT 0,
    snapshot_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(playlist_id, snapshot_date)
);

-- ===== AUDIO FEATURES =====

-- Track audio features
CREATE TABLE IF NOT EXISTS spotify_track_audio_features (
    track_id VARCHAR(255) PRIMARY KEY REFERENCES spotify_tracks(id),
    danceability DECIMAL(3,2) CHECK (danceability >= 0 AND danceability <= 1),
    energy DECIMAL(3,2) CHECK (energy >= 0 AND energy <= 1),
    key INTEGER CHECK (key >= -1 AND key <= 11), -- -1 = no key, 0-11 = C through B
    loudness DECIMAL(4,2), -- dB, typically -60 to 0
    mode INTEGER CHECK (mode IN (0, 1)), -- 0 = minor, 1 = major
    speechiness DECIMAL(3,2) CHECK (speechiness >= 0 AND speechiness <= 1),
    acousticness DECIMAL(3,2) CHECK (acousticness >= 0 AND acousticness <= 1),
    instrumentalness DECIMAL(3,2) CHECK (instrumentalness >= 0 AND instrumentalness <= 1),
    liveness DECIMAL(3,2) CHECK (liveness >= 0 AND liveness <= 1),
    valence DECIMAL(3,2) CHECK (valence >= 0 AND valence <= 1),
    tempo DECIMAL(5,2) CHECK (tempo > 0), -- BPM
    time_signature INTEGER CHECK (time_signature > 0),
    retrieved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Track audio analysis
CREATE TABLE IF NOT EXISTS spotify_track_audio_analysis (
    track_id VARCHAR(255) PRIMARY KEY REFERENCES spotify_tracks(id),
    bars_count INTEGER DEFAULT 0,
    beats_count INTEGER DEFAULT 0,
    sections_count INTEGER DEFAULT 0,
    segments_count INTEGER DEFAULT 0,
    tatums_count INTEGER DEFAULT 0,
    duration_ms INTEGER,
    sample_rate INTEGER,
    analysis_data JSONB, -- Full analysis data for advanced features
    retrieved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ===== PLAYLIST TRACKS =====

-- Playlist tracks relationship
CREATE TABLE IF NOT EXISTS spotify_playlist_tracks (
    id SERIAL PRIMARY KEY,
    playlist_id VARCHAR(255) REFERENCES spotify_playlists(id),
    track_id VARCHAR(255) REFERENCES spotify_tracks(id),
    position INTEGER, -- Position in playlist
    added_at TIMESTAMP,
    added_by VARCHAR(255), -- User ID who added the track
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(playlist_id, track_id)
);

-- ===== USER ENGAGEMENT (OAuth Required) =====

-- User library saves
CREATE TABLE IF NOT EXISTS spotify_user_library_saves (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    track_id VARCHAR(255) REFERENCES spotify_tracks(id),
    saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, track_id)
);

-- User recently played
CREATE TABLE IF NOT EXISTS spotify_user_recently_played (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    track_id VARCHAR(255) REFERENCES spotify_tracks(id),
    played_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User follows
CREATE TABLE IF NOT EXISTS spotify_user_follows (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    entity_type VARCHAR(50) CHECK (entity_type IN ('artist', 'playlist')),
    entity_id VARCHAR(255),
    followed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, entity_type, entity_id)
);

-- ===== GROWTH METRICS =====

-- Growth metrics summary
CREATE TABLE IF NOT EXISTS spotify_growth_metrics (
    id SERIAL PRIMARY KEY,
    entity_type VARCHAR(50) CHECK (entity_type IN ('track', 'artist', 'playlist')),
    entity_id VARCHAR(255),
    metric_type VARCHAR(50) CHECK (metric_type IN ('popularity', 'followers', 'tracks_count')),
    current_value DECIMAL(10,2),
    previous_value DECIMAL(10,2),
    change_amount DECIMAL(10,2),
    change_percentage DECIMAL(5,2),
    analysis_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ===== INDEXES FOR PERFORMANCE =====

-- Popularity snapshots
CREATE INDEX IF NOT EXISTS idx_track_popularity_snapshots_track_id ON spotify_track_popularity_snapshots(track_id);
CREATE INDEX IF NOT EXISTS idx_track_popularity_snapshots_date ON spotify_track_popularity_snapshots(snapshot_date);

-- Artist analytics
CREATE INDEX IF NOT EXISTS idx_artist_analytics_snapshots_artist_id ON spotify_artist_analytics_snapshots(artist_id);
CREATE INDEX IF NOT EXISTS idx_artist_analytics_snapshots_date ON spotify_artist_analytics_snapshots(snapshot_date);

-- Playlist analytics
CREATE INDEX IF NOT EXISTS idx_playlist_analytics_snapshots_playlist_id ON spotify_playlist_analytics_snapshots(playlist_id);
CREATE INDEX IF NOT EXISTS idx_playlist_analytics_snapshots_date ON spotify_playlist_analytics_snapshots(snapshot_date);

-- Audio features
CREATE INDEX IF NOT EXISTS idx_track_audio_features_tempo ON spotify_track_audio_features(tempo);
CREATE INDEX IF NOT EXISTS idx_track_audio_features_energy ON spotify_track_audio_features(energy);
CREATE INDEX IF NOT EXISTS idx_track_audio_features_valence ON spotify_track_audio_features(valence);

-- User engagement
CREATE INDEX IF NOT EXISTS idx_user_library_saves_user_id ON spotify_user_library_saves(user_id);
CREATE INDEX IF NOT EXISTS idx_user_recently_played_user_id ON spotify_user_recently_played(user_id);
CREATE INDEX IF NOT EXISTS idx_user_follows_user_id ON spotify_user_follows(user_id);

-- Growth metrics
CREATE INDEX IF NOT EXISTS idx_growth_metrics_entity ON spotify_growth_metrics(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_growth_metrics_date ON spotify_growth_metrics(analysis_date);

-- ===== VIEWS FOR EASY QUERYING =====

-- Current track popularity view
CREATE OR REPLACE VIEW spotify_current_track_popularity AS
SELECT DISTINCT ON (track_id)
    t.id as track_id,
    t.name as track_name,
    a.name as artist_name,
    t.isrc,
    ts.popularity,
    ts.snapshot_date,
    ts.created_at
FROM spotify_tracks t
JOIN spotify_artists a ON t.artist_id = a.id
JOIN spotify_track_popularity_snapshots ts ON t.id = ts.track_id
ORDER BY track_id, ts.snapshot_date DESC;

-- Current artist analytics view
CREATE OR REPLACE VIEW spotify_current_artist_analytics AS
SELECT DISTINCT ON (artist_id)
    a.id as artist_id,
    a.name as artist_name,
    a.genres,
    s.popularity,
    s.followers_total,
    s.snapshot_date,
    s.created_at
FROM spotify_artists a
JOIN spotify_artist_analytics_snapshots s ON a.id = s.artist_id
ORDER BY artist_id, s.snapshot_date DESC;

-- Current playlist analytics view
CREATE OR REPLACE VIEW spotify_current_playlist_analytics AS
SELECT DISTINCT ON (playlist_id)
    p.id as playlist_id,
    p.name as playlist_name,
    p.description,
    p.owner_display_name,
    s.followers_total,
    s.tracks_count,
    s.snapshot_date,
    s.created_at
FROM spotify_playlists p
JOIN spotify_playlist_analytics_snapshots s ON p.id = s.playlist_id
ORDER BY playlist_id, s.snapshot_date DESC;

-- ===== TRIGGERS FOR UPDATED_AT =====

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply triggers to relevant tables
CREATE TRIGGER update_spotify_artists_updated_at BEFORE UPDATE ON spotify_artists FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_spotify_tracks_updated_at BEFORE UPDATE ON spotify_tracks FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_spotify_playlists_updated_at BEFORE UPDATE ON spotify_playlists FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_spotify_track_audio_features_updated_at BEFORE UPDATE ON spotify_track_audio_features FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_spotify_track_audio_analysis_updated_at BEFORE UPDATE ON spotify_track_audio_analysis FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ===== COMMENTS =====

COMMENT ON TABLE spotify_artists IS 'Spotify artists with basic profile information';
COMMENT ON TABLE spotify_tracks IS 'Spotify tracks with metadata and album information';
COMMENT ON TABLE spotify_playlists IS 'Spotify playlists with ownership and visibility settings';
COMMENT ON TABLE spotify_track_popularity_snapshots IS 'Historical track popularity data for trend analysis';
COMMENT ON TABLE spotify_artist_analytics_snapshots IS 'Historical artist analytics for growth tracking';
COMMENT ON TABLE spotify_playlist_analytics_snapshots IS 'Historical playlist analytics for engagement tracking';
COMMENT ON TABLE spotify_track_audio_features IS 'Audio features for tracks (tempo, energy, danceability, etc.)';
COMMENT ON TABLE spotify_track_audio_analysis IS 'Detailed audio analysis including beats, sections, and segments';
COMMENT ON TABLE spotify_playlist_tracks IS 'Relationship between playlists and tracks with positioning';
COMMENT ON TABLE spotify_user_library_saves IS 'User library saves for engagement tracking';
COMMENT ON TABLE spotify_user_recently_played IS 'User recently played tracks for behavior analysis';
COMMENT ON TABLE spotify_user_follows IS 'User follows for social engagement tracking';
COMMENT ON TABLE spotify_growth_metrics IS 'Calculated growth metrics for trend analysis and reporting';
