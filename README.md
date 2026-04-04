# Notes Service — mywebapp

## Варіант завдання

| Параметр | Розрахунок | Значення |
|---|---|---|
| N | порядковий номер у списку | **18** |
| V₂ = (N % 2) + 1 | (18 % 2) + 1 = 1 | Конфігурація: **аргументи командного рядка**, БД: **MariaDB** |
| V₃ = (N % 3) + 1 | (18 % 3) + 1 = 1 | Застосунок: **Notes Service** |
| V₅ = (N % 5) + 1 | (18 % 5) + 1 = 4 | Порт застосунку: **8000** |

## Опис застосунку

Notes Service — простий REST-сервіс для зберігання текстових нотаток.

Кожна нотатка містить поля: `id`, `title`, `content`, `created_at`.

API підтримує два формати відповіді залежно від заголовку `Accept`:
- `Accept: text/html` — повертає просту HTML-сторінку з таблицею (без JS, без стилів)
- `Accept: application/json` — повертає дані у форматі JSON
- Якщо заголовок `Accept` не вказано — повертає HTML

Застосунок реалізовано на **Python + FastAPI**, запускається через **uvicorn** поверх Unix-сокету `/run/mywebapp.sock`.

### Структура проєкту

```
mywebapp/
├── app.py              # FastAPI застосунок
├── migrate.py          # Скрипт міграції БД
├── requirements.txt    # Python залежності
├── mywebapp.service    # Systemd unit-файл
├── mywebapp.socket     # Systemd socket (socket activation)
├── nginx.conf          # Конфігурація Nginx
├── install.sh          # Скрипт автоматичного розгортання
└── README.md
```

---

## API — документація по ендпоінтах

### Бізнес-логіка

#### `GET /notes`
Повертає список усіх нотаток (тільки `id` і `title`).

**JSON:**
```json
[
  {"id": 1, "title": "Перший запис"},
  {"id": 2, "title": "Нова нотатка"}
]
```

**HTML:** таблиця з колонками ID та Заголовок.

---

#### `POST /notes`
Створює нову нотатку. Приймає JSON або form data.

**Тіло запиту:**
```json
{"title": "Заголовок", "content": "Текст нотатки"}
```

**Відповідь (201):**
```json
{"id": 3, "title": "Заголовок"}
```

---

#### `GET /notes/{id}`
Повертає повний вміст нотатки за її `id`.

**JSON:**
```json
{
  "id": 1,
  "title": "Перший запис",
  "content": "Текст нотатки",
  "created_at": "2025-04-04 17:03:23"
}
```

**HTML:** таблиця з усіма полями та посиланням «Назад».

---

### Health endpoints (не доступні через Nginx ззовні)

#### `GET /health/alive`
Завжди повертає `200 OK`. Використовується для перевірки, чи процес живий.

#### `GET /health/ready`
Повертає `200 OK`, якщо сервіс успішно підключився до БД.
Повертає `500`, якщо з'єднання з БД недоступне.

---

### Кореневий ендпоінт

#### `GET /`
Повертає тільки `text/html` — список усіх бізнес-ендпоінтів застосунку у вигляді таблиці.

---

## Налаштування середовища для розробки

### Вимоги
- Python 3.10+
- MariaDB або MySQL (локально або на ВМ)
- PyCharm (рекомендовано, підключення через SSH interpreter)

### Встановлення залежностей

```bash
pip install -r requirements.txt
```

### Запуск міграції

```bash
python migrate.py \
  --db-host 127.0.0.1 \
  --db-user mywebapp \
  --db-password your_password \
  --db-name notes
```

### Запуск застосунку

```bash
python app.py \
  --host 127.0.0.1 \
  --port 8000 \
  --db-host 127.0.0.1 \
  --db-user mywebapp \
  --db-password your_password \
  --db-name notes
```

Або через uvicorn напряму (для розробки з auto-reload):

```bash
uvicorn app:app --host 127.0.0.1 --port 8000 --reload
```

> **Примітка:** на продакшн-сервері застосунок слухає на Unix-сокеті `/run/mywebapp.sock`, а не на TCP-порту. Запуск через systemd це робить автоматично.

---

## Документація по розгортанню

### 1. Базовий образ віртуальної машини

Використовується офіційний образ **Ubuntu 22.04 LTS Server**.

Завантажити: https://ubuntu.com/download/server

Обирати: **Ubuntu Server 22.04.x LTS** (ISO, ~1.5 GB). Версії Desktop не потрібно.

### 2. Вимоги до ресурсів ВМ

| Ресурс | Мінімум | Рекомендовано |
|---|---|---|
| CPU | 1 ядро | 2 ядра |
| RAM | 1 GB | 2 GB |
| Disk | 10 GB | 20 GB |
| Мережа | NAT + Host-only adapter | NAT + Host-only adapter |

### 3. Налаштування мережі у VirtualBox

Для доступу через SSH з Windows додати **Port Forwarding** у налаштуваннях ВМ:

- Adapter 1: NAT
- Adapter 1 → Port Forwarding: Host `127.0.0.1:2222` → Guest `10.0.2.15:22`

Або використовувати Host-only adapter для прямого IP-доступу.

### 4. Вхід на ВМ

```bash
# SSH (через port forwarding)
ssh -p 2222 student@127.0.0.1

# Стандартний SSH (якщо Host-only)
ssh student@<ip-вм>
```

Credentials за замовчуванням (до виконання install.sh): користувач, створений під час встановлення Ubuntu.

### 5. Запуск автоматизації розгортання

