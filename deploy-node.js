#!/usr/bin/env node

const https = require('https');
const fs = require('fs');

console.log('🚀 Deploying to Cloudflare using Node.js...');

// Create worker script
const workerScript = `export default {
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
};`;

// Write worker script to file
fs.writeFileSync('worker-script.js', workerScript);

console.log('✅ Worker script created: worker-script.js');
console.log('');
console.log('📋 Terminal-Only Deployment Options:');
console.log('1. Use deploy-now.sh (Recommended):');
console.log('   ./deploy-now.sh');
console.log('2. Use deploy-terminal-only.sh:');
console.log('   ./deploy-terminal-only.sh');
console.log('3. Use deploy-simple.sh:');
console.log('   ./deploy-simple.sh');
console.log('');
console.log('🔗 Your API will be live at: https://content-crew-api.your-subdomain.workers.dev');
console.log('');
console.log('🧪 Test endpoints:');
console.log('  - GET  /health');
console.log('  - POST /auth/login');
console.log('  - GET  /');
