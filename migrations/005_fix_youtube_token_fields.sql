-- Migration 005: Fix YouTube token fields to be nullable
-- SQLite doesn't support ALTER COLUMN DROP NOT NULL, so we need to recreate the table

-- Create a backup of the current table
CREATE TABLE youtube_connections_backup AS SELECT * FROM youtube_connections;

-- Drop the current table
DROP TABLE youtube_connections;

-- Recreate the table with nullable token fields
CREATE TABLE youtube_connections (
    id VARCHAR(36) NOT NULL,
    brand_id VARCHAR(36) NOT NULL,
    user_id VARCHAR(36) NOT NULL,
    oauth_account_id VARCHAR(36) NOT NULL,
    channel_id VARCHAR(255) NOT NULL,
    channel_title VARCHAR(255) NOT NULL,
    channel_description TEXT,
    channel_avatar VARCHAR(500),
    subscriber_count VARCHAR(50),
    view_count VARCHAR(50),
    token_wrapped_iv VARCHAR(255),  -- Made nullable
    token_wrapped_ct VARCHAR(255),  -- Made nullable
    token_iv VARCHAR(255),          -- Made nullable
    token_ct VARCHAR(255),          -- Made nullable
    token_fp VARCHAR(255),          -- Made nullable
    access_token_exp DATETIME,
    refresh_token_exp DATETIME,
    scopes JSON NOT NULL,
    scope_keys JSON NOT NULL,
    is_active BOOLEAN,
    is_verified BOOLEAN,
    last_used_at DATETIME,
    revoked_at DATETIME,
    created_at DATETIME,
    updated_at DATETIME,
    access_token_encrypted TEXT,    -- New encrypted token format
    CONSTRAINT pk_youtube_connections PRIMARY KEY (id),
    CONSTRAINT fk_youtube_connections_brand_id_brands FOREIGN KEY(brand_id) REFERENCES brands (id),
    CONSTRAINT fk_youtube_connections_user_id_users FOREIGN KEY(user_id) REFERENCES users (id),
    CONSTRAINT fk_youtube_connections_oauth_account_id_oauth_accounts FOREIGN KEY(oauth_account_id) REFERENCES oauth_accounts (id)
);

-- Recreate indexes
CREATE INDEX ix_youtube_connections_channel_id ON youtube_connections (channel_id);
CREATE INDEX ix_youtube_connections_user_id ON youtube_connections (user_id);
CREATE INDEX ix_youtube_connections_brand_id ON youtube_connections (brand_id);

-- Restore data from backup
INSERT INTO youtube_connections SELECT * FROM youtube_connections_backup;

-- Drop the backup table
DROP TABLE youtube_connections_backup;
