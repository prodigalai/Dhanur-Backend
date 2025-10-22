-- Content Crew Multi-Tenant OAuth System
-- Initial database schema migration

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table
CREATE TABLE "users" (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    email text UNIQUE NOT NULL,
    username text UNIQUE NOT NULL,
    full_name text,
    is_active boolean DEFAULT true,
    is_verified boolean DEFAULT false,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

-- Brands table
CREATE TABLE "brands" (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    name text NOT NULL,
    slug text UNIQUE NOT NULL,
    description text,
    logo_url text,
    website_url text,
    is_active boolean DEFAULT true,
    is_verified boolean DEFAULT false,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

-- Brand memberships table
CREATE TABLE "brand_memberships" (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id uuid NOT NULL REFERENCES "users"(id) ON DELETE CASCADE,
    brand_id uuid NOT NULL REFERENCES "brands"(id) ON DELETE CASCADE,
    role text NOT NULL CHECK (role IN ('owner', 'admin', 'editor', 'uploader', 'viewer')),
    is_active boolean DEFAULT true,
    invited_by uuid REFERENCES "users"(id),
    invited_at timestamptz DEFAULT now(),
    accepted_at timestamptz,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now(),
    UNIQUE(user_id, brand_id)
);

-- OAuth accounts table
CREATE TABLE "oauth_accounts" (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id uuid NOT NULL REFERENCES "users"(id) ON DELETE CASCADE,
    provider text NOT NULL,
    provider_user_id text NOT NULL,
    provider_email text,
    provider_username text,
    provider_avatar text,
    is_active boolean DEFAULT true,
    last_used_at timestamptz,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now(),
    UNIQUE(provider, provider_user_id)
);

-- YouTube connections table
CREATE TABLE "youtube_connections" (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    brand_id uuid NOT NULL REFERENCES "brands"(id) ON DELETE CASCADE,
    user_id uuid NOT NULL REFERENCES "users"(id) ON DELETE CASCADE,
    oauth_account_id uuid NOT NULL REFERENCES "oauth_accounts"(id) ON DELETE CASCADE,
    
    -- YouTube Channel Information
    channel_id text NOT NULL,
    channel_title text NOT NULL,
    channel_description text,
    channel_avatar text,
    subscriber_count text,
    view_count text,
    
    -- OAuth Token Information (Encrypted)
    token_wrapped_iv text NOT NULL,
    token_wrapped_ct text NOT NULL,
    token_iv text NOT NULL,
    token_ct text NOT NULL,
    token_fp text NOT NULL,
    
    -- Token Metadata
    access_token_exp timestamptz,
    refresh_token_exp timestamptz,
    scopes jsonb NOT NULL,
    scope_keys jsonb NOT NULL,
    
    -- Connection Status
    is_active boolean DEFAULT true,
    is_verified boolean DEFAULT false,
    last_used_at timestamptz,
    revoked_at timestamptz,
    
    -- Timestamps
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

-- Create indexes for performance
CREATE INDEX idx_users_email ON "users"(email);
CREATE INDEX idx_users_username ON "users"(username);
CREATE INDEX idx_brands_slug ON "brands"(slug);
CREATE INDEX idx_brand_memberships_user ON "brand_memberships"(user_id);
CREATE INDEX idx_brand_memberships_brand ON "brand_memberships"(brand_id);
CREATE INDEX idx_oauth_accounts_user ON "oauth_accounts"(user_id);
CREATE INDEX idx_oauth_accounts_provider ON "oauth_accounts"(provider);
CREATE INDEX idx_youtube_connections_brand ON "youtube_connections"(brand_id);
CREATE INDEX idx_youtube_connections_user ON "youtube_connections"(user_id);
CREATE INDEX idx_youtube_connections_channel ON "youtube_connections"(channel_id);
CREATE INDEX idx_youtube_connections_active ON "youtube_connections"(is_active) WHERE is_active = true;

-- Insert some sample data for development
INSERT INTO "users" (id, email, username, full_name) VALUES 
    (uuid_generate_v4(), 'admin@contentcrew.com', 'admin', 'System Administrator'),
    (uuid_generate_v4(), 'user@contentcrew.com', 'user1', 'Test User');

INSERT INTO "brands" (id, name, slug, description) VALUES 
    (uuid_generate_v4(), 'Content Crew Prodigal', 'content-crew-prodigal', 'Main brand for Content Crew platform'),
    (uuid_generate_v4(), 'Test Brand', 'test-brand', 'Test brand for development');

-- Grant permissions (adjust as needed for your database setup)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO your_user;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO your_user;
