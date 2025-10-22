#!/bin/bash

echo "🚀 Deploying to Cloudflare using cURL..."

# You'll need to get these from Cloudflare dashboard
CLOUDFLARE_ACCOUNT_ID="your-account-id"
CLOUDFLARE_API_TOKEN="your-api-token"
WORKER_NAME="content-crew-api"

# Create the worker script content
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

echo "✅ Worker script created"
echo ""
echo "📋 Terminal-Only Deployment Options:"
echo "1. Use deploy-now.sh (Recommended):"
echo "   ./deploy-now.sh"
echo "2. Use deploy-terminal-only.sh:"
echo "   ./deploy-terminal-only.sh"
echo "3. Use deploy-simple.sh:"
echo "   ./deploy-simple.sh"
echo ""
echo "🔗 You'll get a URL like: https://content-crew-api.your-subdomain.workers.dev"
