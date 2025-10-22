-- Migration: Add scheduled_posts table
-- Date: 2024-12-19

-- Create scheduled_posts table
CREATE TABLE IF NOT EXISTS scheduled_posts (
    id TEXT PRIMARY KEY,
    title TEXT,
    content TEXT,
    post_type TEXT NOT NULL,
    scheduled_time DATETIME NOT NULL,
    timezone TEXT DEFAULT 'UTC',
    status TEXT DEFAULT 'scheduled',
    platform TEXT NOT NULL,
    platform_data TEXT, -- JSON stored as TEXT in SQLite
    connection_id TEXT,
    youtube_connection_id TEXT,
    brand_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    published_at DATETIME,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    FOREIGN KEY (connection_id) REFERENCES linkedin_connections(id),
    FOREIGN KEY (youtube_connection_id) REFERENCES youtube_connections(id)
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_scheduled_posts_platform ON scheduled_posts(platform);
CREATE INDEX IF NOT EXISTS idx_scheduled_posts_status ON scheduled_posts(status);
CREATE INDEX IF NOT EXISTS idx_scheduled_posts_scheduled_time ON scheduled_posts(scheduled_time);
CREATE INDEX IF NOT EXISTS idx_scheduled_posts_brand_user ON scheduled_posts(brand_id, user_id);
CREATE INDEX IF NOT EXISTS idx_scheduled_posts_connection ON scheduled_posts(connection_id);
CREATE INDEX IF NOT EXISTS idx_scheduled_posts_youtube_connection ON scheduled_posts(youtube_connection_id);

-- Create index for finding posts ready to publish
CREATE INDEX IF NOT EXISTS idx_scheduled_posts_ready ON scheduled_posts(status, scheduled_time) 
WHERE status = 'scheduled';
