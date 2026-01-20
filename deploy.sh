#!/bin/bash
set -e

# ==================== MTT Deployment Script ====================
# This script helps deploy the MTT system to a production server
# Run this on your VPS after cloning the repository

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}==================== MTT Deployment Script ====================${NC}"

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo -e "${YELLOW}Warning: Running as root. Consider using a non-root user with sudo.${NC}"
fi

# Check for required tools
check_command() {
    if ! command -v $1 &> /dev/null; then
        echo -e "${RED}Error: $1 is not installed. Please install it first.${NC}"
        exit 1
    fi
}

check_command docker
check_command docker-compose || check_command "docker compose"

# Determine docker compose command
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
else
    DOCKER_COMPOSE="docker compose"
fi

# Check for .env file
if [ ! -f .env ]; then
    echo -e "${YELLOW}No .env file found. Creating from .env.production.example...${NC}"
    if [ -f .env.production.example ]; then
        cp .env.production.example .env
        echo -e "${RED}IMPORTANT: Please edit .env with your production values before continuing!${NC}"
        echo "Required values:"
        echo "  - DOMAIN: Your domain name"
        echo "  - POSTGRES_PASSWORD: Strong database password"
        echo "  - SECRET_KEY: Django secret key"
        echo "  - TELEGRAM_BOT_TOKEN: (if using Telegram bot)"
        exit 1
    else
        echo -e "${RED}Error: .env.production.example not found!${NC}"
        exit 1
    fi
fi

# Load environment variables
source .env

# Verify required variables
if [ -z "$DOMAIN" ] || [ "$DOMAIN" = "your-domain.com" ]; then
    echo -e "${RED}Error: Please set DOMAIN in .env${NC}"
    exit 1
fi

if [ -z "$POSTGRES_PASSWORD" ] || [ "$POSTGRES_PASSWORD" = "GENERATE_A_STRONG_PASSWORD_HERE" ]; then
    echo -e "${RED}Error: Please set POSTGRES_PASSWORD in .env${NC}"
    exit 1
fi

if [ -z "$SECRET_KEY" ] || [ "$SECRET_KEY" = "GENERATE_A_STRONG_SECRET_KEY_HERE" ]; then
    echo -e "${RED}Error: Please set SECRET_KEY in .env${NC}"
    exit 1
fi

# Function to update nginx config with domain
update_nginx_config() {
    echo -e "${GREEN}Updating nginx configuration with domain: $DOMAIN${NC}"
    sed -i "s/YOUR_DOMAIN.com/$DOMAIN/g" nginx/conf.d/default.conf
}

# Function to obtain SSL certificate
obtain_ssl_cert() {
    echo -e "${GREEN}Obtaining SSL certificate for $DOMAIN...${NC}"

    # Create certbot directories
    mkdir -p certbot/conf certbot/www

    # First, start nginx without SSL to get the certificate
    # Create temporary config for initial certificate
    cat > nginx/conf.d/temp.conf << 'EOF'
server {
    listen 80;
    server_name _;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 200 'Waiting for SSL certificate...';
        add_header Content-Type text/plain;
    }
}
EOF

    # Start nginx temporarily
    $DOCKER_COMPOSE -f docker-compose.prod.yml up -d nginx

    # Get certificate
    docker run --rm \
        -v "$(pwd)/certbot/conf:/etc/letsencrypt" \
        -v "$(pwd)/certbot/www:/var/www/certbot" \
        certbot/certbot certonly \
        --webroot \
        --webroot-path=/var/www/certbot \
        --email admin@$DOMAIN \
        --agree-tos \
        --no-eff-email \
        -d $DOMAIN \
        -d www.$DOMAIN

    # Remove temporary config
    rm nginx/conf.d/temp.conf

    # Restart nginx with full config
    $DOCKER_COMPOSE -f docker-compose.prod.yml restart nginx
}

# Main deployment
echo -e "${GREEN}Starting deployment...${NC}"

# Update nginx config
update_nginx_config

# Build and start services
echo -e "${GREEN}Building and starting services...${NC}"
$DOCKER_COMPOSE -f docker-compose.prod.yml build

# Check if SSL certificates exist
if [ ! -d "certbot/conf/live/$DOMAIN" ]; then
    echo -e "${YELLOW}SSL certificates not found. Obtaining new certificates...${NC}"
    obtain_ssl_cert
fi

# Start all services
$DOCKER_COMPOSE -f docker-compose.prod.yml up -d

# Run Django migrations
echo -e "${GREEN}Running database migrations...${NC}"
$DOCKER_COMPOSE -f docker-compose.prod.yml exec backend python manage.py migrate

# Collect static files
echo -e "${GREEN}Collecting static files...${NC}"
$DOCKER_COMPOSE -f docker-compose.prod.yml exec backend python manage.py collectstatic --noinput

# Create admin user if needed
echo -e "${YELLOW}Do you want to create an admin user? (y/n)${NC}"
read -r create_admin
if [ "$create_admin" = "y" ]; then
    $DOCKER_COMPOSE -f docker-compose.prod.yml exec backend python manage.py createsuperuser
fi

echo -e "${GREEN}==================== Deployment Complete! ====================${NC}"
echo ""
echo "Your MTT system is now running at: https://$DOMAIN"
echo ""
echo "Services:"
echo "  - Frontend: https://$DOMAIN"
echo "  - API: https://$DOMAIN/api/"
echo "  - Admin: https://$DOMAIN/admin/"
echo "  - Telegram Mini App: https://$DOMAIN/telegram/"
echo ""
echo "Useful commands:"
echo "  - View logs: $DOCKER_COMPOSE -f docker-compose.prod.yml logs -f"
echo "  - Stop services: $DOCKER_COMPOSE -f docker-compose.prod.yml down"
echo "  - Restart: $DOCKER_COMPOSE -f docker-compose.prod.yml restart"
echo "  - Update: git pull && $DOCKER_COMPOSE -f docker-compose.prod.yml up -d --build"
