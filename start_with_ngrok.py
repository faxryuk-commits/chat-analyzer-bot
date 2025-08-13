#!/usr/bin/env python3
"""
Скрипт для запуска веб-приложения с ngrok для HTTPS
"""

import subprocess
import time
import requests
import json
import os
from threading import Thread

def check_ngrok():
    """Проверяет, установлен ли ngrok"""
    try:
        result = subprocess.run(['ngrok', 'version'], capture_output=True, text=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False

def install_ngrok():
    """Устанавливает ngrok"""
    print("📦 Установка ngrok...")
    
    # Для macOS
    if os.name == 'posix':
        try:
            subprocess.run(['brew', 'install', 'ngrok'], check=True)
            print("✅ ngrok установлен через Homebrew")
            return True
        except subprocess.CalledProcessError:
            print("❌ Не удалось установить ngrok через Homebrew")
            print("💡 Установите ngrok вручную: https://ngrok.com/download")
            return False

def get_ngrok_url():
    """Получает публичный URL от ngrok"""
    try:
        response = requests.get('http://localhost:4040/api/tunnels')
        tunnels = response.json()['tunnels']
        for tunnel in tunnels:
            if tunnel['proto'] == 'https':
                return tunnel['public_url']
    except:
        pass
    return None

def start_ngrok():
    """Запускает ngrok"""
    print("🚀 Запуск ngrok...")
    
    # Запускаем ngrok в фоне
    ngrok_process = subprocess.Popen(
        ['ngrok', 'http', '8080'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Ждем запуска
    time.sleep(3)
    
    # Получаем URL
    url = get_ngrok_url()
    if url:
        print(f"🌐 Ngrok URL: {url}")
        return url, ngrok_process
    else:
        print("❌ Не удалось получить ngrok URL")
        ngrok_process.terminate()
        return None, None

def update_bot_url(url):
    """Обновляет URL в боте"""
    print(f"🔄 Обновление URL в боте: {url}")
    
    # Заменяем URL в webhook_server.py
    with open('webhook_server.py', 'r') as f:
        content = f.read()
    
    # Заменяем все localhost URL на ngrok URL
    content = content.replace('http://localhost:8080', url)
    
    with open('webhook_server.py', 'w') as f:
        f.write(content)
    
    print("✅ URL обновлен в боте")

def main():
    """Главная функция"""
    print("🤖 Chat Analyzer Bot - Запуск с ngrok")
    print("=" * 50)
    
    # Проверяем ngrok
    if not check_ngrok():
        print("❌ ngrok не найден")
        if install_ngrok():
            print("✅ ngrok установлен")
        else:
            print("❌ Не удалось установить ngrok")
            return
    
    # Запускаем ngrok
    url, ngrok_process = start_ngrok()
    if not url:
        return
    
    # Обновляем URL в боте
    update_bot_url(url)
    
    print("\n🎯 Теперь запустите бота:")
    print("python3 webhook_server.py")
    print("\n📱 В Telegram используйте команду /start")
    print(f"🌐 Веб-приложение будет доступно по адресу: {url}")
    
    try:
        # Ждем завершения
        ngrok_process.wait()
    except KeyboardInterrupt:
        print("\n🛑 Остановка...")
        ngrok_process.terminate()
        
        # Восстанавливаем локальный URL
        with open('webhook_server.py', 'r') as f:
            content = f.read()
        content = content.replace(url, 'http://localhost:8080')
        with open('webhook_server.py', 'w') as f:
            f.write(content)
        
        print("✅ Локальный URL восстановлен")

if __name__ == '__main__':
    main()
