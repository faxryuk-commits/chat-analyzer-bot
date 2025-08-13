#!/bin/bash

# Скрипт для деплоя Chat Analyzer Bot в облако

echo "🚀 Деплой Chat Analyzer Bot в облако..."

# Проверяем наличие переменных окружения
if [ -z "$BOT_TOKEN" ]; then
    echo "❌ Ошибка: BOT_TOKEN не установлен"
    echo "Установите переменную: export BOT_TOKEN=your_token"
    exit 1
fi

if [ -z "$ADMIN_USER_IDS" ]; then
    echo "❌ Ошибка: ADMIN_USER_IDS не установлен"
    echo "Установите переменную: export ADMIN_USER_IDS=your_id"
    exit 1
fi

# Выбираем платформу
echo "Выберите платформу для деплоя:"
echo "1) Heroku"
echo "2) Railway"
echo "3) Render"
echo "4) Docker"
read -p "Введите номер (1-4): " choice

case $choice in
    1)
        echo "📦 Деплой на Heroku..."
        
        # Проверяем наличие Heroku CLI
        if ! command -v heroku &> /dev/null; then
            echo "❌ Heroku CLI не установлен"
            echo "Установите: brew install heroku/brew/heroku"
            exit 1
        fi
        
        # Создаем приложение если не существует
        if [ -z "$HEROKU_APP_NAME" ]; then
            echo "Создание нового Heroku приложения..."
            heroku create
        else
            echo "Использование существующего приложения: $HEROKU_APP_NAME"
            heroku git:remote -a $HEROKU_APP_NAME
        fi
        
        # Устанавливаем переменные окружения
        heroku config:set BOT_TOKEN=$BOT_TOKEN
        heroku config:set ADMIN_USER_IDS=$ADMIN_USER_IDS
        
        # Деплой
        git push heroku main
        
        # Получаем URL
        APP_URL=$(heroku info -s | grep web_url | cut -d= -f2)
        echo "✅ Приложение развернуто: $APP_URL"
        
        # Устанавливаем вебхук
        echo "🔗 Установка вебхука..."
        curl -X POST "https://api.telegram.org/bot$BOT_TOKEN/setWebhook" \
            -H "Content-Type: application/json" \
            -d "{\"url\": \"$APP_URL/webhook\"}"
        
        echo "🎉 Деплой завершен! Откройте: $APP_URL"
        ;;
        
    2)
        echo "🚂 Деплой на Railway..."
        echo "1. Перейдите на https://railway.app"
        echo "2. Подключите GitHub репозиторий"
        echo "3. Установите переменные окружения:"
        echo "   - BOT_TOKEN: $BOT_TOKEN"
        echo "   - ADMIN_USER_IDS: $ADMIN_USER_IDS"
        echo "4. Деплой произойдет автоматически"
        ;;
        
    3)
        echo "🎨 Деплой на Render..."
        echo "1. Перейдите на https://render.com"
        echo "2. Создайте новый Web Service"
        echo "3. Подключите GitHub репозиторий"
        echo "4. Настройте:"
        echo "   - Build Command: pip install -r requirements.txt"
        echo "   - Start Command: python3 web_app.py"
        echo "   - Environment Variables:"
        echo "     BOT_TOKEN: $BOT_TOKEN"
        echo "     ADMIN_USER_IDS: $ADMIN_USER_IDS"
        ;;
        
    4)
        echo "🐳 Деплой с Docker..."
        
        # Собираем образ
        docker build -t chat-analyzer-bot .
        
        # Запускаем контейнер
        docker run -d \
            --name chat-analyzer-bot \
            -p 8080:8080 \
            -e BOT_TOKEN=$BOT_TOKEN \
            -e ADMIN_USER_IDS=$ADMIN_USER_IDS \
            chat-analyzer-bot
            
        echo "✅ Контейнер запущен на http://localhost:8080"
        ;;
        
    *)
        echo "❌ Неверный выбор"
        exit 1
        ;;
esac

echo "�� Деплой завершен!"
