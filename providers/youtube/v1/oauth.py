import json, time, requests
from pathlib import Path
from typing import Dict, Tuple, List
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

REGISTRY_ROOT = Path("config/platforms/registries/youtube/versions/v1/spec")
ENDPOINTS = json.loads((REGISTRY_ROOT / "endpoints.json").read_text())
SCOPES = json.loads((REGISTRY_ROOT / "scopes.json").read_text())

def _resolve_scopes(scope_keys: List[str], extra_scopes: List[str] | None = None) -> List[str]:
    scopes: List[str] = []
    for k in scope_keys:
        scopes.extend(SCOPES[k])
    if extra_scopes:
        scopes.extend(extra_scopes)
    # De-dupe
    return sorted(set(scopes))

def build_flow(client_json: Dict, scopes: list, redirect_uri: str) -> Flow:
    flow = Flow.from_client_config(client_config=client_json, scopes=scopes)
    flow.redirect_uri = redirect_uri
    return flow

def authorization_url(client_json: Dict, scope_keys: list, redirect_uri: str, state: str = "", extra_scopes: List[str] | None = None) -> Tuple[str, str]:
    scopes = _resolve_scopes(scope_keys, extra_scopes=extra_scopes)
    flow = build_flow(client_json, scopes, redirect_uri)
    auth_url, state_val = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        state=state
    )
    return auth_url, state_val

def exchange_code_for_tokens(client_json: Dict, scope_keys: list, redirect_uri: str, code: str, extra_scopes: List[str] | None = None) -> Dict:
    # Use direct HTTP request to bypass scope validation
    import requests
    
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": client_json["web"]["client_id"],
        "client_secret": client_json["web"]["client_secret"],
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code"
    }
    
    response = requests.post(token_url, data=data)
    response.raise_for_status()
    
    token_data = response.json()
    
    # Parse the scopes from the response
    scopes = token_data.get("scope", "").split(" ") if token_data.get("scope") else []
    
    return {
        "token": token_data.get("access_token"),
        "refresh_token": token_data.get("refresh_token"),
        "token_uri": ENDPOINTS["oauth"]["token_uri"],
        "client_id": client_json["web"]["client_id"],
        "client_secret": client_json["web"]["client_secret"],
        "scopes": scopes,
        "expiry": None,  # We'll handle expiry separately if needed
        "id_token": token_data.get("id_token"),
    }

def refresh_tokens(token_blob: Dict) -> Dict:
    creds = Credentials(
        token=token_blob.get("token"),
        refresh_token=token_blob.get("refresh_token"),
        token_uri=token_blob.get("token_uri"),
        client_id=token_blob.get("client_id"),
        client_secret=token_blob.get("client_secret"),
        scopes=token_blob.get("scopes"),
    )
    if not creds.valid or (creds.expired and creds.refresh_token):
        creds.refresh(Request())
    return {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": token_blob["token_uri"],
        "client_id": token_blob["client_id"],
        "client_secret": token_blob["client_secret"],
        "scopes": creds.scopes,
        "expiry": creds.expiry.timestamp() if creds.expiry else None,
        "id_token": token_blob.get("id_token"),
    }

def build_credentials(token_blob: Dict) -> Credentials:
    now = time.time()
    exp = token_blob.get("expiry") or 0
    if exp and exp - now < 120:
        token_blob = refresh_tokens(token_blob)
    return Credentials(
        token=token_blob.get("token"),
        refresh_token=token_blob.get("refresh_token"),
        token_uri=token_blob.get("token_uri"),
        client_id=token_blob.get("client_id"),
        client_secret=token_blob.get("client_secret"),
        scopes=token_blob.get("scopes"),
    )

def revoke_token(refresh_token: str) -> bool:
    revoke_uri = ENDPOINTS["oauth"]["revoke_uri"]
    # Per Google docs, pass 'token' as either access or refresh token
    r = requests.post(revoke_uri, data={"token": refresh_token}, timeout=10)
    return r.status_code in (200, 400)  # 200 OK; 400 if already invalid
