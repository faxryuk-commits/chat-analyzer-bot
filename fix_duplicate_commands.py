#!/usr/bin/env python3
"""
Скрипт для исправления проблемы с дублированием команд
"""

import requests
import time
from config import BOT_TOKEN

def clear_webhook_completely():
    """Полностью очищает webhook и переустанавливает его"""
    
    print("🔧 Полная очистка и переустановка webhook...")
    print("=" * 60)
    
    # 1. Удаляем webhook
    print("1️⃣ Удаляем webhook...")
    delete_url = f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook"
    delete_response = requests.post(delete_url)
    
    if delete_response.json()['ok']:
        print("✅ Webhook удален")
    else:
        print(f"❌ Ошибка удаления webhook: {delete_response.json()}")
        return False
    
    # 2. Ждем немного
    print("2️⃣ Ждем 3 секунды...")
    time.sleep(3)
    
    # 3. Устанавливаем webhook заново
    print("3️⃣ Устанавливаем webhook заново...")
    webhook_url = "https://web-production-e5d0f.up.railway.app/webhook"
    set_url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook"
    set_data = {"url": webhook_url}
    
    set_response = requests.post(set_url, json=set_data)
    if set_response.json()['ok']:
        print(f"✅ Webhook установлен: {webhook_url}")
    else:
        print(f"❌ Ошибка установки webhook: {set_response.json()}")
        return False
    
    # 4. Проверяем статус
    print("4️⃣ Проверяем статус webhook...")
    time.sleep(2)
    
    status_url = f"https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo"
    status_response = requests.get(status_url)
    
    if status_response.json()['ok']:
        webhook_info = status_response.json()['result']
        print(f"✅ Webhook активен: {webhook_info.get('url', 'Нет')}")
        print(f"📊 Ожидающие обновления: {webhook_info.get('pending_update_count', 0)}")
        
        if webhook_info.get('pending_update_count', 0) > 0:
            print("⚠️  Есть ожидающие обновления, очищаем их...")
            # Очищаем ожидающие обновления
            clear_url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
            clear_data = {"offset": -1}
            clear_response = requests.post(clear_url, json=clear_data)
            if clear_response.json()['ok']:
                print("✅ Ожидающие обновления очищены")
    else:
        print(f"❌ Ошибка получения статуса webhook: {status_response.json()}")
        return False
    
    return True

def test_webhook_response():
    """Тестирует ответ webhook"""
    
    print("\n🧪 Тестирование webhook...")
    print("=" * 40)
    
    # Проверяем доступность сервера
    webhook_url = "https://web-production-e5d0f.up.railway.app/health"
    
    try:
        response = requests.get(webhook_url, timeout=10)
        if response.status_code == 200:
            print("✅ Сервер доступен")
            print(f"📊 Ответ: {response.text}")
        else:
            print(f"❌ Сервер недоступен: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Ошибка подключения к серверу: {e}")
        return False
    
    return True

def check_bot_status():
    """Проверяет статус бота"""
    
    print("\n🤖 Проверка статуса бота...")
    print("=" * 40)
    
    try:
        me_url = f"https://api.telegram.org/bot{BOT_TOKEN}/getMe"
        response = requests.get(me_url)
        
        if response.json()['ok']:
            bot_info = response.json()['result']
            print(f"✅ Бот активен: @{bot_info['username']}")
            print(f"📝 Имя: {bot_info['first_name']}")
            return True
        else:
            print(f"❌ Ошибка получения информации о боте: {response.json()}")
            return False
    except Exception as e:
        print(f"❌ Ошибка проверки бота: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Исправление проблемы с дублированием команд")
    print("=" * 60)
    
    # Проверяем статус бота
    if not check_bot_status():
        print("❌ Проблема с ботом. Проверьте токен.")
        exit(1)
    
    # Тестируем webhook
    if not test_webhook_response():
        print("❌ Проблема с сервером. Проверьте Railway.")
        exit(1)
    
    # Очищаем и переустанавливаем webhook
    if clear_webhook_completely():
        print("\n🎉 Webhook успешно переустановлен!")
        print("\n💡 Теперь попробуйте отправить команду боту.")
        print("   Если проблема сохраняется, проверьте логи в Railway Dashboard.")
    else:
        print("\n❌ Не удалось переустановить webhook.")
        print("   Проверьте настройки и попробуйте снова.")
