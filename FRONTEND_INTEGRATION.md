# 🚀 Frontend Integration Guide - Content Crew API

## 📋 **Overview**

This guide provides everything you need to integrate your frontend application with the Content Crew API. The API is running on **http://localhost:8080** and provides 114 endpoints for complete content management.

---

## 🔐 **Authentication**

### **JWT Token Authentication**
```javascript
// Add to all API requests
const headers = {
  'Authorization': `Bearer ${jwtToken}`,
  'Content-Type': 'application/json'
};

// Example fetch
fetch('http://localhost:8080/api/users/profile', {
  headers: headers
});
```

### **API Key Authentication**
```javascript
// For service-to-service communication
const headers = {
  'X-API-Key': 'your-api-key-here',
  'Content-Type': 'application/json'
};
```

---

## 🌐 **Base Configuration**

### **API Base URL**
```javascript
const API_BASE_URL = 'http://localhost:8080';

// For production, change to your domain
// const API_BASE_URL = 'https://yourdomain.com';
```

### **CORS Configuration**
The API is configured to accept requests from any origin in development. For production, update the `ALLOWED_ORIGINS` in your backend configuration.

---

## 📱 **Core API Endpoints**

### **1. Health & Status**
```javascript
// Check API health
GET /health
Response: { "status": "healthy", "timestamp": "2025-08-26T10:28:58.415Z" }

// Check database health
GET /health/db
Response: { "status": "healthy", "database": "connected", "connection_info": {...} }
```

### **2. Authentication Endpoints**
```javascript
// User login
POST /auth/login
Body: { "email": "user@example.com", "password": "password123" }
Response: { "access_token": "jwt_token_here", "token_type": "bearer" }

// User registration
POST /auth/register
Body: { "email": "user@example.com", "password": "password123", "full_name": "John Doe" }

// Refresh token
POST /auth/refresh
Body: { "refresh_token": "refresh_token_here" }

// Logout
POST /auth/logout
Headers: Authorization: Bearer <jwt_token>

// Forgot password
POST /auth/forgot-password
Body: { "email": "user@example.com" }

// Reset password
POST /auth/reset-password
Body: { "token": "reset_token", "new_password": "newpassword123" }
```

### **3. User Management**
```javascript
// Get user profile
GET /users/profile
Headers: Authorization: Bearer <jwt_token>

// Update user profile
PUT /users/profile
Headers: Authorization: Bearer <jwt_token>
Body: { "full_name": "Updated Name", "email": "newemail@example.com" }

// Change password
PUT /users/change-password
Headers: Authorization: Bearer <jwt_token>
Body: { "current_password": "oldpass", "new_password": "newpass" }
```

---

## 🏢 **Organization & Brand Management**

### **Organizations**
```javascript
// Create organization
POST /organizations
Headers: Authorization: Bearer <jwt_token>
Body: { "name": "My Company", "description": "Company description" }

// List organizations
GET /organizations
Headers: Authorization: Bearer <jwt_token>

// Get organization details
GET /organizations/{org_id}
Headers: Authorization: Bearer <jwt_token>

// Update organization
PUT /organizations/{org_id}
Headers: Authorization: Bearer <jwt_token>
Body: { "name": "Updated Name", "description": "Updated description" }

// Delete organization
DELETE /organizations/{org_id}
Headers: Authorization: Bearer <jwt_token>
```

### **Brands**
```javascript
// Create brand
POST /brands
Headers: Authorization: Bearer <jwt_token>
Body: { "name": "Brand Name", "description": "Brand description", "organization_id": "org_id" }

// List brands
GET /brands
Headers: Authorization: Bearer <jwt_token>

// Get brand details
GET /brands/{brand_id}
Headers: Authorization: Bearer <jwt_token>

// Update brand
PUT /brands/{brand_id}
Headers: Authorization: Bearer <jwt_token>
Body: { "name": "Updated Brand", "description": "Updated description" }

// Delete brand
DELETE /brands/{brand_id}
Headers: Authorization: Bearer <jwt_token>
```

---

## 🔗 **Social Media Extensions**

