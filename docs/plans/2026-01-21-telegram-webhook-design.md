# Telegram Bot Webhook Mode Design

**Date:** 2026-01-21
**Status:** Implemented
**Author:** Claude Code + User collaboration

## Overview

Implement webhook mode for the Telegram bot to replace polling in production. This provides lower latency, better efficiency, and proper production-grade deployment.

## Current Production Setup

| Component | Configuration |
|-----------|---------------|
| **API Domain** | `mtt-pro-api.xlog.uz` |
| **Frontend Domain** | `mtt-pro.xlog.uz` |
| **Backend** | Gunicorn + Unix socket (`/run/mtt-terminal.sock`) |
| **Systemd** | `mtt-terminal.service` + `mtt-terminal.socket` |
| **Nginx** | Port 80 (Cloudflare handles SSL) |
| **.env location** | `/var/www/terminal-pro/backend/.env` |

## Architecture

```
Telegram API
     │
     │ X-Telegram-Bot-Api-Secret-Token: <secret>
     ▼
┌─────────────┐
│ Cloudflare  │  ← SSL termination, DDoS protection
└──────┬──────┘
       ▼
┌─────────────┐
│   Nginx     │  ← proxy_buffering off
└──────┬──────┘
       │
       ├── /api/*        → Django (gunicorn, unix socket)
       ├── /bot/webhook/ → Bot (aiohttp:8001) ← Secret verified
       └── /bot/health   → Bot (aiohttp:8001) ← Health check
```

### Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Separate server vs Django ASGI | Separate aiohttp | No changes to Django, native aiogram support |
| Security | Secret token header | Cloudflare hides Telegram IPs, token is sufficient |
| Port | 8001 | Adjacent to Django, internal only |
| Dev mode | Keep polling | No public URL needed locally |

## Files Created

### 1. `backend/telegram_bot/webhook.py`

Main webhook server using aiogram's `SimpleRequestHandler`.

- Django setup before imports
- Bot + Dispatcher with Redis storage
- All existing handlers registered (same as polling mode)
- SimpleRequestHandler with secret_token verification
- Health check endpoints
- Startup: register webhook with Telegram
- Shutdown: cleanup connections

### 2. `backend/telegram_bot/health.py`

Health check endpoints for monitoring:

- `GET /bot/health` - Basic liveness check (always 200 if running)
- `GET /bot/ready` - Readiness check (verifies Redis + Django DB)

### 3. `backend/apps/core/management/commands/run_telegram_webhook.py`

Django management command to start webhook server:

```bash
python manage.py run_telegram_webhook
python manage.py run_telegram_webhook --port 8002  # Custom port
```

## Files Modified

### 1. `backend/terminal_app/settings.py`

Added webhook configuration:

```python
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_BOT_MODE = os.getenv("TELEGRAM_BOT_MODE", "polling")

# Webhook mode settings
TELEGRAM_WEBHOOK_URL = os.getenv("TELEGRAM_WEBHOOK_URL", "")
TELEGRAM_WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")
TELEGRAM_WEBHOOK_PORT = int(os.getenv("TELEGRAM_WEBHOOK_PORT", "8001"))
```

### 2. `.env.example`

Documented new variables for webhook mode.

## Deployment Configuration

### Environment Variables

Add to `/var/www/terminal-pro/backend/.env`:

```env
# Telegram Bot
TELEGRAM_BOT_TOKEN=your-bot-token-from-botfather
TELEGRAM_BOT_MODE=webhook
TELEGRAM_WEBHOOK_URL=https://mtt-pro-api.xlog.uz/bot/webhook/
TELEGRAM_WEBHOOK_SECRET=generate-random-32-char-string-here
TELEGRAM_WEBHOOK_PORT=8001
```

Generate secret with:
```bash
openssl rand -hex 32
```

### Nginx Configuration

Add to `/etc/nginx/sites-available/mtt-pro-api`:

