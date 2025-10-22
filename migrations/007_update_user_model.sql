-- Migration 007: Update User model with new fields for registration
-- Add new columns to users table (SQLite compatible)

-- SQLite doesn't support IF NOT EXISTS for ADD COLUMN, so we'll add them one by one
-- and handle errors gracefully

-- Add first_name column
ALTER TABLE users ADD COLUMN first_name VARCHAR(100);

-- Add last_name column  
ALTER TABLE users ADD COLUMN last_name VARCHAR(100);

-- Add password_hash column
ALTER TABLE users ADD COLUMN password_hash VARCHAR(255);

-- Add phone column
ALTER TABLE users ADD COLUMN phone VARCHAR(20);

-- Add company column
ALTER TABLE users ADD COLUMN company VARCHAR(255);

-- Add avatar_url column
ALTER TABLE users ADD COLUMN avatar_url VARCHAR(500);

-- Add mime_type column
ALTER TABLE users ADD COLUMN mime_type VARCHAR(100);

-- Add entity_type column
ALTER TABLE users ADD COLUMN entity_type VARCHAR(50) DEFAULT 'user';

-- Add invitation_token column
ALTER TABLE users ADD COLUMN invitation_token VARCHAR(255);

-- Add referral_code column
ALTER TABLE users ADD COLUMN referral_code VARCHAR(100);

-- Add verification_token column
ALTER TABLE users ADD COLUMN verification_token VARCHAR(255);

-- Add reset_token column
ALTER TABLE users ADD COLUMN reset_token VARCHAR(255);

-- Add reset_token_expires column
ALTER TABLE users ADD COLUMN reset_token_expires DATETIME;

-- Note: SQLite doesn't support ALTER COLUMN to change constraints
-- The username field will remain as is for now

-- Add indexes for better performance (SQLite compatible)
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_verification_token ON users(verification_token);
CREATE INDEX IF NOT EXISTS idx_users_reset_token ON users(reset_token);
