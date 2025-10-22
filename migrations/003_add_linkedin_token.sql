-- Migration: Add LinkedIn access token field
-- Date: 2025-01-19

-- Add access_token_encrypted column to linkedin_connections table
ALTER TABLE linkedin_connections ADD COLUMN access_token_encrypted TEXT;
