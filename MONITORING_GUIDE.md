# 🚨 Система автоматического мониторинга логов

## 📋 Описание

Система автоматически отслеживает ошибки в логах бота и отправляет их в Cursor для автоматического исправления.

## 🚀 Быстрый старт

### 1. Запуск мониторинга отдельно
```bash
python3 start_monitor.py
```

### 2. Запуск с параметрами
```bash
python3 log_monitor.py --log-file bot.log --interval 30 --cursor-url YOUR_CURSOR_API_URL
```

### 3. Автоматический запуск с ботом
Мониторинг автоматически запускается при старте `webhook_server.py`

## ⚙️ Настройка

### Переменные окружения
```bash
# URL для отправки ошибок в Cursor
export CURSOR_API_URL="https://your-cursor-api.com/errors"

# Или добавьте в .env файл
CURSOR_API_URL=https://your-cursor-api.com/errors
```

### Конфигурация в monitor_config.py
```python
MONITOR_CONFIG = {
    "log_file": "bot.log",
    "check_interval": 30,
    "cursor_api_url": os.getenv('CURSOR_API_URL'),
    # ... другие настройки
}
```

## 🔍 Что отслеживается

### Типы ошибок
- ❌ **Critical** - Критические ошибки
- 🚨 **Exception** - Исключения Python
- ⚠️ **Error** - Обычные ошибки
- 💬 **User Error** - Ошибки пользователя

### Паттерны поиска
- `ERROR.*`
- `CRITICAL.*`
- `Exception.*`
- `Traceback.*`
- `Failed.*`
- `❌.*`
- И многие другие...

### Игнорируемые предупреждения
- `NotOpenSSLWarning.*`
- `DeprecationWarning.*`
- `UserWarning.*`
- `INFO.*`
- `DEBUG.*`

## 📊 Отчеты

### Локальное сохранение
Отчеты сохраняются в папку `error_reports/`:
```
error_reports/
├── error_report_20240812_143022.txt
├── error_report_20240812_143156.txt
└── ...
```

### Формат отчета
```
🚨 ОТЧЕТ ОБ ОШИБКЕ
==================
📅 Время: 2024-08-12 14:30:22
🔍 Тип: Exception
📁 Файл: bot.log

❌ Ошибка:
2024-08-12 14:30:22,123 - ERROR - Connection failed

📋 Полный контекст:
2024-08-12 14:30:22,123 - ERROR - Connection failed
2024-08-12 14:30:22,124 - ERROR - Retrying...

🛠️ Рекомендации:
- Проверьте логи для дополнительной информации
- Убедитесь, что все зависимости установлены
- Проверьте подключение к базе данных
- Проверьте токен бота и права доступа

⏰ Отчет создан: 2024-08-12 14:30:22
```

## 🔧 Отправка в Cursor

### Формат сообщения
```json
{
  "type": "error_report",
  "timestamp": "2024-08-12T14:30:22.123456",
  "error_data": {
    "timestamp": "2024-08-12 14:30:22",
    "error_type": "Exception",
    "main_error": "Connection failed",
    "full_context": "...",
    "log_file": "bot.log"
  },
  "request": "auto_fix",
  "context": {
    "project": "telegram-chat-analyzer-bot",
    "files": [
      "webhook_server.py",
      "database.py",
      "message_collector.py",
      "text_analyzer.py",
      "report_generator.py",
      "conversation_analyzer.py",
      "task_manager.py",
      "timezone_utils.py"
    ],
    "priority": "high"
  }
}
```

## 🎯 Приоритеты ошибок

| Тип ошибки | Приоритет | Описание |
|------------|-----------|----------|
| Critical | high | Критические ошибки |
| Exception | high | Исключения Python |
| Error | medium | Обычные ошибки |
| User Error | low | Ошибки пользователя |
| Unknown | medium | Неизвестные ошибки |

## 📁 Структура файлов

```
├── log_monitor.py          # Основной модуль мониторинга
├── monitor_config.py       # Конфигурация
├── start_monitor.py        # Скрипт запуска
├── MONITORING_GUIDE.md     # Это руководство
├── error_reports/          # Папка с отчетами
└── bot.log                 # Лог файл для мониторинга
```

## 🛠️ Команды управления

### Запуск мониторинга
```bash
# Простой запуск
python3 start_monitor.py

# С параметрами
python3 log_monitor.py --log-file bot.log --interval 60

# В фоновом режиме
nohup python3 start_monitor.py > monitor.log 2>&1 &
```

### Остановка мониторинга
```bash
# Найти процесс
ps aux | grep log_monitor

# Остановить процесс
kill -TERM <PID>

# Или Ctrl+C в терминале
```

### Просмотр отчетов
```bash
# Последние отчеты
ls -la error_reports/

# Просмотр отчета
cat error_reports/error_report_20240812_143022.txt

# Поиск по ошибкам
grep -r "Connection failed" error_reports/
```

## 🔄 Интеграция с ботом

Мониторинг автоматически интегрирован в `webhook_server.py`:

```python
# В конструкторе CloudChatAnalyzerBot
self.log_monitor = LogMonitor(log_file="bot.log")
self.monitor_thread = threading.Thread(target=self._start_log_monitoring, daemon=True)
self.monitor_thread.start()
```

## 📈 Мониторинг производительности

### Метрики
- Количество найденных ошибок
- Время обработки ошибок
- Успешность отправки в Cursor
- Размер файлов отчетов

### Логи мониторинга
```bash
# Просмотр логов мониторинга
tail -f monitor.log

# Поиск ошибок в мониторинге
grep "ERROR" monitor.log
```

## 🚨 Устранение неполадок

### Мониторинг не запускается
1. Проверьте наличие `bot.log`
2. Проверьте права доступа к файлам
3. Убедитесь, что все зависимости установлены

### Ошибки не отправляются в Cursor
1. Проверьте `CURSOR_API_URL`
2. Проверьте сетевое подключение
3. Проверьте формат URL

### Слишком много отчетов
1. Настройте `max_reports_per_hour` в конфигурации
2. Добавьте паттерны в `ignored_patterns`
3. Увеличьте `check_interval`

## 📞 Поддержка

При возникновении проблем:
1. Проверьте логи мониторинга
2. Просмотрите отчеты в `error_reports/`
3. Проверьте конфигурацию в `monitor_config.py`
4. Убедитесь, что все переменные окружения настроены

---

**🎯 Система готова к использованию! Автоматическое исправление ошибок теперь работает!**
