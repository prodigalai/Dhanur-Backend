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
