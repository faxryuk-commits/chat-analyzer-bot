#!/usr/bin/env python3
"""
Скрипт для автоматического деплоя на Railway
"""

import os
import requests
import json
import time
from urllib.parse import urljoin

def deploy_to_railway():
    """Автоматический деплой на Railway"""
    
    print("🚀 Начинаем автоматический деплой на Railway...")
    print("=" * 50)
    
    # Проверяем наличие токена
    bot_token = os.getenv('BOT_TOKEN', '5294761386:AAGjj8JPOwm8fjxBJzcUYDIWx_F06VfW6u8')
    
    print(f"✅ Токен бота: {bot_token[:20]}...")
    
    # Инструкции для пользователя
    print("\n📋 ИНСТРУКЦИИ ДЛЯ ДЕПЛОЯ:")
    print("1. Перейдите на https://railway.app")
    print("2. Войдите через GitHub")
    print("3. Нажмите 'New Project'")
    print("4. Выберите 'Deploy from GitHub repo'")
    print("5. Найдите репозиторий: faxryuk-commits/chat-analyzer-bot")
    print("6. Нажмите 'Deploy Now'")
    print("\n⏳ Ждем завершения деплоя...")
    
    # Ждем ввода пользователя
    input("\nНажмите Enter когда деплой завершится и получите URL приложения...")
    
    # Запрашиваем URL приложения
    app_url = input("\nВведите URL вашего приложения на Railway (например: https://chat-analyzer-bot-production.up.railway.app): ")
    
    if not app_url:
        print("❌ URL не указан. Деплой прерван.")
        return
    
    print(f"\n✅ URL приложения: {app_url}")
    
    # Настраиваем webhook
    print("\n🔧 Настраиваем webhook...")
    
    webhook_url = f"{app_url}/webhook"
    webhook_data = {
        "url": webhook_url
    }
    
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{bot_token}/setWebhook",
            json=webhook_data,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('ok'):
                print("✅ Webhook успешно настроен!")
                print(f"📡 Webhook URL: {webhook_url}")
            else:
                print(f"❌ Ошибка настройки webhook: {result.get('description')}")
        else:
            print(f"❌ HTTP ошибка: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Ошибка при настройке webhook: {e}")
    
    # Проверяем статус webhook
    print("\n🔍 Проверяем статус webhook...")
    
    try:
        response = requests.get(
            f"https://api.telegram.org/bot{bot_token}/getWebhookInfo",
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('ok'):
                webhook_info = result.get('result', {})
                print(f"✅ Webhook активен: {webhook_info.get('url')}")
                print(f"📊 Ожидающие обновления: {webhook_info.get('pending_update_count', 0)}")
            else:
                print(f"❌ Ошибка получения информации о webhook: {result.get('description')}")
        else:
            print(f"❌ HTTP ошибка: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Ошибка при проверке webhook: {e}")
    
    # Проверяем health check
    print("\n🏥 Проверяем health check...")
    
    try:
        response = requests.get(f"{app_url}/health", timeout=10)
        
        if response.status_code == 200:
            health_data = response.json()
            print(f"✅ Приложение работает: {health_data}")
        else:
            print(f"⚠️ Health check вернул статус: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Ошибка при проверке health check: {e}")
    
    print("\n🎉 ДЕПЛОЙ ЗАВЕРШЕН!")
    print("=" * 50)
    print(f"🌐 URL приложения: {app_url}")
    print(f"📡 Webhook URL: {webhook_url}")
    print(f"🤖 Бот готов к работе!")
    print("\n📱 Теперь можете протестировать бота в Telegram!")
    print("💡 Отправьте команду /start вашему боту")

if __name__ == "__main__":
    deploy_to_railway()
