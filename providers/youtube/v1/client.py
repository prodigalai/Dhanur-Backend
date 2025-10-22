import json
from pathlib import Path
from typing import Dict
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from .oauth import build_credentials

REGISTRY_ROOT = Path("config/platforms/registries/youtube/versions/v1/spec")
ENDPOINTS = json.loads((REGISTRY_ROOT / "endpoints.json").read_text())

def youtube_service(token_blob: Dict):
    creds = build_credentials(token_blob)
    return build(
        ENDPOINTS["api"]["discovery_service_name"],
        ENDPOINTS["api"]["discovery_version"],
        credentials=creds,
        cache_discovery=False
    )

def media_upload(path: str, mimetype: str) -> MediaFileUpload:
    return MediaFileUpload(path, mimetype=mimetype, resumable=True)
