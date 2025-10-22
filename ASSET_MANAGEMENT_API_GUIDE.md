# 🚀 Asset Management API Guide

## 📋 **Complete Asset Management System for Content Crew Prodigal**

**Total APIs**: **15 endpoints**  
**Database**: **MongoDB**  
**File Storage**: **S3 (DigitalOcean Spaces)**  
**Authentication**: **JWT Bearer Token**

---

## 🎯 **API Categories**

### **1. Campaign Asset Management (7 APIs)**
- Upload multiple assets to campaign
- Get campaign assets with filtering
- Get single asset details
- Update asset metadata
- Delete asset
- Download asset
- Get asset preview URL

### **2. Brand Guidelines Management (3 APIs)**
- Upload brand guideline
- Get brand guidelines with filtering
- Download brand guideline

### **3. Analytics & Statistics (1 API)**
- Get asset statistics for campaign

### **4. Search & Filter (2 APIs)**
- Advanced asset search
- Get available filters

---

## 📁 **1. Campaign Asset Management APIs**

### **1.1 Upload Campaign Assets**
```http
POST /api/brands/{brand_id}/campaigns/{campaign_id}/assets/upload
```

**Headers:**
```
Authorization: Bearer {jwt_token}
Content-Type: multipart/form-data
```

**Request Body (FormData):**
```javascript
{
  files: File[], // Multiple files
  category: 'brand' | 'content' | 'marketing' | 'technical' | 'legal' | 'other',
  description: string, // Optional
  tags: string, // JSON array as string: '["tag1", "tag2"]'
  is_public: boolean // Default: true
}
```

**Response:**
```json
{
  "success": true,
  "message": "Successfully uploaded 2 assets",
  "data": {
    "assets": [
      {
        "id": "asset-uuid-123",
        "name": "brand-logo.png",
        "type": "image",
        "url": "https://api.dhanur-ai.com/assets/asset-uuid-123.png",
        "size": "2.4 MB",
        "sizeBytes": 2516582,
        "category": "brand",
        "description": "Main brand logo",
        "tags": ["logo", "brand", "primary"],
        "isPublic": true,
        "uploadedBy": "user-id",
        "uploadedAt": "2025-10-21T10:30:00Z",
        "downloadCount": 0,
        "metadata": {
          "content_type": "image/png",
          "file_extension": ".png",
          "original_name": "brand-logo.png"
        }
      }
    ]
  }
}
```

### **1.2 Get Campaign Assets**
```http
GET /api/brands/{brand_id}/campaigns/{campaign_id}/assets
```

**Query Parameters:**
```
?category=brand&type=image&search=logo&page=1&limit=20&sort_by=name&sort_order=asc
```

**Response:**
```json
{
  "success": true,
  "data": {
    "assets": [...],
    "pagination": {
      "page": 1,
      "limit": 20,
      "total": 50,
      "totalPages": 3
    },
    "filters": {
      "categories": ["brand", "content", "marketing"],
      "types": ["image", "video", "document"]
    }
  }
}
```

### **1.3 Get Single Asset**
```http
GET /api/brands/{brand_id}/campaigns/{campaign_id}/assets/{asset_id}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "asset-uuid-123",
    "name": "brand-logo.png",
    "type": "image",
    "url": "https://api.dhanur-ai.com/assets/asset-uuid-123.png",
    "size": "2.4 MB",
    "sizeBytes": 2516582,
    "category": "brand",
    "description": "Main brand logo",
    "tags": ["logo", "brand", "primary"],
    "isPublic": true,
    "uploadedBy": "user-id",
    "uploadedAt": "2025-10-21T10:30:00Z",
    "downloadCount": 5,
    "lastAccessed": "2025-10-21T15:30:00Z",
    "metadata": {...}
  }
}
```

### **1.4 Update Asset**
```http
PUT /api/brands/{brand_id}/campaigns/{campaign_id}/assets/{asset_id}
```

**Request Body:**
```json
{
  "name": "Updated Asset Name",
  "description": "Updated description",
  "category": "marketing",
  "tags": ["updated", "tag"],
  "is_public": false
}
```

**Response:**
```json
{
  "success": true,
  "message": "Asset updated successfully"
}
```

### **1.5 Delete Asset**
```http
DELETE /api/brands/{brand_id}/campaigns/{campaign_id}/assets/{asset_id}
```

**Response:**
```json
{
  "success": true,
  "message": "Asset deleted successfully"
}
```

### **1.6 Download Asset**
```http
GET /api/brands/{brand_id}/campaigns/{campaign_id}/assets/{asset_id}/download
```

**Response:**
```json
{
  "success": true,
  "download_url": "https://api.dhanur-ai.com/assets/asset-uuid-123.png",
  "filename": "brand-logo.png"
}
```

### **1.7 Get Asset Preview URL**
```http
GET /api/brands/{brand_id}/campaigns/{campaign_id}/assets/{asset_id}/preview
```

