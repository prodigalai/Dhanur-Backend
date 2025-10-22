# 🚀 Content Crew API - Production Ready Backend

A comprehensive FastAPI backend for content management with LinkedIn and YouTube OAuth integration, built for production deployment.

---

## 🎯 **Features**

- **114 API Endpoints** - Complete content management system
- **Supabase PostgreSQL** - Production database with connection pooling
- **LinkedIn OAuth** - Full OAuth 2.0 integration for social media posting
- **YouTube OAuth** - Google OAuth 2.0 for video content management
- **JWT Authentication** - Secure user authentication system
- **API Key Management** - Service-to-service authentication
- **Role-Based Access Control** - Granular permissions system
- **Health Monitoring** - Database and application health checks
- **Production Ready** - Docker containerization and deployment scripts

---

## 📋 **Prerequisites**

- Python 3.8 or later
- Docker and Docker Compose (for production deployment)
- Supabase account (database)
- LinkedIn Developer account
- Google Cloud Console account (for YouTube API)

---

## ⚙️ **Quick Setup**

### **1. Clone and Setup**
```bash
# Navigate to project directory
cd content-crew

# Make setup script executable
chmod +x setup_database.sh

# Run setup script
./setup_database.sh
```

### **2. Environment Configuration**
The setup script will create a `.env` file from `env.production`. Update it with your credentials:

```bash
# Database Configuration (Already configured)
DATABASE_HOST=aws-1-ap-south-1.pooler.supabase.com
DATABASE_PORT=6543
DATABASE_NAME=postgres
DATABASE_USERNAME=postgres.xifakyfvevebelsziyjm
DATABASE_PASSWORD=ej&Mbs.H2FCUK6s.

# LinkedIn OAuth
LINKEDIN_CLIENT_ID=your_linkedin_client_id
LINKEDIN_CLIENT_SECRET=your_linkedin_client_secret
LINKEDIN_CALLBACK_URI=http://localhost:8000/oauth/linkedin/callback

# YouTube OAuth
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_REDIRECT_URL=http://localhost:8000/oauth/youtube/callback
```

### **3. Install Dependencies**
```bash
# Activate virtual environment
source venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

---

## 🚀 **Running the API**

### **Local Development**
```bash
# Start the API
python main.py

# Or with auto-reload (if you have watchdog installed)
uvicorn main:app --reload --host 0.0.0.0 --port 8080
```

### **Production with Docker**
```bash
# Build and start services
./deploy.sh

# Or manually with Docker Compose
docker-compose up -d
```

---

## 🔍 **Testing the API**

### **Health Checks**
```bash
# Application health
curl http://localhost:8080/health

# Database health
curl http://localhost:8080/health/db
```

### **OAuth Testing**
```bash
# LinkedIn OAuth
curl -X POST http://localhost:8080/extension/linkedin/add \
  -H "Authorization: Bearer <jwt_token>"

# YouTube OAuth
curl -X GET http://localhost:8080/extension/youtube/auth \
  -H "Authorization: Bearer <jwt_token>"
```

---

## 📊 **API Endpoints**

### **Total: 114 Endpoints**

- **Health & Database**: 2 endpoints
- **Authentication**: 13 endpoints
- **User Management**: 1 endpoint
- **Invitations**: 5 endpoints
- **Roles**: 5 endpoints
- **Brands**: 25 endpoints
- **Information Services**: 8 endpoints
- **Extensions**: 20 endpoints (LinkedIn + YouTube)
- **Payments**: 8 endpoints
- **Access Control**: 20 endpoints
- **API Keys**: 8 endpoints
- **Admin**: 3 endpoints

**Full API Documentation**: Available at `/docs` when running

---

## 🏗 **Project Structure**

```
content-crew/
├── api/                    # API routes and middleware
├── controllers/            # Business logic controllers
├── core/                   # Core services and utilities
├── models/                 # Database models
├── providers/              # OAuth providers (LinkedIn, YouTube)
├── repositories/           # Data access layer
├── routes/                 # API route definitions
├── services/               # Business services
├── static/                 # Static files
├── main.py                 # FastAPI application entry point
├── requirements.txt        # Python dependencies
├── Dockerfile              # Docker image definition
├── docker-compose.yml      # Multi-service deployment
├── deploy.sh               # Production deployment script
├── setup_database.sh       # Database setup script
└── env.production          # Environment configuration template
```

---

## 🔐 **Authentication**

### **JWT Tokens**
- **Algorithm**: HS256
- **Expiration**: 24 hours (configurable)
- **Header**: `Authorization: Bearer <token>`

### **API Keys**
- **Header**: `X-API-Key: <api_key>`
- **Rate Limiting**: 100 requests per minute (configurable)

---

## 🗄 **Database**

### **Supabase PostgreSQL**
- **Connection Pooling**: 10-30 connections
- **Health Monitoring**: Automatic connection testing
- **Migration Support**: SQL migration files included

### **Models**
- Users, Organizations, Projects
- Brand Memberships and Permissions
- OAuth Accounts and Tokens
- Scheduled Posts and Content
- API Keys and Access Control

---

## 🚀 **Production Deployment**

### **Docker Deployment**
```bash
# Deploy to production
./deploy.sh

# Check status
docker-compose ps

# View logs
docker-compose logs -f content-crew-api
```

### **Environment Variables**
- Copy `env.production` to `.env`
- Update production values (hosts, secrets, etc.)
- Set `FASTAPI_ENV=production`

---

## 📈 **Monitoring & Health**

### **Health Endpoints**
- `/health` - Application status
- `/health/db` - Database connection status

### **Logging**
- **Level**: Configurable (INFO/DEBUG)
- **Format**: Structured logging with timestamps
- **Output**: Console and file logging

---

## 🔧 **Configuration**

### **Server Settings**
- **Host**: 0.0.0.0 (all interfaces)
- **Port**: 8080 (configurable)
- **CORS**: Configurable origins
- **Rate Limiting**: Configurable per minute

### **Database Settings**
- **Connection Pool**: 10-30 connections
- **Timeout**: 60 seconds
- **SSL**: Required for Supabase

---

## 🆘 **Troubleshooting**

### **Common Issues**

1. **Database Connection Failed**
   - Check `.env` file configuration
   - Verify Supabase credentials
   - Test connection with `/health/db`

2. **OAuth Not Working**
   - Verify client IDs and secrets
   - Check redirect URIs match exactly
   - Ensure OAuth apps are configured

3. **Port Already in Use**
   - Change `PORT` in `.env`
   - Kill existing processes: `pkill -f python`

### **Logs**
```bash
# View application logs
docker-compose logs -f content-crew-api

# View database logs
docker-compose logs -f postgres
```

---

## 📚 **Documentation**

- **API Documentation**: `/docs` (Swagger UI)
- **Integration Summary**: `INTEGRATION_SUMMARY.md`
- **Production Guide**: `PRODUCTION_README.md`
- **API Endpoints**: `API_ENDPOINTS_SUMMARY.md`

---

## 🤝 **Support**

For issues and questions:
1. Check the troubleshooting section
2. Review logs and error messages
3. Verify configuration files
4. Test individual components

---

## 🎉 **Ready to Deploy!**

Your Content Crew API is now:
- ✅ **Fully Integrated** with all 114 endpoints
- ✅ **Database Connected** to Supabase
- ✅ **OAuth Ready** for LinkedIn and YouTube
- ✅ **Production Optimized** with Docker
- ✅ **Health Monitored** with status endpoints

**Start building amazing content management experiences!** 🚀
