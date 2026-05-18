# ⬡ SecureMsg  — End-to-End Encrypted Messaging System

## Security fixes in v2.0

| Issue | v1.0 | v2.0 |
|---|---|---|
| Login credentials  | ✅ HTTPS/TLS (all traffic encrypted) |
| sender_uuid / receiver_uuid | ✅ AES-256-GCM encrypted tokens |
| Two machines can communicate  | ✅ LAN via 0.0.0.0 binding + auto LAN IP cert |

---

```
TLSv1.3 Application Data  [Encrypted — 512 bytes]      ← ONLY THIS
```

---

## Architecture

```
CLIENT A (Browser)                    SERVER (FastAPI + TLS)            CLIENT B (Browser)
─────────────────                     ──────────────────────            ─────────────────
                    ◄── TLS ──────────────────────────────── TLS ──►

Credentials     ──► HTTPS POST /login (encrypted by TLS)
                     └─ Server sees only after TLS decrypt, then Argon2 verify

Message         ──► NaCl Box encrypt ──► WSS relay (ciphertext only) ──► NaCl Box decrypt
                     Server stores: AES(sender_uuid) | AES(receiver_uuid) | NaCl(message)
                     Server cannot read any of these
```

---

## Tech Stack

| Component | Technology | Purpose |
|---|---|---|
| Transport security | TLS 1.3 (self-signed RSA-2048) | Encrypts ALL HTTP traffic |
| Metadata protection | AES-256-GCM | Hides sender/receiver identity |
| Message encryption | NaCl Box (X25519 + XSalsa20-Poly1305) | E2E message privacy |
| Password storage | Argon2id | Brute-force resistant hashing |
| Real-time chat | WebSocket Secure (WSS) | Encrypted live delivery |
| Backend | FastAPI + Uvicorn | REST API + WebSocket |
| Database | SQLite + SQLAlchemy | Stores only ciphertext |

---

## Quick Start

### Linux / macOS
```bash
chmod +x start.sh
./start.sh
```

### Windows (PowerShell)
```powershell
.\start.bat
```

### Manual
```bash
# 1. Create and activate venv
python -m venv venv
.\venv\Scripts\activate          # Windows
source venv/bin/activate         # Linux/Mac

# 2. Install dependencies
pip install -r requirements.txt
pip install cryptography

# 3. Generate TLS certificate (auto-detects your LAN IP)
python generate_certs.py

# 4. Start HTTPS server
python -m uvicorn server:app --ssl-keyfile certs/key.pem --ssl-certfile certs/cert.pem --host 0.0.0.0 --port 8443 --reload
```

Open **https://localhost:8443** in your browser.

---

## Cross-Machine Communication (Windows ↔ Linux VM)

### Step 1 — Run server on ONE machine only
Pick either Windows or Linux. Run `start.bat` or `start.sh` there.
The server will print your LAN IP, e.g.:
```
  LAN  →  https://192.168.1.42:8443
```

### Step 2 — Trust the certificate on BOTH machines
The self-signed cert will trigger a browser warning. Either:

**Option A — Click through (easiest for prototype):**
Open the URL → click "Advanced" → "Proceed to 192.168.1.xx (unsafe)"

**Option B — Install certificate (no warning):**

Linux:
```bash
sudo cp certs/cert.pem /usr/local/share/ca-certificates/securemsg.crt
sudo update-ca-certificates
```

Windows (PowerShell as Administrator):
```powershell
Import-Certificate -FilePath .\certs\cert.pem -CertStoreLocation Cert:\LocalMachine\Root
```

### Step 3 — Open the app on BOTH machines
Both open: `https://<SERVER_LAN_IP>:8443`

### Step 4 — Firewall rule (if needed)
Windows may block port 8443. Run as Administrator:
```powershell
netsh advfirewall firewall add rule name="SecureMsg" dir=in action=allow protocol=TCP localport=8443
```

Linux:
```bash
sudo ufw allow 8443/tcp
```

---

## File Structure

```
secure_messenger/
├── server.py               ← FastAPI HTTPS backend
├── generate_certs.py       ← TLS cert generator (auto LAN IP)
├── requirements.txt
├── start.sh / start.bat    ← One-click launchers
│
├── certs/
│   ├── cert.pem            ← Self-signed TLS certificate
│   ├── key.pem             ← TLS private key
│   ├── meta.key            ← AES-256 key for UUID encryption
│   └── lan_ip.txt          ← Auto-detected LAN IP (used by start scripts)
│
├── database/models.py      ← SQLAlchemy User + Message tables
├── auth/password.py        ← Argon2id hash + verify
├── encryption/
│   ├── crypto.py           ← NaCl Box E2E encryption + key generation
│   └── metadata.py         ← AES-256-GCM UUID token encryption
├── websocket/manager.py    ← WSS connection manager
└── ui/index.html           ← SPA — auto-uses https:// and wss://
```

---

## Security Properties

| Property | Implementation | Wireshark sees |
|---|---|---|
| Transport | TLS 1.3 | Encrypted bytes only |
| Credentials | TLS + Argon2id | Encrypted (TLS) + never stored plaintext |
| Sender identity | AES-256-GCM token | Opaque token, not UUID |
| Receiver identity | AES-256-GCM token | Opaque token, not UUID |
| Message content | NaCl Box (E2E) | Ciphertext even after TLS unwrap |
| Stored messages | NaCl ciphertext in DB | Server cannot decrypt |

Built by: Francis S T | B.E. Cybersecurity | SKCT Coimbatore