**Response:**
```json
{
  "success": true,
  "preview_url": "https://api.dhanur-ai.com/assets/asset-uuid-123.png",
  "filename": "brand-logo.png",
  "content_type": "image/png"
}
```

---

## 📚 **2. Brand Guidelines Management APIs**

### **2.1 Upload Brand Guideline**
```http
POST /api/brands/{brand_id}/guidelines/upload
```

**Headers:**
```
Authorization: Bearer {jwt_token}
Content-Type: multipart/form-data
```

**Request Body (FormData):**
```javascript
{
  file: File,
  title: string,
  version: string,
  category: 'complete' | 'logo' | 'typography' | 'colors' | 'imagery' | 'voice' | 'layout',
  description: string, // Optional
  tags: string, // JSON array as string
  is_active: boolean // Default: true
}
```

**Response:**
```json
{
  "success": true,
  "message": "Brand guideline uploaded successfully",
  "data": {
    "id": "guideline-uuid-123",
    "title": "Brand Guidelines v2.0",
    "version": "2.0",
    "category": "complete",
    "url": "https://api.dhanur-ai.com/guidelines/guideline-uuid-123.pdf",
    "size": "5.2 MB",
    "isActive": true
  }
}
```

### **2.2 Get Brand Guidelines**
```http
GET /api/brands/{brand_id}/guidelines
```

**Query Parameters:**
```
?category=logo&is_active=true&search=typography&page=1&limit=20
```

**Response:**
```json
{
  "success": true,
  "data": {
    "guidelines": [
      {
        "id": "guideline-uuid-123",
        "title": "Brand Guidelines v2.0",
        "version": "2.0",
        "category": "complete",
        "description": "Complete brand guidelines",
        "url": "https://api.dhanur-ai.com/guidelines/guideline-uuid-123.pdf",
        "size": "5.2 MB",
        "sizeBytes": 5452595,
        "isActive": true,
        "tags": ["brand", "guidelines", "complete"],
        "uploadedBy": "user-id",
        "uploadedAt": "2025-10-21T10:30:00Z",
        "downloadCount": 12,
        "lastAccessed": "2025-10-21T15:30:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "limit": 20,
      "total": 5,
      "totalPages": 1
    }
  }
}
```

### **2.3 Download Brand Guideline**
```http
GET /api/brands/{brand_id}/guidelines/{guideline_id}/download
```

**Response:**
```json
{
  "success": true,
  "download_url": "https://api.dhanur-ai.com/guidelines/guideline-uuid-123.pdf",
  "filename": "Brand_Guidelines_v2.0"
}
```

---

## 📊 **3. Analytics & Statistics APIs**

### **3.1 Get Asset Statistics**
```http
GET /api/brands/{brand_id}/campaigns/{campaign_id}/assets/stats
```

**Response:**
```json
{
  "success": true,
  "data": {
    "totalAssets": 25,
    "totalSize": "150.5 MB",
    "totalSizeBytes": 157286400,
    "byCategory": {
      "brand": 5,
      "content": 10,
      "marketing": 8,
      "technical": 2
    },
    "byType": {
      "image": 15,
      "video": 5,
      "document": 3,
      "audio": 2
    },
    "downloadStats": {
      "totalDownloads": 150,
      "mostDownloaded": "asset-uuid-123"
    },
    "recentActivity": [
      {
        "assetId": "asset-uuid-123",
        "action": "download",
        "user": "user-id",
        "timestamp": "2025-10-21T10:30:00Z"
      }
    ]
  }
}
```

---

## 🔍 **4. Search & Filter APIs**

### **4.1 Advanced Asset Search**
```http
POST /api/brands/{brand_id}/campaigns/{campaign_id}/assets/search
```

**Request Body:**
```json
{
  "query": "logo",
  "category": "brand",
  "type": "image",
  "tags": ["primary", "official"],
  "is_public": true,
  "page": 1,
  "limit": 20,
  "sort_by": "name",
  "sort_order": "asc"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "assets": [...],
    "pagination": {
      "page": 1,
      "limit": 20,
      "total": 5,
      "totalPages": 1
    },
    "query": {
      "search": "logo",
      "category": "brand",
      "type": "image",
      "tags": ["primary", "official"],
      "isPublic": true
    }
  }
}
```

### **4.2 Get Asset Filters**
```http
GET /api/brands/{brand_id}/campaigns/{campaign_id}/assets/filters
```

**Response:**
```json
{
  "success": true,
  "data": {
    "categories": ["brand", "content", "marketing", "technical", "legal", "other"],
    "types": ["image", "video", "document", "audio"],
    "tags": [
      {"tag": "logo", "count": 5},
      {"tag": "banner", "count": 3},
      {"tag": "social", "count": 8}
    ]
  }
}
```

---

## 🗄️ **Database Schema (MongoDB Collections)**

