#!/usr/bin/env python3
"""
Input validation utilities for Content Crew Prodigal API
"""

import re
from typing import Any, Dict, List, Optional
from utils.error_handler import ValidationException

class InputValidator:
    """Comprehensive input validation for all API endpoints."""
    
    # Email validation regex
    EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    
    # Password strength requirements
    PASSWORD_MIN_LENGTH = 8
    PASSWORD_MAX_LENGTH = 128
    
    # Phone number regex (international format)
    PHONE_REGEX = re.compile(r'^\+?[1-9]\d{1,14}$')
    
    @classmethod
    def validate_email(cls, email: str, field_name: str = "email") -> str:
        """Validate email address format."""
        if not email:
            raise ValidationException(f"{field_name} is required", field_name)
        
        if not isinstance(email, str):
            raise ValidationException(f"{field_name} must be a string", field_name)
        
        email = email.strip().lower()
        
        if len(email) > 254:
            raise ValidationException(f"{field_name} is too long (max 254 characters)", field_name)
        
        if not cls.EMAIL_REGEX.match(email):
            raise ValidationException(f"{field_name} has invalid format", field_name)
        
        return email
    
    @classmethod
    def validate_password(cls, password: str, field_name: str = "password") -> str:
        """Validate password strength."""
        if not password:
            raise ValidationException(f"{field_name} is required", field_name)
        
        if not isinstance(password, str):
            raise ValidationException(f"{field_name} must be a string", field_name)
        
        if len(password) < cls.PASSWORD_MIN_LENGTH:
            raise ValidationException(
                f"{field_name} must be at least {cls.PASSWORD_MIN_LENGTH} characters long", 
                field_name
            )
        
        if len(password) > cls.PASSWORD_MAX_LENGTH:
            raise ValidationException(
                f"{field_name} is too long (max {cls.PASSWORD_MAX_LENGTH} characters)", 
                field_name
            )
        
        # Check for at least one letter and one number
        if not re.search(r'[A-Za-z]', password):
            raise ValidationException(f"{field_name} must contain at least one letter", field_name)
        
        if not re.search(r'\d', password):
            raise ValidationException(f"{field_name} must contain at least one number", field_name)
        
        return password
    
    @classmethod
    def validate_name(cls, name: str, field_name: str = "name", min_length: int = 2, max_length: int = 100) -> str:
        """Validate name fields."""
        if not name:
            raise ValidationException(f"{field_name} is required", field_name)
        
        if not isinstance(name, str):
            raise ValidationException(f"{field_name} must be a string", field_name)
        
        name = name.strip()
        
        if len(name) < min_length:
            raise ValidationException(f"{field_name} must be at least {min_length} characters long", field_name)
        
        if len(name) > max_length:
            raise ValidationException(f"{field_name} is too long (max {max_length} characters)", field_name)
        
        return name
    
    @classmethod
    def validate_uuid(cls, uuid_str: str, field_name: str = "id") -> str:
        """Validate UUID format."""
        if not uuid_str:
            raise ValidationException(f"{field_name} is required", field_name)
        
        if not isinstance(uuid_str, str):
            raise ValidationException(f"{field_name} must be a string", field_name)
        
        uuid_str = uuid_str.strip()
        
        # UUID v4 format validation
        uuid_pattern = re.compile(
            r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
            re.IGNORECASE
        )
        
        if not uuid_pattern.match(uuid_str):
            raise ValidationException(f"{field_name} has invalid UUID format", field_name)
        
        return uuid_str
    
    @classmethod
    def validate_user_registration(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate user registration data."""
        validated = {}
        
        validated['email'] = cls.validate_email(data.get('email'), 'email')
        validated['password'] = cls.validate_password(data.get('password'), 'password')
        validated['full_name'] = cls.validate_name(data.get('full_name'), 'full_name')
        validated['organization_name'] = cls.validate_name(data.get('organization_name'), 'organization_name')
        
        return validated
    
    @classmethod
    def validate_user_login(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate user login data."""
        validated = {}
        
        validated['email'] = cls.validate_email(data.get('email'), 'email')
        validated['password'] = cls.validate_password(data.get('password'), 'password')
        
        return validated
