#!/usr/bin/env python3
"""
Скрипт для запуска веб-приложения Chat Analyzer Bot
"""

import os
import sys
import subprocess
from pathlib import Path

def check_dependencies():
    """Проверяет наличие необходимых зависимостей"""
    required_packages = ['flask', 'python-dotenv']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ Отсутствуют зависимости: {', '.join(missing_packages)}")
        print("Установите их командой:")
        print(f"pip install {' '.join(missing_packages)}")
        return False
    
    return True

def check_database():
    """Проверяет наличие базы данных"""
    db_path = Path('chat_analyzer.db')
    if not db_path.exists():
        print("⚠️ База данных не найдена. Создайте её, запустив бота.")
        return False
    return True

def start_webapp():
    """Запускает веб-приложение"""
    print("🚀 Запуск веб-приложения Chat Analyzer Bot...")
    
    # Проверяем зависимости
    if not check_dependencies():
        return False
    
    # Проверяем базу данных
    if not check_database():
        print("💡 Создайте базу данных, запустив бота командой: python webhook_server.py")
        return False
    
    # Запускаем веб-приложение
    try:
        print("🌐 Веб-приложение запускается на http://localhost:5000")
        print("📱 Для остановки нажмите Ctrl+C")
        print("-" * 50)
        
        subprocess.run([sys.executable, 'web_app.py'])
        
    except KeyboardInterrupt:
        print("\n🛑 Веб-приложение остановлено")
    except Exception as e:
        print(f"❌ Ошибка запуска: {e}")
        return False
    
    return True

if __name__ == '__main__':
    start_webapp()
