#!/bin/bash
set -e

#------------------------------------------------------
# Setup script for target node (Ubuntu 24.04)
# Installs: docker, nginx, mariadb
# Usage: sudo bash setup_target.sh
#------------------------------------------------------

DB_USER="mywebapp"
DB_NAME="notes"
DB_PASSWORD="${DB_PASSWORD:-changeme}"
APP_PORT="8000"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

log "Starting target node setup..."

#------------------------------------------------------
# Install packages
log "Installing packages..."
apt-get update
apt-get install -y \
    docker.io \
    nginx \
    mariadb-server \
    curl \
    wget

#------------------------------------------------------
# Enable and start services
log "Enabling services..."
systemctl enable docker
systemctl start docker
systemctl enable mariadb
systemctl start mariadb
systemctl enable nginx
systemctl start nginx

#------------------------------------------------------
# Setup MariaDB
log "Setting up MariaDB..."
mysql -e "CREATE DATABASE IF NOT EXISTS ${DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
mysql -e "CREATE USER IF NOT EXISTS '${DB_USER}'@'127.0.0.1' IDENTIFIED BY '${DB_PASSWORD}';"
mysql -e "CREATE USER IF NOT EXISTS '${DB_USER}'@'localhost' IDENTIFIED BY '${DB_PASSWORD}';"
mysql -e "GRANT ALL PRIVILEGES ON ${DB_NAME}.* TO '${DB_USER}'@'127.0.0.1';"
mysql -e "GRANT ALL PRIVILEGES ON ${DB_NAME}.* TO '${DB_USER}'@'localhost';"
mysql -e "FLUSH PRIVILEGES;"

#------------------------------------------------------
# Setup nginx
log "Setting up nginx..."
cat > /etc/nginx/sites-available/mywebapp << 'EOF'
server {
    listen 80;
    server_name _;

    access_log /var/log/nginx/mywebapp_access.log;
    error_log /var/log/nginx/mywebapp_error.log;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /notes {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /health {
        return 404;
    }
}
EOF

ln -sf /etc/nginx/sites-available/mywebapp /etc/nginx/sites-enabled/mywebapp
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx

#------------------------------------------------------
# Setup systemd unit for container
log "Setting up systemd unit..."
cat > /etc/systemd/system/mywebapp-container.service << EOF
[Unit]
Description=MyWebApp Container
After=docker.service mariadb.service
Requires=docker.service

[Service]
Restart=always
ExecStartPre=-/usr/bin/docker stop mywebapp-lab3
ExecStartPre=-/usr/bin/docker rm mywebapp-lab3
ExecStart=/usr/bin/docker run --name mywebapp-lab3 \\
  --network host \\
  -e DB_HOST=127.0.0.1 \\
  -e DB_USER=${DB_USER} \\
  -e DB_PASSWORD=${DB_PASSWORD} \\
  -e DB_NAME=${DB_NAME} \\
  ghcr.io/ann0123-cyber/mywebapp:latest
ExecStop=/usr/bin/docker stop mywebapp-lab3

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable mywebapp-container

#------------------------------------------------------
# Setup sudo for deploy user
log "Setting up sudo permissions..."
echo "${SUDO_USER:-anna} ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/deploy-user
chmod 440 /etc/sudoers.d/deploy-user

log "Setup complete!"
log "Run 'sudo systemctl start mywebapp-container' to start the application"
