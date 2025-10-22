#!/bin/bash

# Setup local environment variables for Content Crew Prodigal API

echo "🔧 Setting up local environment variables..."

# Export environment variables for local development
export DATABASE_HOST="localhost"
export DATABASE_PORT="5432"
export DATABASE_NAME="content_crew"
export DATABASE_USERNAME="postgres"
export DATABASE_PASSWORD="password"
export JWT_SECRET_KEY="local-dev-secret-key-12345"
export JWT_ALGORITHM="HS256"
export JWT_ACCESS_TOKEN_EXPIRE_MINUTES="30"
export JWT_REFRESH_TOKEN_EXPIRE_DAYS="7"
export API_KEY_HEADER="X-API-Key"
export API_KEY_SECRET="local-api-key-secret-12345"
export ALLOWED_ORIGINS="http://localhost:3000,http://localhost:8080,http://127.0.0.1:3000,http://127.0.0.1:8080"
export PORT="8080"
export HOST="0.0.0.0"
export DEBUG="true"

echo "✅ Environment variables set for local development"
echo ""
echo "📋 Current environment:"
echo "   DATABASE_HOST: $DATABASE_HOST"
echo "   DATABASE_PORT: $DATABASE_PORT"
echo "   DATABASE_NAME: $DATABASE_NAME"
echo "   PORT: $PORT"
echo "   DEBUG: $DEBUG"
echo ""
echo "🚀 You can now run: python main.py"
