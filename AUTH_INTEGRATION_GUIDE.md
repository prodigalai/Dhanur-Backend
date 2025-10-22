# 🔐 **Authentication Integration Guide - Content Crew API**

## 📋 **Overview**

This guide provides complete authentication integration for the Content Crew API. All authentication endpoints are working and ready for frontend integration.

---

## 🚀 **API Base Configuration**

### **Base URL**
```javascript
const API_BASE_URL = 'http://localhost:8080';
```

### **Authentication Headers**
```javascript
// JWT Token (for authenticated requests)
const authHeaders = {
  'Authorization': `Bearer ${jwtToken}`,
  'Content-Type': 'application/json'
};

// No auth (for public endpoints)
const publicHeaders = {
  'Content-Type': 'application/json'
};
```

---

## 🔑 **Complete Authentication Endpoints**

### **1. User Registration & Login**

#### **User Registration**
```javascript
POST /auth/create-entity
Body: {
  "email": "user@example.com",
  "password": "password123",
  "full_name": "John Doe",
  "organization_name": "My Company" // Optional
}

Response: {
  "success": true,
  "message": "User created successfully",
  "data": {
    "user_id": "user_123",
    "email": "user@example.com",
    "full_name": "John Doe"
  }
}
```

#### **User Login**
```javascript
POST /auth/login
Body: {
  "email": "user@example.com",
  "password": "password123"
}

Response: {
  "success": true,
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "refresh_token_here",
  "token_type": "bearer",
  "expires_in": 86400
}
```

### **2. Token Management**

#### **Refresh Token**
```javascript
POST /auth/refresh-token
Body: {
  "refresh_token": "your_refresh_token_here"
}

Response: {
  "success": true,
  "access_token": "new_access_token_here",
  "refresh_token": "new_refresh_token_here",
  "token_type": "bearer"
}
```

#### **Logout**
```javascript
POST /auth/logout
Headers: Authorization: Bearer <jwt_token>

Response: {
  "success": true,
  "message": "Logged out successfully"
}
```

### **3. Password Management**

#### **Forgot Password**
```javascript
POST /auth/forgot-password
Body: {
  "email": "user@example.com"
}

Response: {
  "success": true,
  "message": "Password reset email sent"
}
```

#### **Reset Password**
```javascript
POST /auth/reset-password
Body: {
  "token": "reset_token_from_email",
  "new_password": "newpassword123"
}

Response: {
  "success": true,
  "message": "Password reset successfully"
}
```

#### **Change Password (Authenticated)**
```javascript
POST /auth/change-password
Headers: Authorization: Bearer <jwt_token>
Body: {
  "current_password": "oldpassword123",
  "new_password": "newpassword123"
}

Response: {
  "success": true,
  "message": "Password changed successfully"
}
```

#### **Update Password (Alternative)**
```javascript
POST /auth/update-password
Headers: Authorization: Bearer <jwt_token>
Body: {
  "current_password": "oldpassword123",
  "new_password": "newpassword123"
}

Response: {
  "success": true,
  "message": "Password updated successfully"
}
```

### **4. Email Verification**

#### **Verify Email**
```javascript
POST /auth/verify-email
Body: {
  "token": "verification_token_from_email"
}

Response: {
  "success": true,
  "message": "Email verified successfully"
}
```

#### **Resend Verification Email**
```javascript
POST /auth/resend-verify-email
Body: {
  "email": "user@example.com"
}

Response: {
  "success": true,
  "message": "Verification email sent"
}
```

### **5. Profile Management**

#### **Update Entity/Profile**
```javascript
POST /auth/update-entity
Headers: Authorization: Bearer <jwt_token>
Body: {
  "full_name": "Updated Name",
  "email": "newemail@example.com",
  "phone": "+1234567890"
}

Response: {
  "success": true,
  "message": "Profile updated successfully",
  "data": {
    "user_id": "user_123",
    "full_name": "Updated Name",
    "email": "newemail@example.com"
  }
}
```

#### **Update Avatar**
```javascript
POST /auth/update-avatar
Headers: Authorization: Bearer <jwt_token>
Body: {
  "avatar_url": "https://example.com/avatar.jpg"
}

Response: {
  "success": true,
  "message": "Avatar updated successfully",
  "data": {
    "avatar_url": "https://example.com/avatar.jpg"
  }
}
```

