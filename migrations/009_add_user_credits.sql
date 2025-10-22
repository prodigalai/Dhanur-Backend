-- Migration 009: Add credits fields to users table
ALTER TABLE users ADD COLUMN prodigal_credits INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN dhanur_credits INTEGER DEFAULT 0;

-- Create indexes for better performance
CREATE INDEX idx_users_prodigal_credits ON users(prodigal_credits);
CREATE INDEX idx_users_dhanur_credits ON users(dhanur_credits);
