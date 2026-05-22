#!/usr/bin/env bash
# ─────────────────────────────────────────
#  Spendwise — Expense Tracker Startup
# ─────────────────────────────────────────

echo ""
echo "╔═══════════════════════════════════════╗"
echo "║        💸 Spendwise Expense Tracker   ║"
echo "╚═══════════════════════════════════════╝"
echo ""

# Install deps if needed
pip install flask PyJWT --break-system-packages -q 2>/dev/null

# Start Flask
cd "$(dirname "$0")/backend"
echo "🚀 Starting server at http://localhost:5000"
echo "📧 Demo: user@demo.com / demo123"
echo "🌐 Open http://localhost:5000 in your browser"
echo ""
python3 app.py
