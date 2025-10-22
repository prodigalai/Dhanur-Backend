"""
Key Management Service for Content Crew
Handles encryption key rotation, backup, and recovery
"""

import base64
import os
from typing import Optional, Dict, Any
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
from core.config import settings

class KMS:
    """Key Management Service for encryption operations"""
    
    def __init__(self):
        self.master_key = base64.b64decode(settings.encryption_master_b64)
        self.salt = b"content-crew-kms-salt-v1"
        self.info = b"content-crew-kms-info-v1"
    
    def derive_key(self, purpose: str, length: int = 32) -> bytes:
        """Derive a purpose-specific key from master"""
        purpose_info = f"purpose-{purpose}".encode()
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=length,
            salt=self.salt,
            info=self.info + purpose_info,
        )
        return hkdf.derive(self.master_key)
    
    def rotate_master_key(self, new_master_key_b64: str) -> bool:
        """Rotate the master key (requires re-encrypting all data)"""
        try:
            new_master_key = base64.b64decode(new_master_key_b64)
            if len(new_master_key) != 32:
                raise ValueError("Master key must be 32 bytes")
            
            # TODO: Implement key rotation logic
            # This would require:
            # 1. Decrypt all existing tokens with old key
            # 2. Re-encrypt with new key
            # 3. Update master key in settings
            # 4. Backup old key for recovery
            
            return True
        except Exception as e:
            print(f"Key rotation failed: {e}")
            return False
    
    def backup_master_key(self) -> Dict[str, Any]:
        """Create a backup of the current master key"""
        return {
            "key": settings.encryption_master_b64,
            "timestamp": "2024-01-01T00:00:00Z",  # TODO: Use actual timestamp
            "version": "v1",
            "checksum": self._calculate_checksum(self.master_key)
        }
    
    def _calculate_checksum(self, key: bytes) -> str:
        """Calculate checksum for key verification"""
        import hashlib
        return hashlib.sha256(key).hexdigest()
    
    def verify_key_integrity(self) -> bool:
        """Verify that the master key is valid and not corrupted"""
        try:
            if len(self.master_key) != 32:
                return False
            
            # Test key derivation
            test_key = self.derive_key("test", 16)
            if len(test_key) != 16:
                return False
            
            return True
        except Exception:
            return False

# Global KMS instance
kms = KMS()
