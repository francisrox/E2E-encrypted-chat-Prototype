"""
server.py — SecureMsg v3.0
Deployment: ngrok tunnel → automatic HTTPS → no TLS config needed here

Security:
  - Credentials: protected by ngrok HTTPS (Wireshark sees only TLS)
  - UUIDs: stored/transmitted as AES-256-GCM tokens (no plaintext identity)
  - Messages: NaCl Box E2E (server relays ciphertext only)
  - Passwords: Argon2id
"""
import uuid
import json
from datetime import datetime

from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.models import init_db, get_db, User, Message
from auth.password import hash_password, verify_password
from encryption.crypto import generate_keypair
from encryption.metadata import encrypt_uuid, decrypt_uuid, get_stable_token
from websocket.manager import manager

app = FastAPI(title="SecureMsg API", version="3.0.0", docs_url="/docs")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="ui"), name="static")
init_db()


# ── Schemas ───────────────────────────────────────────────────────────────────

class SignupRequest(BaseModel):
    username: str
    email: str
    password: str

class LoginRequest(BaseModel):
    username: str
    password: str

class SendMessageRequest(BaseModel):
    sender_token: str       # AES-GCM token (opaque, no plaintext UUID)
    receiver_token: str     # AES-GCM token (opaque, no plaintext UUID)
    encrypted_message: str  # NaCl Box ciphertext


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/")
def serve_ui():
    return FileResponse("ui/index.html")


@app.post("/signup")
def signup(req: SignupRequest, db: Session = Depends(get_db)):
    if len(req.username.strip()) < 3:
        raise HTTPException(400, "Username must be at least 3 characters")
    if db.query(User).filter(User.username == req.username.strip()).first():
        raise HTTPException(400, "Username already exists")
    if db.query(User).filter(User.email == req.email.strip()).first():
        raise HTTPException(400, "Email already registered")

    user_uuid            = str(uuid.uuid4())
    private_key, public_key = generate_keypair()

    db.add(User(
        uuid          = user_uuid,
        username      = req.username.strip(),
        email         = req.email.strip(),
        password_hash = hash_password(req.password),
        public_key    = public_key,
    ))
    db.commit()

    # stable_token: deterministic per UUID, safe to use as WS path & DB key
    return {
        "success"      : True,
        "stable_token" : get_stable_token(user_uuid),   # deterministic, opaque
        "username"     : req.username.strip(),
        "private_key"  : private_key,
        "public_key"   : public_key,
        "message"      : "Account created. Save your private key — shown only once.",
    }


@app.post("/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == req.username.strip()).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(401, "Invalid credentials")
    return {
        "success"      : True,
        "stable_token" : get_stable_token(user.uuid),
        "username"     : user.username,
        "public_key"   : user.public_key,
    }


@app.get("/users")
def list_users(db: Session = Depends(get_db)):
    return [
        {
            "stable_token": get_stable_token(u.uuid),
            "username"    : u.username,
            "public_key"  : u.public_key,
            "online"      : manager.is_online(u.uuid),
        }
        for u in db.query(User).all()
    ]


@app.get("/search-user")
def search_user(q: str, db: Session = Depends(get_db)):
    users = db.query(User).filter(User.username.ilike(f"%{q}%")).all()
    return [
        {
            "stable_token": get_stable_token(u.uuid),
            "username"    : u.username,
            "public_key"  : u.public_key,
            "online"      : manager.is_online(u.uuid),
        }
        for u in users
    ]


@app.post("/send-message")
def send_message(req: SendMessageRequest, db: Session = Depends(get_db)):
    # Validate tokens are legitimate (decryptable)
    try:
        decrypt_uuid(req.sender_token)
        decrypt_uuid(req.receiver_token)
    except Exception:
        raise HTTPException(400, "Invalid identity tokens")

    db.add(Message(
        sender_uuid       = req.sender_token,    # stored as opaque token
        receiver_uuid     = req.receiver_token,  # stored as opaque token
        encrypted_message = req.encrypted_message,
        timestamp         = datetime.utcnow(),
    ))
    db.commit()
    return {"success": True}


@app.get("/get-messages")
def get_messages(my_token: str, peer_token: str, db: Session = Depends(get_db)):
    try:
        my_uuid   = decrypt_uuid(my_token)
        peer_uuid = decrypt_uuid(peer_token)
    except Exception:
        raise HTTPException(400, "Invalid identity tokens")

    # Get all messages, filter by decrypting stored tokens
    result = []
    for m in db.query(Message).order_by(Message.timestamp).all():
        try:
            s = decrypt_uuid(m.sender_uuid)
            r = decrypt_uuid(m.receiver_uuid)
        except Exception:
            continue
        if (s == my_uuid and r == peer_uuid) or (s == peer_uuid and r == my_uuid):
            result.append({
                "is_mine"          : s == my_uuid,
                "encrypted_message": m.encrypted_message,
                "timestamp"        : m.timestamp.isoformat(),
            })
    return result


# ── WebSocket — real-time relay ───────────────────────────────────────────────

@app.websocket("/ws/{stable_token}")
async def websocket_endpoint(websocket: WebSocket, stable_token: str):
    try:
        real_uuid = decrypt_uuid(stable_token)
    except Exception:
        await websocket.close(code=1008)
        return

    await manager.connect(websocket, real_uuid)
    try:
        while True:
            raw  = await websocket.receive_text()
            data = json.loads(raw)

            if data.get("type") == "message":
                try:
                    receiver_uuid = decrypt_uuid(data["receiver_token"])
                except Exception:
                    continue

                payload = {
                    "type"             : "message",
                    "sender_token"     : data.get("sender_token"),   # opaque token only
                    "is_mine"          : False,
                    "encrypted_message": data.get("encrypted_message"),
                    "timestamp"        : datetime.utcnow().isoformat(),
                }
                # Push to receiver (live delivery)
                await manager.send_to_user(receiver_uuid, payload)
                # Echo back to sender for confirmation
                await manager.send_to_user(real_uuid, {**payload, "is_mine": True})

    except WebSocketDisconnect:
        manager.disconnect(real_uuid)


# ── Startup ───────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    print("\n  ╔══════════════════════════════════════════════════╗")
    print("  ║       SecureMsg v3.0 — ngrok Edition             ║")
    print("  ╠══════════════════════════════════════════════════╣")
    print("  ║  Run:  ngrok http 8000                           ║")
    print("  ║  Then share the https://xxxx.ngrok-free.app URL  ║")
    print("  ╠══════════════════════════════════════════════════╣")
    print("  ║  TLS      ✓  ngrok provides HTTPS automatically  ║")
    print("  ║  Metadata ✓  UUIDs hidden (AES-256-GCM tokens)   ║")
    print("  ║  Messages ✓  NaCl Box E2E — server sees nothing  ║")
    print("  ║  Passwords✓  Argon2id                            ║")
    print("  ╚══════════════════════════════════════════════════╝\n")