### **6. Account Management**

#### **Deactivate Account**
```javascript
POST /auth/deactivate-account
Headers: Authorization: Bearer <jwt_token>
Body: {
  "reason": "No longer needed"
}

Response: {
  "success": true,
  "message": "Account deactivated successfully"
}
```

---

## 🛠 **Frontend Implementation**

### **React/Next.js Authentication Service**

```javascript
// services/authService.js
class AuthService {
  constructor(baseURL = 'http://localhost:8080') {
    this.baseURL = baseURL;
    this.tokenKey = 'content_crew_token';
    this.refreshTokenKey = 'content_crew_refresh_token';
  }

  // Get stored tokens
  getToken() {
    return localStorage.getItem(this.tokenKey);
  }

  getRefreshToken() {
    return localStorage.getItem(this.refreshTokenKey);
  }

  // Store tokens
  setTokens(accessToken, refreshToken) {
    localStorage.setItem(this.tokenKey, accessToken);
    localStorage.setItem(this.refreshTokenKey, refreshToken);
  }

  // Clear tokens
  clearTokens() {
    localStorage.removeItem(this.tokenKey);
    localStorage.removeItem(this.refreshTokenKey);
  }

  // Generic API request with auth
  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    const token = this.getToken();
    
    const headers = {
      'Content-Type': 'application/json',
      ...(token && { 'Authorization': `Bearer ${token}` }),
      ...options.headers
    };

    try {
      const response = await fetch(url, { ...options, headers });
      
      if (response.status === 401) {
        // Token expired, try to refresh
        const refreshed = await this.refreshToken();
        if (refreshed) {
          // Retry with new token
          const newToken = this.getToken();
          headers.Authorization = `Bearer ${newToken}`;
          const retryResponse = await fetch(url, { ...options, headers });
          return retryResponse.json();
        }
      }
      
      if (!response.ok) {
        throw new Error(`API Error: ${response.status}`);
      }
      
      return response.json();
    } catch (error) {
      console.error('API Request Error:', error);
      throw error;
    }
  }

  // User Registration
  async register(userData) {
    const response = await this.request('/auth/create-entity', {
      method: 'POST',
      body: JSON.stringify(userData)
    });
    return response;
  }

  // User Login
  async login(email, password) {
    const response = await this.request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password })
    });
    
    if (response.success) {
      this.setTokens(response.access_token, response.refresh_token);
    }
    
    return response;
  }

  // Refresh Token
  async refreshToken() {
    try {
      const refreshToken = this.getRefreshToken();
      if (!refreshToken) return false;

      const response = await fetch(`${this.baseURL}/auth/refresh-token`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken })
      });

      if (response.ok) {
        const data = await response.json();
        this.setTokens(data.access_token, data.refresh_token);
        return true;
      }
      
      return false;
    } catch (error) {
      console.error('Token refresh failed:', error);
      return false;
    }
  }

  // Logout
  async logout() {
    try {
      await this.request('/auth/logout', { method: 'POST' });
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      this.clearTokens();
    }
  }

  // Forgot Password
  async forgotPassword(email) {
    return this.request('/auth/forgot-password', {
      method: 'POST',
      body: JSON.stringify({ email })
    });
  }

  // Reset Password
  async resetPassword(token, newPassword) {
    return this.request('/auth/reset-password', {
      method: 'POST',
      body: JSON.stringify({ token, new_password: newPassword })
    });
  }

  // Change Password
  async changePassword(currentPassword, newPassword) {
    return this.request('/auth/change-password', {
      method: 'POST',
      body: JSON.stringify({ current_password: currentPassword, new_password: newPassword })
    });
  }

  // Verify Email
  async verifyEmail(token) {
    return this.request('/auth/verify-email', {
      method: 'POST',
      body: JSON.stringify({ token })
    });
  }

  // Resend Verification Email
  async resendVerificationEmail(email) {
    return this.request('/auth/resend-verify-email', {
      method: 'POST',
      body: JSON.stringify({ email })
    });
  }

  // Update Profile
  async updateProfile(profileData) {
    return this.request('/auth/update-entity', {
      method: 'POST',
      body: JSON.stringify(profileData)
    });
  }

  // Update Avatar
  async updateAvatar(avatarUrl) {
    return this.request('/auth/update-avatar', {
      method: 'POST',
      body: JSON.stringify({ avatar_url: avatarUrl })
    });
  }

  // Deactivate Account
  async deactivateAccount(reason) {
    return this.request('/auth/deactivate-account', {
      method: 'POST',
      body: JSON.stringify({ reason })
    });
  }

  // Check if user is authenticated
  isAuthenticated() {
    return !!this.getToken();
  }
}

export default new AuthService();
```