```nginx
# MTT Pro API Backend
server {
    listen 80;
    server_name mtt-pro-api.xlog.uz;

    # ... existing config (static, media, etc.) ...

    # === Telegram Bot Webhook ===
    location /bot/ {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_buffering off;
        proxy_read_timeout 60s;
    }

    # API and Admin (existing)
    location / {
        include proxy_params;
        proxy_pass http://unix:/run/mtt-terminal.sock;
        proxy_connect_timeout 60s;
        proxy_read_timeout 60s;
    }

    # ... rest of existing config ...
}
```

After editing:
```bash
sudo nginx -t && sudo systemctl reload nginx
```

### Systemd Service

Create `/etc/systemd/system/mtt-telegram-bot.service`:

```ini
[Unit]
Description=MTT Telegram Bot Webhook
After=network.target postgresql.service redis.service mtt-terminal.service

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/var/www/terminal-pro/backend
Environment="PATH=/var/www/terminal-pro/backend/.venv/bin"
ExecStart=/var/www/terminal-pro/backend/.venv/bin/python manage.py run_telegram_webhook
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable mtt-telegram-bot
sudo systemctl start mtt-telegram-bot
```

## Deployment Checklist

- [x] Create `backend/telegram_bot/webhook.py`
- [x] Create `backend/telegram_bot/health.py`
- [x] Create `backend/apps/core/management/commands/run_telegram_webhook.py`
- [x] Update `backend/terminal_app/settings.py` with webhook config
- [x] Update `.env.example` with new variables
- [ ] Add webhook settings to production `.env`
- [ ] Update nginx config with `/bot/` location
- [ ] Reload nginx
- [ ] Create systemd service file
- [ ] Enable and start bot service
- [ ] Verify webhook registration with Telegram

## Testing

### Local Test (before deploying)

```bash
cd /var/www/terminal-pro/backend
source .venv/bin/activate

# Test that webhook.py has no syntax errors
python -c "from telegram_bot.webhook import main; print('OK')"

# Test health module
python -c "from telegram_bot.health import health_check; print('OK')"
```

### Production Test

```bash
# Check service status
sudo systemctl status mtt-telegram-bot

# Test health endpoint locally
curl http://127.0.0.1:8001/bot/health

# Test via nginx
curl https://mtt-pro-api.xlog.uz/bot/health

# Verify webhook registered with Telegram
curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"
```

### Expected Webhook Info Response

```json
{
  "ok": true,
  "result": {
    "url": "https://mtt-pro-api.xlog.uz/bot/webhook/",
    "has_custom_certificate": false,
    "pending_update_count": 0,
    "last_error_date": null,
    "last_error_message": null,
    "max_connections": 40
  }
}
```

## Development Workflow

### Local Development (Polling)

```bash
cd /var/www/terminal-pro/backend
source .venv/bin/activate
export TELEGRAM_BOT_MODE=polling
python manage.py run_telegram_bot
```

### Production (Webhook)

```bash
# Service managed by systemd
sudo systemctl start mtt-telegram-bot
sudo systemctl stop mtt-telegram-bot
sudo systemctl restart mtt-telegram-bot

# View logs
sudo journalctl -u mtt-telegram-bot -f
```

## Rollback Plan

If webhook mode fails:

1. Stop webhook service:
   ```bash
   sudo systemctl stop mtt-telegram-bot
   ```

2. Delete webhook from Telegram:
   ```bash
   curl "https://api.telegram.org/bot<TOKEN>/deleteWebhook"
   ```

3. Start polling mode temporarily:
   ```bash
   cd /var/www/terminal-pro/backend
   source .venv/bin/activate
   python manage.py run_telegram_bot
   ```

## Security Considerations

1. **Secret Token**: Random 32+ character string verified on every request
2. **No IP Filtering**: Cloudflare proxy hides origin IPs; secret token is sufficient
3. **Internal Port**: Port 8001 not exposed externally, only via nginx
4. **Cloudflare**: Provides DDoS protection and SSL termination
5. **drop_pending_updates**: Ignores old messages on restart (no replay attacks)

## References

- [aiogram Webhook Documentation](https://docs.aiogram.dev/en/latest/dispatcher/webhook.html)
- [Telegram Bot API - setWebhook](https://core.telegram.org/bots/api#setwebhook)
