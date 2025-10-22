#!/usr/bin/env python3

import os
import json
import requests
import subprocess
import sys
from datetime import datetime

class CloudflareDeployer:
    def __init__(self):
        self.account_id = None
        self.api_token = None
        self.worker_name = None
        self.worker_url = None
        
    def check_requirements(self):
        """Check if required tools are installed."""
        print("🔍 Checking requirements...")
        
        # Check if requests is available
        try:
            import requests
        except ImportError:
            print("❌ requests library not found. Installing...")
            subprocess.run([sys.executable, "-m", "pip", "install", "requests"])
        
        print("✅ Requirements met")
    
    def get_credentials(self):
        """Get Cloudflare credentials from user or environment."""
        print("🔐 Getting Cloudflare credentials...")
        
        # Check environment variables first
        self.account_id = os.getenv('CLOUDFLARE_ACCOUNT_ID')
        self.api_token = os.getenv('CLOUDFLARE_API_TOKEN')
        
        if not self.account_id or not self.api_token:
            print("Please provide your Cloudflare credentials:")
            self.account_id = input("Enter your Cloudflare Account ID: ").strip()
            self.api_token = input("Enter your Cloudflare API Token: ").strip()
            
            # Save to environment file
            with open('.cloudflare-env', 'w') as f:
                f.write(f"CLOUDFLARE_ACCOUNT_ID={self.account_id}\n")
                f.write(f"CLOUDFLARE_API_TOKEN={self.api_token}\n")
            print("✅ Credentials saved to .cloudflare-env")
        else:
            print("✅ Using existing credentials")
    
    def create_worker_script(self):
        """Create the worker script file."""
        print("📝 Creating worker script...")
        
        worker_script = '''export default {
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
};'''
        
        with open('worker-script.js', 'w') as f:
            f.write(worker_script)
        
        print("✅ Worker script created")
    
    def deploy_to_cloudflare(self):
        """Deploy to Cloudflare using API."""
        print("🚀 Deploying to Cloudflare...")
        
        self.worker_name = f"content-crew-api-{int(datetime.now().timestamp())}"
        
        # Read worker script
        with open('worker-script.js', 'r') as f:
            worker_code = f.read()
        
        # Prepare headers
        headers = {
            'Authorization': f'Bearer {self.api_token}',
            'Content-Type': 'application/javascript'
        }
        
        # Deploy using Cloudflare API
        url = f"https://api.cloudflare.com/client/v4/accounts/{self.account_id}/workers/scripts"
        
        try:
            response = requests.post(
                url,
                headers=headers,
                data=worker_code,
                params={'name': self.worker_name}
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    print("✅ Worker deployed successfully!")
                    
                    # Get worker URL
                    self.worker_url = f"https://{self.worker_name}.{self.account_id}.workers.dev"
                    print(f"🔗 Your API is live at: {self.worker_url}")
                    
                    # Save URL
                    with open('.worker-url', 'w') as f:
                        f.write(self.worker_url)
                    print("✅ Worker URL saved to .worker-url")
                    
                    # Test deployment
                    self.test_deployment()
                else:
                    print("❌ Deployment failed")
                    print(json.dumps(result, indent=2))
                    sys.exit(1)
            else:
                print(f"❌ Deployment failed with status {response.status_code}")
                print(response.text)
                sys.exit(1)
                
        except Exception as e:
            print(f"❌ Deployment error: {e}")
            sys.exit(1)
    
    def test_deployment(self):
        """Test the deployed API."""
        print("🧪 Testing deployment...")
        
        # Test health endpoint
        print("🏥 Testing health endpoint...")
        try:
            response = requests.get(f"{self.worker_url}/health")
            if response.status_code == 200:
                print("✅ Health check passed")
                print(json.dumps(response.json(), indent=2))
            else:
                print(f"❌ Health check failed: {response.status_code}")
        except Exception as e:
            print(f"❌ Health check error: {e}")
        
        # Test main endpoint
        print("🏠 Testing main endpoint...")
        try:
            response = requests.get(self.worker_url)
            if response.status_code == 200:
                print("✅ Main endpoint working")
                print(json.dumps(response.json(), indent=2))
            else:
                print(f"❌ Main endpoint failed: {response.status_code}")
        except Exception as e:
            print(f"❌ Main endpoint error: {e}")
        
        print("🎉 Deployment and testing completed!")
    
    def run(self):
        """Run the complete deployment process."""
        print("🚀 Fully Automated Cloudflare Deployment")
        print("========================================")
        
        self.check_requirements()
        self.get_credentials()
        self.create_worker_script()
        self.deploy_to_cloudflare()

if __name__ == "__main__":
    deployer = CloudflareDeployer()
    deployer.run()
