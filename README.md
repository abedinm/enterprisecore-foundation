# EnterpriseCore AI Suite

Full-stack enterprise SaaS foundation. FastAPI backend + React/Tailwind frontend + SQLite.

## Quick start

```powershell
# Backend
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python run.py
# → http://127.0.0.1:8000  (API docs at /api/docs)

# Frontend (new terminal)
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

Default admin: **admin@enterprisecore.io / Admin123!**

## What's in here

- **JWT auth** with access + refresh tokens, server-side refresh revocation, logout-all
- **RBAC** with four roles: Admin, Manager, Employee, Developer
- **SQLite + SQLAlchemy 2.0** ORM with 10 tables: users, refresh_tokens, notifications, user_settings, system_settings, audit_logs, departments, projects, tasks, api_keys
- **Modules**: users, projects, tasks, notifications, departments, audit log, settings
- **Dashboard** with live stats (users by role, task completion, unread notifs)
- **Theme**: light / dark / system, persisted, no FOUC
- **Notifications**: bell dropdown + dedicated page, mark/delete, admin broadcast
- **Audit log**: every privileged action is logged

## Structure

```
EnterpriseCore/
├── backend/           FastAPI + SQLAlchemy 2.0 + JWT
│   ├── app/
│   │   ├── api/routes/    9 route modules
│   │   ├── core/          security, permissions, audit, notifications
│   │   ├── models/        10 ORM models
│   │   ├── schemas/       Pydantic request/response models
│   │   ├── services/      Bootstrap / seeding
│   │   ├── config.py      Pydantic Settings
│   │   ├── database.py    Engine + session + Base
│   │   └── main.py        App factory + lifespan
│   └── requirements.txt
└── frontend/          React 18 + Vite + Tailwind + Zustand
    └── src/
        ├── api/           Axios with auto-refresh
        ├── components/    UI primitives + layout
        ├── pages/         Dashboard, Settings, Users, etc.
        ├── store/         auth / theme / notifications
        └── App.tsx
```
