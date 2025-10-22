# 🔐 OAuth Integration Guide - LinkedIn & YouTube

## 📋 **Overview**

This guide covers the complete OAuth integration for LinkedIn and YouTube platforms in the Content Crew API. Both platforms are now fully integrated with proper OAuth flow, token management, and API access.

---

## 🔗 **LinkedIn OAuth Integration**

### **1. LinkedIn App Setup**

1. **Create LinkedIn App:**
   - Go to [LinkedIn Developers](https://www.linkedin.com/developers/)
   - Click "Create App"
   - Fill in app details and submit

2. **Configure OAuth Settings:**
   - Add redirect URI: `https://yourdomain.com/extension/linkedin/callback`
   - Request these scopes:
     - `r_liteprofile` - Read basic profile
     - `r_emailaddress` - Read email address
     - `w_member_social` - Write posts

3. **Get Credentials:**
   - Copy `Client ID` and `Client Secret`
   - Add to your `.env` file

### **2. LinkedIn OAuth Flow**

#### **Step 1: Initiate OAuth**
```bash
POST /extension/linkedin/add
Authorization: Bearer <jwt_token>
```

**Response:**
```json
{
  "success": true,
  "data": {
    "auth_url": "https://www.linkedin.com/oauth/v2/authorization?...",
    "message": "LinkedIn OAuth URL generated"
  }
}
```

#### **Step 2: User Authorization**
- User visits the `auth_url` from step 1
- User authorizes the app
- LinkedIn redirects to callback with `code` and `state`

#### **Step 3: Handle Callback**
```bash
GET /extension/linkedin/callback?code=<auth_code>&state=<state>
```

**Response:**
```json
{
  "success": true,
  "data": {
    "access_token": "AQV...",
    "refresh_token": "AQV...",
    "expires_in": 3600,
    "profile": {
      "id": "user_id",
      "name": "John Doe",
      "email": "john@example.com"
    },
    "message": "LinkedIn authentication successful"
  }
}
```

### **3. LinkedIn API Endpoints**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/extension/linkedin/add` | POST | Get OAuth URL |
| `/extension/linkedin/callback` | GET | Handle OAuth callback |
| `/extension/linkedin/post` | POST | Create LinkedIn post |
| `/extension/linkedin/schedule/post` | POST | Schedule LinkedIn post |
| `/extension/linkedin/posts` | GET | List LinkedIn posts |

---

## 🎥 **YouTube OAuth Integration**

### **1. YouTube App Setup**

1. **Create Google Cloud Project:**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create new project or select existing

2. **Enable YouTube Data API:**
   - Go to "APIs & Services" > "Library"
   - Search for "YouTube Data API v3"
   - Enable the API

3. **Create OAuth 2.0 Credentials:**
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth 2.0 Client IDs"
   - Choose "Web application"
   - Add redirect URI: `https://yourdomain.com/extension/youtube/callback`
   - Download the JSON file

4. **Configure Scopes:**
   - `youtube.upload` - Upload videos
   - `youtube.readonly` - Read channel data

### **2. YouTube OAuth Flow**

#### **Step 1: Initiate OAuth**
```bash
GET /extension/youtube/auth
Authorization: Bearer <jwt_token>
```

**Response:**
```json
{
  "success": true,
  "data": {
    "auth_url": "https://accounts.google.com/oauth/authorize?...",
    "state": "youtube_auth",
    "message": "YouTube OAuth URL generated"
  }
}
```

#### **Step 2: User Authorization**
- User visits the `auth_url` from step 1
- User authorizes the app
- Google redirects to callback with `code` and `state`

#### **Step 3: Handle Callback**
```bash
GET /extension/youtube/callback?code=<auth_code>&state=<state>
```

**Response:**
```json
{
  "success": true,
  "data": {
    "access_token": "ya29...",
    "refresh_token": "1//04...",
    "scopes": ["https://www.googleapis.com/auth/youtube.upload"],
    "message": "YouTube authentication successful"
  }
}
```

### **3. YouTube API Endpoints**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/extension/youtube/auth` | GET | Get OAuth URL |
| `/extension/youtube/callback` | GET | Handle OAuth callback |
| `/extension/youtube/post` | POST | Upload YouTube video |
| `/extension/youtube/scheduled` | GET | List scheduled videos |
| `/extension/youtube/live` | GET | Get live stream info |
| `/extension/youtube/videos` | GET | List uploaded videos |

---

## ⚙️ **Environment Configuration**

### **LinkedIn OAuth Variables**
```bash
LINKEDIN_CLIENT_ID=your-linkedin-client-id
LINKEDIN_CLIENT_SECRET=your-linkedin-client-secret
LINKEDIN_REDIRECT_URI=https://yourdomain.com/extension/linkedin/callback
```

### **YouTube OAuth Variables**
```bash
YOUTUBE_CLIENT_JSON_PATH=/path/to/your/youtube-client.json
YOUTUBE_REDIRECT_URI=https://yourdomain.com/extension/youtube/callback
```

---

## 🔐 **Token Management**

### **Token Storage**
- OAuth tokens are stored in the `entity_extensions` table
- Access tokens, refresh tokens, and expiry times are encrypted
- Automatic token refresh when expired

### **Security Features**
- Tokens are encrypted using AES encryption
- Refresh tokens are used to get new access tokens
- Tokens are scoped to specific API permissions

---

## 📱 **Frontend Integration**

### **LinkedIn OAuth Flow**
```javascript
// 1. Get OAuth URL
const response = await fetch('/extension/linkedin/add', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${jwtToken}`,
    'Content-Type': 'application/json'
  }
});

