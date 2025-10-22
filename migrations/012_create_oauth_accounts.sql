-- Migration 012: Create oauth_accounts table
-- This table stores OAuth account information for various providers (Spotify, LinkedIn, YouTube, etc.)

CREATE TABLE IF NOT EXISTS oauth_accounts (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36),
    provider VARCHAR(50) NOT NULL,
    provider_user_id VARCHAR(255) NOT NULL,
    access_token TEXT NOT NULL,
    refresh_token TEXT,
    expires_at TIMESTAMP,
    scope VARCHAR(500),
    profile_data JSON DEFAULT '{}',
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes for performance
    INDEX idx_oauth_provider (provider),
    INDEX idx_oauth_provider_user_id (provider_user_id),
    INDEX idx_oauth_user_id (user_id),
    INDEX idx_oauth_active (is_active),
    
    -- Foreign key constraint
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Add comments for documentation
COMMENT ON TABLE oauth_accounts IS 'Stores OAuth account information for various providers';
COMMENT ON COLUMN oauth_accounts.provider IS 'OAuth provider name (spotify, linkedin, youtube, etc.)';
COMMENT ON COLUMN oauth_accounts.provider_user_id IS 'User ID from the OAuth provider';
COMMENT ON COLUMN oauth_accounts.profile_data IS 'JSON data containing user profile information from the provider';
