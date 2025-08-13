# ☁️ Облачный деплой Chat Analyzer Bot

## 🚀 Быстрый деплой

### Heroku (Рекомендуется)

1. **Установите Heroku CLI:**
   ```bash
   # macOS
   brew install heroku/brew/heroku
   
   # Windows
   # Скачайте с https://devcenter.heroku.com/articles/heroku-cli
   ```

2. **Войдите в Heroku:**
   ```bash
   heroku login
   ```

3. **Создайте приложение:**
   ```bash
   heroku create your-chat-analyzer-bot
   ```

4. **Настройте переменные окружения:**
   ```bash
   heroku config:set BOT_TOKEN=your_telegram_bot_token
   heroku config:set ADMIN_USER_IDS=your_user_id
   ```

5. **Деплой:**
   ```bash
   git push heroku main
   ```

6. **Откройте приложение:**
   ```bash
   heroku open
   ```

### Railway

1. **Перейдите на [Railway.app](https://railway.app)**
2. **Подключите GitHub репозиторий**
3. **Настройте переменные окружения:**
   - `BOT_TOKEN`
   - `ADMIN_USER_IDS`
4. **Деплой произойдет автоматически**

### Render

1. **Перейдите на [Render.com](https://render.com)**
2. **Создайте новый Web Service**
3. **Подключите GitHub репозиторий**
4. **Настройте:**
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python3 web_app.py`
   - **Environment Variables:** `BOT_TOKEN`, `ADMIN_USER_IDS`

### Docker (Любая платформа)

1. **Соберите образ:**
   ```bash
   docker build -t chat-analyzer-bot .
   ```

2. **Запустите контейнер:**
   ```bash
   docker run -p 8080:8080 \
     -e BOT_TOKEN=your_token \
     -e ADMIN_USER_IDS=your_id \
     chat-analyzer-bot
   ```

3. **Или используйте docker-compose:**
   ```bash
   docker-compose up -d
   ```

## 🔧 Настройка переменных окружения

### Обязательные переменные:

- **`BOT_TOKEN`** - токен вашего Telegram бота
- **`ADMIN_USER_IDS`** - ID администраторов (через запятую)

### Опциональные переменные:

- **`PORT`** - порт (обычно устанавливается автоматически)
- **`DATABASE_PATH`** - путь к базе данных (по умолчанию: `./data/chat_analyzer.db`)

## 📱 Обновление URL бота

После деплоя обновите URL вебхука в боте:

```bash
# Получите URL вашего приложения
heroku info -s | grep web_url

# Установите вебхук
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://your-app-name.herokuapp.com/webhook"}'
```

## 🔍 Проверка работы

1. **Откройте веб-интерфейс:** `https://your-app-url.com`
2. **Проверьте API:** `https://your-app-url.com/api/system/status`
3. **Отправьте сообщение боту в Telegram**

## 🛠️ Логи и мониторинг

### Heroku:
```bash
heroku logs --tail
```

### Railway:
- Логи доступны в веб-интерфейсе

### Docker:
```bash
docker logs <container_id>
```

## 🔄 Обновление приложения

```bash
# Внесите изменения в код
git add .
git commit -m "Update app"
git push heroku main  # или другую платформу
```

## 🆘 Устранение неполадок

### Приложение не запускается:
1. Проверьте логи: `heroku logs --tail`
2. Убедитесь, что все переменные окружения установлены
3. Проверьте, что порт настроен правильно

### Бот не отвечает:
1. Проверьте, что вебхук установлен правильно
2. Убедитесь, что URL доступен извне
3. Проверьте токен бота

### База данных не работает:
1. Убедитесь, что путь к БД доступен для записи
2. Проверьте права доступа
3. Рассмотрите использование внешней БД (PostgreSQL)

## 💡 Рекомендации

- **Используйте PostgreSQL** для продакшена
- **Настройте мониторинг** (UptimeRobot, Pingdom)
- **Используйте CDN** для статических файлов
- **Настройте SSL** (обычно включен автоматически)
