#!/bin/bash

echo "🚀 Deploy to Cloudflare Tunnel (.trycloudflare.com)"
echo "=================================================="

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

# Check if cloudflared is installed
if ! command -v cloudflared &> /dev/null; then
    echo -e "${BLUE}📥 Installing cloudflared...${NC}"
    curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-darwin-amd64 -o cloudflared
    chmod +x cloudflared
    export PATH="$PWD:$PATH"
fi

echo -e "${BLUE}🔍 Starting Cloudflare Tunnel...${NC}"

# Create a simple API server
echo -e "${BLUE}📝 Creating API server...${NC}"

cat > simple-api.py << 'EOF'
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
from datetime import datetime
import urllib.parse

class ContentCrewAPI(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()
    
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        
        if self.path == '/health':
            data = {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "version": "1.0.0",
                "deployment": "cloudflare-tunnel",
                "message": "Content Crew Prodigal API is running!"
            }
        else:
            data = {
                "message": "Content Crew Prodigal API",
                "version": "1.0.0",
                "status": "live-on-cloudflare-tunnel",
                "endpoints": ["/", "/health", "/auth/login"],
                "deployment": "Cloudflare Tunnel (.trycloudflare.com)"
            }
        
        self.wfile.write(json.dumps(data, indent=2).encode())
    
    def do_POST(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        
        if self.path == '/auth/login':
            data = {
                "success": true,
                "message": "Login endpoint reached",
                "deployment": "cloudflare-tunnel",
                "timestamp": datetime.now().isoformat()
            }
        else:
            data = {
                "message": "POST endpoint reached",
                "path": self.path,
                "timestamp": datetime.now().isoformat()
            }
        
        self.wfile.write(json.dumps(data, indent=2).encode())

if __name__ == '__main__':
    server = HTTPServer(('localhost', 8080), ContentCrewAPI)
    print("🚀 API Server running on http://localhost:8080")
    print("🔗 Cloudflare Tunnel will expose this to the internet")
    server.serve_forever()
EOF

echo -e "${GREEN}✅ API server created${NC}"

# Start the API server in background
echo -e "${BLUE}🚀 Starting API server...${NC}"
python3 simple-api.py &
API_PID=$!

# Wait a moment for server to start
sleep 2

# Start Cloudflare Tunnel
echo -e "${BLUE}🌐 Starting Cloudflare Tunnel...${NC}"
echo -e "${YELLOW}💡 This will give you a .trycloudflare.com URL${NC}"

# Start tunnel in background
cloudflared tunnel --url http://localhost:8080 &
TUNNEL_PID=$!

# Wait for tunnel to establish
echo -e "${BLUE}⏳ Waiting for tunnel to establish...${NC}"
sleep 5

# Get tunnel info
echo -e "${BLUE}🔍 Getting tunnel URL...${NC}"
TUNNEL_URL=$(cloudflared tunnel info 2>/dev/null | grep -o 'https://[^.]*\.trycloudflare\.com' | head -1)

if [ -n "$TUNNEL_URL" ]; then
    echo -e "${GREEN}🎉 SUCCESS! Your API is LIVE!${NC}"
    echo "=============================================="
    echo ""
    echo -e "${BLUE}🔗 Your API URL:${NC}"
    echo "   $TUNNEL_URL"
    echo ""
    echo -e "${BLUE}🧪 Test your API:${NC}"
    echo "   curl $TUNNEL_URL/health"
    echo "   curl $TUNNEL_URL/"
    echo "   curl -X POST $TUNNEL_URL/auth/login -H 'Content-Type: application/json' -d '{\"email\":\"test@example.com\",\"password\":\"test\"}'"
    echo ""
    echo -e "${BLUE}💾 URL saved to:${NC}"
    echo "$TUNNEL_URL" > .tunnel-url
    echo "   .tunnel-url"
    echo ""
    echo -e "${GREEN}🚀 Your API is now live on Cloudflare Tunnel!${NC}"
    echo ""
    echo -e "${YELLOW}💡 To stop the tunnel and server:${NC}"
    echo "   kill $TUNNEL_PID $API_PID"
    echo ""
    echo -e "${YELLOW}💡 Or just press Ctrl+C in this terminal${NC}"
    
    # Keep running
    wait
else
    echo -e "${RED}❌ Could not get tunnel URL${NC}"
    echo -e "${BLUE}🔍 Checking tunnel status...${NC}"
    cloudflared tunnel info
    
    # Cleanup
    kill $API_PID 2>/dev/null
    kill $TUNNEL_PID 2>/dev/null
    exit 1
fi
