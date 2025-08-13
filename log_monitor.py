#!/usr/bin/env python3
"""
Система автоматического мониторинга логов и отправки ошибок в Cursor
"""

import os
import time
import json
import requests
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import re
from pathlib import Path
from monitor_config import get_error_patterns, get_ignored_patterns, get_cursor_files, get_error_priority

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LogMonitor:
    def __init__(self, log_file: str = "bot.log", cursor_api_url: str = None):
        self.log_file = log_file
        self.cursor_api_url = cursor_api_url or os.getenv('CURSOR_API_URL')
        self.last_position = 0
        self.error_patterns = get_error_patterns()
        self.ignored_patterns = get_ignored_patterns()
        
    def read_new_logs(self) -> List[str]:
        """Читает новые записи из лог файла"""
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                f.seek(self.last_position)
                new_lines = f.readlines()
                self.last_position = f.tell()
                return new_lines
        except FileNotFoundError:
            logger.warning(f"Лог файл {self.log_file} не найден")
            return []
        except Exception as e:
            logger.error(f"Ошибка чтения лог файла: {e}")
            return []
    
    def is_error_line(self, line: str) -> bool:
        """Проверяет, является ли строка ошибкой"""
        line_lower = line.lower()
        
        # Игнорируем предупреждения
        for pattern in self.ignored_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                return False
        
        # Проверяем на ошибки
        for pattern in self.error_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                return True
        
        return False
    
    def extract_error_context(self, error_lines: List[str]) -> Dict:
        """Извлекает контекст ошибки"""
        if not error_lines:
            return {}
        
        # Находим основную ошибку
        main_error = error_lines[0].strip()
        
        # Извлекаем timestamp
        timestamp_match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', main_error)
        timestamp = timestamp_match.group(1) if timestamp_match else datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Определяем тип ошибки
        error_type = "Unknown"
        if "Exception" in main_error:
            error_type = "Exception"
        elif "ERROR" in main_error:
            error_type = "Error"
        elif "CRITICAL" in main_error:
            error_type = "Critical"
        elif "❌" in main_error:
            error_type = "User Error"
        
        return {
            "timestamp": timestamp,
            "error_type": error_type,
            "main_error": main_error,
            "full_context": "\n".join(error_lines),
            "log_file": self.log_file
        }
    
    def send_to_cursor(self, error_data: Dict) -> bool:
        """Отправляет ошибку в Cursor для автоматического исправления"""
        if not self.cursor_api_url:
            logger.warning("CURSOR_API_URL не настроен, пропускаем отправку")
            return False
        
        try:
            # Формируем сообщение для Cursor
            cursor_message = {
                "type": "error_report",
                "timestamp": datetime.now().isoformat(),
                "error_data": error_data,
                "request": "auto_fix",
                "context": {
                    "project": "telegram-chat-analyzer-bot",
                    "files": get_cursor_files(),
                    "priority": get_error_priority(error_data["error_type"])
                }
            }
            
            # Отправляем в Cursor
            response = requests.post(
                self.cursor_api_url,
                json=cursor_message,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"Ошибка отправлена в Cursor: {error_data['error_type']}")
                return True
            else:
                logger.error(f"Ошибка отправки в Cursor: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Ошибка отправки в Cursor: {e}")
            return False
    
    def create_error_report(self, error_data: Dict) -> str:
        """Создает отчет об ошибке для локального сохранения"""
        report = f"""
🚨 ОТЧЕТ ОБ ОШИБКЕ
==================
📅 Время: {error_data['timestamp']}
🔍 Тип: {error_data['error_type']}
📁 Файл: {error_data['log_file']}

❌ Ошибка:
{error_data['main_error']}

📋 Полный контекст:
{error_data['full_context']}

🛠️ Рекомендации:
- Проверьте логи для дополнительной информации
- Убедитесь, что все зависимости установлены
- Проверьте подключение к базе данных
- Проверьте токен бота и права доступа

⏰ Отчет создан: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        return report
    
    def save_error_report(self, error_data: Dict):
        """Сохраняет отчет об ошибке локально"""
        try:
            reports_dir = Path("error_reports")
            reports_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            report_file = reports_dir / f"error_report_{timestamp}.txt"
            
            report_content = self.create_error_report(error_data)
            
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(report_content)
            
            logger.info(f"Отчет об ошибке сохранен: {report_file}")
            
        except Exception as e:
            logger.error(f"Ошибка сохранения отчета: {e}")
    
    def monitor(self, interval: int = 30):
        """Основной цикл мониторинга"""
        logger.info(f"Запуск мониторинга логов: {self.log_file}")
        logger.info(f"Интервал проверки: {interval} секунд")
        
        while True:
            try:
                # Читаем новые логи
                new_lines = self.read_new_logs()
                
                if new_lines:
                    # Ищем ошибки
                    error_lines = []
                    for line in new_lines:
                        if self.is_error_line(line):
                            error_lines.append(line)
                    
                    # Обрабатываем найденные ошибки
                    if error_lines:
                        error_data = self.extract_error_context(error_lines)
                        
                        # Сохраняем локально
                        self.save_error_report(error_data)
                        
                        # Отправляем в Cursor
                        self.send_to_cursor(error_data)
                        
                        # Логируем
                        logger.warning(f"Найдена ошибка: {error_data['error_type']} - {error_data['main_error']}")
                
                # Ждем следующей проверки
                time.sleep(interval)
                
            except KeyboardInterrupt:
                logger.info("Мониторинг остановлен пользователем")
                break
            except Exception as e:
                logger.error(f"Ошибка в цикле мониторинга: {e}")
                time.sleep(interval)

def main():
    """Точка входа"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Мониторинг логов и отправка ошибок в Cursor")
    parser.add_argument("--log-file", default="bot.log", help="Путь к лог файлу")
    parser.add_argument("--interval", type=int, default=30, help="Интервал проверки в секундах")
    parser.add_argument("--cursor-url", help="URL API Cursor")
    
    args = parser.parse_args()
    
    # Создаем монитор
    monitor = LogMonitor(
        log_file=args.log_file,
        cursor_api_url=args.cursor_url
    )
    
    # Запускаем мониторинг
    monitor.monitor(interval=args.interval)

if __name__ == "__main__":
    main()
