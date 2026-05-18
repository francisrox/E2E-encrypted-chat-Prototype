#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
echo ""
echo "  ====================================================="
echo "   SecureMsg v3.0 — Internet Messaging via ngrok"
echo "  ====================================================="
echo ""
[ ! -d venv ] && python3 -m venv venv
source venv/bin/activate 2>/dev/null || true
pip install -r requirements.txt -q
echo ""
echo "  STEP 1: Server starting on http://localhost:8000"
echo "  STEP 2: Open a NEW terminal → run: ngrok http 8000"
echo "  STEP 3: Copy the https://xxxx.ngrok-free.app URL"
echo "  STEP 4: Share that URL with anyone, anywhere"
echo ""
python3 -m uvicorn server:app --host 0.0.0.0 --port 8000 --reload
