from js import Response, console
import json

def handle_request(request, env):
    """Handle HTTP requests for Content Crew Prodigal API."""
    
    # Get request details
    url = request.url
    method = request.method
    path = url.split('/')[-1] if '/' in url else ''
    
    # CORS headers
    cors_headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization',
        'Content-Type': 'application/json'
    }
    
    # Handle OPTIONS (CORS preflight)
    if method == 'OPTIONS':
        return Response('OK', headers=cors_headers)
    
    # Handle different endpoints
    if path == '' or path == 'index.html':
        # Return the HTML test page
        html_content = '''
<!DOCTYPE html>
<html>
<head>
    <title>Content Crew Prodigal API</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background: #f0f0f0; }
        .container { max-width: 800px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; }
        .endpoint { background: #f8f9fa; padding: 15px; margin: 10px 0; border-radius: 5px; }
        .method { background: #007bff; color: white; padding: 2px 8px; border-radius: 3px; font-size: 12px; }
        button { background: #28a745; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; }
        button:hover { background: #218838; }
        .response { background: #f8f9fa; padding: 10px; margin: 10px 0; border-radius: 5px; font-family: monospace; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 Content Crew Prodigal API</h1>
        <p>Your API is now live on Cloudflare Workers!</p>
        
        <div class="endpoint">
            <h3><span class="method">GET</span> /health</h3>
            <p>Health check endpoint</p>
            <button onclick="testHealth()">Test Health</button>
            <div id="healthResponse" class="response" style="display:none;"></div>
        </div>
        
        <div class="endpoint">
            <h3><span class="method">POST</span> /auth/login</h3>
            <p>User authentication endpoint</p>
            <button onclick="testLogin()">Test Login</button>
            <div id="loginResponse" class="response" style="display:none;"></div>
        </div>
        
        <div class="endpoint">
            <h3><span class="method">GET</span> /</h3>
            <p>This page (API info)</p>
        </div>
        
        <h2>📊 API Status</h2>
        <div id="status">Ready to test endpoints</div>
    </div>

    <script>
        const API_BASE = window.location.origin;
        
        async function testHealth() {
            try {
                const response = await fetch(API_BASE + '/health');
                const data = await response.json();
                document.getElementById('healthResponse').innerHTML = JSON.stringify(data, null, 2);
                document.getElementById('healthResponse').style.display = 'block';
                document.getElementById('status').innerHTML = '✅ Health check successful';
            } catch (error) {
                document.getElementById('status').innerHTML = '❌ Error: ' + error.message;
            }
        }
        
        async function testLogin() {
            try {
                const response = await fetch(API_BASE + '/auth/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email: 'test@example.com', password: 'test' })
                });
                const data = await response.json();
                document.getElementById('loginResponse').innerHTML = JSON.stringify(data, null, 2);
                document.getElementById('loginResponse').style.display = 'block';
                document.getElementById('status').innerHTML = '✅ Login test completed';
            } catch (error) {
                document.getElementById('status').innerHTML = '❌ Error: ' + error.message;
            }
        }
    </script>
</body>
</html>
        '''
        return Response(html_content, headers={'Content-Type': 'text/html'})
    
    elif path == 'health':
        # Health check endpoint
        health_data = {
            "status": "healthy",
            "timestamp": "2024-01-01T00:00:00Z",
            "version": "1.0.0",
            "deployment": "cloudflare-workers",
            "message": "Content Crew Prodigal API is running on Cloudflare Workers!"
        }
        return Response(json.dumps(health_data), headers=cors_headers)
    
    elif path == 'auth' and 'login' in url:
        # Mock login endpoint
        login_data = {
            "success": True,
            "message": "Login endpoint reached (mock response)",
            "deployment": "cloudflare-workers",
            "note": "This is a demo endpoint. Connect your real API for full functionality."
        }
        return Response(json.dumps(login_data), headers=cors_headers)
    
    else:
        # Default response
        default_data = {
            "message": "Content Crew Prodigal API",
            "version": "1.0.0",
            "status": "live-on-cloudflare",
            "endpoints": [
                "/ - API Information",
                "/health - Health Check",
                "/auth/login - Authentication (Mock)"
            ],
            "deployment": "Cloudflare Workers"
        }
        return Response(json.dumps(default_data), headers=cors_headers)

# Cloudflare Workers entry point
def fetch(request, env):
    return handle_request(request, env)