### **LinkedIn Integration**
```javascript
// Get LinkedIn OAuth URL
POST /extension/linkedin/add
Headers: Authorization: Bearer <jwt_token>
Response: { "auth_url": "https://www.linkedin.com/oauth/v2/authorization?..." }

// LinkedIn OAuth callback (handled by backend)
GET /oauth/linkedin/callback?code={code}&state={state}

// List LinkedIn extensions
GET /extension/linkedin
Headers: Authorization: Bearer <jwt_token>

// Create LinkedIn post
POST /extension/linkedin/posts
Headers: Authorization: Bearer <jwt_token>
Body: { "content": "Post content", "brand_id": "brand_id" }

// Schedule LinkedIn post
POST /extension/linkedin/schedule
Headers: Authorization: Bearer <jwt_token>
Body: { "content": "Scheduled post", "scheduled_time": "2025-08-27T10:00:00Z", "brand_id": "brand_id" }
```

### **YouTube Integration**
```javascript
// Get YouTube OAuth URL
GET /extension/youtube/auth
Headers: Authorization: Bearer <jwt_token>
Response: { "auth_url": "https://accounts.google.com/o/oauth2/auth?..." }

// YouTube OAuth callback (handled by backend)
GET /oauth/youtube/callback?code={code}&state={state}

// List YouTube extensions
GET /extension/youtube
Headers: Authorization: Bearer <jwt_token>

// Upload YouTube video
POST /extension/youtube/upload
Headers: Authorization: Bearer <jwt_token>
Body: { "title": "Video Title", "description": "Video description", "file_path": "video.mp4" }

// Schedule YouTube video
POST /extension/youtube/schedule
Headers: Authorization: Bearer <jwt_token>
Body: { "title": "Scheduled video", "description": "Description", "scheduled_time": "2025-08-27T10:00:00Z" }
```

---

## 📅 **Scheduling & Content Management**

### **Scheduled Posts**
```javascript
// Create scheduled post
POST /scheduling/schedule
Headers: Authorization: Bearer <jwt_token>
Body: { "content": "Post content", "platform": "linkedin", "scheduled_time": "2025-08-27T10:00:00Z", "brand_id": "brand_id" }

// List scheduled posts
GET /scheduling/scheduled
Headers: Authorization: Bearer <jwt_token>

// Update scheduled post
PUT /scheduling/{schedule_id}
Headers: Authorization: Bearer <jwt_token>
Body: { "content": "Updated content", "scheduled_time": "2025-08-27T11:00:00Z" }

// Delete scheduled post
DELETE /scheduling/{schedule_id}
Headers: Authorization: Bearer <jwt_token>
```

---

## 🔑 **API Key Management**

### **API Keys**
```javascript
// Generate API key
POST /api-keys/generate
Headers: Authorization: Bearer <jwt_token>
Body: { "name": "Frontend App", "permissions": ["read", "write"] }

// List API keys
GET /api-keys
Headers: Authorization: Bearer <jwt_token>

// Revoke API key
DELETE /api-keys/{key_id}
Headers: Authorization: Bearer <jwt_token>
```

---

## 👥 **Team & Permissions**

### **Invitations**
```javascript
// Send invitation
POST /invitations/send
Headers: Authorization: Bearer <jwt_token>
Body: { "email": "invite@example.com", "role": "member", "organization_id": "org_id" }

// Accept invitation
POST /invitations/{invitation_id}/accept
Headers: Authorization: Bearer <jwt_token>

// Decline invitation
POST /invitations/{invitation_id}/decline
Headers: Authorization: Bearer <jwt_token>
```

### **Roles & Permissions**
```javascript
// Create role
POST /roles
Headers: Authorization: Bearer <jwt_token>
Body: { "name": "Content Manager", "permissions": ["read", "write", "schedule"] }

// List roles
GET /roles
Headers: Authorization: Bearer <jwt_token>

// Assign role to user
POST /roles/{role_id}/assign
Headers: Authorization: Bearer <jwt_token>
Body: { "user_id": "user_id", "organization_id": "org_id" }
```

---

## 💳 **Payment & Billing**

### **Subscriptions**
```javascript
// Create subscription
POST /payment/subscriptions
Headers: Authorization: Bearer <jwt_token>
Body: { "plan_id": "pro_plan", "payment_method": "card_token" }

// List subscriptions
GET /payment/subscriptions
Headers: Authorization: Bearer <jwt_token>

// Cancel subscription
DELETE /payment/subscriptions/{subscription_id}
Headers: Authorization: Bearer <jwt_token>
```

