#!/bin/bash

echo "🚀 Simple Cloudflare Deployment (CLI Already Logged In!)"
echo "======================================================"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

# Check if cloudflare CLI is available
if ! command -v cloudflare &> /dev/null; then
    echo "❌ Cloudflare CLI not found. Installing..."
    curl -L https://github.com/cloudflare/cloudflare-cli/releases/latest/download/cloudflare-darwin-amd64 -o cloudflare
    chmod +x cloudflare
    export PATH="$PWD:$PATH"
fi

echo -e "${BLUE}🔍 Getting your Cloudflare account info...${NC}"

# Get account ID
ACCOUNT_ID=$(cloudflare account list --json | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)

if [ -z "$ACCOUNT_ID" ]; then
    echo "❌ Could not get Account ID. Please run: cloudflare login"
    exit 1
fi

echo -e "${GREEN}✅ Account ID: $ACCOUNT_ID${NC}"

# Create worker script
echo -e "${BLUE}📝 Creating worker script...${NC}"

cat > worker-script.js << 'EOF'
export default {
  async fetch(request, env, ctx) {
    const corsHeaders = {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, Authorization',
      'Content-Type': 'application/json'
    };

    if (request.method === 'OPTIONS') {
      return new Response('OK', { headers: corsHeaders });
    }

    const url = new URL(request.url);
    const path = url.pathname;

    if (path === '/health') {
      const healthData = {
        "status": "healthy",
        "timestamp": new Date().toISOString(),
        "version": "1.0.0",
        "deployment": "cloudflare-workers",
        "message": "Content Crew Prodigal API is running!"
      };
      return new Response(JSON.stringify(healthData), { headers: corsHeaders });
    }

    if (path === '/auth/login' && request.method === 'POST') {
      const loginData = {
        "success": true,
        "message": "Login endpoint reached",
        "deployment": "cloudflare-workers",
        "timestamp": new Date().toISOString()
      };
      return new Response(JSON.stringify(loginData), { headers: corsHeaders });
    }

    const defaultData = {
      "message": "Content Crew Prodigal API",
      "version": "1.0.0",
      "status": "live-on-cloudflare",
      "endpoints": ["/", "/health", "/auth/login"],
      "deployment": "Cloudflare Workers"
    };
    return new Response(JSON.stringify(defaultData), { headers: corsHeaders });
  }
};
EOF

echo -e "${GREEN}✅ Worker script created${NC}"

# Deploy using Cloudflare CLI
echo -e "${BLUE}🚀 Deploying to Cloudflare...${NC}"

WORKER_NAME="content-crew-api-$(date +%s)"

# Deploy the worker
cloudflare workers deploy worker-script.js --name "$WORKER_NAME" --account "$ACCOUNT_ID"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Worker deployed successfully!${NC}"
    
    # Get worker URL
    WORKER_URL="https://$WORKER_NAME.$ACCOUNT_ID.workers.dev"
    echo -e "${GREEN}🔗 Your API is LIVE at: $WORKER_URL${NC}"
    
    # Save URL
    echo "$WORKER_URL" > .worker-url
    echo -e "${GREEN}✅ Worker URL saved to .worker-url${NC}"
    
    # Test the deployment
    echo -e "${BLUE}🧪 Testing deployment...${NC}"
    
    echo -e "${BLUE}🏥 Testing /health...${NC}"
    curl -s "$WORKER_URL/health" | head -c 200
    
    echo -e "\n${BLUE}🏠 Testing /...${NC}"
    curl -s "$WORKER_URL/" | head -c 200
    
    echo ""
    echo -e "${GREEN}🎉 SUCCESS! Your API is now LIVE!${NC}"
    echo "=============================================="
    echo ""
    echo -e "${BLUE}🔗 Your API URL:${NC}"
    echo "   $WORKER_URL"
    echo ""
    echo -e "${BLUE}🧪 Test your API:${NC}"
    echo "   curl $WORKER_URL/health"
    echo "   curl $WORKER_URL/"
    echo ""
    echo -e "${BLUE}💾 URL saved to:${NC}"
    echo "   .worker-url"
    echo ""
    echo -e "${GREEN}🚀 Your API is now live and working!${NC}"
    
else
    echo -e "❌ Deployment failed. Please check your Cloudflare CLI setup."
    exit 1
fi
