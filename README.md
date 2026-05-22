# 💸 Spendwise — Full Stack Expense Tracker

A complete Python + Flask expense tracker with JWT authentication, AI insights, and a beautiful dark-mode UI.

## 🚀 Quick Start

```bash
# 1. Install dependencies
pip install flask PyJWT

# 2. Run the app
cd backend
python3 app.py

# 3. Open in browser
# http://localhost:5000

# Demo account:
# Email:    user@demo.com
# Password: demo123
```

## 📁 Project Structure

```
expense-tracker/
├── backend/
│   └── app.py              # Flask API + SQLite + JWT
├── frontend/
│   └── index.html          # Single-file UI (HTML/CSS/JS)
├── requirements.txt
├── start.sh
└── README.md
```

## 🔐 Authentication (Step 1)
- JWT tokens with 7-day expiry
- Passwords hashed with SHA-256 + salt
- Multi-user isolation — each user only sees their own data
- Demo account pre-seeded with 20 sample expenses
- Session persists via localStorage

## ➕ Add Expenses (Step 2)
- Title, amount, category, date, note fields
- Form validation (client + server)
- 7 categories: Food, Transport, Housing, Entertainment, Shopping, Health, Other

## 📋 Expense List (Step 3)
- Filter by category (chip buttons)
- Full-text search (title + note)
- Delete any expense
- Shows category icon, date, amount

## 📊 Dashboard (Step 4)
- 4 stat cards: this month, this week, total count, remaining budget
- Doughnut chart — spending by category (Chart.js)
- Bar chart — last 6 months spending trend
- Budget progress bars per category (green → amber → red at 80%/100%)

## 🔔 Budget Alerts (Step 5)
- Warning alert at 80% of monthly budget used
- Danger alert when total or per-category budget exceeded
- Shown on the dashboard in real-time

## ⚙️ Settings (Step 6)
- Set monthly budget per category
- Danger zone: clear all expenses (with confirmation)

## 🤖 AI Insights
- Backend rule-based engine analyses spending patterns
- Budget utilisation insights
- Category-specific warnings
- Savings tips (meal prep, etc.)
- Positive reinforcement when under budget

## 🛠 Tech Stack
| Layer      | Technology           |
|------------|----------------------|
| Backend    | Python 3 + Flask     |
| Auth       | PyJWT (HS256)        |
| Database   | SQLite (built-in)    |
| Frontend   | Vanilla HTML/CSS/JS  |
| Charts     | Chart.js 4.4         |
| Fonts      | Syne + DM Sans       |

## 🌐 API Endpoints

| Method | Path                    | Auth | Description              |
|--------|-------------------------|------|--------------------------|
| POST   | /api/auth/signup        | —    | Register new user        |
| POST   | /api/auth/signin        | —    | Sign in, get JWT token   |
| GET    | /api/auth/me            | ✓    | Verify token             |
| GET    | /api/expenses           | ✓    | List expenses (filtered) |
| POST   | /api/expenses           | ✓    | Add new expense          |
| DELETE | /api/expenses/:id       | ✓    | Delete expense           |
| DELETE | /api/expenses/clear     | ✓    | Clear all expenses       |
| GET    | /api/budgets            | ✓    | Get budget settings      |
| POST   | /api/budgets            | ✓    | Save budget settings     |
| GET    | /api/stats              | ✓    | Analytics & charts data  |
| GET    | /api/ai/insights        | ✓    | AI spending insights     |