---

## 📊 **Analytics & Reporting**

### **Content Analytics**
```javascript
// Get content performance
GET /analytics/content/{content_id}
Headers: Authorization: Bearer <jwt_token>

// Get brand analytics
GET /analytics/brand/{brand_id}
Headers: Authorization: Bearer <jwt_token>
Query: ?start_date=2025-08-01&end_date=2025-08-26

// Get platform analytics
GET /analytics/platform/linkedin
Headers: Authorization: Bearer <jwt_token>
Query: ?period=monthly
```

---

## 🛠 **Frontend Implementation Examples**

### **React/Next.js Example**
```javascript
// api.js - API service layer
class ContentCrewAPI {
  constructor(baseURL = 'http://localhost:8080') {
    this.baseURL = baseURL;
  }

  // Set auth token
  setAuthToken(token) {
    this.authToken = token;
  }

  // Generic request method
  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    const headers = {
        'Content-Type': 'application/json',
      ...(this.authToken && { 'Authorization': `Bearer ${this.authToken}` }),
        ...options.headers
    };

    const response = await fetch(url, { ...options, headers });
    
    if (!response.ok) {
      throw new Error(`API Error: ${response.status}`);
    }
    
    return response.json();
  }

  // Authentication methods
  async login(email, password) {
    const response = await this.request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password })
    });
    
    this.setAuthToken(response.access_token);
    return response;
  }

  async logout() {
    await this.request('/auth/logout', { method: 'POST' });
    this.authToken = null;
  }

  // User methods
  async getProfile() {
    return this.request('/users/profile');
  }

  // Organization methods
  async createOrganization(name, description) {
    return this.request('/organizations', {
      method: 'POST',
      body: JSON.stringify({ name, description })
    });
  }

  async getOrganizations() {
    return this.request('/organizations');
  }

  // LinkedIn methods
  async getLinkedInAuthURL() {
    const response = await this.request('/extension/linkedin/add', {
      method: 'POST'
    });
    return response.data.auth_url;
  }

  // YouTube methods
  async getYouTubeAuthURL() {
    const response = await this.request('/extension/youtube/auth');
    return response.data.auth_url;
  }
}

// Usage
const api = new ContentCrewAPI();
export default api;
```

### **Vue.js Example**
```javascript
// composables/useContentCrew.js
import { ref } from 'vue';

export function useContentCrew() {
  const baseURL = 'http://localhost:8080';
  const authToken = ref(null);
  const user = ref(null);

  const setAuthToken = (token) => {
    authToken.value = token;
    localStorage.setItem('authToken', token);
  };

  const getAuthHeaders = () => ({
    'Content-Type': 'application/json',
    ...(authToken.value && { 'Authorization': `Bearer ${authToken.value}` })
  });

  const apiRequest = async (endpoint, options = {}) => {
    const url = `${baseURL}${endpoint}`;
    const response = await fetch(url, {
      ...options,
      headers: getAuthHeaders()
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.status}`);
    }

    return response.json();
  };

  const login = async (email, password) => {
    const response = await apiRequest('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password })
    });

    setAuthToken(response.access_token);
    return response;
  };

  const logout = async () => {
    await apiRequest('/auth/logout', { method: 'POST' });
    authToken.value = null;
    localStorage.removeItem('authToken');
  };

  const getProfile = async () => {
    const response = await apiRequest('/users/profile');
    user.value = response;
    return response;
  };

  return {
    authToken,
    user,
    login,
    logout,
    getProfile,
    apiRequest
  };
}
```

---

## 🔄 **OAuth Flow Implementation**

### **LinkedIn OAuth Flow**
```javascript
// 1. Get OAuth URL
const getLinkedInAuthURL = async () => {
  const response = await api.post('/extension/linkedin/add');
  const authURL = response.data.auth_url;
  
  // 2. Redirect user to LinkedIn
  window.location.href = authURL;
};

