#!/usr/bin/env python3
"""
Конфигурация для системы мониторинга логов
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Настройки мониторинга
MONITOR_CONFIG = {
    # Основные настройки
    "log_file": "bot.log",
    "check_interval": 30,  # секунды
    
    # URL для отправки ошибок в Cursor
    "cursor_api_url": os.getenv('CURSOR_API_URL'),
    
    # Паттерны для поиска ошибок
    "error_patterns": [
        r'ERROR.*',
        r'CRITICAL.*',
        r'Exception.*',
        r'Traceback.*',
        r'Failed.*',
        r'Error.*',
        r'❌.*',
        r'Failed to.*',
        r'Unable to.*',
        r'Connection.*error',
        r'Timeout.*',
        r'Database.*error',
        r'Telegram.*error',
        r'Webhook.*error',
        r'ImportError.*',
        r'ModuleNotFoundError.*',
        r'AttributeError.*',
        r'TypeError.*',
        r'ValueError.*',
        r'KeyError.*',
        r'IndexError.*',
        r'FileNotFoundError.*',
        r'PermissionError.*',
        r'OSError.*',
        r'RuntimeError.*',
        r'MemoryError.*',
        r'RecursionError.*',
        r'SyntaxError.*',
        r'IndentationError.*',
        r'TabError.*',
        r'SystemError.*',
        r'FloatingPointError.*',
        r'OverflowError.*',
        r'ZeroDivisionError.*',
        r'AssertionError.*',
        r'LookupError.*',
        r'ArithmeticError.*',
        r'BufferError.*',
        r'BlockingIOError.*',
        r'ChildProcessError.*',
        r'ConnectionError.*',
        r'BrokenPipeError.*',
        r'ConnectionAbortedError.*',
        r'ConnectionRefusedError.*',
        r'ConnectionResetError.*',
        r'FileExistsError.*',
        r'FileNotFoundError.*',
        r'InterruptedError.*',
        r'IsADirectoryError.*',
        r'NotADirectoryError.*',
        r'ProcessLookupError.*',
        r'TimeoutError.*',
        r'UnsupportedOperation.*'
    ],
    
    # Паттерны для игнорирования (предупреждения)
    "ignored_patterns": [
        r'NotOpenSSLWarning.*',
        r'DeprecationWarning.*',
        r'UserWarning.*',
        r'FutureWarning.*',
        r'PendingDeprecationWarning.*',
        r'RuntimeWarning.*',
        r'SyntaxWarning.*',
        r'ImportWarning.*',
        r'UnicodeWarning.*',
        r'BytesWarning.*',
        r'ResourceWarning.*',
        r'INFO.*',
        r'DEBUG.*'
    ],
    
    # Настройки отчетов
    "reports": {
        "save_locally": True,
        "send_to_cursor": True,
        "max_reports_per_hour": 10,
        "report_retention_days": 7
    },
    
    # Настройки уведомлений
    "notifications": {
        "telegram_admin_notification": True,
        "telegram_error_reports": True,
        "telegram_fix_reports": True,
        "email_notification": False,
        "discord_webhook": False
    },
    
    # Файлы для анализа в Cursor
    "cursor_files": [
        "webhook_server.py",
        "database.py", 
        "message_collector.py",
        "text_analyzer.py",
        "report_generator.py",
        "conversation_analyzer.py",
        "task_manager.py",
        "timezone_utils.py"
    ],
    
    # Приоритеты ошибок
    "error_priorities": {
        "Critical": "high",
        "Exception": "high", 
        "Error": "medium",
        "User Error": "low",
        "Unknown": "medium"
    }
}

# Функции для работы с конфигурацией
def get_config(key, default=None):
    """Получает значение из конфигурации"""
    keys = key.split('.')
    value = MONITOR_CONFIG
    
    for k in keys:
        if isinstance(value, dict) and k in value:
            value = value[k]
        else:
            return default
    
    return value

def set_config(key, value):
    """Устанавливает значение в конфигурации"""
    keys = key.split('.')
    config = MONITOR_CONFIG
    
    for k in keys[:-1]:
        if k not in config:
            config[k] = {}
        config = config[k]
    
    config[keys[-1]] = value

def get_error_patterns():
    """Получает паттерны для поиска ошибок"""
    return get_config('error_patterns', [])

def get_ignored_patterns():
    """Получает паттерны для игнорирования"""
    return get_config('ignored_patterns', [])

def get_cursor_files():
    """Получает список файлов для анализа в Cursor"""
    return get_config('cursor_files', [])

def get_error_priority(error_type):
    """Получает приоритет для типа ошибки"""
    priorities = get_config('error_priorities', {})
    return priorities.get(error_type, 'medium')
