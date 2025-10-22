import re
from typing import List

def validate_password(password: str) -> None:
    """
    Validate password strength.
    
    Args:
        password: The password to validate
        
    Raises:
        ValueError: If password doesn't meet requirements
    """
    if not password:
        raise ValueError("Password cannot be empty")
    
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")
    
    if len(password) > 128:
        raise ValueError("Password cannot exceed 128 characters")
    
    # Check for at least one uppercase letter
    if not re.search(r'[A-Z]', password):
        raise ValueError("Password must contain at least one uppercase letter")
    
    # Check for at least one lowercase letter
    if not re.search(r'[a-z]', password):
        raise ValueError("Password must contain at least one lowercase letter")
    
    # Check for at least one digit
    if not re.search(r'\d', password):
        raise ValueError("Password must contain at least one digit")
    
    # Check for at least one special character
    if not re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?]', password):
        raise ValueError("Password must contain at least one special character")
    
    # Check for common weak passwords
    weak_passwords = [
        'password', '123456', 'qwerty', 'admin', 'letmein',
        'welcome', 'monkey', 'dragon', 'master', 'football'
    ]
    
    if password.lower() in weak_passwords:
        raise ValueError("Password is too common, please choose a stronger password")

def get_password_strength(password: str) -> dict:
    """
    Get password strength score and feedback.
    
    Args:
        password: The password to analyze
        
    Returns:
        Dictionary with score and feedback
    """
    score = 0
    feedback = []
    
    if not password:
        return {"score": 0, "feedback": ["Password cannot be empty"]}
    
    # Length score
    if len(password) >= 8:
        score += 1
    else:
        feedback.append("Password should be at least 8 characters long")
    
    if len(password) >= 12:
        score += 1
    elif len(password) >= 8:
        score += 0.5
    
    # Character variety score
    if re.search(r'[A-Z]', password):
        score += 1
    else:
        feedback.append("Add uppercase letters")
    
    if re.search(r'[a-z]', password):
        score += 1
    else:
        feedback.append("Add lowercase letters")
    
    if re.search(r'\d', password):
        score += 1
    else:
        feedback.append("Add numbers")
    
    if re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?]', password):
        score += 1
    else:
        feedback.append("Add special characters")
    
    # Bonus for length
    if len(password) >= 16:
        score += 1
    
    # Determine strength level
    if score >= 5:
        strength = "very_strong"
    elif score >= 4:
        strength = "strong"
    elif score >= 3:
        strength = "medium"
    elif score >= 2:
        strength = "weak"
    else:
        strength = "very_weak"
    
    return {
        "score": score,
        "strength": strength,
        "feedback": feedback,
        "is_valid": score >= 3
    }

def validate_password_strength(password: str) -> dict:
    """
    Validate password strength and return detailed feedback.
    
    Args:
        password: The password to validate
        
    Returns:
        Dictionary with validation results
    """
    try:
        validate_password(password)
        strength_info = get_password_strength(password)
        return {
            "is_valid": True,
            "message": "Password meets all requirements",
            "strength": strength_info["strength"],
            "score": strength_info["score"]
        }
    except ValueError as e:
        strength_info = get_password_strength(password)
        return {
            "is_valid": False,
            "message": str(e),
            "strength": strength_info["strength"],
            "score": strength_info["score"]
        }
    if score >= 5:
        strength = "Very Strong"
    elif score >= 4:
        strength = "Strong"
    elif score >= 3:
        strength = "Moderate"
    elif score >= 2:
        strength = "Weak"
    else:
        strength = "Very Weak"
    
    return {
        "score": score,
        "max_score": 6,
        "strength": strength,
        "feedback": feedback
    }

def is_password_strong_enough(password: str, min_score: int = 4) -> bool:
    """
    Check if password meets minimum strength requirements.
    
    Args:
        password: The password to check
        min_score: Minimum required score (default: 4)
        
    Returns:
        True if password meets requirements, False otherwise
    """
    try:
        validate_password(password)
        strength_info = get_password_strength(password)
        return strength_info["score"] >= min_score
    except ValueError:
        return False
