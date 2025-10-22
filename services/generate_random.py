import secrets
import string
import uuid
from typing import Optional

def generate_random_identifier(length: int = 8) -> str:
    """
    Generate a random alphanumeric identifier.
    
    Args:
        length: Length of the identifier (default: 8)
        
    Returns:
        Random alphanumeric string
    """
    if length <= 0:
        raise ValueError("Length must be positive")
    
    # Use alphanumeric characters (0-9, a-z, A-Z)
    characters = string.ascii_letters + string.digits
    
    # Generate random string
    return ''.join(secrets.choice(characters) for _ in range(length))

def generate_random_string(length: int = 16, include_special: bool = False) -> str:
    """
    Generate a random string with optional special characters.
    
    Args:
        length: Length of the string (default: 16)
        include_special: Whether to include special characters (default: False)
        
    Returns:
        Random string
    """
    if length <= 0:
        raise ValueError("Length must be positive")
    
    if include_special:
        characters = string.ascii_letters + string.digits + "!@#$%^&*()_+-=[]{}|;:,.<>?"
    else:
        characters = string.ascii_letters + string.digits
    
    return ''.join(secrets.choice(characters) for _ in range(length))

def generate_uuid() -> str:
    """
    Generate a UUID4 string.
    
    Returns:
        UUID4 string
    """
    return str(uuid.uuid4())

def generate_secure_token(length: int = 32) -> str:
    """
    Generate a cryptographically secure token.
    
    Args:
        length: Length of the token in bytes (default: 32)
        
    Returns:
        Hex-encoded secure token
    """
    if length <= 0:
        raise ValueError("Length must be positive")
    
    return secrets.token_hex(length)

def generate_numeric_code(length: int = 6) -> str:
    """
    Generate a random numeric code.
    
    Args:
        length: Length of the numeric code (default: 6)
        
    Returns:
        Random numeric string
    """
    if length <= 0:
        raise ValueError("Length must be positive")
    
    # Ensure first digit is not 0 for better readability
    first_digit = secrets.choice(string.digits[1:])
    remaining_digits = ''.join(secrets.choice(string.digits) for _ in range(length - 1))
    
    return first_digit + remaining_digits

def generate_alpha_code(length: int = 6) -> str:
    """
    Generate a random alphabetic code.
    
    Args:
        length: Length of the alphabetic code (default: 6)
        
    Returns:
        Random alphabetic string
    """
    if length <= 0:
        raise ValueError("Length must be positive")
    
    return ''.join(secrets.choice(string.ascii_uppercase) for _ in range(length))

def generate_file_safe_name(prefix: str = "", suffix: str = "", length: int = 8) -> str:
    """
    Generate a file-safe random name.
    
    Args:
        prefix: Prefix for the filename (default: "")
        suffix: Suffix for the filename (default: "")
        length: Length of the random part (default: 8)
        
    Returns:
        File-safe random name
    """
    random_part = generate_random_identifier(length)
    
    if prefix and suffix:
        return f"{prefix}_{random_part}_{suffix}"
    elif prefix:
        return f"{prefix}_{random_part}"
    elif suffix:
        return f"{random_part}_{suffix}"
    else:
        return random_part
