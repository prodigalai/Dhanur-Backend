from datetime import datetime, timezone
from sqlalchemy.orm import Session
from models.youtube_connection import YoutubeConnections

def upsert_youtube_connection(
    db: Session, *,
    brand_id, user_id, oauth_account_id,
    channel_id: str, channel_title: str,
    role: str, scope_keys: list[str], scopes: list[str],
    token_blob: dict
) -> YoutubeConnections:
    row = db.query(YoutubeConnections).filter_by(
        brand_id=brand_id, channel_id=channel_id, revoked_at=None
    ).one_or_none()

    if row is None:
        row = YoutubeConnections(
            brand_id=brand_id, user_id=user_id, oauth_account_id=oauth_account_id,
            channel_id=channel_id, channel_title=channel_title,
            role=role, scope_keys=scope_keys, scopes=scopes,
            token_wrapped_iv=token_blob["wrapped_iv"],
            token_wrapped_ct=token_blob["wrapped_ct"],
            token_iv=token_blob["iv"],
            token_ct=token_blob["ct"],
            token_fp=token_blob["fp"],
            access_token_exp=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.add(row)
        db.flush()
        return row

    # update existing
    row.channel_title = channel_title
    row.role = role
    row.scope_keys = scope_keys
    row.scopes = scopes
    row.token_wrapped_iv = token_blob["wrapped_iv"]
    row.token_wrapped_ct = token_blob["wrapped_ct"]
    row.token_iv = token_blob["iv"]
    row.token_ct = token_blob["ct"]
    row.token_fp = token_blob["fp"]
    row.updated_at = datetime.now(timezone.utc)
    db.flush()
    return row

def get_youtube_connection(db: Session, brand_id: str, user_id: str):
    """Get YouTube connection for a specific brand and user"""
    return db.query(YoutubeConnections).filter_by(
        brand_id=brand_id, 
        user_id=user_id, 
        revoked_at=None
    ).first()

def list_brand_connections(db: Session, brand_id):
    q = db.query(YoutubeConnections).filter_by(brand_id=brand_id, revoked_at=None)
    return q.order_by(YoutubeConnections.created_at.desc()).all()

def revoke_connection(db: Session, connection_id):
    row = db.get(YoutubeConnections, connection_id)
    if row:
        row.revoked_at = datetime.now(timezone.utc)
        row.updated_at = datetime.now(timezone.utc)
        db.flush()
    return row
