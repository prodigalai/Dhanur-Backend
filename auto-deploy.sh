#!/bin/bash

echo "🚀 Fully Automated Cloudflare Deployment"
echo "========================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if required tools are installed
check_requirements() {
    echo -e "${BLUE}🔍 Checking requirements...${NC}"
    
    if ! command -v curl &> /dev/null; then
        echo -e "${RED}❌ cURL is not installed${NC}"
        exit 1
    fi
    
    if ! command -v jq &> /dev/null; then
        echo -e "${YELLOW}⚠️  jq is not installed. Installing...${NC}"
        if command -v brew &> /dev/null; then
            brew install jq
        elif command -v apt-get &> /dev/null; then
            sudo apt-get update && sudo apt-get install -y jq
        elif command -v yum &> /dev/null; then
            sudo yum install -y jq
        else
            echo -e "${RED}❌ Please install jq manually${NC}"
            exit 1
        fi
    fi
    
    echo -e "${GREEN}✅ Requirements met${NC}"
}

# Get Cloudflare credentials
get_credentials() {
    echo -e "${BLUE}🔐 Getting Cloudflare credentials...${NC}"
    
    # Check if credentials are already set
    if [ -z "$CLOUDFLARE_ACCOUNT_ID" ] || [ -z "$CLOUDFLARE_API_TOKEN" ]; then
        echo -e "${YELLOW}Please provide your Cloudflare credentials:${NC}"
        
        read -p "Enter your Cloudflare Account ID: " CLOUDFLARE_ACCOUNT_ID
        read -s -p "Enter your Cloudflare API Token: " CLOUDFLARE_API_TOKEN
        echo ""
        
        # Save to environment file
        echo "CLOUDFLARE_ACCOUNT_ID=$CLOUDFLARE_ACCOUNT_ID" > .cloudflare-env
        echo "CLOUDFLARE_API_TOKEN=$CLOUDFLARE_API_TOKEN" >> .cloudflare-env
        echo -e "${GREEN}✅ Credentials saved to .cloudflare-env${NC}"
    else
        echo -e "${GREEN}✅ Using existing credentials${NC}"
    fi
    
    export CLOUDFLARE_ACCOUNT_ID
    export CLODFLARE_API_TOKEN
}

# Create worker script
create_worker_script() {
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

# Deploy to Cloudflare using API
deploy_to_cloudflare() {
    echo -e "${BLUE}🚀 Deploying to Cloudflare...${NC}"
    
    WORKER_NAME="content-crew-api-$(date +%s)"
    
    # Create deployment
    echo -e "${BLUE}📦 Creating deployment...${NC}"
    
    DEPLOY_RESPONSE=$(curl -s -X POST \
        "https://api.cloudflare.com/client/v4/accounts/$CLOUDFLARE_ACCOUNT_ID/workers/scripts" \
        -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
        -H "Content-Type: application/javascript" \
        --data-binary @worker-script.js \
        -d "{\"name\":\"$WORKER_NAME\"}")
    
    if echo "$DEPLOY_RESPONSE" | jq -e '.success' > /dev/null; then
        echo -e "${GREEN}✅ Worker deployed successfully!${NC}"
        
        # Get the worker URL
        WORKER_URL="https://$WORKER_NAME.$CLOUDFLARE_ACCOUNT_ID.workers.dev"
        echo -e "${GREEN}🔗 Your API is live at: $WORKER_URL${NC}"
        
        # Save the URL
        echo "$WORKER_URL" > .worker-url
        echo -e "${GREEN}✅ Worker URL saved to .worker-url${NC}"
        
        # Test the deployment
        test_deployment "$WORKER_URL"
        
    else
        echo -e "${RED}❌ Deployment failed${NC}"
        echo "$DEPLOY_RESPONSE" | jq '.errors[]?.message' 2>/dev/null || echo "$DEPLOY_RESPONSE"
        exit 1
    fi
}

# Test the deployed API
test_deployment() {
    local WORKER_URL="$1"
    echo -e "${BLUE}🧪 Testing deployment...${NC}"
    
    # Test health endpoint
    echo -e "${BLUE}🏥 Testing health endpoint...${NC}"
    HEALTH_RESPONSE=$(curl -s "$WORKER_URL/health")
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Health check passed${NC}"
        echo "$HEALTH_RESPONSE" | jq '.' 2>/dev/null || echo "$HEALTH_RESPONSE"
    else
        echo -e "${RED}❌ Health check failed${NC}"
    fi
    
    # Test main endpoint
    echo -e "${BLUE}🏠 Testing main endpoint...${NC}"
    MAIN_RESPONSE=$(curl -s "$WORKER_URL/")
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Main endpoint working${NC}"
        echo "$MAIN_RESPONSE" | jq '.' 2>/dev/null || echo "$MAIN_RESPONSE"
    else
        echo -e "${RED}❌ Main endpoint failed${NC}"
    fi
    
    echo -e "${GREEN}🎉 Deployment and testing completed!${NC}"
}

# Main execution
main() {
    check_requirements
    get_credentials
    create_worker_script
    deploy_to_cloudflare
}

# Run main function
main "$@"
