# Quotation Module

Web application for creating, reviewing, and downloading quotation reports. Each organization has its own customers, activities, templates, and users. An admin sets up the company; users generate reports from the starred template.

## What it includes

- Organization sign-up and sign-in (admin and user roles)
- Report template designer, with one starred template used when generating reports
- Customers, activities, and custom columns
- Quotation workflow: send, accept, reject, and resubmit
- Notifications, dashboard, and audit log
- PDF and Excel download

## Stack

- Frontend: React, Vite, Ant Design, Tailwind CSS (port **5176**)
- Backend: FastAPI (port **8000**), API prefix `/api/v1`
- Database: PostgreSQL

## Requirements

- Node.js 20 or newer
- Python 3.11 or newer
- PostgreSQL

## Setup

### 1. Database

Create an empty PostgreSQL database for this app.

### 2. Backend

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
playwright install chromium
copy .env.example .env
```

Edit `backend\.env`:

- `DATABASE_URL` — your Postgres user, password, host, and database name
- `JWT_SECRET_KEY` — a long random string (at least 16 characters)
- `FRONTEND_URL` and `CORS_ORIGINS` — the address people use to open the site, for example `http://localhost:5176`

Apply the schema:

```powershell
alembic upgrade head
```

Start the API so other computers on the network can reach it:

```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Interactive API docs: `http://localhost:8000/docs`

### 3. Frontend

```powershell
cd frontend
npm install
copy .env.example .env
npm run dev
```

Open `http://localhost:5176`.

In development the Vite server proxies `/api` to `http://127.0.0.1:8000`, so `frontend\.env` can leave `VITE_API_BASE_URL` empty. Set it only when the API is on another machine, for example:

```text
VITE_API_BASE_URL=http://192.168.1.20:8000/api/v1
```

Restart Vite after changing that file. Other people on the LAN open `http://<this-pc-ip>:5176`. Allow ports **5176** and **8000** in the firewall.

## First use

1. Sign up to create the organization and the first admin account.
2. In **Configuration**, add users. Admins can reset a forgotten password from the lock icon on that user’s row.
3. Design a template under **Reports → Design template** and star the one users should use.
4. Users sign in, open **Reports**, and choose **Generate Report**.

Passwords cannot contain spaces. Names and organization name/code cannot start or end with a space, and cannot contain two spaces in a row.

## Project layout

| Path | Purpose |
| --- | --- |
| `frontend/` | React app |
| `backend/` | FastAPI app, Alembic migrations, tests |
