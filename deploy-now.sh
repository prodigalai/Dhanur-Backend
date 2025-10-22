#!/bin/bash

echo "🚀 Simple Working Deployment"
echo "============================"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Function to check if port is in use
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null ; then
        echo -e "${YELLOW}⚠️  Port $port is already in use${NC}"
        echo -e "${BLUE}🔍 Killing process on port $port...${NC}"
        lsof -ti:$port | xargs kill -9
        sleep 2
        echo -e "${GREEN}✅ Port $port is now free${NC}"
    fi
}

# Check and free port 8080
check_port 8080

# Check if cloudflared is available
if ! command -v cloudflared &> /dev/null; then
    echo -e "${RED}❌ cloudflared not found${NC}"
    echo -e "${BLUE}💡 Installing cloudflared...${NC}"
    brew install cloudflared
fi

echo -e "${GREEN}✅ cloudflared is ready: $(cloudflared version)${NC}"

# Create a simple API
echo -e "${BLUE}📝 Creating simple API...${NC}"

cat > api.py << 'EOF'
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
from datetime import datetime
import sys

class API(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        
        data = {
            "message": "Content Crew API is working!",
            "timestamp": datetime.now().isoformat(),
            "status": "success",
            "endpoint": self.path
        }
        
        self.wfile.write(json.dumps(data, indent=2).encode())
    
    def do_POST(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        
        data = {
            "message": "POST request received",
            "timestamp": datetime.now().isoformat(),
            "status": "success",
            "endpoint": self.path
        }
        
        self.wfile.write(json.dumps(data, indent=2).encode())

try:
    print("🚀 Starting API server on port 8080...")
    server = HTTPServer(('localhost', 8080), API)
    print("✅ API server is running!")
    print("🔗 Local URL: http://localhost:8080")
    print("🌐 Cloudflare tunnel will expose this to the internet")
    server.serve_forever()
except OSError as e:
    if e.errno == 48:
        print("❌ Port 8080 is still in use. Please close other applications using this port.")
        print("💡 Try: lsof -ti:8080 | xargs kill -9")
    else:
        print(f"❌ Error starting server: {e}")
    sys.exit(1)
EOF

echo -e "${GREEN}✅ API created${NC}"

# Start the API
echo -e "${BLUE}🚀 Starting API server...${NC}"
python3 api.py &
API_PID=$!

# Wait for server to start
sleep 5

# Check if server is running
echo -e "${BLUE}🔍 Checking if API server is running...${NC}"
if curl -s http://localhost:8080 >/dev/null; then
    echo -e "${GREEN}✅ API server is running on port 8080${NC}"
else
    echo -e "${RED}❌ API server failed to start${NC}"
    kill $API_PID 2>/dev/null
    exit 1
fi

# Start tunnel
echo -e "${BLUE}🌐 Starting Cloudflare tunnel...${NC}"
echo -e "${YELLOW}💡 This will give you a public URL${NC}"

# Start tunnel in background
cloudflared tunnel --url http://localhost:8080 &
TUNNEL_PID=$!

# Wait for tunnel to establish
sleep 5

# Get tunnel info
echo -e "${BLUE}🔍 Getting tunnel URL...${NC}"
TUNNEL_URL=$(./cloudflared tunnel info 2>/dev/null | grep -o 'https://[^.]*\.trycloudflare\.com' | head -1)

if [ -n "$TUNNEL_URL" ]; then
    echo -e "${GREEN}🎉 SUCCESS! Your API is LIVE!${NC}"
    echo "=============================================="
    echo ""
    echo -e "${BLUE}🔗 Your API URL:${NC}"
    echo "   $TUNNEL_URL"
    echo ""
    echo -e "${BLUE}🧪 Test your API:${NC}"
    echo "   curl $TUNNEL_URL/"
    echo "   curl $TUNNEL_URL/health"
    echo ""
    echo -e "${BLUE}💾 URL saved to:${NC}"
    echo "$TUNNEL_URL" > .tunnel-url
    echo "   .tunnel-url"
    echo ""
    echo -e "${GREEN}🚀 Your API is now live on Cloudflare Tunnel!${NC}"
    echo ""
    echo -e "${YELLOW}💡 To stop: Press Ctrl+C${NC}"
    
    # Keep running
    wait
else
    echo -e "${RED}❌ Could not get tunnel URL${NC}"
    echo -e "${BLUE}🔍 Checking tunnel status...${NC}"
    ./cloudflared tunnel info
    
    # Cleanup
    kill $API_PID 2>/dev/null
    kill $TUNNEL_PID 2>/dev/null
    exit 1
fi
