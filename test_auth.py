#!/usr/bin/env python3

import os
import sys
import asyncio
from datetime import datetime, timezone

# Set JWT secret
os.environ["JWT_SECRET_KEY"] = "hanur_super_secret_jwt_key_2024_make_it_long_and_secure"

# Add the project root to Python path
sys.path.append('.')

from services.jwt_service import verify_jwt_token, get_jwt_secret

def test_jwt_token():
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiNjhlYTIwMjUyMzVhYmQwMmI4ODJkODk5IiwiZW1haWwiOiJkZXZsZWFkQGRoYW51cmFpLmNvbSIsInB1cnBvc2UiOiJhY2Nlc3MiLCJleHAiOjE3NjA3ODk4OTcsImlhdCI6MTc2MDcwMzQ5N30.h9q2ZPEEoVEW1lpd0VkMartCVvp7iV1bxcYysfAvGw4"
    
    try:
        secret = get_jwt_secret()
        print(f"JWT Secret: {secret}")
        
        claims = verify_jwt_token(token, secret)
        print(f"JWT Claims: {claims}")
        
        if claims:
            print("✅ JWT token is valid!")
            print(f"User ID: {claims.get('user_id')}")
            print(f"Email: {claims.get('email')}")
        else:
            print("❌ JWT token is invalid!")
            
    except Exception as e:
        print(f"❌ Error verifying JWT: {e}")

if __name__ == "__main__":
    test_jwt_token()
