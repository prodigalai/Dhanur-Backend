#!/bin/bash

echo "🚀 Simple Cloudflare Tunnel Deployment"
echo "======================================"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check if cloudflared is available
if ! command -v cloudflared &> /dev/null; then
    echo -e "${RED}❌ cloudflared not found${NC}"
    echo -e "${BLUE}💡 Installing cloudflared...${NC}"
    brew install cloudflared
fi

echo -e "${GREEN}✅ cloudflared is ready: $(cloudflared version)${NC}"

# Check if port 8080 is in use
if lsof -Pi :8080 -sTCP:LISTEN -t >/dev/null ; then
    echo -e "${YELLOW}⚠️  Port 8080 is already in use${NC}"
    echo -e "${BLUE}🔍 Killing process on port 8080...${NC}"
    lsof -ti:8080 | xargs kill -9
    sleep 2
    echo -e "${GREEN}✅ Port 8080 is now free${NC}"
fi

# Create a simple API
echo -e "${BLUE}📝 Creating simple API...${NC}"

cat > simple-api.py << 'EOF'
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
from datetime import datetime

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
            "endpoint": self.path,
            "deployment": "Cloudflare Tunnel"
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
            "endpoint": self.path,
            "deployment": "Cloudflare Tunnel"
        }
        
        self.wfile.write(json.dumps(data, indent=2).encode())

print("🚀 Starting API server on port 8080...")
print("✅ API server is running!")
print("🔗 Local URL: http://localhost:8080")
print("🌐 Cloudflare tunnel will expose this to the internet")
print("💡 Press Ctrl+C to stop")

server = HTTPServer(('localhost', 8080), API)
server.serve_forever()
EOF

echo -e "${GREEN}✅ API created${NC}"

echo ""
echo -e "${BLUE}📋 Next Steps:${NC}"
echo "1. Open a NEW terminal window/tab"
echo "2. Run this command:"
echo "   python3 simple-api.py"
echo "3. Come back to this terminal and run:"
echo "   cloudflared tunnel --url http://localhost:8080"
echo ""
echo -e "${YELLOW}💡 This will give you a working .trycloudflare.com URL${NC}"
echo ""
echo -e "${GREEN}🚀 Ready to deploy!${NC}"
