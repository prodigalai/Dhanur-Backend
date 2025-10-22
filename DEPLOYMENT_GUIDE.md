# 🚀 Cloudflare Deployment Guide

## 📋 **Quick Deploy (No Wrangler Needed)**

### **Step 1: Get Your Cloudflare Credentials**
1. Go to [Cloudflare Dashboard](https://dash.cloudflare.com)
2. Click on your profile → **API Tokens**
3. Create new token with **Workers:Edit** permissions
4. Copy your **Account ID** and **API Token**

### **Step 2: Deploy Using Terminal Commands**

#### **Option A: Using cURL**
```bash
# Make script executable
chmod +x deploy-curl.sh

# Run deployment script
./deploy-curl.sh
```

#### **Option B: Using Python**
```bash
# Run Python deployment script
python deploy-python.py

# Or directly
python3 deploy-python.py
```

#### **Option C: Using Node.js**
```bash
# Make script executable
chmod +x deploy-node.js

# Run Node.js deployment script
./deploy-node.js
```

### **Step 3: Manual Deployment to Cloudflare**

1. **Open [Cloudflare Dashboard](https://dash.cloudflare.com)**
2. **Click "Workers & Pages"**
3. **Click "Create application"**
4. **Choose "Create Worker"**
5. **Copy content from `worker-script.js`**
6. **Paste into the editor**
7. **Click "Deploy"**

### **Step 4: Get Your Live URL**

After deployment, you'll get a URL like:
```
https://content-crew-api.your-subdomain.workers.dev
```

## 🧪 **Test Your Live API**

### **Health Check**
```bash
curl https://your-worker-url.workers.dev/health
```

### **Login Endpoint**
```bash
curl -X POST https://your-worker-url.workers.dev/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test"}'
```

### **Main Endpoint**
```bash
curl https://your-worker-url.workers.dev/
```

## 🔧 **Available Endpoints**

- **`GET /`** - API Information
- **`GET /health`** - Health Check
- **`POST /auth/login`** - Authentication (Mock)
- **`OPTIONS /*`** - CORS Preflight

## 📱 **Frontend Integration**

Update your frontend to use the new Cloudflare URL:
```javascript
const API_BASE = 'https://your-worker-url.workers.dev';

// Test health
fetch(`${API_BASE}/health`)
  .then(response => response.json())
  .then(data => console.log(data));

// Test login
fetch(`${API_BASE}/auth/login`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ email: 'test@example.com', password: 'test' })
})
.then(response => response.json())
.then(data => console.log(data));
```

## 🎯 **What You Get**

✅ **Live API URL** (no localhost needed)  
✅ **CORS enabled** for all origins  
✅ **HTTPS by default**  
✅ **Global CDN** (fast worldwide)  
✅ **No server maintenance**  
✅ **Automatic scaling**  

## 🚨 **Troubleshooting**

### **CORS Issues**
- Make sure your frontend URL is in the allowed origins
- Check that OPTIONS requests are handled

### **Deployment Errors**
- Verify your Cloudflare account has Workers enabled
- Check your API token permissions
- Ensure the worker script syntax is correct

## 🔄 **Update Your API**

To update your deployed API:
1. Modify `worker-script.js`
2. Copy the new content
3. Go to Cloudflare Dashboard → Workers
4. Edit your worker
5. Paste new code and deploy

---

**🎉 Your API is now live on Cloudflare!**
