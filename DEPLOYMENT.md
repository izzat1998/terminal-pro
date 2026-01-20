# MTT Production Deployment Guide

This guide covers deploying the MTT Container Terminal Management System to a production VPS server with SSL.

## Prerequisites

### Server Requirements
- **OS**: Ubuntu 20.04+ or Debian 11+
- **RAM**: Minimum 2GB, recommended 4GB+
- **Disk**: Minimum 20GB SSD
- **CPU**: 2+ cores recommended

### Required Software on Server
- Docker (version 20.10+)
- Docker Compose (version 2.0+)

### Before You Start
1. A registered domain name pointing to your server's IP
2. Email address for SSL certificate registration
3. SSH access to your server

## Quick Deployment

### 1. Install Docker on Ubuntu

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add your user to docker group (logout/login required after)
sudo usermod -aG docker $USER

# Install Docker Compose plugin
sudo apt install docker-compose-plugin -y

# Verify installation
docker --version
docker compose version
```

### 2. Clone and Configure

```bash
# Clone the repository
git clone https://github.com/your-repo/mtt-combined.git
cd mtt-combined

# Create production environment file
cp .env.production.example .env

# Edit the .env file with your values
nano .env
```

### 3. Configure Environment Variables

Edit `.env` with your production values:

```env
# Your domain (without https://)
DOMAIN=mtt.yourdomain.com

# Generate strong password (copy output)
# openssl rand -base64 32
POSTGRES_PASSWORD=your_generated_password

# Generate Django secret key
# python3 -c "import secrets; print(secrets.token_urlsafe(50))"
SECRET_KEY=your_generated_secret_key

# Update allowed hosts and CORS
ALLOWED_HOSTS=mtt.yourdomain.com,www.mtt.yourdomain.com
CORS_ALLOWED_ORIGINS=https://mtt.yourdomain.com,https://www.mtt.yourdomain.com

# Telegram bot token (optional but recommended)
TELEGRAM_BOT_TOKEN=your_bot_token
```

### 4. Update Nginx Configuration

Replace `YOUR_DOMAIN.com` in the nginx config:

```bash
# Replace with your actual domain
sed -i 's/YOUR_DOMAIN.com/mtt.yourdomain.com/g' nginx/conf.d/default.conf
```

### 5. Deploy

```bash
# Run the deployment script
./deploy.sh
```

Or deploy manually:

```bash
# Build all services
docker compose -f docker-compose.prod.yml build

# Start services (without SSL first for certificate)
docker compose -f docker-compose.prod.yml up -d

# Get SSL certificate (first time only)
mkdir -p certbot/conf certbot/www

docker run --rm \
  -v "$(pwd)/certbot/conf:/etc/letsencrypt" \
  -v "$(pwd)/certbot/www:/var/www/certbot" \
  certbot/certbot certonly \
  --webroot \
  --webroot-path=/var/www/certbot \
  --email your-email@domain.com \
  --agree-tos \
  --no-eff-email \
  -d mtt.yourdomain.com

# Restart nginx to load SSL
docker compose -f docker-compose.prod.yml restart nginx

# Run migrations
docker compose -f docker-compose.prod.yml exec backend python manage.py migrate

# Collect static files
docker compose -f docker-compose.prod.yml exec backend python manage.py collectstatic --noinput

# Create admin user
docker compose -f docker-compose.prod.yml exec backend python manage.py createsuperuser
```

## Post-Deployment

### Verify Installation

1. **Frontend**: https://your-domain.com
2. **API Documentation**: https://your-domain.com/api/docs/
3. **Django Admin**: https://your-domain.com/admin/
4. **Telegram Mini App**: https://your-domain.com/telegram/

### Seed Initial Data (Optional)

```bash
# Seed test data
docker compose -f docker-compose.prod.yml exec backend python manage.py seed_data

# Seed file categories
docker compose -f docker-compose.prod.yml exec backend python manage.py seed_file_categories
```

## Maintenance

### View Logs

```bash
# All services
docker compose -f docker-compose.prod.yml logs -f

# Specific service
docker compose -f docker-compose.prod.yml logs -f backend
docker compose -f docker-compose.prod.yml logs -f nginx
```

### Update Application

```bash
# Pull latest code
git pull origin main

# Rebuild and restart
docker compose -f docker-compose.prod.yml up -d --build

# Run migrations if needed
docker compose -f docker-compose.prod.yml exec backend python manage.py migrate
```

### Backup Database

```bash
# Create backup
docker compose -f docker-compose.prod.yml exec db pg_dump -U mtt mtt > backup_$(date +%Y%m%d).sql

# Restore backup
docker compose -f docker-compose.prod.yml exec -T db psql -U mtt mtt < backup_20250120.sql
```

### SSL Certificate Renewal

Certificates auto-renew via the certbot container. To manually renew:

```bash
docker compose -f docker-compose.prod.yml run --rm certbot renew
docker compose -f docker-compose.prod.yml restart nginx
```

### Stop Services

```bash
# Stop all
docker compose -f docker-compose.prod.yml down

# Stop and remove volumes (CAUTION: deletes data)
docker compose -f docker-compose.prod.yml down -v
```

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| 502 Bad Gateway | Check if backend is running: `docker compose -f docker-compose.prod.yml logs backend` |
| SSL certificate error | Ensure domain DNS is pointing to server, then re-run certbot |
| Database connection refused | Wait for db health check, or check `docker compose -f docker-compose.prod.yml logs db` |
| Permission denied | Ensure you're in docker group: `groups` should show `docker` |

### Health Checks

```bash
# Check service status
docker compose -f docker-compose.prod.yml ps

# Test API health
curl -k https://localhost/api/docs/

# Test database connection
docker compose -f docker-compose.prod.yml exec backend python manage.py check
```

## Security Recommendations

1. **Firewall**: Only open ports 80 and 443
   ```bash
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   sudo ufw enable
   ```

2. **Regular Updates**: Keep system and Docker updated
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

3. **Backup Strategy**: Set up automated daily backups

4. **Monitoring**: Consider adding monitoring (Prometheus, Grafana)

5. **Log Rotation**: Docker handles this, but verify with `docker system df`

## Architecture

```
Internet
    │
    ▼
┌─────────────────────────────────────────────────┐
│                 Nginx (Port 80/443)              │
│            SSL Termination & Reverse Proxy       │
└────────┬────────────┬────────────┬──────────────┘
         │            │            │
    ┌────▼────┐  ┌────▼────┐  ┌────▼────┐
    │Frontend │  │ Backend │  │Telegram │
    │  Vue.js │  │ Django  │  │Mini App │
    │  :1001  │  │  :8000  │  │  :1002  │
    └─────────┘  └────┬────┘  └─────────┘
                      │
         ┌────────────┼────────────┐
         │            │            │
    ┌────▼────┐  ┌────▼────┐  ┌────▼────┐
    │PostgreSQL│  │  Redis  │  │ Media/  │
    │   :5432  │  │  :6379  │  │ Static  │
    └──────────┘  └─────────┘  └─────────┘
```

## Support

For issues or questions:
1. Check the logs first
2. Review this guide
3. Open an issue on GitHub