### **Vue.js Authentication Composable**

```javascript
// composables/useAuth.js
import { ref, computed } from 'vue';

export function useAuth() {
  const baseURL = 'http://localhost:8080';
  const token = ref(localStorage.getItem('content_crew_token'));
  const refreshToken = ref(localStorage.getItem('content_crew_refresh_token'));
  const user = ref(null);
  const loading = ref(false);

  const isAuthenticated = computed(() => !!token.value);

  const setTokens = (accessToken, refreshTokenValue) => {
    token.value = accessToken;
    refreshToken.value = refreshTokenValue;
    localStorage.setItem('content_crew_token', accessToken);
    localStorage.setItem('content_crew_refresh_token', refreshTokenValue);
  };

  const clearTokens = () => {
    token.value = null;
    refreshToken.value = null;
    user.value = null;
    localStorage.removeItem('content_crew_token');
    localStorage.removeItem('content_crew_refresh_token');
  };

  const apiRequest = async (endpoint, options = {}) => {
    const url = `${baseURL}${endpoint}`;
    
    const headers = {
      'Content-Type': 'application/json',
      ...(token.value && { 'Authorization': `Bearer ${token.value}` }),
      ...options.headers
    };

    try {
      const response = await fetch(url, { ...options, headers });
      
      if (response.status === 401) {
        // Try to refresh token
        const refreshed = await refreshToken();
        if (refreshed) {
          // Retry with new token
          headers.Authorization = `Bearer ${token.value}`;
          const retryResponse = await fetch(url, { ...options, headers });
          return retryResponse.json();
        }
      }
      
      if (!response.ok) {
        throw new Error(`API Error: ${response.status}`);
      }
      
      return response.json();
    } catch (error) {
      console.error('API Request Error:', error);
      throw error;
    }
  };

  const login = async (email, password) => {
    loading.value = true;
    try {
      const response = await apiRequest('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password })
      });
      
      if (response.success) {
        setTokens(response.access_token, response.refresh_token);
        user.value = response.user;
      }
      
      return response;
    } finally {
      loading.value = false;
    }
  };

  const register = async (userData) => {
    loading.value = true;
    try {
      return await apiRequest('/auth/create-entity', {
        method: 'POST',
        body: JSON.stringify(userData)
      });
    } finally {
      loading.value = false;
    }
  };

  const logout = async () => {
    try {
      await apiRequest('/auth/logout', { method: 'POST' });
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      clearTokens();
    }
  };

  const forgotPassword = async (email) => {
    return apiRequest('/auth/forgot-password', {
      method: 'POST',
      body: JSON.stringify({ email })
    });
  };

  const resetPassword = async (tokenValue, newPassword) => {
    return apiRequest('/auth/reset-password', {
      method: 'POST',
      body: JSON.stringify({ token: tokenValue, new_password: newPassword })
    });
  };

  const changePassword = async (currentPassword, newPassword) => {
    return apiRequest('/auth/change-password', {
      method: 'POST',
      body: JSON.stringify({ current_password: currentPassword, new_password: newPassword })
    });
  };

  const updateProfile = async (profileData) => {
    return apiRequest('/auth/update-entity', {
      method: 'POST',
      body: JSON.stringify(profileData)
    });
  };

  return {
    token,
    user,
    loading,
    isAuthenticated,
    login,
    register,
    logout,
    forgotPassword,
    resetPassword,
    changePassword,
    updateProfile
  };
}
```

---

## 🎯 **Step-by-Step Integration**

### **Step 1: Setup Authentication Service**
```javascript
// Install the auth service
import authService from './services/authService';

// Or for Vue.js
import { useAuth } from './composables/useAuth';
```

