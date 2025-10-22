import requests
from typing import Dict, Optional
import json
import base64


# LinkedIn OAuth functions - removed unused build_linkedin_credentials


def exchange_code_for_token(
    code: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str
) -> Dict:
    """
    Exchange authorization code for access token.
    """
    token_url = "https://www.linkedin.com/oauth/v2/accessToken"
    
    data = {
        'grant_type': 'authorization_code',
        'code': code,
        'client_id': client_id,
        'client_secret': client_secret,
        'redirect_uri': redirect_uri
    }
    
    response = requests.post(token_url, data=data)
    response.raise_for_status()
    
    return response.json()


def refresh_access_token(
    refresh_token: str,
    client_id: str,
    client_secret: str
) -> Dict:
    """
    Refresh access token using refresh token.
    """
    token_url = "https://www.linkedin.com/oauth/v2/accessToken"
    
    data = {
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token,
        'client_id': client_id,
        'client_secret': client_secret
    }
    
    response = requests.post(token_url, data=data)
    response.raise_for_status()
    
    return response.json()


def get_user_profile(access_token: str) -> Dict:
    """
    Get LinkedIn user profile using OpenID Connect /v2/userinfo endpoint.
    """
    # LinkedIn OpenID Connect userinfo endpoint
    userinfo_url = "https://api.linkedin.com/v2/userinfo"
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.get(userinfo_url, headers=headers)
        response.raise_for_status()
        profile_data = response.json()
        
        # Map OpenID Connect fields to our expected format
        # OpenID Connect returns: sub, name, given_name, family_name, picture, email
        mapped_data = {
            'id': profile_data.get('sub'),  # sub is the user ID in OpenID Connect
            'localizedFirstName': profile_data.get('given_name'),
            'localizedLastName': profile_data.get('family_name'),
            'emailAddress': profile_data.get('email'),
            'profilePicture': profile_data.get('picture'),
            'name': profile_data.get('name'),
            'headline': None,  # Not available in basic userinfo
            'industry': None,  # Not available in basic userinfo
            'location': None   # Not available in basic userinfo
        }
        
        return mapped_data
        
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 403:
            # Fallback: try to get basic profile info from ID token if available
            raise Exception(f"LinkedIn API access denied. Please ensure your app has 'Sign in with LinkedIn using OpenID Connect' product enabled with scopes: openid profile email")
        else:
            raise e


def decrypt_linkedin_token(encrypted_token_json: str) -> Dict:
    """
    Decrypt LinkedIn access token from JSON string format.
    """
    try:
        # Parse JSON string back to dict
        token_data = json.loads(encrypted_token_json)
        
        # Convert base64 strings back to bytes
        token_blob = {
            "wrapped_iv": base64.b64decode(token_data["wrapped_iv"]),
            "wrapped_ct": base64.b64decode(token_data["wrapped_ct"]),
            "iv": base64.b64decode(token_data["iv"]),
            "ct": base64.b64decode(token_data["ct"]),
            "fp": base64.b64decode(token_data["fp"])
        }
        
        # Decrypt the token using the core crypto module
        from core.crypto import decrypt_token_blob
        return decrypt_token_blob(token_blob)
    except Exception as e:
        raise Exception(f"Failed to decrypt LinkedIn token: {str(e)}")
