# MTT Server Deployment Guide

Complete step-by-step guide to deploy the MTT Container Terminal Management System on a production server.

---

## Table of Contents

1. [Server Requirements](#1-server-requirements)
2. [Initial Server Setup](#2-initial-server-setup)
3. [Install Docker](#3-install-docker)
4. [Clone the Project](#4-clone-the-project)
5. [Configure Environment](#5-configure-environment)
6. [Configure Domain & SSL](#6-configure-domain--ssl)
7. [Deploy the Application](#7-deploy-the-application)
8. [Post-Deployment Setup](#8-post-deployment-setup)
9. [Maintenance & Operations](#9-maintenance--operations)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. Server Requirements

### Minimum Hardware
| Resource | Minimum | Recommended |
|----------|---------|-------------|
| CPU | 2 cores | 4 cores |
| RAM | 2 GB | 4 GB |
| Storage | 20 GB SSD | 50 GB SSD |
| Bandwidth | 1 TB/month | Unlimited |

### Supported Operating Systems
- Ubuntu 20.04 LTS or newer (recommended)
- Debian 11 or newer
- CentOS 8 / Rocky Linux 8

### Required Ports
| Port | Service | Required |
|------|---------|----------|
| 22 | SSH | Yes |
| 80 | HTTP | Yes (for SSL certificate) |
| 443 | HTTPS | Yes |

### Before You Start
You need:
- [ ] A VPS/server with SSH access
- [ ] A domain name (e.g., `mtt.yourdomain.com`)
- [ ] Domain DNS pointing to your server IP
- [ ] Telegram Bot Token (if using Telegram features)

---

## 2. Initial Server Setup

### 2.1 Connect to Your Server

```bash
ssh root@your-server-ip
# Or with a specific user
ssh username@your-server-ip
```

### 2.2 Update System

```bash
# Ubuntu/Debian
sudo apt update && sudo apt upgrade -y

# Install essential tools
sudo apt install -y curl git wget nano ufw
```

### 2.3 Create a Deploy User (Recommended)

Running as root is not recommended. Create a dedicated user:

```bash
# Create user
sudo adduser deploy

# Add to sudo group
sudo usermod -aG sudo deploy

# Switch to new user
su - deploy
```

### 2.4 Configure Firewall

```bash
# Allow SSH
sudo ufw allow 22/tcp

# Allow HTTP and HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Enable firewall
sudo ufw enable

# Check status
sudo ufw status
```

Expected output:
```
Status: active

To                         Action      From
--                         ------      ----
22/tcp                     ALLOW       Anywhere
80/tcp                     ALLOW       Anywhere
443/tcp                    ALLOW       Anywhere
```

---

## 3. Install Docker

### 3.1 Install Docker Engine

```bash
# Download and run Docker install script
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add your user to docker group (so you don't need sudo)
sudo usermod -aG docker $USER

# Apply group changes (or logout and login)
newgrp docker

# Verify installation
docker --version
```

Expected output: `Docker version 24.x.x` or newer

### 3.2 Install Docker Compose

Docker Compose is included with Docker Desktop, but on Linux servers:

```bash
# Install Docker Compose plugin
sudo apt install docker-compose-plugin -y

# Verify installation
docker compose version
```

Expected output: `Docker Compose version v2.x.x`

### 3.3 Verify Docker Works

```bash
# Run test container
docker run hello-world
```

If you see "Hello from Docker!", Docker is working correctly.

---

## 4. Clone the Project

### 4.1 Clone Repository

```bash
# Go to home directory
cd ~

# Clone the repository
git clone https://github.com/izzat1998/terminal-pro.git mtt-combined

# Enter project directory
cd mtt-combined
```

### 4.2 Verify Project Structure

```bash
ls -la
```

You should see:
```
├── backend/
├── frontend/
├── telegram-miniapp/
├── docker-compose.yml
├── docker-compose.prod.yml
├── deploy.sh
├── nginx/
├── .env.production.example
└── ...
```

---

## 5. Configure Environment

### 5.1 Create Environment File

```bash
# Copy the example file
cp .env.production.example .env

# Edit the file
nano .env
```

### 5.2 Configure Required Variables

```env
# ==================== Domain Configuration ====================
# Your domain name (without https://)
DOMAIN=mtt.yourdomain.com

# ==================== Database ====================
POSTGRES_DB=mtt
POSTGRES_USER=mtt
# Generate a strong password (run this command and copy output):
# openssl rand -base64 32
POSTGRES_PASSWORD=YOUR_STRONG_PASSWORD_HERE

# ==================== Django Backend ====================
DEBUG=False

# Generate a secret key (run this command and copy output):
# python3 -c "import secrets; print(secrets.token_urlsafe(50))"
SECRET_KEY=YOUR_SECRET_KEY_HERE

# Allowed hosts (your domain)
ALLOWED_HOSTS=mtt.yourdomain.com,www.mtt.yourdomain.com

# CORS origins (with https://)
CORS_ALLOWED_ORIGINS=https://mtt.yourdomain.com,https://www.mtt.yourdomain.com

# ==================== Frontend ====================
# API URL as seen by browser (through nginx)
VITE_API_BASE_URL=/api

# ==================== Telegram Bot (Optional) ====================
TELEGRAM_BOT_TOKEN=your-telegram-bot-token

# ==================== External APIs (Optional) ====================
PLATE_RECOGNIZER_API_KEY=your-api-key
```

### 5.3 Generate Secure Passwords

Run these commands to generate secure values:

```bash
# Generate database password
echo "POSTGRES_PASSWORD: $(openssl rand -base64 32)"

# Generate Django secret key
echo "SECRET_KEY: $(openssl rand -base64 50)"
```

Copy these values into your `.env` file.

### 5.4 Verify Configuration

```bash
# Check that .env exists and has content
cat .env | grep -E "^[A-Z]" | head -10
```

---

## 6. Configure Domain & SSL

### 6.1 Update Nginx Configuration

Replace the placeholder domain in nginx config:

```bash
# Replace YOUR_DOMAIN.com with your actual domain
sed -i 's/YOUR_DOMAIN.com/mtt.yourdomain.com/g' nginx/conf.d/default.conf

# Verify the change
grep "server_name" nginx/conf.d/default.conf
```

### 6.2 Verify DNS

Before proceeding, verify your domain points to the server:

```bash
# Check DNS resolution
dig +short mtt.yourdomain.com

# Should return your server's IP address
```

If it doesn't return your server IP, wait for DNS propagation (can take up to 48 hours, usually 15-30 minutes).

---

## 7. Deploy the Application

### 7.1 Option A: Use the Deploy Script (Recommended)

```bash
# Make script executable
chmod +x deploy.sh

# Run deployment
./deploy.sh
```

The script will:
1. Validate your `.env` configuration
2. Build all Docker images
3. Obtain SSL certificate from Let's Encrypt
4. Start all services
5. Run database migrations
6. Collect static files

### 7.2 Option B: Manual Deployment

If you prefer manual control:

```bash
# Step 1: Build all images
docker compose -f docker-compose.prod.yml build

# Step 2: Create directories for SSL
mkdir -p certbot/conf certbot/www

# Step 3: Start services (without SSL first)
docker compose -f docker-compose.prod.yml up -d db redis

# Wait for database to be ready
sleep 10

# Step 4: Start backend
docker compose -f docker-compose.prod.yml up -d backend

# Step 5: Obtain SSL certificate
docker run --rm \
  -v "$(pwd)/certbot/conf:/etc/letsencrypt" \
  -v "$(pwd)/certbot/www:/var/www/certbot" \
  certbot/certbot certonly \
  --webroot \
  --webroot-path=/var/www/certbot \
  --email admin@yourdomain.com \
  --agree-tos \
  --no-eff-email \
  -d mtt.yourdomain.com

# Step 6: Start all remaining services
docker compose -f docker-compose.prod.yml up -d

# Step 7: Run migrations
docker compose -f docker-compose.prod.yml exec backend python manage.py migrate

# Step 8: Collect static files
docker compose -f docker-compose.prod.yml exec backend python manage.py collectstatic --noinput
```

### 7.3 Verify Deployment

```bash
# Check all services are running
docker compose -f docker-compose.prod.yml ps
```

Expected output:
```
NAME                IMAGE                  STATUS
mtt-db              postgres:15-alpine     Up (healthy)
mtt-redis           redis:7-alpine         Up (healthy)
mtt-backend         mtt-combined-backend   Up
mtt-frontend        mtt-combined-frontend  Up
mtt-telegram-miniapp mtt-combined-telegram  Up
mtt-nginx           nginx:alpine           Up
mtt-certbot         certbot/certbot        Up
```

---

## 8. Post-Deployment Setup

### 8.1 Create Admin User

```bash
docker compose -f docker-compose.prod.yml exec backend python manage.py createsuperuser
```

Follow the prompts:
- Username: `admin`
- Email: `admin@yourdomain.com`
- Password: (enter a strong password)

### 8.2 Seed Initial Data (Optional)

```bash
# Seed destinations for vehicles
docker compose -f docker-compose.prod.yml exec backend python manage.py seed_destinations

# Seed file categories
docker compose -f docker-compose.prod.yml exec backend python manage.py seed_file_categories

# Seed expense types for billing
docker compose -f docker-compose.prod.yml exec backend python manage.py seed_expense_types
```

### 8.3 Test the Application

Open your browser and visit:

| URL | Description |
|-----|-------------|
| `https://mtt.yourdomain.com` | Main frontend |
| `https://mtt.yourdomain.com/admin/` | Django admin panel |
| `https://mtt.yourdomain.com/api/docs/` | API documentation |
| `https://mtt.yourdomain.com/telegram/` | Telegram Mini App |

### 8.4 Configure Telegram Bot Webhook (If Using Telegram)

```bash
# Set webhook URL
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://mtt.yourdomain.com/api/telegram/webhook/"}'
```

---

## 9. Maintenance & Operations

### 9.1 View Logs

```bash
# All services
docker compose -f docker-compose.prod.yml logs -f

# Specific service
docker compose -f docker-compose.prod.yml logs -f backend
docker compose -f docker-compose.prod.yml logs -f nginx

# Last 100 lines
docker compose -f docker-compose.prod.yml logs --tail=100 backend
```

### 9.2 Restart Services

```bash
# Restart all
docker compose -f docker-compose.prod.yml restart

# Restart specific service
docker compose -f docker-compose.prod.yml restart backend
docker compose -f docker-compose.prod.yml restart nginx
```

### 9.3 Update Application

```bash
# Pull latest code
git pull origin main

# Rebuild and restart (zero-downtime for frontend)
docker compose -f docker-compose.prod.yml up -d --build

# Run migrations if needed
docker compose -f docker-compose.prod.yml exec backend python manage.py migrate

# Collect static files if changed
docker compose -f docker-compose.prod.yml exec backend python manage.py collectstatic --noinput
```

### 9.4 Database Backup

```bash
# Create backup
docker compose -f docker-compose.prod.yml exec db \
  pg_dump -U mtt mtt > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore backup
docker compose -f docker-compose.prod.yml exec -T db \
  psql -U mtt mtt < backup_20250120_120000.sql
```

### 9.5 Automated Backup Script

Create `/home/deploy/backup.sh`:

```bash
#!/bin/bash
BACKUP_DIR="/home/deploy/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup database
cd /home/deploy/mtt-combined
docker compose -f docker-compose.prod.yml exec -T db \
  pg_dump -U mtt mtt > $BACKUP_DIR/db_$DATE.sql

# Keep only last 7 days of backups
find $BACKUP_DIR -name "db_*.sql" -mtime +7 -delete

echo "Backup completed: $BACKUP_DIR/db_$DATE.sql"
```

Add to crontab for daily backups:
```bash
chmod +x /home/deploy/backup.sh
crontab -e
# Add this line for daily backup at 2 AM:
0 2 * * * /home/deploy/backup.sh >> /home/deploy/backup.log 2>&1
```

### 9.6 SSL Certificate Renewal

Certificates auto-renew via the certbot container. To manually renew:

```bash
docker compose -f docker-compose.prod.yml run --rm certbot renew
docker compose -f docker-compose.prod.yml restart nginx
```

### 9.7 Monitor Disk Space

```bash
# Check disk usage
df -h

# Check Docker disk usage
docker system df

# Clean unused Docker resources
docker system prune -a --volumes
```

---

## 10. Troubleshooting

### 10.1 Common Issues

#### Service won't start
```bash
# Check logs for errors
docker compose -f docker-compose.prod.yml logs backend

# Check if port is already in use
sudo netstat -tlnp | grep :80
sudo netstat -tlnp | grep :443
```

#### Database connection error
```bash
# Check if database is healthy
docker compose -f docker-compose.prod.yml ps db

# Check database logs
docker compose -f docker-compose.prod.yml logs db

# Try to connect manually
docker compose -f docker-compose.prod.yml exec db psql -U mtt mtt
```

#### 502 Bad Gateway
```bash
# Backend might not be running
docker compose -f docker-compose.prod.yml ps backend
docker compose -f docker-compose.prod.yml logs backend

# Restart backend
docker compose -f docker-compose.prod.yml restart backend
```

#### SSL Certificate Error
```bash
# Check certificate status
sudo ls -la certbot/conf/live/

# Re-obtain certificate
docker run --rm \
  -v "$(pwd)/certbot/conf:/etc/letsencrypt" \
  -v "$(pwd)/certbot/www:/var/www/certbot" \
  certbot/certbot certonly \
  --webroot \
  --webroot-path=/var/www/certbot \
  --email admin@yourdomain.com \
  --agree-tos \
  --force-renewal \
  -d mtt.yourdomain.com
```

#### Frontend shows old version
```bash
# Rebuild frontend with cache bust
docker compose -f docker-compose.prod.yml build --no-cache frontend
docker compose -f docker-compose.prod.yml up -d frontend
```

### 10.2 Useful Commands

```bash
# Enter backend container shell
docker compose -f docker-compose.prod.yml exec backend bash

# Run Django management commands
docker compose -f docker-compose.prod.yml exec backend python manage.py shell
docker compose -f docker-compose.prod.yml exec backend python manage.py dbshell

# Check nginx configuration
docker compose -f docker-compose.prod.yml exec nginx nginx -t

# View real-time resource usage
docker stats
```

### 10.3 Emergency Stop

```bash
# Stop all services
docker compose -f docker-compose.prod.yml down

# Stop and remove volumes (WARNING: deletes all data!)
docker compose -f docker-compose.prod.yml down -v
```

---

## Architecture Diagram

```
                                    INTERNET
                                        │
                                        ▼
                            ┌───────────────────────┐
                            │   YOUR DOMAIN DNS     │
                            │ mtt.yourdomain.com    │
                            └───────────┬───────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              YOUR VPS SERVER                                 │
│                                                                             │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                         DOCKER NETWORK                                  │ │
│  │                                                                        │ │
│  │   ┌─────────────────────────────────────────────────────────────────┐  │ │
│  │   │                    NGINX (Port 80, 443)                         │  │ │
│  │   │              SSL Termination & Reverse Proxy                    │  │ │
│  │   │                                                                 │  │ │
│  │   │  /api/*  ──────────────────► Backend (8000)                    │  │ │
│  │   │  /admin/* ─────────────────► Backend (8000)                    │  │ │
│  │   │  /static/* ────────────────► Static Files Volume               │  │ │
│  │   │  /media/* ─────────────────► Media Files Volume                │  │ │
│  │   │  /telegram/* ──────────────► Telegram Mini App (1002)          │  │ │
│  │   │  /* ───────────────────────► Frontend (1001)                   │  │ │
│  │   └─────────────────────────────────────────────────────────────────┘  │ │
│  │                                    │                                    │ │
│  │          ┌─────────────────────────┼─────────────────────────┐          │ │
│  │          │                         │                         │          │ │
│  │          ▼                         ▼                         ▼          │ │
│  │   ┌─────────────┐          ┌─────────────┐          ┌─────────────┐     │ │
│  │   │  Frontend   │          │   Backend   │          │  Telegram   │     │ │
│  │   │   Vue.js    │          │   Django    │          │  Mini App   │     │ │
│  │   │  Port 1001  │          │  Port 8000  │          │  Port 1002  │     │ │
│  │   └─────────────┘          └──────┬──────┘          └─────────────┘     │ │
│  │                                   │                                     │ │
│  │                    ┌──────────────┼──────────────┐                      │ │
│  │                    │              │              │                      │ │
│  │                    ▼              ▼              ▼                      │ │
│  │             ┌───────────┐  ┌───────────┐  ┌───────────┐                 │ │
│  │             │ PostgreSQL│  │   Redis   │  │  Volumes  │                 │ │
│  │             │ Port 5432 │  │ Port 6379 │  │  (Data)   │                 │ │
│  │             └───────────┘  └───────────┘  └───────────┘                 │ │
│  │                                                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Quick Reference Card

### Essential Commands

| Task | Command |
|------|---------|
| Start all | `docker compose -f docker-compose.prod.yml up -d` |
| Stop all | `docker compose -f docker-compose.prod.yml down` |
| View logs | `docker compose -f docker-compose.prod.yml logs -f` |
| Restart | `docker compose -f docker-compose.prod.yml restart` |
| Update | `git pull && docker compose -f docker-compose.prod.yml up -d --build` |
| Migrate | `docker compose -f docker-compose.prod.yml exec backend python manage.py migrate` |
| Shell | `docker compose -f docker-compose.prod.yml exec backend bash` |
| Backup DB | `docker compose -f docker-compose.prod.yml exec db pg_dump -U mtt mtt > backup.sql` |

### Service URLs

| Service | URL |
|---------|-----|
| Frontend | https://mtt.yourdomain.com |
| Admin | https://mtt.yourdomain.com/admin/ |
| API Docs | https://mtt.yourdomain.com/api/docs/ |
| Telegram App | https://mtt.yourdomain.com/telegram/ |

---

## Support

If you encounter issues:
1. Check the logs: `docker compose -f docker-compose.prod.yml logs`
2. Verify configuration: `cat .env`
3. Check service status: `docker compose -f docker-compose.prod.yml ps`
4. Review this guide's troubleshooting section

---

*Last updated: January 2026*