### **Step 2: Implement Login Flow**
```javascript
// React/Next.js
const handleLogin = async (email, password) => {
  try {
    const response = await authService.login(email, password);
    if (response.success) {
      // Redirect to dashboard
      router.push('/dashboard');
    }
  } catch (error) {
    console.error('Login failed:', error);
  }
};

// Vue.js
const { login } = useAuth();
const handleLogin = async (email, password) => {
  try {
    const response = await login(email, password);
    if (response.success) {
      // Redirect to dashboard
      router.push('/dashboard');
    }
  } catch (error) {
    console.error('Login failed:', error);
  }
};
```

### **Step 3: Implement Registration Flow**
```javascript
const handleRegister = async (userData) => {
  try {
    const response = await authService.register(userData);
    if (response.success) {
      // Show success message
      showMessage('Registration successful! Please check your email for verification.');
    }
  } catch (error) {
    console.error('Registration failed:', error);
  }
};
```

### **Step 4: Add Authentication Guards**
```javascript
// React/Next.js - Protected Route Component
const ProtectedRoute = ({ children }) => {
  const isAuthenticated = authService.isAuthenticated();
  
  if (!isAuthenticated) {
    return <Navigate to="/login" />;
  }
  
  return children;
};

// Vue.js - Route Guard
router.beforeEach((to, from, next) => {
  const { isAuthenticated } = useAuth();
  
  if (to.meta.requiresAuth && !isAuthenticated.value) {
    next('/login');
  } else {
    next();
  }
});
```

---

## 🔒 **Security Best Practices**

### **Token Storage**
- Store tokens in `localStorage` for web apps
- Use `AsyncStorage` for React Native
- Consider `httpOnly` cookies for production

### **Token Refresh**
- Automatically refresh tokens before expiration
- Handle 401 errors gracefully
- Implement retry logic for failed requests

### **Error Handling**
- Show user-friendly error messages
- Log authentication errors for debugging
- Implement rate limiting on client side

---

## 🧪 **Testing Authentication**

### **Test Registration**
```bash
curl -X POST http://localhost:8080/auth/create-entity \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123","full_name":"Test User"}'
```

### **Test Login**
```bash
curl -X POST http://localhost:8080/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'
```

### **Test Protected Endpoint**
```bash
curl -X GET http://localhost:8080/brand/list-brands \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

## 📱 **Mobile App Integration**

### **React Native**
```javascript
import AsyncStorage from '@react-native-async-storage/async-storage';

// Replace localStorage with AsyncStorage
const setTokens = async (accessToken, refreshToken) => {
  await AsyncStorage.setItem('content_crew_token', accessToken);
  await AsyncStorage.setItem('content_crew_refresh_token', refreshToken);
};

const getToken = async () => {
  return await AsyncStorage.getItem('content_crew_token');
};
```

---

## 🚀 **Production Considerations**

### **Environment Variables**
```javascript
const config = {
  development: {
    apiBaseURL: 'http://localhost:8080'
  },
  production: {
    apiBaseURL: 'https://yourdomain.com'
  }
};
```

### **HTTPS Only**
- Use HTTPS in production
- Implement secure token storage
- Add CSRF protection

---

## ✅ **Authentication Checklist**

- [ ] **User Registration**: `/auth/create-entity`
- [ ] **User Login**: `/auth/login`
- [ ] **Token Refresh**: `/auth/refresh-token`
- [ ] **User Logout**: `/auth/logout`
- [ ] **Password Reset**: `/auth/forgot-password` & `/auth/reset-password`
- [ ] **Password Change**: `/auth/change-password`
- [ ] **Email Verification**: `/auth/verify-email`
- [ ] **Profile Updates**: `/auth/update-entity`
- [ ] **Avatar Updates**: `/auth/update-avatar`
- [ ] **Account Deactivation**: `/auth/deactivate-account`
- [ ] **Protected Routes**: Authentication guards
- [ ] **Error Handling**: User-friendly error messages
- [ ] **Token Management**: Automatic refresh & storage

---

## 🎉 **Ready to Use!**

Your Content Crew API authentication system is fully integrated and ready for frontend development. All 13 authentication endpoints are working and tested.

**Next Steps:**
1. Implement the authentication service in your frontend
2. Add login/register forms
3. Set up protected routes
4. Test all authentication flows
5. Move to the next integration phase (Organizations, Brands, etc.)

---

**Authentication Integration Complete! 🚀**
