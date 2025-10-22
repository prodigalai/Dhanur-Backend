# 🚀 Quick Cloudflare Workers Deployment

## ❌ **Why Pages.dev Doesn't Work**
- `https://content-crew-api-test.pages.dev/` is for static websites
- We need **Cloudflare Workers** for API endpoints
- Workers give you URLs like: `https://your-api.your-subdomain.workers.dev`

## ✅ **Quick Fix: Deploy to Workers**

### **Step 1: Get Your Cloudflare Account ID**
```bash
# Run this command to get your account ID
curl -s "https://api.cloudflare.com/client/v4/user/tokens/verify" \
  -H "Authorization: Bearer YOUR_API_TOKEN" | jq '.result.id'
```

### **Step 2: Create API Token**
1. Go to [Cloudflare Dashboard](https://dash.cloudflare.com/profile/api-tokens)
2. Click "Create Token"
3. Use template: "Custom token"
4. Permissions: `Workers:Edit`
5. Copy the token

### **Step 3: Deploy Using Terminal**
```bash
# Set your credentials
export CLOUDFLARE_ACCOUNT_ID="your-account-id"
export CLOUDFLARE_API_TOKEN="your-api-token"

# Run deployment
python auto-deploy.py
```

## 🔗 **What You'll Get**
- **Working API URL**: `https://content-crew-api-1234567890.your-subdomain.workers.dev`
- **Live endpoints**: `/health`, `/auth/login`, `/`
- **CORS enabled** for all origins
- **HTTPS by default**

## 🧪 **Test Your Live API**
```bash
# Test health
curl https://your-worker-url.workers.dev/health

# Test login
curl -X POST https://your-worker-url.workers.dev/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test"}'
```

## 🎯 **Alternative: Use Existing Scripts**
```bash
# Make executable and run
chmod +x auto-deploy.sh
./auto-deploy.sh
```

**🎉 Your API will be live and working!**
