# 🗄️ Database Table Creation Guide

## Overview

This guide explains how to create all the necessary database tables for Content Crew Prodigal using Supabase.

## 🚀 Quick Start

### Option 1: Manual SQL Execution (Recommended)

1. **Go to your Supabase Dashboard**
   - Navigate to [https://supabase.com/dashboard](https://supabase.com/dashboard)
   - Select your project: `xifakyfvevebelsziyjm`

2. **Open SQL Editor**
   - Click on "SQL Editor" in the left sidebar
   - Click "New Query"

3. **Copy and Paste the SQL Script**
   - Copy the entire content of `supabase_tables_complete.sql`
   - Paste it into the SQL Editor
   - Click "Run" to execute

4. **Verify Tables Created**
   - Go to "Table Editor" in the left sidebar
   - You should see all 15 tables listed

### Option 2: Python Script (Limited)

We've created Python scripts that attempt to create tables, but due to Supabase's architecture, they cannot execute DDL operations directly.

## 📋 Required Tables

The application needs these 15 tables:

| # | Table Name | Purpose |
|---|------------|---------|
| 1 | `users` | User accounts and profiles |
| 2 | `brands` | Brand/organization information |
| 3 | `brand_memberships` | User-brand relationships |
| 4 | `organizations` | Organization details |
| 5 | `organization_members` | User-organization relationships |
| 6 | `projects` | Project management |
| 7 | `scheduled_posts` | Social media post scheduling |
| 8 | `linkedin_connections` | LinkedIn OAuth connections |
| 9 | `youtube_connections` | YouTube OAuth connections |
| 10 | `oauth_accounts` | General OAuth account management |
| 11 | `user_credits` | User credit system |
| 12 | `api_keys` | API key management |
| 13 | `invitations` | User invitation system |
| 14 | `payments` | Payment tracking |
| 15 | `analytics` | Analytics and metrics |

## 🔧 Table Features

Each table includes:
- ✅ **Primary Keys** with auto-incrementing IDs
- ✅ **Foreign Keys** with proper referential integrity
- ✅ **Indexes** for optimal query performance
- ✅ **Timestamps** (created_at, updated_at)
- ✅ **Triggers** to automatically update timestamps
- ✅ **Constraints** for data validation
- ✅ **JSONB** fields for flexible metadata storage

## 📊 Sample Data

The SQL script automatically creates:
- Admin user account
- Sample brand and organization
- Sample project
- User credits for testing

## 🧪 Testing

After creating tables, run the test script:

```bash
python test_tables.py
```

This will verify that all tables exist and are accessible.

## 🚨 Troubleshooting

### Common Issues

1. **"Table not found" errors**
   - Ensure you ran the SQL script in Supabase dashboard
   - Check that the script executed without errors

2. **Permission errors**
   - Use the service role key for DDL operations
   - Ensure your user has proper permissions

3. **Connection issues**
   - Verify your Supabase credentials in `.env`
   - Check network connectivity

### Error Messages

- `PGRST205`: Table doesn't exist
- `PGRST202`: Function not found
- `FATAL: password authentication failed`: Check credentials

## 📁 File Structure

```
content-crew/
├── supabase_tables_complete.sql    # Complete SQL script
├── test_tables.py                  # Table verification script
├── create_tables_supabase.py       # Supabase client script (limited)
├── models/
│   ├── sqlalchemy_models.py        # SQLAlchemy models (for reference)
│   └── simple_models.py            # Simplified models
└── TABLE_CREATION_GUIDE.md         # This guide
```

## 🔄 Next Steps

After creating tables:

1. **Test the backend**:
   ```bash
   python test_tables.py
   ```

2. **Start the application**:
   ```bash
   PORT=8000 python main.py
   ```

3. **Test API endpoints**:
   ```bash
   curl http://localhost:8000/health
   curl http://localhost:8000/auth/login
   ```

## 📚 Additional Resources

- [Supabase Documentation](https://supabase.com/docs)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)

## 🆘 Support

If you encounter issues:

1. Check the error messages in Supabase dashboard
2. Verify your environment variables
3. Test the connection with `python create_tables_supabase.py`
4. Review the troubleshooting section above

---

**Note**: The Python scripts cannot create tables directly due to Supabase's security model. Always use the SQL script in the Supabase dashboard for table creation.
