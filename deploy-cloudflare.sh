#!/bin/bash

# Content Crew Prodigal - Cloudflare Deployment Script
# This script deploys the API to Cloudflare Workers

set -e

echo "🚀 Content Crew Prodigal - Cloudflare Deployment"
echo "================================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if Wrangler is installed
if ! command -v wrangler &> /dev/null; then
    echo -e "${YELLOW}❌ Wrangler CLI not found. Installing...${NC}"
    npm install -g wrangler
fi

# Check if user is logged in to Cloudflare
if ! wrangler whoami &> /dev/null; then
    echo -e "${YELLOW}🔐 Please log in to Cloudflare...${NC}"
    wrangler login
fi

# Function to deploy to environment
deploy_to_env() {
    local env=$1
    local env_name=$2
    
    echo -e "${BLUE}📦 Deploying to ${env_name}...${NC}"
    
    if wrangler deploy --env $env; then
        echo -e "${GREEN}✅ Successfully deployed to ${env_name}!${NC}"
    else
        echo -e "${RED}❌ Failed to deploy to ${env_name}${NC}"
        exit 1
    fi
}

# Check command line arguments
if [ "$1" = "staging" ]; then
    echo -e "${BLUE}🎯 Deploying to STAGING environment${NC}"
    deploy_to_env "staging" "Staging"
elif [ "$1" = "production" ]; then
    echo -e "${BLUE}🎯 Deploying to PRODUCTION environment${NC}"
    deploy_to_env "production" "Production"
else
    echo -e "${YELLOW}Usage: $0 [staging|production]${NC}"
    echo -e "${YELLOW}  staging    - Deploy to staging environment${NC}"
    echo -e "${YELLOW}  production - Deploy to production environment${NC}"
    echo ""
    echo -e "${BLUE}Available commands:${NC}"
    echo -e "  $0 staging     # Deploy to staging"
    echo -e "  $0 production  # Deploy to production"
    exit 1
fi

echo ""
echo -e "${GREEN}🎉 Deployment completed successfully!${NC}"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo -e "1. Update your DNS records to point to the Cloudflare Workers URL"
echo -e "2. Configure your OAuth redirect URIs for the new domain"
echo -e "3. Update your frontend to use the new API endpoints"
echo -e "4. Test all endpoints to ensure they work correctly"
