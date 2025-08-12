#!/usr/bin/env python3
"""
Скрипт для проверки и настройки webhook
"""

import requests
import json
import os
from config import BOT_TOKEN

def check_webhook_status():
    """Проверяет статус webhook"""
    
    print("🔍 Проверка статуса webhook...")
    print("=" * 50)
    
    # Получаем информацию о webhook
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo"
    
    try:
        response = requests.get(url)
        data = response.json()
        
        if data['ok']:
            webhook_info = data['result']
            
            print(f"✅ Webhook активен: {webhook_info.get('url', 'Нет')}")
            print(f"📊 Ожидающие обновления: {webhook_info.get('pending_update_count', 0)}")
            print(f"🔄 Последняя ошибка: {webhook_info.get('last_error_message', 'Нет')}")
            print(f"⏰ Последняя ошибка: {webhook_info.get('last_error_date', 'Нет')}")
            
            # Если есть ожидающие обновления, очищаем их
            if webhook_info.get('pending_update_count', 0) > 0:
                print(f"\n🧹 Очищаем {webhook_info['pending_update_count']} ожидающих обновлений...")
                delete_url = f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook"
                delete_response = requests.post(delete_url)
                
                if delete_response.json()['ok']:
                    print("✅ Webhook очищен")
                    
                    # Устанавливаем webhook заново
                    webhook_url = "https://web-production-e5d0f.up.railway.app/webhook"
                    set_url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook"
                    set_data = {"url": webhook_url}
                    
                    set_response = requests.post(set_url, json=set_data)
                    if set_response.json()['ok']:
                        print(f"✅ Webhook переустановлен: {webhook_url}")
                    else:
                        print(f"❌ Ошибка установки webhook: {set_response.json()}")
                else:
                    print(f"❌ Ошибка очистки webhook: {delete_response.json()}")
            
        else:
            print(f"❌ Ошибка получения информации о webhook: {data}")
            
    except Exception as e:
        print(f"❌ Ошибка при проверке webhook: {e}")

def clear_webhook():
    """Очищает webhook и устанавливает заново"""
    
    print("🧹 Очистка и переустановка webhook...")
    print("=" * 50)
    
    # Удаляем webhook
    delete_url = f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook"
    delete_response = requests.post(delete_url)
    
    if delete_response.json()['ok']:
        print("✅ Webhook удален")
        
        # Устанавливаем webhook заново
        webhook_url = "https://web-production-e5d0f.up.railway.app/webhook"
        set_url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook"
        set_data = {"url": webhook_url}
        
        set_response = requests.post(set_url, json=set_data)
        if set_response.json()['ok']:
            print(f"✅ Webhook установлен: {webhook_url}")
        else:
            print(f"❌ Ошибка установки webhook: {set_response.json()}")
    else:
        print(f"❌ Ошибка удаления webhook: {delete_response.json()}")

def test_webhook():
    """Тестирует webhook"""
    
    print("🧪 Тестирование webhook...")
    print("=" * 50)
    
    # Проверяем доступность сервера
    webhook_url = "https://web-production-e5d0f.up.railway.app/health"
    
    try:
        response = requests.get(webhook_url, timeout=10)
        if response.status_code == 200:
            print("✅ Сервер доступен")
            print(f"📊 Ответ: {response.text}")
        else:
            print(f"❌ Сервер недоступен: {response.status_code}")
    except Exception as e:
        print(f"❌ Ошибка подключения к серверу: {e}")

if __name__ == "__main__":
    print("🤖 Проверка и настройка webhook для Chat Analyzer Bot")
    print("=" * 60)
    
    # Проверяем статус
    check_webhook_status()
    
    print("\n" + "=" * 60)
    
    # Тестируем webhook
    test_webhook()
    
    print("\n" + "=" * 60)
    print("💡 Рекомендации:")
    print("1. Если есть дублирование сообщений, запустите clear_webhook()")
    print("2. Проверьте логи в Railway Dashboard")
    print("3. Убедитесь, что локальный бот не запущен")
    print("4. Обновите переменные окружения в Railway")
