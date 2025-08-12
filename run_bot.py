#!/usr/bin/env python3
"""
Скрипт для запуска Chat Analyzer Bot
"""

import sys
import os
import logging
from pathlib import Path

# Добавляем текущую директорию в путь
sys.path.insert(0, str(Path(__file__).parent))

def check_dependencies():
    """Проверяет наличие необходимых зависимостей"""
    required_modules = [
        'telegram',
        'matplotlib',
        'seaborn',
        'pandas',
        'numpy',
        'wordcloud',
        'nltk',
        'textblob',
        'schedule'
    ]
    
    missing_modules = []
    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing_modules.append(module)
    
    if missing_modules:
        print("❌ Отсутствуют необходимые модули:")
        for module in missing_modules:
            print(f"   - {module}")
        print("\nУстановите их командой:")
        print("pip install -r requirements.txt")
        return False
    
    return True

def check_config():
    """Проверяет наличие конфигурации"""
    if not os.path.exists('.env'):
        print("❌ Файл .env не найден!")
        print("Создайте файл .env на основе env_example.txt")
        print("cp env_example.txt .env")
        print("И заполните необходимые переменные:")
        print("- BOT_TOKEN - токен вашего бота")
        print("- ADMIN_USER_IDS - ID администраторов")
        return False
    
    # Проверяем наличие токена
    from dotenv import load_dotenv
    load_dotenv()
    
    bot_token = os.getenv('BOT_TOKEN')
    if not bot_token or bot_token == 'your_bot_token_here':
        print("❌ Не установлен токен бота!")
        print("Получите токен у @BotFather и добавьте его в .env файл")
        return False
    
    return True

def main():
    """Основная функция запуска"""
    print("🤖 Запуск Chat Analyzer Bot...")
    print("=" * 50)
    
    # Проверяем зависимости
    print("📦 Проверка зависимостей...")
    if not check_dependencies():
        sys.exit(1)
    print("✅ Зависимости установлены")
    
    # Проверяем конфигурацию
    print("⚙️ Проверка конфигурации...")
    if not check_config():
        sys.exit(1)
    print("✅ Конфигурация корректна")
    
    # Настраиваем логирование
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('bot.log'),
            logging.StreamHandler()
        ]
    )
    
    try:
        # Импортируем и запускаем бота
        from telegram_bot import ChatAnalyzerBot
        
        print("🚀 Запуск бота...")
        bot = ChatAnalyzerBot()
        bot.run()
        
    except KeyboardInterrupt:
        print("\n⏹️ Бот остановлен пользователем")
    except Exception as e:
        print(f"❌ Ошибка при запуске бота: {e}")
        logging.error(f"Ошибка при запуске бота: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
