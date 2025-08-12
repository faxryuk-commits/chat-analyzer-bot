#!/usr/bin/env python3
"""
Скрипт для обновления переменных окружения в Railway
"""

import os
import requests
import json

def update_railway_environment():
    """Обновляет переменные окружения в Railway"""
    
    print("🔧 Обновление переменных окружения в Railway...")
    print("=" * 50)
    
    # Новые переменные окружения
    env_vars = {
        "BOT_TOKEN": "5294761386:AAGjj8JPOwm8fjxBJzcUYDIWx_F06VfW6u8",
        "ADMIN_USER_IDS": "98838625",
        "WEBHOOK_URL": "https://web-production-e5d0f.up.railway.app",
        "DATABASE_PATH": "/tmp/chat_analyzer.db",
        "HISTORY_DAYS": "45",
        "REPORT_TIME": "18:00",
        "TASK_TIMEOUT_HOURS": "24"
    }
    
    print("📋 Новые переменные окружения:")
    for key, value in env_vars.items():
        print(f"  {key}={value}")
    
    print("\n⚠️  ВАЖНО: Обновите переменные окружения в Railway Dashboard:")
    print("1. Перейдите в Railway Dashboard")
    print("2. Откройте ваш проект")
    print("3. Перейдите в раздел 'Variables'")
    print("4. Обновите ADMIN_USER_IDS на: 98838625")
    print("5. Сохраните изменения")
    print("6. Railway автоматически перезапустит приложение")
    
    print("\n🎯 После обновления переменных:")
    print("- Команда /admin будет доступна")
    print("- Вы сможете использовать все административные функции")
    print("- Бот автоматически перезапустится с новыми настройками")

if __name__ == "__main__":
    update_railway_environment()
