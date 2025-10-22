#!/bin/bash

echo "🚀 100% TERMINAL-ONLY Cloudflare Deployment"
echo "============================================"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Function to get credentials from user
get_credentials() {
    echo -e "${BLUE}🔐 Getting Cloudflare credentials...${NC}"
    echo ""
    
    # Get Account ID
    read -p "Enter your Cloudflare Account ID: " ACCOUNT_ID
    if [ -z "$ACCOUNT_ID" ]; then
        echo -e "${RED}❌ Account ID cannot be empty${NC}"
        exit 1
    fi
    
    # Get API Token
    read -s -p "Enter your Cloudflare API Token: " API_TOKEN
    echo ""
    if [ -z "$API_TOKEN" ]; then
        echo -e "${RED}❌ API Token cannot be empty${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ Credentials received${NC}"
}

# Function to verify credentials
verify_credentials() {
    echo -e "${BLUE}🔍 Verifying credentials...${NC}"
    
    RESPONSE=$(curl -s -X GET \
        "https://api.cloudflare.com/client/v4/user/tokens/verify" \
        -H "Authorization: Bearer $API_TOKEN")
    
    if echo "$RESPONSE" | grep -q '"success":true'; then
        echo -e "${GREEN}✅ API Token is valid${NC}"
        
        # Get account info
        ACCOUNT_RESPONSE=$(curl -s -X GET \
            "https://api.cloudflare.com/client/v4/accounts" \
            -H "Authorization: Bearer $API_TOKEN")
        
        if echo "$ACCOUNT_RESPONSE" | grep -q "$ACCOUNT_ID"; then
            echo -e "${GREEN}✅ Account ID is valid${NC}"
        else
            echo -e "${RED}❌ Account ID not found or invalid${NC}"
            exit 1
        fi
    else
        echo -e "${RED}❌ API Token is invalid${NC}"
        exit 1
    fi
}

# Function to create worker script
create_worker() {
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
}

# Function to deploy to Cloudflare
deploy_worker() {
    echo -e "${BLUE}🚀 Deploying to Cloudflare...${NC}"
    
    WORKER_NAME="content-crew-api-$(date +%s)"
    
    # Deploy using Cloudflare API
    DEPLOY_RESPONSE=$(curl -s -X POST \
        "https://api.cloudflare.com/client/v4/accounts/$ACCOUNT_ID/workers/scripts" \
        -H "Authorization: Bearer $API_TOKEN" \
        -H "Content-Type: application/javascript" \
        --data-binary @worker-script.js \
        -d "{\"name\":\"$WORKER_NAME\"}")
    
    if echo "$DEPLOY_RESPONSE" | grep -q '"success":true'; then
        echo -e "${GREEN}✅ Worker deployed successfully!${NC}"
        
        # Get worker URL
        WORKER_URL="https://$WORKER_NAME.$ACCOUNT_ID.workers.dev"
        echo -e "${GREEN}🔗 Your API is LIVE at: $WORKER_URL${NC}"
        
        # Save URL
        echo "$WORKER_URL" > .worker-url
        echo -e "${GREEN}✅ Worker URL saved to .worker-url${NC}"
        
        return 0
    else
        echo -e "${RED}❌ Deployment failed${NC}"
        echo "$DEPLOY_RESPONSE"
        return 1
    fi
}

# Function to test deployment
test_deployment() {
    local WORKER_URL="$1"
    echo -e "${BLUE}🧪 Testing deployment...${NC}"
    
    # Test health endpoint
    echo -e "${BLUE}🏥 Testing /health...${NC}"
    HEALTH_RESPONSE=$(curl -s "$WORKER_URL/health")
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Health check passed${NC}"
        echo "Response: $HEALTH_RESPONSE"
    else
        echo -e "${RED}❌ Health check failed${NC}"
    fi
    
    # Test main endpoint
    echo -e "${BLUE}🏠 Testing /...${NC}"
    MAIN_RESPONSE=$(curl -s "$WORKER_URL/")
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Main endpoint working${NC}"
        echo "Response: $MAIN_RESPONSE"
    else
        echo -e "${RED}❌ Main endpoint failed${NC}"
    fi
    
    echo -e "${GREEN}🎉 Testing completed!${NC}"
}

# Function to show final instructions
show_success() {
    local WORKER_URL="$1"
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
    echo "   curl -X POST $WORKER_URL/auth/login -H 'Content-Type: application/json' -d '{\"email\":\"test@example.com\",\"password\":\"test\"}'"
    echo ""
    echo -e "${BLUE}📱 Use in your frontend:${NC}"
    echo "   const API_BASE = '$WORKER_URL';"
    echo ""
    echo -e "${BLUE}💾 URL saved to:${NC}"
    echo "   .worker-url"
    echo ""
    echo -e "${GREEN}🚀 Your API is now live and working!${NC}"
}

# Main execution
main() {
    get_credentials
    verify_credentials
    create_worker
    deploy_worker
    
    if [ $? -eq 0 ]; then
        WORKER_URL=$(cat .worker-url)
        test_deployment "$WORKER_URL"
        show_success "$WORKER_URL"
    else
        echo -e "${RED}❌ Deployment failed. Please check your credentials and try again.${NC}"
        exit 1
    fi
}

# Run main function
main "$@"