### **1. Campaign Assets Collection:**
```javascript
{
  _id: ObjectId,
  asset_id: String, // UUID
  campaign_id: String, // Reference to campaigns
  brand_id: String, // Reference to brands
  name: String,
  original_name: String,
  type: String, // image, video, document, audio
  url: String, // S3 URL
  size_bytes: Number,
  size_display: String,
  category: String, // brand, content, marketing, technical, legal, other
  description: String,
  tags: [String],
  is_public: Boolean,
  uploaded_by: String, // user_id
  uploaded_at: Date,
  download_count: Number,
  last_accessed: Date,
  metadata: {
    content_type: String,
    file_extension: String,
    original_name: String
  },
  created_at: Date,
  updated_at: Date
}
```

### **2. Brand Guidelines Collection:**
```javascript
{
  _id: ObjectId,
  guideline_id: String, // UUID
  brand_id: String, // Reference to brands
  title: String,
  version: String,
  category: String, // complete, logo, typography, colors, imagery, voice, layout
  description: String,
  file_url: String, // S3 URL
  file_type: String,
  file_size: String,
  file_size_bytes: Number,
  uploaded_by: String, // user_id
  uploaded_at: Date,
  is_active: Boolean,
  tags: [String],
  download_count: Number,
  last_accessed: Date,
  created_at: Date,
  updated_at: Date
}
```

### **3. Asset Activity Log Collection:**
```javascript
{
  _id: ObjectId,
  asset_id: String, // Reference to campaign_assets
  user_id: String,
  action: String, // upload, view, edit, delete, download, preview
  metadata: {
    ip_address: String,
    user_agent: String,
    referrer: String
  },
  created_at: Date
}
```

---

## 🔐 **Authentication & Permissions**

### **Required Headers:**
```
Authorization: Bearer {jwt_token}
```

### **Permission Levels:**
- **Owner**: Full access to all assets
- **Admin**: Full access to all assets
- **Editor**: Upload, edit, delete assets
- **Uploader**: Upload assets only
- **Viewer**: View and download assets only

### **Access Control:**
- Users must be team members of the brand
- Campaign must exist and belong to the brand
- Asset operations are scoped to specific campaigns

---

## 🚀 **Frontend Integration Examples**

### **1. Upload Assets:**
```typescript
const uploadAssets = async (files: File[], campaignId: string, brandId: string) => {
  const formData = new FormData();
  
  files.forEach(file => {
    formData.append('files', file);
  });
  
  formData.append('category', 'brand');
  formData.append('description', 'Brand assets');
  formData.append('tags', JSON.stringify(['logo', 'brand']));
  formData.append('is_public', 'true');
  
  const response = await fetch(`/api/brands/${brandId}/campaigns/${campaignId}/assets/upload`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`
    },
    body: formData
  });
  
  return response.json();
};
```

### **2. Get Assets with Filters:**
```typescript
const getAssets = async (brandId: string, campaignId: string, filters: any) => {
  const params = new URLSearchParams();
  
  if (filters.category) params.append('category', filters.category);
  if (filters.type) params.append('type', filters.type);
  if (filters.search) params.append('search', filters.search);
  if (filters.page) params.append('page', filters.page.toString());
  if (filters.limit) params.append('limit', filters.limit.toString());
  
  const response = await fetch(`/api/brands/${brandId}/campaigns/${campaignId}/assets?${params}`);
  return response.json();
};
```

### **3. Download Asset:**
```typescript
const downloadAsset = async (brandId: string, campaignId: string, assetId: string) => {
  const response = await fetch(`/api/brands/${brandId}/campaigns/${campaignId}/assets/${assetId}/download`, {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  
  const data = await response.json();
  
  if (data.success) {
    // Create download link
    const link = document.createElement('a');
    link.href = data.download_url;
    link.download = data.filename;
    link.click();
  }
};
```

---

## 📋 **Implementation Status**

### **✅ Completed (Phase 1):**
- [x] Upload Campaign Assets API
- [x] Get Campaign Assets API
- [x] Get Single Asset API
- [x] Update Asset API
- [x] Delete Asset API
- [x] Download Asset API
- [x] Get Asset Preview API
- [x] Upload Brand Guideline API
- [x] Get Brand Guidelines API
- [x] Download Brand Guideline API
- [x] Get Asset Statistics API
- [x] Advanced Asset Search API
- [x] Get Asset Filters API

### **🔄 Next Phase (Phase 2):**
- [ ] Asset Activity Logging
- [ ] Permission Management APIs
- [ ] File Processing APIs (Thumbnails)
- [ ] Advanced Analytics APIs

---

## 🎯 **Total APIs: 15 Endpoints**

**Campaign Assets**: 7 APIs  
**Brand Guidelines**: 3 APIs  
**Analytics**: 1 API  
**Search & Filter**: 2 APIs  
**File Management**: 2 APIs (Future)

यह सभी APIs MongoDB के साथ implement हो गई हैं! 🚀
