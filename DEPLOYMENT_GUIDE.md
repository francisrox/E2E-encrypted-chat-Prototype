# SecureMsg — Internet Deployment Guide
# Alice and Bob on different machines, different locations

## What you need (all free)
- GitHub account → github.com
- Render account → render.com
- Git installed on your machine

---

## STEP 1 — Create a GitHub Repository

1. Go to https://github.com → click "New" (top left)
2. Repository name: `securemsg`
3. Set to **Private** (your keys folder is gitignored but still good practice)
4. Do NOT add README or .gitignore (you have your own)
5. Click "Create repository"
6. GitHub shows you a URL like:
   `https://github.com/YOUR_USERNAME/securemsg.git`
   Copy it.

---

## STEP 2 — Push your code to GitHub

Open PowerShell (Windows) or Terminal (Linux) inside your project folder:

```
cd D:\secure_messenger_cl\secure_messenger
```

Run these commands ONE BY ONE:

```powershell
git init
git add .
git commit -m "SecureMsg v2.0 - Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/securemsg.git
git push -u origin main
```

When it asks for username/password: use your GitHub username and a
Personal Access Token (not your password).

To create a token:
  GitHub → Settings → Developer settings → Personal access tokens
  → Tokens (classic) → Generate new token → tick "repo" → Generate
  Copy the token and use it as your password.

---

## STEP 3 — Get your META_KEY

Run your server locally ONCE first (this generates the encryption key):

Windows:
```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn server:app --port 8000
```

Linux:
```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python3 -m uvicorn server:app --port 8000
```

Look at the terminal output. It will print something like:

```
  META_KEY (copy this to Render dashboard):

  abc123XYZ...base64string...==
```

Copy that entire base64 string. You will need it in Step 5.

Alternatively, read it directly:
Windows:   type certs\meta.key
Linux:     cat certs/meta.key

---

## STEP 4 — Create a Render account and connect GitHub

1. Go to https://render.com
2. Click "Get Started for Free"
3. Sign up with GitHub (easiest — auto-connects your repos)
4. Authorise Render to access your GitHub

---

## STEP 5 — Deploy on Render

1. In Render dashboard, click "New +" → "Web Service"
2. Choose "Build and deploy from a Git repository"
3. Select your `securemsg` repository → click "Connect"
4. Fill in these settings:

   Name:           securemsg
   Region:         Singapore (closest to India)
   Branch:         main
   Runtime:        Python 3
   Build Command:  pip install -r requirements.txt
   Start Command:  uvicorn server:app --host 0.0.0.0 --port $PORT

5. Scroll down to "Environment Variables" → click "Add Environment Variable":

   Key:    META_KEY
   Value:  [paste your base64 key from Step 3]

6. Plan: Select "Free"
7. Click "Create Web Service"

Render will now:
  - Pull your code from GitHub
  - Install all dependencies
  - Start the server
  - Give you a URL like: https://securemsg.onrender.com

This takes about 2-3 minutes.

---

## STEP 6 — Open the app

Once deployment is complete (Render shows "Live"), open:

   https://securemsg.onrender.com

Share this SAME URL with Bob (or anyone else).

Both Alice (Windows) and Bob (Linux) open this URL in their browser.
They register, exchange messages — fully end-to-end encrypted, from
anywhere in the world.

---

## STEP 7 — Test the encryption

Open Wireshark on either machine and capture traffic.
You will see ONLY:
   TLSv1.3  Application Data  [Encrypted Application Data]

No usernames, no passwords, no UUIDs, no message content — nothing readable.

---

## Important notes

### Free tier limitations on Render
- The service SPINS DOWN after 15 minutes of inactivity
- First request after spin-down takes ~1 minute to wake up
- SQLite database RESETS on every restart (ephemeral filesystem)
- For a permanent database, upgrade to paid OR use a free PostgreSQL
  service (Render provides one free PostgreSQL for 90 days)

### To keep data across restarts (upgrade path)
Replace SQLite with PostgreSQL:
1. Render dashboard → New → PostgreSQL (free)
2. Copy the "Internal Database URL"
3. Add env var: DATABASE_URL = [your postgres URL]
4. Update database/models.py: change DATABASE_URL to read from env

### Auto-redeploy
Every time you push to GitHub:
   git add .
   git commit -m "update"
   git push
Render automatically redeploys within 1-2 minutes.

---

## Quick reference

| URL | Purpose |
|-----|---------|
| https://securemsg.onrender.com | Your live app (share this) |
| https://securemsg.onrender.com/docs | API documentation |
| https://render.com/dashboard | Check logs, restart server |

---

## Architecture summary

Alice (any location)
      |
      | HTTPS (TLS 1.3)  — Wireshark sees only encrypted bytes
      |
      ▼
Render Server (Singapore)
   - All traffic encrypted by TLS
   - Login credentials: hidden by TLS
   - UUIDs: hidden by AES-256-GCM
   - Messages: hidden by NaCl Box (server can't read even after TLS)
      |
      | HTTPS (TLS 1.3)
      |
      ▼
Bob (any location)