// 3. Handle callback (in your callback route)
const handleLinkedInCallback = async (code, state) => {
  try {
    // The backend handles the OAuth exchange
    // You can now use LinkedIn features
    const linkedinExtensions = await api.get('/extension/linkedin');
    console.log('LinkedIn connected:', linkedinExtensions);
  } catch (error) {
    console.error('LinkedIn connection failed:', error);
  }
};
```

### **YouTube OAuth Flow**
```javascript
// 1. Get OAuth URL
const getYouTubeAuthURL = async () => {
  const response = await api.get('/extension/youtube/auth');
  const authURL = response.data.auth_url;
  
  // 2. Redirect user to Google
  window.location.href = authURL;
};

// 3. Handle callback (in your callback route)
const handleYouTubeCallback = async (code, state) => {
  try {
    // The backend handles the OAuth exchange
    // You can now use YouTube features
    const youtubeExtensions = await api.get('/extension/youtube');
    console.log('YouTube connected:', youtubeExtensions);
  } catch (error) {
    console.error('YouTube connection failed:', error);
  }
};
```

---

## 📱 **Mobile App Integration**

### **React Native Example**
```javascript
// api.js for React Native
import AsyncStorage from '@react-native-async-storage/async-storage';

class ContentCrewMobileAPI {
  constructor(baseURL = 'http://localhost:8080') {
    this.baseURL = baseURL;
  }

  async getAuthToken() {
    return await AsyncStorage.getItem('authToken');
  }

  async setAuthToken(token) {
    await AsyncStorage.setItem('authToken', token);
  }

  async request(endpoint, options = {}) {
    const token = await this.getAuthToken();
    const url = `${this.baseURL}${endpoint}`;
    
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...(token && { 'Authorization': `Bearer ${token}` }),
        ...options.headers
      }
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.status}`);
    }

    return response.json();
  }

  // Same methods as web version
  async login(email, password) {
    const response = await this.request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password })
    });
    
    await this.setAuthToken(response.access_token);
    return response;
  }
}

export default new ContentCrewMobileAPI();
```

---

## 🚀 **Production Deployment**

### **Environment Configuration**
```javascript
// config.js
const config = {
  development: {
    apiBaseURL: 'http://localhost:8080',
    linkedinCallback: 'http://localhost:8000/oauth/linkedin/callback',
    youtubeCallback: 'http://localhost:8000/oauth/youtube/callback'
  },
  production: {
    apiBaseURL: 'https://yourdomain.com',
    linkedinCallback: 'https://yourdomain.com/oauth/linkedin/callback',
    youtubeCallback: 'https://yourdomain.com/oauth/youtube/callback'
  }
};

export default config[process.env.NODE_ENV || 'development'];
```

### **Error Handling**
```javascript
// utils/apiErrorHandler.js
export const handleAPIError = (error) => {
  if (error.status === 401) {
    // Unauthorized - redirect to login
    window.location.href = '/login';
  } else if (error.status === 403) {
    // Forbidden - show access denied
    showNotification('Access denied', 'error');
  } else if (error.status >= 500) {
    // Server error - show generic message
    showNotification('Server error. Please try again later.', 'error');
  } else {
    // Other errors - show specific message
    showNotification(error.message || 'An error occurred', 'error');
  }
};
```

---

## 📚 **Additional Resources**

- **API Documentation**: Available at `http://localhost:8080/docs` (Swagger UI)
- **Integration Summary**: `INTEGRATION_SUMMARY.md`
- **Production Guide**: `PRODUCTION_README.md`
- **API Endpoints**: `API_ENDPOINTS_SUMMARY.md`

---

## 🎯 **Next Steps**

1. **Test the API**: Use the health endpoints to verify connectivity
2. **Implement Authentication**: Start with login/register flows
3. **Add OAuth**: Integrate LinkedIn and YouTube authentication
4. **Build Core Features**: Organizations, brands, and content management
5. **Add Scheduling**: Implement post scheduling functionality
6. **Deploy**: Move to production with proper error handling

---

## 🆘 **Support & Troubleshooting**

### **Common Issues**
- **CORS Errors**: Ensure your frontend origin is in `ALLOWED_ORIGINS`
- **Authentication Failures**: Check JWT token expiration and format
- **OAuth Issues**: Verify redirect URIs match exactly
- **Database Errors**: Check `/health/db` endpoint for connection status

### **Testing Tools**
- **Postman**: Import the API endpoints for testing
- **cURL**: Use command line for quick API tests
- **Browser DevTools**: Monitor network requests and responses

---

**Your Content Crew API is ready for frontend integration! 🚀**
