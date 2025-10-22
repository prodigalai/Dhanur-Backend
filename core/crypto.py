import base64, os, hmac, hashlib, json
from typing import Tuple, Dict, Any
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from core.config import settings

_MASTER = base64.b64decode(settings.encryption_master_b64)

def hkdf_sha256(ikm: bytes, salt: bytes, info: bytes, length: int = 64) -> bytes:
    import hashlib, hmac
    prk = hmac.new(salt, ikm, hashlib.sha256).digest()
    t = b""
    okm = b""
    i = 1
    while len(okm) < length:
        t = hmac.new(prk, t + info + bytes([i]), hashlib.sha256).digest()
        okm += t
        i += 1
    return okm[:length]

def derive_keys() -> Tuple[bytes, bytes]:
    # Derive AES and HMAC keys from master
    okm = hkdf_sha256(_MASTER, salt=b"content-crew-kdf", info=b"envelope-v1", length=64)
    return okm[:32], okm[32:]  # (aes_key, hmac_key)

def generate_dek() -> bytes:
    return os.urandom(32)

def wrap_dek(aes_key: bytes, dek: bytes) -> Dict[str, bytes]:
    iv = os.urandom(12)
    ct = AESGCM(aes_key).encrypt(iv, dek, None)
    return {"iv": iv, "ct": ct}

def unwrap_dek(aes_key: bytes, blob: Dict[str, bytes]) -> bytes:
    return AESGCM(aes_key).decrypt(blob["iv"], blob["ct"], None)

def enc_token(dek: bytes, token: Dict[str, Any]) -> Dict[str, bytes]:
    iv = os.urandom(12)
    pt = json.dumps(token, separators=(",", ":")).encode()
    ct = AESGCM(dek).encrypt(iv, pt, None)
    return {"iv": iv, "ct": ct, "pt": pt}

def dec_token(dek: bytes, blob: Dict[str, bytes]) -> Dict[str, Any]:
    pt = AESGCM(dek).decrypt(blob["iv"], blob["ct"], None)
    return json.loads(pt.decode())

def fingerprint(hmac_key: bytes, pt: bytes) -> bytes:
    return hmac.new(hmac_key, pt, hashlib.sha256).digest()

def encrypt_token_blob(token: Dict[str, Any]) -> Dict[str, bytes]:
    aes_key, hmac_key = derive_keys()
    dek = generate_dek()
    wrapped = wrap_dek(aes_key, dek)
    sealed = enc_token(dek, token)
    fp = fingerprint(hmac_key, sealed["pt"])
    return {
        "wrapped_iv": wrapped["iv"],
        "wrapped_ct": wrapped["ct"],
        "iv": sealed["iv"],
        "ct": sealed["ct"],
        "fp": fp
    }

def decrypt_token_blob(blob: Dict[str, bytes]) -> Dict[str, Any]:
    aes_key, _ = derive_keys()
    dek = unwrap_dek(aes_key, {"iv": blob["wrapped_iv"], "ct": blob["wrapped_ct"]})
    return dec_token(dek, {"iv": blob["iv"], "ct": blob["ct"]})
