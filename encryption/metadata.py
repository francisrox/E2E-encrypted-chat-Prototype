"""
metadata.py — Hide UUIDs from wire and DB using two complementary schemes:

1. get_stable_token(uuid)  → HMAC-SHA256 of the UUID (deterministic).
   Same UUID → same token every time.
   Used as: WebSocket path, DB storage key, API parameter.
   Wireshark sees the token — looks like random hex, reveals nothing.

2. encrypt_uuid(uuid)      → AES-256-GCM (random nonce, different every call).
   Used for: one-time tokens where you need to encrypt then decrypt.

Key loaded from:
  - ENV var META_KEY (base64)  ← production / ngrok
  - certs/meta.key file        ← local dev (auto-generated)
"""
import os
import hmac
import hashlib
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_KEY_PATH = os.path.join(os.path.dirname(__file__), "..", "certs", "meta.key")
_AAD      = b"securemsg-v3"


def _load_key() -> bytes:
    # Priority 1: environment variable (ngrok cloud / Render)
    env_val = os.environ.get("META_KEY", "").strip()
    if env_val:
        return base64.b64decode(env_val)
    # Priority 2: local file
    os.makedirs(os.path.dirname(_KEY_PATH), exist_ok=True)
    if os.path.exists(_KEY_PATH):
        with open(_KEY_PATH, "rb") as f:
            return base64.b64decode(f.read().strip())
    # Generate and save
    key = os.urandom(32)
    with open(_KEY_PATH, "wb") as f:
        f.write(base64.b64encode(key))
    b64 = base64.b64encode(key).decode()
    print(f"\n  [SecureMsg] NEW META_KEY generated → {_KEY_PATH}")
    print(f"  [SecureMsg] For cloud/ngrok persistent sessions:")
    print(f"              set META_KEY={b64}\n")
    return key


_KEY    = _load_key()
_aesgcm = AESGCM(_KEY)


# ── Stable token (deterministic HMAC) ────────────────────────────────────────

def get_stable_token(uuid_str: str) -> str:
    """
    Deterministic opaque token for a UUID.
    HMAC-SHA256(key, uuid) — same input always gives same output.
    Safe to use as DB key, WS path, and API query parameter.
    """
    mac = hmac.new(_KEY, uuid_str.encode(), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(mac).decode().rstrip("=")


def decrypt_uuid(token: str) -> str:
    """
    Reverse-lookup: given a stable token, find the UUID it belongs to.
    We brute-force compare against all known UUIDs from DB.
    For a prototype this is fine (small user count).
    For production: maintain a token→uuid lookup table.
    """
    from database.models import SessionLocal, User
    db = SessionLocal()
    try:
        for user in db.query(User).all():
            if get_stable_token(user.uuid) == token:
                return user.uuid
        raise ValueError(f"No user found for token: {token[:10]}...")
    finally:
        db.close()


# ── AES-GCM encrypt/decrypt (non-deterministic) ───────────────────────────────

def encrypt_uuid(uuid_str: str) -> str:
    """Encrypt UUID → base64url ciphertext (random nonce, different each call)."""
    nonce = os.urandom(12)
    ct    = _aesgcm.encrypt(nonce, uuid_str.encode(), _AAD)
    return base64.urlsafe_b64encode(nonce + ct).decode().rstrip("=")


def encrypt_meta(data: str) -> str:
    """Alias for encrypt_uuid — kept for backward compat."""
    return encrypt_uuid(data)


def decrypt_meta(token: str) -> str:
    """Decrypt an AES-GCM token → original string."""
    padded = token + "=" * (-len(token) % 4)
    raw    = base64.urlsafe_b64decode(padded)
    nonce, ct = raw[:12], raw[12:]
    return _aesgcm.decrypt(nonce, ct, _AAD).decode()
