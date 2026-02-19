# ib-cs-ia-tutor-app

This is my IB CS IA project.
its basically a tutor/student homework app.

stack is Flask + MySQL for backend and React (Vite) for frontend.

## folder structure (rough)

```txt
.
├── backend/
│   ├── app.py
│   ├── scripts/
│   │   └── send_reminders.py
│   └── server/
│       ├── routes/      # auth, tasks, students, shop
│       ├── services/    # logic for users/tasks/submissions etc
│       ├── utils/       # auth + file stuff
│       ├── db.py
│       ├── models.py
│       └── config.py
├── frontend/
│   ├── app/
│   │   ├── routes/
│   │   ├── components/
│   │   ├── features/
│   │   └── lib/
│   ├── package.json
│   └── vite.config.ts
├── schema.sql
└── uploads/
```

## what tech i used

- Flask
- MySQL (pymysql)
- JWT auth
- React + TypeScript + Vite
- Tailwind (for UI)

## how to run

### backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install flask flask-cors flask-bcrypt pymysql pyjwt python-dotenv
```

set env vars (or put in your shell profile):

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

make db + run sql:

```bash
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS tutor_app;"
mysql -u root -p tutor_app < schema.sql
```

run backend:

```bash
cd backend
python app.py
```

backend runs on `http://127.0.0.1:5001`.

### frontend

```bash
cd frontend
npm install
npm run dev
```

frontend is `http://127.0.0.1:5173`

## notes

- uploads go to `uploads/` unless changed by env var
- cors default is 127.0.0.1:5173
- reminder email thing uses smtp vars above

## common problems

- DB error: check mysql is running + env vars
- CORS error: make sure frontend url matches backend config
- upload error: check uploads folder permissions

