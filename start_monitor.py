#!/usr/bin/env python3
"""
Скрипт для запуска мониторинга логов отдельно
"""

import os
import sys
import time
from log_monitor import LogMonitor

def main():
    print("🚀 Запуск системы мониторинга логов...")
    
    # Проверяем наличие лог файла
    log_file = "bot.log"
    if not os.path.exists(log_file):
        print(f"❌ Лог файл {log_file} не найден")
        print("Создаем пустой файл...")
        with open(log_file, 'w') as f:
            f.write("")
    
    # Проверяем переменную окружения для Cursor API
    cursor_url = os.getenv('CURSOR_API_URL')
    if cursor_url:
        print(f"✅ Cursor API URL настроен: {cursor_url}")
    else:
        print("⚠️  CURSOR_API_URL не настроен, ошибки будут только сохраняться локально")
    
    # Создаем монитор
    monitor = LogMonitor(
        log_file=log_file,
        cursor_api_url=cursor_url
    )
    
    print(f"📊 Мониторинг файла: {log_file}")
    print("⏰ Интервал проверки: 30 секунд")
    print("🛑 Для остановки нажмите Ctrl+C")
    print("=" * 50)
    
    try:
        # Запускаем мониторинг
        monitor.monitor(interval=30)
    except KeyboardInterrupt:
        print("\n🛑 Мониторинг остановлен пользователем")
    except Exception as e:
        print(f"❌ Ошибка в мониторинге: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
