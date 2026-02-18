---
name: devstart
description: Start all dev servers with health checks and auto-restart on failure. Use when the user says "start dev", "run the project", or "devstart".
---

# Start Development Environment (Self-Healing)

Follow these steps exactly. Do NOT skip health checks.

## Step 1: Check Prerequisites

```bash
# Check venv exists
ls backend/.venv/bin/python 2>/dev/null || echo "MISSING: Run 'make install'"

# Check node_modules
ls frontend/node_modules/.package-lock.json 2>/dev/null || echo "MISSING: Run 'cd frontend && npm ci'"
ls telegram-miniapp/node_modules/.package-lock.json 2>/dev/null || echo "MISSING: Run 'cd telegram-miniapp && npm ci'"
```

If anything is missing, run `make install` first.

## Step 2: Kill Existing Processes on Target Ports

```bash
lsof -ti:8008 | xargs kill -9 2>/dev/null; echo "Port 8008 cleared"
lsof -ti:5174 | xargs kill -9 2>/dev/null; echo "Port 5174 cleared"
lsof -ti:5175 | xargs kill -9 2>/dev/null; echo "Port 5175 cleared"
```

## Step 3: Check for Pending Migrations

```bash
backend/.venv/bin/python backend/manage.py showmigrations --list 2>&1 | grep "\[ \]" | head -5
```

If unapplied migrations exist, run `make migrate` first.

## Step 4: Start All Services

Start each service in background using Bash with `run_in_background`:

1. **Backend:** `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib backend/.venv/bin/python backend/manage.py runserver 0.0.0.0:8008`
2. **Frontend:** `cd frontend && npm run dev`
3. **Telegram Mini App:** `cd telegram-miniapp && npm run dev`

## Step 5: Health Check (wait 8 seconds first)

```bash
sleep 8
echo "Backend:  $(curl -s -o /dev/null -w '%{http_code}' http://localhost:8008/api/ 2>/dev/null || echo 'FAILED')"
echo "Frontend: $(curl -s -o /dev/null -w '%{http_code}' http://localhost:5174/ 2>/dev/null || echo 'FAILED')"
echo "Telegram: $(curl -s -o /dev/null -w '%{http_code}' http://localhost:5175/ 2>/dev/null || echo 'FAILED')"
```

## Step 6: Auto-Fix Failed Services (up to 3 retries)

If any service failed:

1. Read the background task output to see the error
2. **Common fixes:**
   - `ModuleNotFoundError` → `backend/.venv/bin/pip install -r backend/requirements.txt`
   - `No module named 'xxx'` (frontend) → `cd frontend && npm install`
   - Migration error → `make migrate`
   - Address already in use → kill the port (Step 2) and restart
3. Restart ONLY the failed service
4. Health check again after 5 seconds
5. Repeat up to 3 times per service

## Step 7: Report Status

Report final status as a table:

```
Service          Status    URL
─────────────────────────────────────
Backend          ✅/❌     http://localhost:8008/api/
Frontend         ✅/❌     http://localhost:5174/
Telegram MiniApp ✅/❌     http://localhost:5175/
```

If all services are up, say: "All services running. Happy coding!"
If any failed after 3 retries, show the error and suggest manual intervention.
