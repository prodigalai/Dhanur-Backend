-- Migration 010: Make oauth_accounts.user_id nullable for anonymous OAuth flows
-- This allows storing OAuth accounts for users who haven't created accounts yet

-- Make user_id nullable in oauth_accounts table
ALTER TABLE "oauth_accounts" ALTER COLUMN user_id DROP NOT NULL;

-- Add a comment explaining the change
COMMENT ON COLUMN "oauth_accounts"."user_id" IS 'User ID (nullable for anonymous OAuth flows)';

-- Update the foreign key constraint to allow NULL values
-- Note: PostgreSQL automatically handles this when we make the column nullable
