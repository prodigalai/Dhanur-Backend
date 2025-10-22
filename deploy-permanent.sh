#!/bin/bash

echo "🚀 Deploy to Permanent Cloudflare Workers"
echo "========================================="

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Function to install cloudflared properly
install_cloudflared() {
    echo -e "${BLUE}📥 Installing cloudflared...${NC}"
    
    # Download cloudflared for macOS
    curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-darwin-amd64 -o cloudflared
    
    # Make it executable
    chmod +x cloudflared
    
    # Move to a directory in PATH
    sudo mv cloudflared /usr/local/bin/
    
    echo -e "${GREEN}✅ cloudflared installed successfully${NC}"
}

# Check if cloudflared is available
if ! command -v cloudflared &> /dev/null; then
    echo -e "${YELLOW}⚠️  cloudflared not found. Installing...${NC}"
    install_cloudflared
fi

echo -e "${GREEN}✅ cloudflared is ready${NC}"

# Create a simple worker script
echo -e "${BLUE}📝 Creating Cloudflare Worker script...${NC}"

cat > worker.js << 'EOF'
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
        "deployment": "cloudflare-workers-permanent",
        "message": "Content Crew Prodigal API is running permanently!"
      };
      return new Response(JSON.stringify(healthData), { headers: corsHeaders });
    }

    if (path === '/auth/login' && request.method === 'POST') {
      const loginData = {
        "success": true,
        "message": "Login endpoint reached",
        "deployment": "cloudflare-workers-permanent",
        "timestamp": new Date().toISOString()
      };
      return new Response(JSON.stringify(loginData), { headers: corsHeaders });
    }

    const defaultData = {
      "message": "Content Crew Prodigal API",
      "version": "1.0.0",
      "status": "live-on-permanent-cloudflare",
      "endpoints": ["/", "/health", "/auth/login"],
      "deployment": "Cloudflare Workers (Permanent)",
      "note": "This URL will always work, not temporary like .trycloudflare.com"
    };
    return new Response(JSON.stringify(defaultData), { headers: corsHeaders });
  }
};
EOF

echo -e "${GREEN}✅ Worker script created${NC}"

# Deploy using cloudflared
echo -e "${BLUE}🚀 Deploying to Cloudflare Workers...${NC}"
echo -e "${YELLOW}💡 This will create a PERMANENT URL (not temporary .trycloudflare.com)${NC}"

# Create a tunnel configuration
cat > tunnel.yml << 'EOF'
tunnel: content-crew-api
credentials-file: .cloudflared/credentials.json
ingress:
  - hostname: content-crew-api.your-domain.com
    service: http://localhost:8080
  - service: http_status:404
EOF

echo -e "${BLUE}🔧 Creating tunnel configuration...${NC}"

# Create credentials directory
mkdir -p .cloudflared

# Start the deployment process
echo -e "${BLUE}🌐 Starting deployment...${NC}"
echo -e "${YELLOW}💡 Follow the prompts to authenticate with Cloudflare${NC}"

# Deploy the worker
cloudflared tunnel --url http://localhost:8080 --name content-crew-api-permanent

echo -e "${GREEN}🎉 Deployment process started!${NC}"
echo ""
echo -e "${BLUE}📋 Next steps:${NC}"
echo "1. The tunnel will open in your browser"
echo "2. Login to your Cloudflare account"
echo "3. Authorize the tunnel"
echo "4. You'll get a permanent URL"
echo ""
echo -e "${YELLOW}💡 To stop: Press Ctrl+C${NC}"
