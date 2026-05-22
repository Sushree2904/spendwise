"""
Expense Tracker Backend — Flask + JWT + SQLite
Full REST API with multi-user isolation, AI budget insights
"""

import json
import sqlite3
import hashlib
import secrets
import datetime
import os
from functools import wraps
from flask import Flask, request, jsonify, send_from_directory

try:
    import jwt as pyjwt
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False

app = Flask(__name__, static_folder='../frontend', static_url_path='')

# ─── Config ───────────────────────────────────────────────────────────────────
SECRET_KEY = os.environ.get("SECRET_KEY", "expense-tracker-super-secret-2024-xk9m")
DB_PATH    = os.path.join(os.path.dirname(__file__), "expense_tracker.db")
JWT_EXPIRY_HOURS = 24 * 7  # 7 days

CATEGORIES = ["Food", "Transport", "Housing", "Entertainment", "Shopping", "Health", "Other"]
DEFAULT_BUDGETS = {
    "Food": 300, "Transport": 150, "Housing": 800,
    "Entertainment": 200, "Shopping": 250, "Health": 100, "Other": 100
}

# ─── DB Setup ─────────────────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            name      TEXT    NOT NULL,
            email     TEXT    UNIQUE NOT NULL,
            password  TEXT    NOT NULL,
            created   TEXT    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS expenses (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL,
            title      TEXT    NOT NULL,
            amount     REAL    NOT NULL,
            category   TEXT    NOT NULL,
            date       TEXT    NOT NULL,
            note       TEXT    DEFAULT '',
            created    TEXT    NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS budgets (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL UNIQUE,
            data       TEXT    NOT NULL,
            updated    TEXT    NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """)
    # Seed demo user
    pw = hash_password("demo123")
    try:
        c.execute(
            "INSERT OR IGNORE INTO users (name, email, password, created) VALUES (?,?,?,?)",
            ("Demo User", "user@demo.com", pw, now())
        )
        conn.commit()
        # Add demo expenses if new
        uid = c.execute("SELECT id FROM users WHERE email=?", ("user@demo.com",)).fetchone()["id"]
        count = c.execute("SELECT COUNT(*) FROM expenses WHERE user_id=?", (uid,)).fetchone()[0]
        if count == 0:
            seed_demo_data(c, uid)
            conn.commit()
    except Exception:
        conn.rollback()
    conn.close()

def seed_demo_data(c, uid):
    today = datetime.date.today()
    samples = [
        ("Grocery Run", 68.50, "Food",          str(today - datetime.timedelta(days=1)),  "Weekly groceries"),
        ("Uber to Office", 14.20, "Transport",  str(today - datetime.timedelta(days=2)),  "Morning commute"),
        ("Electricity Bill", 92.00, "Housing",  str(today - datetime.timedelta(days=5)),  "Monthly bill"),
        ("Netflix", 15.99, "Entertainment",     str(today - datetime.timedelta(days=7)),  "Monthly sub"),
        ("Pharmacy", 23.40, "Health",           str(today - datetime.timedelta(days=9)),  "Vitamins"),
        ("Dinner Out", 45.00, "Food",           str(today - datetime.timedelta(days=10)), "Birthday dinner"),
        ("Amazon Order", 89.99, "Shopping",     str(today - datetime.timedelta(days=12)), "Electronics"),
        ("Bus Pass", 35.00, "Transport",        str(today - datetime.timedelta(days=14)), "Monthly pass"),
        ("Coffee Shop", 12.50, "Food",          str(today - datetime.timedelta(days=15)), "Work meeting"),
        ("Gym Membership", 40.00, "Health",     str(today - datetime.timedelta(days=18)), "Monthly"),
        ("Movie Tickets", 28.00, "Entertainment", str(today - datetime.timedelta(days=20)), "Weekend"),
        ("Groceries", 55.30, "Food",            str(today - datetime.timedelta(days=22)), ""),
        ("Taxi", 18.00, "Transport",            str(today - datetime.timedelta(days=25)), "Airport"),
        ("Books", 32.00, "Shopping",            str(today - datetime.timedelta(days=28)), "Programming books"),
        ("Restaurant", 62.00, "Food",           str(today - datetime.timedelta(days=35)), ""),
        ("Streaming", 9.99, "Entertainment",    str(today - datetime.timedelta(days=40)), "Music"),
        ("Doctor Visit", 55.00, "Health",       str(today - datetime.timedelta(days=45)), "Checkup"),
        ("Fuel", 60.00, "Transport",            str(today - datetime.timedelta(days=50)), ""),
        ("Clothing", 120.00, "Shopping",        str(today - datetime.timedelta(days=55)), "Winter jacket"),
        ("Rent",  800.00, "Housing",            str(today - datetime.timedelta(days=32)), "Monthly rent"),
    ]
    for s in samples:
        c.execute(
            "INSERT INTO expenses (user_id,title,amount,category,date,note,created) VALUES (?,?,?,?,?,?,?)",
            (uid, s[0], s[1], s[2], s[3], s[4], now())
        )

# ─── Helpers ──────────────────────────────────────────────────────────────────
def now():
    return datetime.datetime.utcnow().isoformat()

def hash_password(pw):
    salt = "expense_tracker_salt_v1"
    return hashlib.sha256((pw + salt).encode()).hexdigest()

def make_token(user_id, email, name):
    if JWT_AVAILABLE:
        payload = {
            "user_id": user_id,
            "email":   email,
            "name":    name,
            "exp":     datetime.datetime.utcnow() + datetime.timedelta(hours=JWT_EXPIRY_HOURS),
            "iat":     datetime.datetime.utcnow(),
            "jti":     secrets.token_hex(16),
        }
        return pyjwt.encode(payload, SECRET_KEY, algorithm="HS256")
    # Fallback: simple base64-ish token
    import base64
    data = json.dumps({"user_id": user_id, "email": email, "name": name})
    return base64.b64encode(data.encode()).decode()

def decode_token(token):
    if JWT_AVAILABLE:
        try:
            return pyjwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        except pyjwt.ExpiredSignatureError:
            return None
        except pyjwt.InvalidTokenError:
            return None
    # Fallback
    import base64
    try:
        data = base64.b64decode(token.encode()).decode()
        return json.loads(data)
    except Exception:
        return None

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return jsonify({"error": "Missing or invalid token"}), 401
        token = auth[7:]
        payload = decode_token(token)
        if not payload:
            return jsonify({"error": "Token expired or invalid"}), 401
        request.user = payload
        return f(*args, **kwargs)
    return decorated

def cors_headers(resp):
    resp.headers["Access-Control-Allow-Origin"]  = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,DELETE,OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
    return resp

@app.after_request
def after_request(resp):
    return cors_headers(resp)

@app.before_request
def handle_options():
    if request.method == "OPTIONS":
        from flask import Response
        r = Response()
        r.headers["Access-Control-Allow-Origin"]  = "*"
        r.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,DELETE,OPTIONS"
        r.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
        return r

# ─── Auth Routes ──────────────────────────────────────────────────────────────
@app.route("/api/auth/signup", methods=["POST"])
def signup():
    data = request.get_json()
    name  = (data.get("name", "")  or "").strip()
    email = (data.get("email", "") or "").strip().lower()
    pw    = (data.get("password", "") or "").strip()

    if not name:
        return jsonify({"error": "Name is required"}), 400
    if not email or "@" not in email:
        return jsonify({"error": "Valid email is required"}), 400
    if len(pw) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    conn = get_db()
    try:
        exists = conn.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
        if exists:
            return jsonify({"error": "Email already registered"}), 409
        conn.execute(
            "INSERT INTO users (name,email,password,created) VALUES (?,?,?,?)",
            (name, email, hash_password(pw), now())
        )
        conn.commit()
        user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        token = make_token(user["id"], user["email"], user["name"])
        return jsonify({"token": token, "user": {"id": user["id"], "name": user["name"], "email": user["email"]}}), 201
    finally:
        conn.close()

@app.route("/api/auth/signin", methods=["POST"])
def signin():
    data  = request.get_json()
    email = (data.get("email", "") or "").strip().lower()
    pw    = (data.get("password", "") or "").strip()

    if not email or not pw:
        return jsonify({"error": "Email and password required"}), 400

    conn = get_db()
    try:
        user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        if not user or user["password"] != hash_password(pw):
            return jsonify({"error": "Invalid email or password"}), 401
        token = make_token(user["id"], user["email"], user["name"])
        return jsonify({"token": token, "user": {"id": user["id"], "name": user["name"], "email": user["email"]}})
    finally:
        conn.close()

@app.route("/api/auth/me", methods=["GET"])
@require_auth
def me():
    return jsonify({"user": {"id": request.user["user_id"], "email": request.user["email"], "name": request.user["name"]}})

# ─── Expense Routes ───────────────────────────────────────────────────────────
@app.route("/api/expenses", methods=["GET"])
@require_auth
def get_expenses():
    uid      = request.user["user_id"]
    category = request.args.get("category", "")
    search   = request.args.get("search", "")
    limit    = int(request.args.get("limit", 500))

    conn = get_db()
    try:
        q    = "SELECT * FROM expenses WHERE user_id=?"
        args = [uid]
        if category and category != "All":
            q += " AND category=?"
            args.append(category)
        if search:
            q += " AND (title LIKE ? OR note LIKE ?)"
            args += [f"%{search}%", f"%{search}%"]
        q += " ORDER BY date DESC, created DESC LIMIT ?"
        args.append(limit)
        rows = conn.execute(q, args).fetchall()
        return jsonify({"expenses": [dict(r) for r in rows]})
    finally:
        conn.close()

@app.route("/api/expenses", methods=["POST"])
@require_auth
def add_expense():
    uid  = request.user["user_id"]
    data = request.get_json()

    title    = (data.get("title", "") or "").strip()
    amount   = data.get("amount")
    category = (data.get("category", "") or "").strip()
    date     = (data.get("date", "") or "").strip()
    note     = (data.get("note", "") or "").strip()

    if not title:
        return jsonify({"error": "Title is required"}), 400
    try:
        amount = float(amount)
        if amount <= 0:
            raise ValueError
    except (TypeError, ValueError):
        return jsonify({"error": "Amount must be a positive number"}), 400
    if category not in CATEGORIES:
        return jsonify({"error": f"Invalid category"}), 400
    if not date:
        date = str(datetime.date.today())

    conn = get_db()
    try:
        c = conn.execute(
            "INSERT INTO expenses (user_id,title,amount,category,date,note,created) VALUES (?,?,?,?,?,?,?)",
            (uid, title, amount, category, date, note, now())
        )
        conn.commit()
        row = conn.execute("SELECT * FROM expenses WHERE id=?", (c.lastrowid,)).fetchone()
        return jsonify({"expense": dict(row)}), 201
    finally:
        conn.close()

@app.route("/api/expenses/<int:exp_id>", methods=["DELETE"])
@require_auth
def delete_expense(exp_id):
    uid  = request.user["user_id"]
    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM expenses WHERE id=? AND user_id=?", (exp_id, uid)).fetchone()
        if not row:
            return jsonify({"error": "Expense not found"}), 404
        conn.execute("DELETE FROM expenses WHERE id=?", (exp_id,))
        conn.commit()
        return jsonify({"deleted": exp_id})
    finally:
        conn.close()

# ─── Budget Routes ────────────────────────────────────────────────────────────
@app.route("/api/budgets", methods=["GET"])
@require_auth
def get_budgets():
    uid  = request.user["user_id"]
    conn = get_db()
    try:
        row = conn.execute("SELECT data FROM budgets WHERE user_id=?", (uid,)).fetchone()
        budgets = json.loads(row["data"]) if row else DEFAULT_BUDGETS.copy()
        return jsonify({"budgets": budgets})
    finally:
        conn.close()

@app.route("/api/budgets", methods=["POST"])
@require_auth
def save_budgets():
    uid  = request.user["user_id"]
    data = request.get_json()
    bdata = data.get("budgets", {})
    validated = {}
    for cat in CATEGORIES:
        v = bdata.get(cat, DEFAULT_BUDGETS[cat])
        try:
            validated[cat] = max(0, float(v))
        except (TypeError, ValueError):
            validated[cat] = DEFAULT_BUDGETS[cat]

    conn = get_db()
    try:
        existing = conn.execute("SELECT id FROM budgets WHERE user_id=?", (uid,)).fetchone()
        if existing:
            conn.execute("UPDATE budgets SET data=?,updated=? WHERE user_id=?",
                         (json.dumps(validated), now(), uid))
        else:
            conn.execute("INSERT INTO budgets (user_id,data,updated) VALUES (?,?,?)",
                         (uid, json.dumps(validated), now()))
        conn.commit()
        return jsonify({"budgets": validated})
    finally:
        conn.close()

# ─── Stats / Analytics ────────────────────────────────────────────────────────
@app.route("/api/stats", methods=["GET"])
@require_auth
def get_stats():
    uid   = request.user["user_id"]
    today = datetime.date.today()
    conn  = get_db()
    try:
        # All expenses
        rows = conn.execute("SELECT * FROM expenses WHERE user_id=?", (uid,)).fetchall()
        expenses = [dict(r) for r in rows]

        # This month
        month_start = today.replace(day=1).isoformat()
        month_total = sum(e["amount"] for e in expenses if e["date"] >= month_start)

        # This week
        week_start = (today - datetime.timedelta(days=today.weekday())).isoformat()
        week_total = sum(e["amount"] for e in expenses if e["date"] >= week_start)

        # By category this month
        by_cat = {c: 0.0 for c in CATEGORIES}
        for e in expenses:
            if e["date"] >= month_start:
                by_cat[e["category"]] = by_cat.get(e["category"], 0) + e["amount"]

        # Last 6 months trend
        trend = []
        for i in range(5, -1, -1):
            d  = today - datetime.timedelta(days=30 * i)
            ms = d.replace(day=1).isoformat()
            # End of month
            if d.month == 12:
                me = d.replace(year=d.year+1, month=1, day=1).isoformat()
            else:
                me = d.replace(month=d.month+1, day=1).isoformat()
            total = sum(e["amount"] for e in expenses if ms <= e["date"] < me)
            trend.append({"month": d.strftime("%b %Y"), "total": round(total, 2)})

        return jsonify({
            "month_total": round(month_total, 2),
            "week_total":  round(week_total, 2),
            "total_count": len(expenses),
            "by_category": {k: round(v, 2) for k, v in by_cat.items()},
            "trend":       trend,
        })
    finally:
        conn.close()

# ─── AI Insights ──────────────────────────────────────────────────────────────
@app.route("/api/ai/insights", methods=["GET"])
@require_auth
def ai_insights():
    uid   = request.user["user_id"]
    today = datetime.date.today()
    conn  = get_db()
    try:
        month_start = today.replace(day=1).isoformat()
        rows    = conn.execute(
            "SELECT * FROM expenses WHERE user_id=? AND date>=? ORDER BY amount DESC",
            (uid, month_start)
        ).fetchall()
        expenses = [dict(r) for r in rows]

        brow    = conn.execute("SELECT data FROM budgets WHERE user_id=?", (uid,)).fetchone()
        budgets = json.loads(brow["data"]) if brow else DEFAULT_BUDGETS.copy()

        total_budget = sum(budgets.values())
        total_spent  = sum(e["amount"] for e in expenses)
        by_cat = {c: 0.0 for c in CATEGORIES}
        for e in expenses:
            by_cat[e["category"]] += e["amount"]

        insights = []

        # Budget utilisation insight
        pct = (total_spent / total_budget * 100) if total_budget > 0 else 0
        if pct >= 100:
            insights.append({
                "type": "danger",
                "icon": "🚨",
                "title": "Budget Exceeded",
                "body": f"You've spent ${total_spent:.0f} of your ${total_budget:.0f} monthly budget ({pct:.0f}%). "
                        f"Consider deferring non-essential purchases until next month."
            })
        elif pct >= 80:
            insights.append({
                "type": "warning",
                "icon": "⚠️",
                "title": "Approaching Budget Limit",
                "body": f"You're at {pct:.0f}% of your monthly budget with ${total_budget - total_spent:.0f} remaining. "
                        f"Slow down discretionary spending to stay on track."
            })

        # Top category alert
        for cat, spent in by_cat.items():
            budget = budgets.get(cat, 0)
            if budget > 0 and spent >= budget:
                insights.append({
                    "type": "warning",
                    "icon": "📊",
                    "title": f"{cat} Budget Exceeded",
                    "body": f"${spent:.0f} spent on {cat} vs ${budget:.0f} budgeted ({spent/budget*100:.0f}%)."
                })

        # Biggest expense tip
        if expenses:
            top = expenses[0]
            insights.append({
                "type": "info",
                "icon": "💡",
                "title": "Largest Expense This Month",
                "body": f'"{top["title"]}" (${top["amount"]:.2f} — {top["category"]}) is your biggest single expense. '
                        f"Review if this is recurring."
            })

        # Savings opportunity
        food_spent = by_cat.get("Food", 0)
        food_budget = budgets.get("Food", 300)
        if food_spent > food_budget * 0.6:
            insights.append({
                "type": "tip",
                "icon": "🍽️",
                "title": "Food Spending Tip",
                "body": f"You've spent ${food_spent:.0f} on food this month. Meal prepping 2–3 days/week "
                        f"can typically reduce food costs by 20–30%."
            })

        # Positive reinforcement
        savings = total_budget - total_spent
        if savings > 0 and pct < 60:
            insights.append({
                "type": "success",
                "icon": "🎯",
                "title": "Great Financial Discipline!",
                "body": f"You're only at {pct:.0f}% of your budget with ${savings:.0f} remaining. "
                        f"Consider moving surplus to savings or investments."
            })

        if not insights:
            insights.append({
                "type": "info",
                "icon": "📈",
                "title": "No Expenses This Month",
                "body": "Start tracking your expenses to get personalised AI insights and budget alerts."
            })

        return jsonify({"insights": insights})
    finally:
        conn.close()

# ─── Clear Expenses ───────────────────────────────────────────────────────────
@app.route("/api/expenses/clear", methods=["DELETE"])
@require_auth
def clear_expenses():
    uid  = request.user["user_id"]
    conn = get_db()
    try:
        conn.execute("DELETE FROM expenses WHERE user_id=?", (uid,))
        conn.commit()
        return jsonify({"message": "All expenses cleared"})
    finally:
        conn.close()

# ─── Serve Frontend ───────────────────────────────────────────────────────────
@app.route("/")
def index():
    return send_from_directory("../frontend", "index.html")

@app.route("/health")
def health():
    return jsonify({"status": "ok", "jwt": JWT_AVAILABLE})

# ─── Run ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    init_db()
    print("\n✅ Expense Tracker API running at http://localhost:5000")
    print("📧 Demo account: user@demo.com / demo123\n")
    app.run(debug=True, port=5000, host="0.0.0.0")
