from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import List, Optional

class Settings(BaseSettings):
    app_env: str = Field(default="dev")
    app_secret: str
    database_url: str

    # JWT settings for Dhanur Backend API
    secret_key: str = Field(default="your-secret-key-here")
    algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=30)
    
    # Google OAuth settings
    google_client_id: str
    google_client_secret: str
    google_redirect_url: str

    # LinkedIn OAuth settings
    linkedin_client_id: str = Field(default="")
    linkedin_client_secret: str = Field(default="")
    linkedin_callback_uri: str = Field(default="")

    # Razorpay settings
    razorpay_key_id: str = Field(default="")
    razorpay_key_secret: str = Field(default="")

    # Email settings
    smtp_server: str = Field(default="")
    smtp_port: int = Field(default=587)
    smtp_username: str = Field(default="")
    smtp_password: str = Field(default="")
    smtp_use_tls: bool = Field(default=True)

    # Frontend and CORS
    frontend_url: str = Field(default="http://localhost:3000")
    cors_origins: List[str] = Field(default_factory=list)
    
    # Encryption
    encryption_master_b64: str

    # API settings
    api_base_url: str = Field(default="http://localhost:8080")
    api_version: str = Field(default="v1")
    
    # Rate limiting
    rate_limit_per_minute: int = Field(default=100)
    rate_limit_per_hour: int = Field(default=1000)

    # MongoDB settings
    mongodb_url: str = Field(default="mongodb+srv://ashwini:Ashwini1234@cluster0.lyeisj1.mongodb.net/Dhanur-AI")
    mongodb_database: str = Field(default="Dhanur-AI")

    # Spotify settings (from your .env)
    spotify_client_id: str = Field(default="")
    spotify_client_secret: str = Field(default="")
    spotify_redirect_uri: str = Field(default="")
    spotify_scopes: str = Field(default="")

    # JWT secret (from your .env)
    jwt_secret_key: str = Field(default="")

    # Port (from your .env)
    port: str = Field(default="8080")

    # AI Orchestration settings
    ai_orchestration_url: str = Field(default="https://a389b2d990a2.ngrok.app")

    # MongoDB settings
    mongodb_url: str = Field(default="mongodb+srv://ashwini:Ashwini1234@cluster0.lyeisj1.mongodb.net/Dhanur-AI")
    mongodb_database: str = Field(default="Dhanur-AI")

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="allow")

settings = Settings()
