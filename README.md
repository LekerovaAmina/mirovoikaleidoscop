# 🌍 Мировой калейдоскоп — Система голосования

Система для мероприятия «Мировой калейдоскоп», 22 марта, Дом дружбы.

## Структура страниц

### Админ (пароль: `admin2024`)
| Страница | URL | Описание |
|----------|-----|----------|
| Вход | `/admin` | Вход с паролем |
| QR-код | `/admin/qr` | QR для участников |
| Рейтинг | `/admin/rating` | Красивый рейтинг с салютами и конфети (для проектора) |
| Панель | `/admin/dashboard` | Статистика, создание команд, голоса |

### Пользователь (только через QR)
| Страница | URL | Описание |
|----------|-----|----------|
| Выбор команды | `/join` | Присоединиться к команде |
| Голосование | `/vote` | Проголосовать за другую команду |

---

## Запуск через Docker (рекомендуется)

```bash
# 1. Убедитесь что Docker и Docker Compose установлены
docker --version
docker compose version

# 2. Запустите
docker compose up --build

# 3. Откройте браузер
# http://localhost:5000/admin
```

## Запуск вручную (без Docker)

### 1. PostgreSQL
```bash
# Создайте базу данных
createdb kaleidoscop
```

### 2. Python зависимости
```bash
pip install -r requirements.txt
```

### 3. Настройте переменные окружения
```bash
export DB_HOST=localhost
export DB_NAME=kaleidoscop
export DB_USER=postgres
export DB_PASSWORD=your_password
export ADMIN_PASSWORD=admin2024
export BASE_URL=http://YOUR_LOCAL_IP:5000   # <-- важно для QR!
export SECRET_KEY=your-secret-key
```

### 4. Запустите
```bash
python app.py
```

---

## Настройка для мероприятия

### Важно: BASE_URL для QR-кода
Чтобы участники могли сканировать QR со своих телефонов, нужно указать **локальный IP** вашего компьютера:

```bash
# Узнайте ваш IP (все устройства должны быть в одной сети Wi-Fi)
# Windows: ipconfig
# Mac/Linux: ifconfig или ip addr

export BASE_URL=http://192.168.1.XXX:5000
```

### Смена пароля администратора
```bash
export ADMIN_PASSWORD=ваш_пароль
```

---

## Сценарий использования

1. **До мероприятия**: Создайте команды в панели `/admin/dashboard`
2. **Начало**: Покажите QR-код `/admin/qr` на экране — участники сканируют
3. **Участники**: Выбирают свою команду → голосуют за другую
4. **Итоги**: Откройте `/admin/rating` через проектор — красивый рейтинг с салютами!

---

## API эндпоинты

| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/api/teams` | Список команд с голосами |
| POST | `/api/teams` | Создать команду (admin) |
| DELETE | `/api/teams/<id>` | Удалить команду (admin) |
| GET | `/api/stats` | Статистика (онлайн, голоса) |
| POST | `/api/join-team` | Присоединиться к команде |
| POST | `/api/vote` | Проголосовать |
| GET | `/api/my-status` | Статус текущего пользователя |
