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