# ib-cs-ia-tutor-app

This is my IB Computer Science IA Project.
IB Computer Science IA project: a tutor/student homework system with a Flask + MySQL backend and a React Router (Vite) frontend.

## Project Structure

```
.
├── backend/                 # Flask API, DB schema, reminder script
│   ├── app.py               # App entrypoint
│   ├── schema.sql           # DB schema updates/migrations
│   ├── server/              # Flask app package
│   └── scripts/             # Background/utility scripts
├── frontend/                # React Router (Vite) app
└── uploads/                 # Uploaded files (created at runtime)
```

## Tech Stack

- Backend: Flask, Flask-CORS, Flask-Bcrypt, PyMySQL, PyJWT
- Frontend: React Router (Vite), React, TypeScript, Tailwind CSS
- Database: MySQL

## Getting Started

### Prerequisites

- Node.js (18+ recommended)
- Python 3.10+ (compatible with your environment)
- MySQL server (local or remote)

### 1) Backend Setup

Create and activate a virtual environment, then install dependencies:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install flask flask-cors flask-bcrypt pymysql pyjwt python-dotenv
```

Set environment variables (defaults shown are used if not set):

```bash
export DB_HOST=127.0.0.1
export DB_USER=root
export DB_PASSWORD=12345678
export DB_NAME=tutor_app
export JWT_SECRET=dev-secret-change-me
export JWT_EXPIRES_MINUTES=120
export JWT_COOKIE_SECURE=false
export JWT_COOKIE_SAMESITE=Lax
export BCRYPT_LOG_ROUNDS=12
export UPLOAD_FOLDER=./uploads
export SMTP_HOST=smtp.gmail.com
export SMTP_PORT=587
export SMTP_USER=
export SMTP_PASSWORD=
export SMTP_SENDER=
```

Initialize the database:

```bash
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS tutor_app;"
mysql -u root -p tutor_app < backend/schema.sql
```

Note: `backend/schema.sql` contains migration-style updates and expects existing `users` and `tasks` tables. If you are starting from scratch, create those base tables first or adjust the SQL accordingly.

Run the backend (port `5001`):

```bash
cd backend
python app.py
```

You should see: `Backend is running` at `http://127.0.0.1:5001/`.

### 2) Frontend Setup

Install dependencies and run the dev server (port `5173`):

```bash
cd frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173`.

## Environment Notes

- CORS allows `http://127.0.0.1:5173` by default (`backend/server/config.py`).
- File uploads are stored in `uploads/` (auto-created) unless `UPLOAD_FOLDER` is set.
- Reminder emails use SMTP settings configured via environment variables.

## Cloudflare Tunnel (Setup Record)

Use this section to document how you exposed the local dev server for testing/demo.

### Summary

- Purpose: expose local frontend/backend for remote testing or IA demo.
- Date: YYYY-MM-DD
- Tunnel hostname: `your-subdomain.trycloudflare.com` (or your custom domain)
- Local services: `http://127.0.0.1:5173` (frontend), `http://127.0.0.1:5001` (backend)

### Steps (Example)

```bash
# 1) Install cloudflared (macOS example)
brew install cloudflared

# 2) Login to Cloudflare
cloudflared tunnel login

# 3) Create a named tunnel
cloudflared tunnel create tutor-app

# 4) Run a quick temporary tunnel (frontend)
cloudflared tunnel --url http://127.0.0.1:5173

# 5) Or run with a config file (multi-service)
# config file path example: ~/.cloudflared/config.yml
cloudflared tunnel run tutor-app
```

### Notes

- If using a config file, record the path and the exact `ingress` mapping used.
- If you used a custom domain, note the DNS records created by Cloudflare.
- If the tunnel was temporary (`--url`), record the full temporary URL and date.

## Why Flask Instead of Django (Rationale Guide)

If you need to justify the framework choice in your IA documentation, here is a concise structure you can adapt.

### Key Points to Address

- Project scope: small-to-medium CRUD app with a simple API; no need for Django's built-in admin/ORM complexity.
- Time constraints: Flask has a lighter learning curve and faster initial setup for a focused IA timeline.
- Flexibility: Flask lets you choose only the libraries you need (JWT auth, MySQL, file uploads).
- Architecture fit: separate React frontend + API backend; Flask suits a minimal REST API.
- Deployment simplicity: fewer moving parts and lower resource requirements.

### Example Paragraph

Use a short paragraph like the following and tweak to match your actual decision:

```
I chose Flask instead of Django because the project required a lightweight REST API and a separate React frontend. Flask’s minimal structure allowed faster setup and clearer control over routing, authentication, and database access within the limited IA timeframe. Django’s built-in admin and ORM features are powerful, but they would add complexity that this project does not need. Flask therefore provided a better fit for the project scope, learning objectives, and deployment simplicity.
```

## Useful Commands

Backend:

```bash
cd backend
python app.py
```

Frontend:

```bash
cd frontend
npm run dev
npm run build
npm run start
```

## Troubleshooting

- DB connection errors: verify MySQL credentials in env vars and that `tutor_app` exists.
- CORS errors: ensure frontend is running on `http://127.0.0.1:5173` or update `CORS_ORIGINS`.
- Upload issues: confirm the `uploads/` directory is writable or set `UPLOAD_FOLDER`.