```bash
# 1. Скопіювати проєкт на ВМ
scp -P 2222 -r ./mywebapp student@127.0.0.1:~/

# 2. Підключитися до ВМ
ssh -p 2222 student@127.0.0.1

# 3. Запустити скрипт розгортання
cd ~/mywebapp
sudo bash install.sh
```

Скрипт автоматично:
1. Встановить пакети (python3, mariadb-server, nginx)
2. Створить користувачів (student, teacher, operator, app)
3. Створить БД та користувача для неї
4. Скопіює файли застосунку у `/opt/mywebapp/`
5. Встановить systemd-сервіс
6. Запустить застосунок
7. Налаштує Nginx
8. Створить файл `/home/student/gradebook` зі значенням `18`
9. Заблокує дефолтного користувача Ubuntu

---

## Інструкція з тестування

### Перевірка статусу сервісів

```bash
# Статус socket activation
systemctl status mywebapp.socket

# Статус застосунку
systemctl status mywebapp

# Статус nginx
systemctl status nginx

# Статус MariaDB
systemctl status mariadb
```

Очікуваний результат для socket: `active (listening)`.
Очікуваний результат для сервісу після першого запиту: `active (running)`.

---

### Перевірка health endpoints (напряму на сервері)

```bash
# Завжди має повертати 200 OK
curl -i http://127.0.0.1:8000/health/alive

# Має повертати 200 OK якщо БД доступна
curl -i http://127.0.0.1:8000/health/ready
```

> Health endpoints доступні тільки локально — Nginx повертає 404 на `/health` ззовні.

---

### Перевірка API через Nginx (порт 80)

#### Кореневий ендпоінт

```bash
curl -i http://localhost/
```

Очікується: `200 OK`, HTML-сторінка зі списком ендпоінтів.

---

#### Список нотаток — HTML

```bash
curl -i http://localhost/notes
```

або явно:

```bash
curl -i -H "Accept: text/html" http://localhost/notes
```

Очікується: `200 OK`, HTML-таблиця (або повідомлення «нотаток немає»).

---

#### Список нотаток — JSON

```bash
curl -i -H "Accept: application/json" http://localhost/notes
```

Очікується: `200 OK`, JSON-масив, наприклад `[]` якщо нотаток немає.

---

#### Створити нотатку (JSON)

```bash
curl -i -X POST http://localhost/notes \
  -H "Content-Type: application/json" \
  -d '{"title": "Тестова нотатка", "content": "Це тест"}'
```

Очікується: `201 Created`, JSON з `id` і `title`.

---

#### Створити нотатку (form data)

```bash
curl -i -X POST http://localhost/notes \
  -d "title=Друга нотатка&content=Текст другої нотатки"
```

Очікується: `201 Created`, HTML-сторінка з підтвердженням.

---

#### Отримати конкретну нотатку — JSON

```bash
curl -i -H "Accept: application/json" http://localhost/notes/1
```

Очікується: `200 OK`, JSON з усіма полями нотатки.

---

#### Отримати конкретну нотатку — HTML

```bash
curl -i http://localhost/notes/1
```

Очікується: `200 OK`, HTML-таблиця з полями id, title, content, created_at.

---

#### Неіснуюча нотатка

```bash
curl -i http://localhost/notes/9999
```

Очікується: `404 Not Found`.

---

#### Перевірка що `/health` заблоковано ззовні

```bash
curl -i http://localhost/health/alive
curl -i http://localhost/health/ready
```

Очікується: `404` — Nginx не пропускає ці маршрути.

---

### Перевірка логів Nginx

```bash
# Лог доступу (всі запити)
sudo tail -f /var/log/nginx/mywebapp_access.log

# Лог помилок
sudo tail -f /var/log/nginx/mywebapp_error.log
```

---

### Перевірка користувачів у системі

```bash
# Переглянути всіх локальних користувачів
awk -F: '$3 >= 1000 {print $1, $3}' /etc/passwd

# Перевірити sudo-права operator
sudo -l -U operator

# Перевірити що operator може робити (від імені operator)
su - operator
sudo systemctl status mywebapp   # має працювати
sudo systemctl reload nginx      # має працювати
sudo apt install vim              # має бути ЗАБЛОКОВАНО
```

---

### Перевірка файлу gradebook

```bash
cat /home/student/gradebook
# Очікується: 18
```

---

### Повний smoke-test одною командою

```bash
echo "=== alive ===" && curl -s http://localhost/health/alive
echo "=== ready ===" && curl -s http://localhost/health/ready
echo "=== create ===" && curl -s -X POST http://localhost/notes \
  -H "Content-Type: application/json" \
  -d '{"title":"smoke test","content":"ok"}'
echo "=== list json ===" && curl -s -H "Accept: application/json" http://localhost/notes
echo "=== get note ===" && curl -s -H "Accept: application/json" http://localhost/notes/1
```

---

## Архітектура системи

```
Клієнт
  │
  ▼ HTTP :80
Nginx (reverse proxy)
  │  /        → проксі
  │  /notes   → проксі
  │  /health  → 404 (заблоковано)
  │
  ▼ Unix socket /run/mywebapp.sock
Notes Service (FastAPI + uvicorn)
  │  systemd socket activation
  │  ExecStartPre: migrate.py
  │
  ▼ TCP 127.0.0.1:3306
MariaDB
```

Усі компоненти розгорнуті на одній ВМ. Доступ до застосунку і БД ззовні заблоковано — клієнти взаємодіють виключно через Nginx.

---