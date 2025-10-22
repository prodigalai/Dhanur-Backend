from sqlalchemy.orm import Session
from models.oauth_account import OauthAccounts

def upsert_oauth_account(db: Session, provider: str, provider_user_id: str, email: str | None) -> OauthAccounts:
    acct = db.query(OauthAccounts).filter_by(provider=provider, provider_user_id=provider_user_id).one_or_none()
    if acct:
        if email and acct.email != email:
            acct.email = email
        return acct
    acct = OauthAccounts(provider=provider, provider_user_id=provider_user_id, email=email)
    db.add(acct)
    db.flush()
    return acct
