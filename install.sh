#!/usr/bin/env bash
set -euo pipefail

# --------------------------------------------------------------------------
# Config
# --------------------------------------------------------------------------
APP_DIR="/opt/mywebapp"
APP_USER="app"
DB_NAME="notes"
DB_USER="mywebapp"
DB_PASSWORD="$(openssl rand -base64 16)"
STUDENT_USER="student"
TEACHER_USER="teacher"
OPERATOR_USER="operator"
DEFAULT_PASSWORD="12345678"
GRADEBOOK_N="18"

log() { echo "[install] $*"; }

# --------------------------------------------------------------------------
# 1. Пакети
# --------------------------------------------------------------------------
log "=== 1. Встановлення пакетів ==="
apt-get update -q
apt-get install -y -q \
    python3 python3-pip python3-venv \
    mariadb-server \
    nginx \
    curl \
    openssl

# --------------------------------------------------------------------------
# 2. Користувачі
# --------------------------------------------------------------------------
log "=== 2. Створення користувачів ==="

# student — адмін
if ! id "$STUDENT_USER" &>/dev/null; then
    useradd -m -s /bin/bash "$STUDENT_USER"
    usermod -aG sudo "$STUDENT_USER"
    echo "$STUDENT_USER:$DEFAULT_PASSWORD" | chpasswd
    log "Створено користувача $STUDENT_USER (пароль: $DEFAULT_PASSWORD)"
fi

# teacher — адмін, зміна пароля при першому вході
if ! id "$TEACHER_USER" &>/dev/null; then
    useradd -m -s /bin/bash "$TEACHER_USER"
    usermod -aG sudo "$TEACHER_USER"
    echo "$TEACHER_USER:$DEFAULT_PASSWORD" | chpasswd
    chage -d 0 "$TEACHER_USER"   # примусова зміна пароля
    log "Створено користувача $TEACHER_USER (пароль: $DEFAULT_PASSWORD)"
fi

# operator — обмежений sudo
if ! id "$OPERATOR_USER" &>/dev/null; then
    useradd -m -s /bin/bash "$OPERATOR_USER"
    echo "$OPERATOR_USER:$DEFAULT_PASSWORD" | chpasswd
    chage -d 0 "$OPERATOR_USER"
    log "Створено користувача $OPERATOR_USER (пароль: $DEFAULT_PASSWORD)"
fi

# Судоправила для operator
cat > /etc/sudoers.d/operator << 'EOF'
operator ALL=(root) NOPASSWD: \
    /usr/bin/systemctl start mywebapp, \
    /usr/bin/systemctl stop mywebapp, \
    /usr/bin/systemctl restart mywebapp, \
    /usr/bin/systemctl status mywebapp, \
    /usr/bin/systemctl reload nginx
EOF
chmod 440 /etc/sudoers.d/operator

# app — системний користувач для запуску сервісу
if ! id "$APP_USER" &>/dev/null; then
    useradd -r -s /sbin/nologin "$APP_USER"
    log "Створено системного користувача $APP_USER"
fi

# --------------------------------------------------------------------------
# 3. База даних
# --------------------------------------------------------------------------
log "=== 3. Налаштування MariaDB ==="
systemctl enable mariadb
systemctl start mariadb

mysql -e "CREATE DATABASE IF NOT EXISTS \`$DB_NAME\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
mysql -e "CREATE USER IF NOT EXISTS '$DB_USER'@'127.0.0.1' IDENTIFIED BY '$DB_PASSWORD';"
mysql -e "GRANT ALL PRIVILEGES ON \`$DB_NAME\`.* TO '$DB_USER'@'127.0.0.1';"
mysql -e "FLUSH PRIVILEGES;"
log "БД '$DB_NAME' і користувач '$DB_USER' готові"

# --------------------------------------------------------------------------
# 4. Копіювання файлів застосунку
# --------------------------------------------------------------------------
log "=== 4. Розгортання застосунку ==="
mkdir -p "$APP_DIR"
cp app.py migrate.py requirements.txt "$APP_DIR/"

# Virtualenv
python3 -m venv "$APP_DIR/venv"
"$APP_DIR/venv/bin/pip" install -q --upgrade pip
"$APP_DIR/venv/bin/pip" install -q -r "$APP_DIR/requirements.txt"

chown -R "$APP_USER:$APP_USER" "$APP_DIR"

# --------------------------------------------------------------------------
# 5. Systemd сервіс
# --------------------------------------------------------------------------
log "=== 5. Systemd ==="

# Підставляємо пароль у unit-файл
sed "s/CHANGE_ME/$DB_PASSWORD/g" mywebapp.service > /etc/systemd/system/mywebapp.service
cp mywebapp.socket /etc/systemd/system/mywebapp.socket

systemctl daemon-reload
systemctl enable mywebapp.socket
log "Systemd unit встановлено"

# --------------------------------------------------------------------------
# 6. Запуск (через socket activation)
# --------------------------------------------------------------------------
log "=== 6. Запуск сервісу ==="
systemctl start mywebapp.socket
# Перший запит активує сервіс
sleep 1
curl -s http://127.0.0.1:8000/health/alive || true

# --------------------------------------------------------------------------
# 7. Nginx
# --------------------------------------------------------------------------
log "=== 7. Nginx ==="
cp nginx.conf /etc/nginx/sites-available/mywebapp
ln -sf /etc/nginx/sites-available/mywebapp /etc/nginx/sites-enabled/mywebapp
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl enable nginx
systemctl restart nginx

# --------------------------------------------------------------------------
# 8. Gradebook
# --------------------------------------------------------------------------
log "=== 8. Gradebook ==="
echo "$GRADEBOOK_N" > /home/$STUDENT_USER/gradebook
chown $STUDENT_USER:$STUDENT_USER /home/$STUDENT_USER/gradebook

# --------------------------------------------------------------------------
# 9. Блокування дефолтного користувача
# --------------------------------------------------------------------------
log "=== 9. Блокування дефолтного юзера ==="
# Знаходимо користувача, який не є student/teacher/operator/root/app
DEFAULT_LOGIN=$(awk -F: '$3 >= 1000 && $3 < 65534 {print $1}' /etc/passwd \
    | grep -vE "^(student|teacher|operator)$" | head -1 || true)
if [ -n "$DEFAULT_LOGIN" ]; then
    passwd -l "$DEFAULT_LOGIN"
    log "Заблоковано дефолтного користувача: $DEFAULT_LOGIN"
fi

# --------------------------------------------------------------------------
# Готово
# --------------------------------------------------------------------------
log ""
log "============================================"
log " Розгортання завершено успішно!"
log " Перевірка: curl http://localhost/notes"
log " БД пароль збережено у: /opt/mywebapp/.dbpass"
log "============================================"
echo "$DB_PASSWORD" > /opt/mywebapp/.dbpass
chmod 600 /opt/mywebapp/.dbpass
chown root:root /opt/mywebapp/.dbpass