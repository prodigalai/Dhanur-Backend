-- Migration: Add LinkedIn support
-- Date: 2025-01-19

-- Create linkedin_connections table
CREATE TABLE IF NOT EXISTS linkedin_connections (
    id VARCHAR(36) PRIMARY KEY,
    brand_id VARCHAR(36) NOT NULL,
    user_id VARCHAR(36) NOT NULL,
    oauth_account_id VARCHAR(36) NOT NULL,
    
    -- LinkedIn specific fields
    profile_id VARCHAR(255),
    profile_url VARCHAR(500),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    headline VARCHAR(500),
    industry VARCHAR(255),
    location VARCHAR(255),
    
    -- Connection status
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    last_used_at TIMESTAMP WITH TIME ZONE,
    revoked_at TIMESTAMP WITH TIME ZONE,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign keys
    FOREIGN KEY (brand_id) REFERENCES brands(id),
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (oauth_account_id) REFERENCES oauth_accounts(id)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_linkedin_connections_brand_id ON linkedin_connections(brand_id);
CREATE INDEX IF NOT EXISTS idx_linkedin_connections_user_id ON linkedin_connections(user_id);
CREATE INDEX IF NOT EXISTS idx_linkedin_connections_oauth_account_id ON linkedin_connections(oauth_account_id);
CREATE INDEX IF NOT EXISTS idx_linkedin_connections_profile_id ON linkedin_connections(profile_id);
CREATE INDEX IF NOT EXISTS idx_linkedin_connections_active ON linkedin_connections(is_active, revoked_at);

-- Add LinkedIn provider to oauth_accounts if not exists
-- (This is handled by the application logic, but we can ensure the table structure supports it)