const { auth_url } = await response.json();

// 2. Redirect user to LinkedIn
window.location.href = auth_url;

// 3. Handle callback (in your callback page)
const urlParams = new URLSearchParams(window.location.search);
const code = urlParams.get('code');
const state = urlParams.get('state');

// 4. Exchange code for tokens
const tokenResponse = await fetch(`/extension/linkedin/callback?code=${code}&state=${state}`);
const tokenData = await tokenResponse.json();
```

### **YouTube OAuth Flow**
```javascript
// 1. Get OAuth URL
const response = await fetch('/extension/youtube/auth', {
  headers: {
    'Authorization': `Bearer ${jwtToken}`
  }
});

const { auth_url } = await response.json();

// 2. Redirect user to Google
window.location.href = auth_url;

// 3. Handle callback
const urlParams = new URLSearchParams(window.location.search);
const code = urlParams.get('code');
const state = urlParams.get('state');

// 4. Exchange code for tokens
const tokenResponse = await fetch(`/extension/youtube/callback?code=${code}&state=${state}`);
const tokenData = await tokenResponse.json();
```

---

## 🚀 **Production Deployment**

### **1. Environment Setup**
```bash
# Copy production environment template
cp env.production .env

# Edit with your OAuth credentials
nano .env
```

### **2. OAuth Credentials**
- Ensure all OAuth credentials are properly set
- Use HTTPS redirect URIs in production
- Store client secrets securely

### **3. SSL/TLS Requirements**
- Both LinkedIn and YouTube require HTTPS in production
- Valid SSL certificate required
- Redirect URIs must match exactly

---

## 🔍 **Testing OAuth Integration**

### **Health Check**
```bash
curl -f http://localhost:8080/health
```

### **Test LinkedIn OAuth**
```bash
# Get OAuth URL
curl -X POST http://localhost:8080/extension/linkedin/add \
  -H "Authorization: Bearer <jwt_token>"
```

### **Test YouTube OAuth**
```bash
# Get OAuth URL
curl -X GET http://localhost:8080/extension/youtube/auth \
  -H "Authorization: Bearer <jwt_token>"
```

---

## 📊 **OAuth Status Endpoints**

### **Check Extension Status**
```bash
GET /extension/list-extensions
```

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "name": "LinkedIn",
      "status": "active",
      "type": "social"
    },
    {
      "id": 2,
      "name": "YouTube",
      "status": "active",
      "type": "video"
    }
  ]
}
```

---

## 🎯 **Summary**

**✅ LinkedIn OAuth Integration Complete**
- Full OAuth 2.0 flow implementation
- Profile data retrieval
- Post creation and scheduling
- Token management and refresh

**✅ YouTube OAuth Integration Complete**
- Google OAuth 2.0 implementation
- Video upload capabilities
- Channel data access
- Scheduled video management

**✅ Production Ready**
- Secure token storage
- Environment configuration
- Comprehensive error handling
- Frontend integration examples

**Both LinkedIn and YouTube OAuth integrations are now fully functional and ready for production use!** 🚀
