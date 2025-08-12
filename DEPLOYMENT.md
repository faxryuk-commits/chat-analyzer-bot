# 🚀 Развертывание Chat Analyzer Bot в облаке

Пошаговая инструкция по развертыванию телеграм бота на Railway через GitHub.

## 📋 Подготовка

### 1. Создание Telegram бота

1. Найдите @BotFather в Telegram
2. Отправьте команду `/newbot`
3. Следуйте инструкциям для создания бота
4. Сохраните полученный токен

### 2. Подготовка GitHub репозитория

1. Создайте новый репозиторий на GitHub
2. Загрузите код в репозиторий:
```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/your-username/chat-analyzer-bot.git
git push -u origin main
```

## 🌐 Развертывание на Railway

### 1. Подключение к Railway

1. Перейдите на [railway.app](https://railway.app)
2. Войдите через GitHub
3. Нажмите "New Project"
4. Выберите "Deploy from GitHub repo"
5. Выберите ваш репозиторий

### 2. Настройка переменных окружения

В Railway Dashboard перейдите в раздел "Variables" и добавьте:

```env
BOT_TOKEN=your_bot_token_here
ADMIN_USER_IDS=123456789,987654321
WEBHOOK_URL=https://your-app-name.railway.app
DATABASE_PATH=/tmp/chat_analyzer.db
HISTORY_DAYS=45
REPORT_TIME=18:00
TASK_TIMEOUT_HOURS=24
```

### 3. Настройка домена

1. В Railway Dashboard перейдите в "Settings"
2. В разделе "Domains" скопируйте URL вашего приложения
3. Обновите переменную `WEBHOOK_URL` с этим URL

### 4. Настройка webhook

После деплоя выполните в терминале:

```bash
# Получите URL вашего приложения
curl https://your-app-name.railway.app

# Установите webhook (замените на ваш токен и URL)
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://your-app-name.railway.app/webhook"}'
```

## 🔧 Альтернативные платформы

### Heroku

1. Создайте аккаунт на [heroku.com](https://heroku.com)
2. Установите Heroku CLI
3. Выполните команды:

```bash
# Создание приложения
heroku create your-bot-name

# Настройка переменных
heroku config:set BOT_TOKEN=your_bot_token_here
heroku config:set ADMIN_USER_IDS=123456789,987654321
heroku config:set WEBHOOK_URL=https://your-app-name.herokuapp.com

# Деплой
git push heroku main

# Установка webhook
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://your-app-name.herokuapp.com/webhook"}'
```

### DigitalOcean App Platform

1. Создайте аккаунт на [digitalocean.com](https://digitalocean.com)
2. Перейдите в App Platform
3. Подключите GitHub репозиторий
4. Настройте переменные окружения
5. Деплой произойдет автоматически

### Google Cloud Run

1. Создайте проект в Google Cloud Console
2. Включите Cloud Run API
3. Выполните команды:

```bash
# Установка gcloud CLI
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# Сборка и деплой
gcloud run deploy chat-analyzer-bot \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars BOT_TOKEN=your_bot_token_here
```

## 🔍 Проверка работы

### 1. Проверка health check

```bash
curl https://your-app-name.railway.app/health
```

Ожидаемый ответ:
```json
{"status": "healthy", "bot": "running"}
```

### 2. Проверка webhook

```bash
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo"
```

### 3. Тестирование бота

1. Найдите вашего бота в Telegram
2. Отправьте команду `/start`
3. Проверьте ответ бота

## 📊 Мониторинг

### Railway Dashboard

- Перейдите в Railway Dashboard
- Откройте ваш проект
- Проверьте логи в разделе "Deployments"

### Логи приложения

```bash
# Просмотр логов в Railway
railway logs

# Просмотр логов в Heroku
heroku logs --tail
```

## 🔧 Устранение неполадок

### Проблема: Бот не отвечает

1. Проверьте токен бота
2. Убедитесь, что webhook установлен правильно
3. Проверьте логи приложения

### Проблема: Ошибки в логах

1. Проверьте переменные окружения
2. Убедитесь, что все зависимости установлены
3. Проверьте права доступа к базе данных

### Проблема: База данных не работает

1. В облаке используйте внешнюю базу данных
2. Для Railway добавьте PostgreSQL:
   - В Railway Dashboard нажмите "New"
   - Выберите "Database" → "PostgreSQL"
   - Подключите к вашему приложению

## 🔄 Обновление бота

### Автоматическое обновление

При push в GitHub репозиторий Railway автоматически пересоберет и перезапустит приложение.

### Ручное обновление

```bash
# Обновите код
git add .
git commit -m "Update bot"
git push origin main

# Railway автоматически обновит приложение
```

## 💰 Стоимость

### Railway
- Бесплатный план: $5 кредитов в месяц
- Платный план: от $20/месяц

### Heroku
- Бесплатный план: недоступен
- Платный план: от $7/месяц

### DigitalOcean
- Бесплатный план: недоступен
- Платный план: от $5/месяц

## 🔒 Безопасность

### Переменные окружения
- Никогда не коммитьте токены в репозиторий
- Используйте переменные окружения для всех секретов
- Регулярно обновляйте токены

### Webhook
- Используйте HTTPS только
- Проверяйте подпись webhook от Telegram
- Ограничьте доступ к webhook endpoint

## 📞 Поддержка

При возникновении проблем:

1. Проверьте логи приложения
2. Убедитесь, что все переменные окружения настроены
3. Проверьте статус платформы развертывания
4. Обратитесь к документации платформы

## 🎯 Рекомендации

1. **Используйте Railway** для быстрого старта
2. **Настройте мониторинг** для отслеживания работы бота
3. **Регулярно обновляйте** зависимости
4. **Делайте бэкапы** базы данных
5. **Тестируйте** изменения перед деплоем
