#!/usr/bin/env python3
"""
Веб-сервер для работы с Telegram webhook в облаке
"""

import os
import logging
import time
from datetime import datetime
from typing import Dict
from flask import Flask, request, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
import threading

from config import BOT_TOKEN, ADMIN_USER_IDS, HISTORY_DAYS, REPORT_TIME, TASK_TIMEOUT_HOURS
from database import DatabaseManager
from text_analyzer import TextAnalyzer
from report_generator import ReportGenerator
from message_collector import MessageCollector
from timezone_utils import timezone_manager
from conversation_analyzer import ConversationAnalyzer
from log_monitor import LogMonitor
from pathlib import Path

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

class CloudChatAnalyzerBot:
    def __init__(self):
        self.db = DatabaseManager()
        self.text_analyzer = TextAnalyzer()
        self.report_generator = ReportGenerator()
        self.message_collector = MessageCollector(BOT_TOKEN, self.db, self.text_analyzer)
        self.conversation_analyzer = ConversationAnalyzer()
        self.active_chats = set()
        self.processed_updates = set()  # Для предотвращения дублирования
        self.last_commands = {}  # Для отслеживания последних команд пользователей
        
        # Инициализируем мониторинг логов
        self.log_monitor = LogMonitor(
            log_file="bot.log",
            bot_token=BOT_TOKEN,
            admin_ids=ADMIN_USER_IDS
        )
        self.monitor_thread = threading.Thread(target=self._start_log_monitoring, daemon=True)
        self.monitor_thread.start()
        
        # Создаем приложение
        self.application = Application.builder().token(BOT_TOKEN).build()
        
        # Добавляем обработчики
        self._setup_handlers()
        
        # Инициализируем приложение
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        loop.run_until_complete(self.application.initialize())
        
        # Запускаем планировщик в отдельном потоке
        self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
    
    def _setup_handlers(self):
        """Настраивает обработчики команд"""
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("report", self.generate_report))
        self.application.add_handler(CommandHandler("tasks", self.show_tasks))
        self.application.add_handler(CommandHandler("mentions", self.show_mentions))
        self.application.add_handler(CommandHandler("activity", self.show_activity))
        self.application.add_handler(CommandHandler("topics", self.show_topics))
        self.application.add_handler(CommandHandler("wordcloud", self.show_wordcloud))
        self.application.add_handler(CommandHandler("admin", self.admin_panel))
        self.application.add_handler(CommandHandler("collect_history", self.collect_history))
        self.application.add_handler(CommandHandler("collect_chat", self.collect_chat_history))
        self.application.add_handler(CommandHandler("daily_report", self.generate_daily_report))
        self.application.add_handler(CommandHandler("myid", self.show_my_id))
        self.application.add_handler(CommandHandler("setup_monitoring", self.setup_monitoring))
        self.application.add_handler(CommandHandler("groups", self.show_groups))
        self.application.add_handler(CommandHandler("group_report", self.group_report))
        self.application.add_handler(CommandHandler("group_activity", self.group_activity))
        self.application.add_handler(CommandHandler("group_mentions", self.group_mentions))
        self.application.add_handler(CommandHandler("temperature", self.analyze_temperature))
        self.application.add_handler(CommandHandler("status", self.check_status))
        self.application.add_handler(CommandHandler("debug_groups", self.debug_groups))
        self.application.add_handler(CommandHandler("monitor_status", self.monitor_status))
        self.application.add_handler(CommandHandler("monitor_test", self.monitor_test))
        self.application.add_handler(CommandHandler("monitor_summary", self.monitor_summary))
        self.application.add_handler(CommandHandler("monitor_errors", self.monitor_errors))
        self.application.add_handler(CommandHandler("monitor_clear", self.monitor_clear))
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        
        # Обработчик сообщений
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        # Обработчик кнопок
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        
        # Обработчик ошибок
        self.application.add_error_handler(self.error_handler)
    
    async def start(self, update: Update, context):
        """Обработчик команды /start"""
        user = update.effective_user
        chat_id = update.effective_chat.id
        message_id = update.message.message_id
        
        # Проверяем дублирование команды
        if self._is_duplicate_command(user.id, 'start', message_id):
            return
        
        # Логируем команду
        logger.info(f"Команда /start от пользователя {user.id} в чате {chat_id}")
        
        # Определяем тип чата
        chat_type = "личных сообщениях" if chat_id > 0 else "группе"
        
        welcome_message = f"""
🤖 **Добро пожаловать в Chat Analyzer Bot!**

Привет, {user.first_name}! Я помогу вам анализировать активность в рабочих чатах.

**🎯 Основные возможности:**
📊 **Сбор и анализ данных** - автоматический сбор истории переписки за {HISTORY_DAYS} дней
📈 **Активность пользователей** - кто сколько общается и на какие темы
🎯 **Анализ тем** - определение популярных тем обсуждения
✅ **Управление задачами** - отслеживание задач и их выполнения
👥 **Статистика упоминаний** - кто кого чаще всего упоминает
🌡️ **AI-анализ температуры** - оценка эмоционального климата бесед
📋 **Детальные отчеты** - ежедневные и еженедельные отчеты

**📱 Команды для всех пользователей:**
/start - показать это сообщение
/help - подробная справка по всем командам
/report - получить отчет по активности в текущей группе
/tasks - показать активные задачи
/mentions - статистика упоминаний
/activity - активность пользователей
/topics - популярные темы обсуждения
/wordcloud - облако слов из сообщений

**🔧 Команды для администраторов (в личных сообщениях):**
/groups - список всех групп с интерактивными кнопками
/temperature <ID группы> - AI-анализ температуры беседы
/status - проверить статус бота и права доступа
/myid - показать ваш ID и права администратора
/collect_history - собрать историю сообщений
/daily_report - настроить ежедневные отчеты

**💡 Как начать работу:**
1. Добавьте бота в группу
2. Используйте /collect_history для сбора данных
3. В личных сообщениях используйте /groups для анализа

**🌐 Текущий чат:** {chat_type}
        """
        
        await update.message.reply_text(welcome_message)
        self.active_chats.add(chat_id)
    
    async def help_command(self, update: Update, context):
        """Обработчик команды /help"""
        user = update.effective_user
        chat_id = update.effective_chat.id
        
        # Определяем тип чата
        chat_type = "личных сообщениях" if chat_id > 0 else "группе"
        
        help_text = f"""
📚 **ПОДРОБНАЯ СПРАВКА ПО КОМАНДАМ**

**🌐 Текущий чат:** {chat_type}

**📱 ОСНОВНЫЕ КОМАНДЫ (работают везде):**

📊 **Анализ и отчеты:**
/report [дни] - получить отчет по активности в текущей группе
/activity - активность пользователей по дням
/mentions - статистика упоминаний пользователей
/topics - популярные темы обсуждения
/wordcloud - облако слов из сообщений

✅ **Управление задачами:**
/tasks - показать активные задачи
/task_add @username описание - добавить задачу пользователю
/task_complete ID - отметить задачу как выполненную
/task_list - список всех задач

**🔧 КОМАНДЫ ДЛЯ АДМИНИСТРАТОРОВ:**

**В группах:**
/collect_history [дни] - собрать историю сообщений (по умолчанию {HISTORY_DAYS} дней)
/admin - панель администратора
/myid - показать ваш ID и права доступа

**В личных сообщениях:**
/groups - список всех групп с интерактивными кнопками
/temperature <ID группы> - AI-анализ температуры беседы
/status - проверить статус бота и права доступа
/daily_report - настроить ежедневные отчеты

**📋 ДЕТАЛЬНЫЕ КОМАНДЫ (в личных сообщениях):**
/group_report <ID группы> [дни] - подробный отчет по конкретной группе
/group_activity <ID группы> [дни] - активность пользователей в группе
/group_mentions <ID группы> [дни] - статистика упоминаний в группе
/debug_groups - отладочная информация о группах

🔍 **КОМАНДЫ МОНИТОРИНГА:**
/monitor_status - статус системы мониторинга
/monitor_test - тест уведомлений мониторинга
/monitor_summary - сводка по мониторингу
/monitor_errors - последние ошибки из отчетов
/monitor_clear - очистить старые отчеты (старше 7 дней)

**🎯 ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ:**

**В группе:**
/report 7 - отчет за последние 7 дней
/collect_history 30 - собрать историю за 30 дней
/task_add @ivan подготовить презентацию к завтра

**В личных сообщениях:**
/groups - выбрать группу для анализа
/temperature -1001335359141 - анализ температуры в группе
/group_report -1001335359141 7 - отчет по группе за неделю

**💡 ПОЛЕЗНЫЕ СОВЕТЫ:**
• Используйте /groups в личных сообщениях для удобного выбора группы
• Команда /collect_history должна выполняться в группе для сбора данных
• AI-анализ температуры работает только с собранными данными
• Все отчеты автоматически сохраняются в базе данных

**🔍 ДОПОЛНИТЕЛЬНАЯ ИНФОРМАЦИЯ:**
• Бот автоматически сохраняет все сообщения в базу данных
• Данные сохраняются между перезапусками бота
• Анализ температуры использует AI для оценки эмоционального климата
• Интерактивные кнопки доступны только в личных сообщениях
        """
        
        await update.message.reply_text(help_text)
    
    async def handle_message(self, update: Update, context):
        """Обработчик всех сообщений"""
        if not update.message or not update.message.text:
            return
        
        message = update.message
        chat_id = message.chat.id
        user = message.from_user
        
        # Получаем имя пользователя для отображения
        user_display_name = self._get_user_display_name(user)
        
        # Сохраняем сообщение в базу данных
        message_data = {
            'message_id': message.message_id,
            'chat_id': chat_id,
            'user_id': user.id,
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'display_name': user_display_name,
            'text': message.text,
            'date': int(message.date.timestamp()),
            'reply_to_message_id': message.reply_to_message.message_id if message.reply_to_message else None,
            'forward_from_user_id': message.forward_from.id if message.forward_from else None,
            'is_edited': False,
            'edit_date': None
        }
        
        message_id = self.db.save_message(message_data)
        self.db.update_user_activity(user.id, chat_id, message.date, user_display_name)
        
        # Сохраняем информацию о группе
        chat_info = {
            'chat_id': chat_id,
            'chat_type': message.chat.type,
            'title': message.chat.title,
            'username': message.chat.username,
            'first_name': message.chat.first_name,
            'last_name': message.chat.last_name,
            'description': getattr(message.chat, 'description', None),
            'member_count': getattr(message.chat, 'member_count', None)
        }
        self.db.save_chat_info(chat_info)
        
        # Анализируем текст сообщения
        text = message.text
        
        # Извлекаем упоминания
        mentions = self.text_analyzer.extract_mentions(text)
        for mention in mentions:
            mention_data = {
                'message_id': message_id,
                'mentioned_user_id': 0,
                'mentioned_username': mention,
                'mention_type': 'username'
            }
            self.db.save_mention(mention_data)
        
        # Извлекаем задачи
        tasks = self.text_analyzer.extract_tasks(text)
        for task in tasks:
            if task['assigned_to']:
                task_data = {
                    'message_id': message_id,
                    'chat_id': chat_id,
                    'assigned_by_user_id': user.id,
                    'assigned_to_user_id': 0,
                    'task_text': task['task_text'],
                    'status': 'pending'
                }
                self.db.save_task(task_data)
    
    async def generate_report(self, update: Update, context):
        """Генерирует отчет по активности"""
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        message_id = update.message.message_id
        
        # Проверяем дублирование команды
        if self._is_duplicate_command(user_id, 'report', message_id):
            return
        
        # Логируем команду
        logger.info(f"Команда /report от пользователя {user_id} в чате {chat_id}")
        
        days = 1
        if context.args:
            try:
                days = int(context.args[0])
            except ValueError:
                await update.message.reply_text("❌ Неверный формат количества дней. Используйте число.")
                return
        
        messages = self.db.get_messages_for_period(chat_id, days)
        user_stats = self.db.get_user_activity_stats(chat_id, days)
        mention_stats = self.db.get_mention_stats(chat_id, days)
        task_stats = self.db.get_task_stats(chat_id, days)
        
        texts = [msg['text'] for msg in messages if msg['text']]
        topic_distribution = self.text_analyzer.get_topic_distribution(texts)
        conversation_flow = self.text_analyzer.analyze_conversation_flow(messages)
        
        # Анализируем активность по часам с учетом часового пояса
        hourly_activity = timezone_manager.get_activity_hours(messages, 'Europe/Moscow')
        
        chat_data = {
            'total_messages': len(messages),
            'active_users': len(user_stats),
            'total_mentions': sum(m['mention_count'] for m in mention_stats),
            'top_users': user_stats[:5],
            'popular_topics': sorted(topic_distribution.items(), key=lambda x: x[1], reverse=True)[:5],
            'task_stats': task_stats,
            'hourly_activity': hourly_activity
        }
        
        report = self.report_generator.generate_daily_report(chat_data)
        await update.message.reply_text(report)
    
    async def show_tasks(self, update: Update, context):
        """Показывает активные задачи"""
        chat_id = update.effective_chat.id
        tasks = self.db.get_pending_tasks(chat_id)
        
        if not tasks:
            await update.message.reply_text("✅ Нет активных задач!")
            return
        
        task_report = self.report_generator.generate_task_report(tasks)
        await update.message.reply_text(task_report, parse_mode='Markdown')
    
    async def show_mentions(self, update: Update, context):
        """Показывает статистику упоминаний"""
        chat_id = update.effective_chat.id
        mentions = self.db.get_mention_stats(chat_id, 7)
        
        mention_report = self.report_generator.generate_mention_report(mentions)
        await update.message.reply_text(mention_report, parse_mode='Markdown')
    
    async def show_activity(self, update: Update, context):
        """Показывает активность пользователей"""
        chat_id = update.effective_chat.id
        user_stats = self.db.get_user_activity_stats(chat_id, 7)
        
        if not user_stats:
            await update.message.reply_text("📊 Нет данных об активности пользователей")
            return
        
        activity_text = "👥 **АКТИВНОСТЬ ПОЛЬЗОВАТЕЛЕЙ:**\n\n"
        for i, user in enumerate(user_stats[:10], 1):
            name = user.get('name', f"Пользователь {user['user_id']}")
            time_spent = self.report_generator.format_time_spent(user.get('total_time_minutes', 0))
            activity_text += f"{i}. {name}\n"
            activity_text += f"   📝 Сообщений: {user['messages_count']}\n"
            activity_text += f"   ⏱ Время в чате: {time_spent}\n\n"
        
        await update.message.reply_text(activity_text, parse_mode='Markdown')
    
    async def show_topics(self, update: Update, context):
        """Показывает популярные темы"""
        chat_id = update.effective_chat.id
        messages = self.db.get_messages_for_period(chat_id, 7)
        
        texts = [msg['text'] for msg in messages if msg['text']]
        topic_distribution = self.text_analyzer.get_topic_distribution(texts)
        
        if not topic_distribution:
            await update.message.reply_text("🎯 Нет данных о темах обсуждения")
            return
        
        topics_text = "🎯 **ПОПУЛЯРНЫЕ ТЕМЫ:**\n\n"
        for topic, count in sorted(topic_distribution.items(), key=lambda x: x[1], reverse=True):
            topics_text += f"• {topic}: {count} упоминаний\n"
        
        await update.message.reply_text(topics_text, parse_mode='Markdown')
    
    async def show_wordcloud(self, update: Update, context):
        """Показывает облако слов"""
        chat_id = update.effective_chat.id
        messages = self.db.get_messages_for_period(chat_id, 7)
        
        texts = [msg['text'] for msg in messages if msg['text']]
        word_data = self.text_analyzer.generate_word_cloud_data(texts)
        
        if not word_data:
            await update.message.reply_text("☁️ Недостаточно данных для создания облака слов")
            return
        
        # Формируем отчет о популярных словах
        wordcloud_report = "☁️ **ОБЛАКО СЛОВ**\n\n"
        wordcloud_report += f"📊 **Популярные слова в чате за последние 7 дней:**\n\n"
        
        # Показываем топ-15 слов
        for i, (word, count) in enumerate(word_data[:15], 1):
            # Добавляем эмодзи в зависимости от частоты
            if count >= 10:
                emoji = "🔥"
            elif count >= 5:
                emoji = "⭐"
            elif count >= 3:
                emoji = "💬"
            else:
                emoji = "📝"
            
            wordcloud_report += f"{i}. {emoji} **{word}** - {count} раз\n"
        
        wordcloud_report += f"\n📈 **Всего уникальных слов:** {len(word_data)}"
        wordcloud_report += f"\n💬 **Проанализировано сообщений:** {len(texts)}"
        
        await update.message.reply_text(wordcloud_report, parse_mode='Markdown')
    
    async def button_callback(self, update: Update, context):
        """Обработчик нажатий на кнопки"""
        query = update.callback_query
        await query.answer()
        
        if query.data.startswith("complete_task_"):
            task_id = int(query.data.split("_")[2])
            self.db.mark_task_completed(task_id)
            await query.edit_message_text("✅ Задача отмечена как выполненная!")
    
    async def admin_panel(self, update: Update, context):
        """Панель администратора"""
        user_id = update.effective_user.id
        
        if user_id not in ADMIN_USER_IDS:
            await update.message.reply_text("❌ У вас нет прав администратора")
            return
        
        await update.message.reply_text("🔧 Панель администратора доступна")
    
    async def collect_history(self, update: Update, context):
        """Собирает историю сообщений"""
        user_id = update.effective_user.id
        message_id = update.message.message_id
        chat_id = update.effective_chat.id
        
        # Проверяем дублирование команды
        if self._is_duplicate_command(user_id, 'collect_history', message_id):
            return
        
        if user_id not in ADMIN_USER_IDS:
            await update.message.reply_text("❌ У вас нет прав администратора")
            return
        
        # Логируем команду
        logger.info(f"Команда /collect_history от пользователя {user_id} в чате {chat_id}")
        
        # Отправляем сообщение о начале сбора
        status_message = await update.message.reply_text("🔄 Начинаем сбор истории сообщений...")
        
        try:
            # Получаем количество дней из аргументов или используем значение по умолчанию
            days = HISTORY_DAYS
            if context.args:
                try:
                    days = int(context.args[0])
                except ValueError:
                    await status_message.edit_text("❌ Неверный формат количества дней. Используйте число.")
                    return
            
            # Функция для обновления прогресса
            async def update_progress(message):
                await status_message.edit_text(f"🔄 **Сбор истории...**\n\n{message}")
            
            # Запускаем сбор истории с прогрессом
            result = await self.message_collector.collect_chat_history(chat_id, days, update_progress)
            
            if result.get('error'):
                await status_message.edit_text(f"❌ Ошибка при сборе истории: {result['error']}")
            else:
                # Формируем подробный отчет о результатах
                source_info = ""
                if result.get('source') == 'database':
                    source_info = " (из базы данных)"
                elif result.get('source') == 'demo_data':
                    source_info = " (демо-данные)"
                
                # Определяем статус выполнения
                steps_completed = result.get('steps_completed', [])
                status_emoji = "✅" if len(steps_completed) > 0 else "⚠️"
                
                report = f"""
{status_emoji} **Сбор истории завершен!**

📋 **Результаты:**
• Чат: {result.get('chat_title', f'ID: {chat_id}')}
• Период: {result.get('period_days', days)} дней
• Собрано сообщений: {result.get('messages_collected', 0)}{source_info}
• Уникальных пользователей: {result.get('users_found', 0)}

📅 **Период сбора:**
• С: {result.get('start_date', '').strftime('%d.%m.%Y') if result.get('start_date') else 'N/A'}
• По: {result.get('end_date', '').strftime('%d.%m.%Y') if result.get('end_date') else 'N/A'}

💾 **Источник данных:**
• {result.get('source', 'новые сообщения')}

🔧 **Выполненные шаги:**
"""
                
                # Добавляем выполненные шаги
                step_descriptions = {
                    'chat_info': '• ✅ Получена информация о чате',
                    'database_check': '• ✅ Проверена база данных',
                    'existing_data_analysis': '• ✅ Проанализированы существующие данные',
                    'demo_data_creation': '• ✅ Созданы демонстрационные данные'
                }
                
                for step in steps_completed:
                    if step in step_descriptions:
                        report += step_descriptions[step] + "\n"
                
                report += f"""
💡 **Теперь вы можете использовать команды:**
• `/report` - получить отчет по активности
• `/activity` - активность пользователей
• `/mentions` - статистика упоминаний
• `/topics` - популярные темы
• `/wordcloud` - облако слов

🚀 **Для AI-анализа используйте личные сообщения:**
• `/groups` - выбрать группу для анализа
• `/temperature` - AI-анализ температуры беседы
"""
                await status_message.edit_text(report, parse_mode='Markdown')
                
        except Exception as e:
            logger.error(f"Ошибка при сборе истории: {e}")
            await status_message.edit_text(f"❌ Ошибка при сборе истории: {str(e)}")
    
    async def collect_chat_history(self, update: Update, context):
        """Собирает историю конкретного чата"""
        user_id = update.effective_user.id
        
        if user_id not in ADMIN_USER_IDS:
            await update.message.reply_text("❌ У вас нет прав администратора")
            return
        
        # Получаем ID чата из аргументов или текущего чата
        if context.args:
            try:
                chat_id = int(context.args[0])
            except ValueError:
                await update.message.reply_text("❌ Неверный формат ID чата. Используйте: /collect_chat <chat_id>")
                return
        else:
            chat_id = update.effective_chat.id
        
        # Получаем количество дней
        days = 45
        if len(context.args) > 1:
            try:
                days = int(context.args[1])
            except ValueError:
                await update.message.reply_text("❌ Неверный формат количества дней")
                return
        
        await update.message.reply_text(f"📥 Начинаем сбор истории для чата {chat_id} за последние {days} дней...")
        
        try:
            # Запускаем сбор в отдельном потоке
            def collect_async():
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(self.message_collector.collect_chat_history(chat_id, days))
                loop.close()
                return result
            
            import threading
            thread = threading.Thread(target=collect_async)
            thread.start()
            
            await update.message.reply_text("✅ Сбор истории запущен в фоновом режиме!")
            
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка при сборе истории: {e}")
    
    async def generate_daily_report(self, update: Update, context):
        """Генерирует ежедневный отчет"""
        user_id = update.effective_user.id
        
        if user_id not in ADMIN_USER_IDS:
            await update.message.reply_text("❌ У вас нет прав администратора")
            return
        
        # Получаем ID чата
        if context.args:
            try:
                chat_id = int(context.args[0])
            except ValueError:
                await update.message.reply_text("❌ Неверный формат ID чата. Используйте: /daily_report <chat_id>")
                return
        else:
            chat_id = update.effective_chat.id
        
        await update.message.reply_text(f"📊 Генерируем ежедневный отчет для чата {chat_id}...")
        
        try:
            report = await self.message_collector.generate_daily_report(chat_id)
            
            # Формируем отчет
            report_text = f"""
📊 **ЕЖЕДНЕВНЫЙ ОТЧЕТ**
📅 Дата: {report['date']}
📋 Чат ID: {report['chat_id']}

📈 **СТАТИСТИКА:**
• Всего сообщений: {report['total_messages']}
• Активных пользователей: {report['active_users']}
• Упоминаний: {report['total_mentions']}
• Среднее время ответа: {report['avg_response_time']:.1f} мин

👥 **ТОП АКТИВНЫХ ПОЛЬЗОВАТЕЛЕЙ:**
"""
            
            for i, user in enumerate(report['top_users'][:3], 1):
                name = user.get('name', f"Пользователь {user['user_id']}")
                report_text += f"{i}. {name}: {user['messages_count']} сообщений\n"
            
            report_text += "\n🎯 **ПОПУЛЯРНЫЕ ТЕМЫ:**\n"
            for topic, count in report['popular_topics'][:3]:
                report_text += f"• {topic}: {count} упоминаний\n"
            
            if report['task_stats']:
                task_stats = report['task_stats']
                report_text += f"\n✅ **ЗАДАЧИ:**\n"
                report_text += f"• Всего: {task_stats.get('total_tasks', 0)}\n"
                report_text += f"• Выполнено: {task_stats.get('status_stats', {}).get('completed', 0)}\n"
                report_text += f"• В работе: {task_stats.get('status_stats', {}).get('pending', 0)}\n"
            
            await update.message.reply_text(report_text, parse_mode='Markdown')
            
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка при генерации отчета: {e}")
    
    async def setup_monitoring(self, update: Update, context):
        """Настраивает мониторинг чатов"""
        user_id = update.effective_user.id
        
        if user_id not in ADMIN_USER_IDS:
            await update.message.reply_text("❌ У вас нет прав администратора")
            return
        
        # Получаем список чатов для мониторинга
        if not context.args:
            await update.message.reply_text("❌ Укажите ID чатов для мониторинга. Используйте: /setup_monitoring <chat_id1> <chat_id2> ...")
            return
        
        chat_ids = []
        for arg in context.args:
            try:
                chat_ids.append(int(arg))
            except ValueError:
                await update.message.reply_text(f"❌ Неверный формат ID чата: {arg}")
                return
        
        await update.message.reply_text(f"📅 Настраиваем мониторинг для {len(chat_ids)} чатов...")
        
        try:
            await self.message_collector.schedule_daily_collection(chat_ids)
            await update.message.reply_text(f"✅ Мониторинг настроен для чатов: {', '.join(map(str, chat_ids))}")
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка при настройке мониторинга: {e}")
    
    async def error_handler(self, update: Update, context):
        """Обработчик ошибок"""
        logger.error(f"Ошибка при обработке обновления {update}: {context.error}")
    
    def _run_scheduler(self):
        """Запускает планировщик задач"""
        while True:
            time.sleep(60)
    
    def _start_log_monitoring(self):
        """Запускает мониторинг логов"""
        try:
            logger.info("Запуск автоматического мониторинга логов")
            self.log_monitor.monitor(interval=30)  # Проверяем каждые 30 секунд
        except Exception as e:
            logger.error(f"Ошибка в мониторинге логов: {e}")
    
    async def handle_webhook(self, update_dict):
        """Обрабатывает webhook от Telegram"""
        update = Update.de_json(update_dict, self.application.bot)
        
        # Ограничиваем размер множества обработанных обновлений
        if len(self.processed_updates) > 1000:
            # Удаляем старые записи
            self.processed_updates = set(list(self.processed_updates)[-500:])
        
        # Логируем обработку обновления
        if update.message:
            user = update.message.from_user
            chat = update.message.chat
            logger.info(f"Обрабатываем обновление {update.update_id}: пользователь {user.id} в чате {chat.id}")
        
        try:
            # Создаем новый event loop для каждого webhook
            import asyncio
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Обрабатываем обновление
            await self.application.process_update(update)
            logger.info(f"Обновление {update.update_id} успешно обработано")
        except Exception as e:
            logger.error(f"Ошибка при обработке обновления {update.update_id}: {e}")
            # Не поднимаем исключение, чтобы не прерывать обработку
            pass
    
    def _get_user_display_name(self, user):
        """Получает отображаемое имя пользователя"""
        if user.username:
            return f"@{user.username}"
        elif user.first_name and user.last_name:
            return f"{user.first_name} {user.last_name}"
        elif user.first_name:
            return user.first_name
        else:
            return f"Пользователь {user.id}"
    
    def _is_duplicate_command(self, user_id: int, command: str, message_id: int) -> bool:
        """Проверяет, является ли команда дублированной"""
        user_key = f"{user_id}_{command}"
        last_info = self.last_commands.get(user_key)
        
        if last_info and last_info['message_id'] == message_id:
            logger.info(f"Дублированная команда {command} от пользователя {user_id}")
            return True
        
        # Сохраняем информацию о команде
        self.last_commands[user_key] = {
            'message_id': message_id,
            'timestamp': time.time()
        }
        
        # Очищаем старые записи (старше 5 минут)
        current_time = time.time()
        self.last_commands = {
            k: v for k, v in self.last_commands.items() 
            if current_time - v['timestamp'] < 300
        }
        
        return False
    
    async def show_my_id(self, update: Update, context):
        """Показывает ID пользователя и информацию об администраторах"""
        user = update.effective_user
        chat_id = update.effective_chat.id
        
        # Формируем информацию о пользователе
        user_info = f"""
🆔 **Информация о пользователе:**

👤 **Ваш ID:** `{user.id}`
👤 **Имя:** {user.first_name}
👤 **Фамилия:** {user.last_name or 'Не указана'}
👤 **Username:** @{user.username or 'Не указан'}

🔧 **Права администратора:** {'✅ Да' if user.id in ADMIN_USER_IDS else '❌ Нет'}

📋 **Текущие администраторы:** {ADMIN_USER_IDS}

💡 **Для добавления администратора:**
Обновите переменную `ADMIN_USER_IDS` в Railway Dashboard
"""
        
        await update.message.reply_text(user_info, parse_mode='Markdown')
    
    async def show_groups(self, update: Update, context):
        """Показывает список групп, которые мониторит бот"""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        # Проверяем права администратора
        if user_id not in ADMIN_USER_IDS:
            await update.message.reply_text(f"❌ У вас нет прав администратора\nВаш ID: {user_id}\nАдминистраторы: {ADMIN_USER_IDS}")
            return
        
        # Проверяем, что это личные сообщения
        if chat_id > 0:
            # Это личные сообщения - можно показывать группы
            pass
        else:
            # Это группа - отправляем сообщение о том, что нужно использовать личные сообщения
            await update.message.reply_text("💡 Для просмотра списка групп используйте личные сообщения с ботом")
            return
        
        # Получаем список групп из базы данных
        groups = self.db.get_monitored_groups()
        
        if not groups:
            await update.message.reply_text("📋 Пока нет данных о группах. Используйте команду `/collect_history` в группе для начала мониторинга.")
            return
        
        groups_info = "📋 **ГРУППЫ ПОД МОНИТОРИНГОМ:**\n\n"
        
        for i, group in enumerate(groups, 1):
            group_id = group['chat_id']
            group_title = group.get('title', f'Группа {group_id}')
            chat_type = group.get('chat_type', 'группа')
            messages_count = group.get('messages_count', 0)
            users_count = group.get('users_count', 0)
            member_count = group.get('member_count', 0)
            last_activity = group.get('last_activity', 'Неизвестно')
            
            groups_info += f"{i}. **{group_title}**\n"
            groups_info += f"   📋 Тип: {chat_type}\n"
            groups_info += f"   🆔 ID: `{group_id}`\n"
            groups_info += f"   💬 Сообщений: {messages_count}\n"
            groups_info += f"   👥 Активных пользователей: {users_count}\n"
            if member_count:
                groups_info += f"   👤 Всего участников: {member_count}\n"
            groups_info += f"   ⏰ Последняя активность: {last_activity}\n\n"
        
        groups_info += "💡 **Выберите группу для анализа:**\n"
        
        # Создаем кнопки для каждой группы
        keyboard = []
        for group in groups:
            group_id = group['chat_id']
            group_title = group.get('title', f'Группа {group_id}')
            # Ограничиваем длину названия для кнопки
            button_text = group_title[:30] + "..." if len(group_title) > 30 else group_title
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"group_{group_id}")])
        
        # Добавляем кнопки для общих действий
        keyboard.append([
            InlineKeyboardButton("📊 Все отчеты", callback_data="all_reports"),
            InlineKeyboardButton("🌡️ Температура всех", callback_data="all_temperature")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(groups_info, parse_mode='Markdown', reply_markup=reply_markup)
    
    async def group_report(self, update: Update, context):
        """Генерирует отчет по конкретной группе"""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        if user_id not in ADMIN_USER_IDS:
            await update.message.reply_text("❌ У вас нет прав администратора")
            return
        
        # Если команда вызвана в группе, используем текущую группу
        if chat_id < 0:  # Это группа
            target_chat_id = chat_id
            days = 7
            if context.args:
                try:
                    days = int(context.args[0])
                except ValueError:
                    await update.message.reply_text("❌ Неверный формат количества дней. Пример: `/group_report 7`")
                    return
        else:  # Это личные сообщения
            # Получаем ID группы из аргументов
            if not context.args:
                # Показываем список групп
                await self.show_groups(update, context)
                return
            
            try:
                target_chat_id = int(context.args[0])
            except ValueError:
                await update.message.reply_text("❌ Неверный формат ID группы. Пример: `/group_report -1001335359141`")
                return
            
            # Получаем количество дней из аргументов или используем значение по умолчанию
            days = 7
            if len(context.args) > 1:
                try:
                    days = int(context.args[1])
                except ValueError:
                    await update.message.reply_text("❌ Неверный формат количества дней")
                    return
        
        # Получаем данные группы
        messages = self.db.get_messages_for_period(target_chat_id, days)
        user_stats = self.db.get_user_activity_stats(target_chat_id, days)
        mention_stats = self.db.get_mention_stats(target_chat_id, days)
        task_stats = self.db.get_task_stats(target_chat_id, days)
        
        if not messages:
            await update.message.reply_text(f"❌ Нет данных для группы {target_chat_id} за последние {days} дней.")
            return
        
        # Анализируем данные
        texts = [msg['text'] for msg in messages if msg['text']]
        topic_distribution = self.text_analyzer.get_topic_distribution(texts)
        conversation_flow = self.text_analyzer.analyze_conversation_flow(messages)
        
        # Анализируем активность по часам с учетом часового пояса
        hourly_activity = timezone_manager.get_activity_hours(messages, 'Europe/Moscow')
        
        chat_data = {
            'total_messages': len(messages),
            'active_users': len(user_stats),
            'total_mentions': sum(m['mention_count'] for m in mention_stats),
            'top_users': user_stats[:5],
            'popular_topics': sorted(topic_distribution.items(), key=lambda x: x[1], reverse=True)[:5],
            'task_stats': task_stats,
            'hourly_activity': hourly_activity
        }
        
        report = self.report_generator.generate_daily_report(chat_data)
        
        # Получаем информацию о группе
        chat_info = self.db.get_chat_info(target_chat_id)
        group_title = chat_info.get('title', f'Группа {target_chat_id}') if chat_info else f'Группа {target_chat_id}'
        
        # Добавляем заголовок с информацией о группе
        group_info = f"📊 **ОТЧЕТ ПО ГРУППЕ**\n"
        group_info += f"📋 **{group_title}**\n"
        group_info += f"🆔 ID: `{target_chat_id}`\n"
        group_info += f"📅 Период: последние {days} дней\n\n"
        
        full_report = group_info + report
        await update.message.reply_text(full_report)
    
    async def group_activity(self, update: Update, context):
        """Показывает активность пользователей в конкретной группе"""
        user_id = update.effective_user.id
        
        if user_id not in ADMIN_USER_IDS:
            await update.message.reply_text("❌ У вас нет прав администратора")
            return
        
        if not context.args:
            await update.message.reply_text("❌ Укажите ID группы. Пример: `/group_activity -1001335359141`")
            return
        
        try:
            chat_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("❌ Неверный формат ID группы. Используйте число.")
            return
        
        days = 7  # По умолчанию за неделю
        if len(context.args) > 1:
            try:
                days = int(context.args[1])
            except ValueError:
                await update.message.reply_text("❌ Неверный формат количества дней.")
                return
        
        # Получаем статистику активности
        user_stats = self.db.get_user_activity_stats(chat_id, days)
        
        if not user_stats:
            await update.message.reply_text(f"❌ Нет данных об активности в группе {chat_id} за последние {days} дней.")
            return
        
        # Получаем информацию о группе
        chat_info = self.db.get_chat_info(chat_id)
        group_title = chat_info.get('title', f'Группа {chat_id}') if chat_info else f'Группа {chat_id}'
        
        activity_info = f"👥 **АКТИВНОСТЬ ПОЛЬЗОВАТЕЛЕЙ В ГРУППЕ**\n"
        activity_info += f"📋 **{group_title}**\n"
        activity_info += f"🆔 ID: `{chat_id}`\n"
        activity_info += f"📅 Период: последние {days} дней\n\n"
        
        for i, user in enumerate(user_stats[:10], 1):  # Топ 10 пользователей
            display_name = user.get('display_name', f"Пользователь {user['user_id']}")
            messages_count = user['messages_count']
            total_time = user.get('total_time_minutes', 0)
            
            activity_info += f"{i}. **{display_name}**\n"
            activity_info += f"   💬 Сообщений: {messages_count}\n"
            activity_info += f"   ⏱ Время в чате: {total_time} мин\n\n"
        
        await update.message.reply_text(activity_info, parse_mode='Markdown')
    
    async def group_mentions(self, update: Update, context):
        """Показывает статистику упоминаний в конкретной группе"""
        user_id = update.effective_user.id
        
        if user_id not in ADMIN_USER_IDS:
            await update.message.reply_text("❌ У вас нет прав администратора")
            return
        
        if not context.args:
            await update.message.reply_text("❌ Укажите ID группы. Пример: `/group_mentions -1001335359141`")
            return
        
        try:
            chat_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("❌ Неверный формат ID группы. Используйте число.")
            return
        
        days = 7  # По умолчанию за неделю
        if len(context.args) > 1:
            try:
                days = int(context.args[1])
            except ValueError:
                await update.message.reply_text("❌ Неверный формат количества дней.")
                return
        
        # Получаем статистику упоминаний
        mention_stats = self.db.get_mention_stats(chat_id, days)
        
        if not mention_stats:
            await update.message.reply_text(f"❌ Нет данных об упоминаниях в группе {chat_id} за последние {days} дней.")
            return
        
        # Получаем информацию о группе
        chat_info = self.db.get_chat_info(chat_id)
        group_title = chat_info.get('title', f'Группа {chat_id}') if chat_info else f'Группа {chat_id}'
        
        mentions_info = f"📢 **СТАТИСТИКА УПОМИНАНИЙ В ГРУППЕ**\n"
        mentions_info += f"📋 **{group_title}**\n"
        mentions_info += f"🆔 ID: `{chat_id}`\n"
        mentions_info += f"📅 Период: последние {days} дней\n\n"
        
        for i, mention in enumerate(mention_stats[:10], 1):  # Топ 10 упоминаний
            username = mention.get('mentioned_username', 'Неизвестно')
            mention_count = mention['mention_count']
            
            mentions_info += f"{i}. **@{username}**\n"
            mentions_info += f"   📊 Упоминаний: {mention_count}\n\n"
        
        await update.message.reply_text(mentions_info, parse_mode='Markdown')
    
    async def analyze_temperature(self, update: Update, context):
        """Анализирует температуру беседы в группе"""
        user_id = update.effective_user.id
        
        if user_id not in ADMIN_USER_IDS:
            await update.message.reply_text("❌ У вас нет прав администратора")
            return
        
        if not context.args:
            await update.message.reply_text("❌ Укажите ID группы. Пример: `/temperature -1001335359141`")
            return
        
        try:
            chat_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("❌ Неверный формат ID группы. Используйте число.")
            return
        
        days = 7  # По умолчанию за неделю
        if len(context.args) > 1:
            try:
                days = int(context.args[1])
            except ValueError:
                await update.message.reply_text("❌ Неверный формат количества дней.")
                return
        
        # Получаем сообщения для анализа
        messages = self.db.get_messages_for_period(chat_id, days)
        
        if not messages:
            await update.message.reply_text(f"❌ Нет данных для анализа температуры в группе {chat_id} за последние {days} дней.")
            return
        
        # Получаем информацию о группе
        chat_info = self.db.get_chat_info(chat_id)
        group_title = chat_info.get('title', f'Группа {chat_id}') if chat_info else f'Группа {chat_id}'
        
        # Анализируем температуру
        analysis = self.conversation_analyzer.analyze_conversation_temperature(messages, days)
        
        # Формируем отчет
        temperature_emoji = self.conversation_analyzer.get_temperature_emoji(analysis['temperature'])
        
        report = f"""
🌡️ **АНАЛИЗ ТЕМПЕРАТУРЫ БЕСЕДЫ**

📋 **Группа:** {group_title}
🆔 **ID:** `{chat_id}`
📅 **Период:** последние {days} дней

{temperature_emoji} **Температура:** **{analysis['temperature']}/10**
📊 **Уверенность:** {analysis['confidence'] * 100:.0f}%

📝 **Описание:**
{analysis['description']}

📈 **Детали анализа:**
• 💬 Всего сообщений: {analysis['details']['total_messages']}
• 😊 Позитивных: {analysis['details']['emotion_distribution']['positive']}
• 😔 Негативных: {analysis['details']['emotion_distribution']['negative']}
• 😐 Нейтральных: {analysis['details']['emotion_distribution']['neutral']}
• ⚡ Срочных: {analysis['details']['urgency_messages']}
• ❓ Вопросов: {analysis['details']['question_messages']}
• ✅ Решений: {analysis['details']['resolution_messages']}

💡 **Рекомендации:**
{self._get_temperature_recommendations(analysis)}
"""
        
        await update.message.reply_text(report, parse_mode='Markdown')
    
    def _get_temperature_recommendations(self, analysis: Dict) -> str:
        """Генерирует рекомендации на основе анализа температуры"""
        temperature = analysis['temperature']
        details = analysis['details']
        
        recommendations = []
        
        if temperature >= 8.0:
            recommendations.append("• 🔥 Температура очень высокая - рассмотрите возможность паузы в обсуждении")
            recommendations.append("• 💬 Попробуйте перевести разговор в более спокойное русло")
        elif temperature >= 6.5:
            recommendations.append("• ⚡ Активное обсуждение - следите за эмоциями участников")
            recommendations.append("• 🤝 Поощряйте конструктивный диалог")
        elif temperature <= 3.0:
            recommendations.append("• ❄️ Низкая активность - попробуйте оживить обсуждение")
            recommendations.append("• 💡 Задавайте открытые вопросы для вовлечения")
        
        if details['urgency_messages'] > details['total_messages'] * 0.3:
            recommendations.append("• ⏰ Много срочных сообщений - проверьте приоритеты")
        
        if details['question_messages'] > details['total_messages'] * 0.4:
            recommendations.append("• ❓ Много вопросов - возможно, нужна дополнительная информация")
        
        if not recommendations:
            recommendations.append("• ✅ Температура в норме - продолжайте в том же духе")
        
        return "\n".join(recommendations)

    async def check_status(self, update: Update, context):
        """Проверяет статус пользователя и бота"""
        user = update.effective_user
        chat_id = update.effective_chat.id
        
        # Проверяем, что это личные сообщения
        if chat_id <= 0:
            await update.message.reply_text("💡 Для проверки статуса используйте личные сообщения с ботом")
            return
        
        # Информация о пользователе
        user_info = f"""
🔍 **СТАТУС БОТА И ПОЛЬЗОВАТЕЛЯ**

👤 **Информация о вас:**
• ID: `{user.id}`
• Имя: {user.first_name}
• Фамилия: {user.last_name or 'Не указана'}
• Username: @{user.username or 'Не указан'}

🔧 **Права администратора:** {'✅ Да' if user.id in ADMIN_USER_IDS else '❌ Нет'}

📋 **Текущие администраторы:** {ADMIN_USER_IDS}

🌐 **Тип чата:** {'Личные сообщения' if chat_id > 0 else 'Группа'}

💾 **База данных:** {'✅ Доступна' if self.db else '❌ Недоступна'}

🤖 **Статус бота:** ✅ Работает

💡 **Доступные команды:**
• `/myid` - ваш ID и права
• `/groups` - список групп (только админ)
• `/temperature <ID группы>` - анализ температуры (только админ)
• `/help` - справка
"""
        
        await update.message.reply_text(user_info, parse_mode='Markdown')

    async def debug_groups(self, update: Update, context):
        """Отладочная команда для просмотра групп (без проверки прав)"""
        user = update.effective_user
        
        try:
            # Получаем список групп из базы данных
            groups = self.db.get_monitored_groups()
            
            if not groups:
                await update.message.reply_text("📋 Пока нет данных о группах в базе данных.")
                return
            
            groups_info = f"🔍 **ОТЛАДКА: ГРУППЫ В БАЗЕ ДАННЫХ**\n\n"
            groups_info += f"👤 **Запросил:** {user.first_name} (ID: {user.id})\n\n"
            
            for i, group in enumerate(groups, 1):
                group_id = group['chat_id']
                group_title = group.get('title', f'Группа {group_id}')
                messages_count = group.get('messages_count', 0)
                users_count = group.get('users_count', 0)
                last_activity = group.get('last_activity', 'Неизвестно')
                
                groups_info += f"{i}. **{group_title}**\n"
                groups_info += f"   🆔 ID: `{group_id}`\n"
                groups_info += f"   💬 Сообщений: {messages_count}\n"
                groups_info += f"   👥 Пользователей: {users_count}\n"
                groups_info += f"   ⏰ Последняя активность: {last_activity}\n\n"
            
            groups_info += "💡 **Для анализа используйте:**\n"
            groups_info += f"• `/temperature {groups[0]['chat_id']}` - анализ температуры\n"
            groups_info += f"• `/group_report {groups[0]['chat_id']}` - отчет по группе\n"
            
            await update.message.reply_text(groups_info, parse_mode='Markdown')
            
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка при получении групп: {str(e)}")
    
    async def monitor_status(self, update: Update, context):
        """Показывает статус системы мониторинга"""
        user_id = update.effective_user.id
        
        if user_id not in ADMIN_USER_IDS:
            await update.message.reply_text("❌ У вас нет прав администратора")
            return
        
        # Проверяем статус мониторинга
        monitor_active = hasattr(self, 'log_monitor') and self.log_monitor is not None
        
        status_info = "🔍 **СТАТУС СИСТЕМЫ МОНИТОРИНГА**\n\n"
        
        if monitor_active:
            status_info += "✅ **Мониторинг активен**\n"
            status_info += f"📊 Найдено ошибок: {getattr(self.log_monitor, 'error_counter', 0)}\n"
            status_info += f"🔧 Исправлено ошибок: {getattr(self.log_monitor, 'fix_counter', 0)}\n"
        else:
            status_info += "❌ **Мониторинг неактивен**\n"
        
        # Проверяем настройки
        status_info += f"\n⚙️ **Настройки:**\n"
        status_info += f"📁 Лог файл: bot.log\n"
        status_info += f"🔔 Уведомления в Telegram: {'✅' if getattr(self.log_monitor, 'bot_token', None) else '❌'}\n"
        status_info += f"🔄 Отправка в Cursor: {'✅' if getattr(self.log_monitor, 'cursor_api_url', None) else '❌'}\n"
        
        # Проверяем наличие лог файла
        import os
        log_exists = os.path.exists("bot.log")
        status_info += f"📄 Лог файл существует: {'✅' if log_exists else '❌'}\n"
        
        if log_exists:
            log_size = os.path.getsize("bot.log")
            status_info += f"📏 Размер лог файла: {log_size} байт\n"
        
        await update.message.reply_text(status_info, parse_mode='Markdown')
    
    async def monitor_test(self, update: Update, context):
        """Тестирует систему мониторинга"""
        user_id = update.effective_user.id
        
        if user_id not in ADMIN_USER_IDS:
            await update.message.reply_text("❌ У вас нет прав администратора")
            return
        
        # Создаем тестовую ошибку
        test_error_data = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'error_type': 'Test Error',
            'main_error': 'Тестовая ошибка для проверки системы мониторинга',
            'log_file': 'bot.log'
        }
        
        # Отправляем тестовое уведомление
        if hasattr(self, 'log_monitor') and self.log_monitor:
            self.log_monitor.send_error_notification(test_error_data)
            await update.message.reply_text("🧪 Тестовое уведомление отправлено! Проверьте, получили ли вы сообщение.")
        else:
            await update.message.reply_text("❌ Система мониторинга не инициализирована")
    
    async def monitor_summary(self, update: Update, context):
        """Показывает сводку по мониторингу"""
        user_id = update.effective_user.id
        
        if user_id not in ADMIN_USER_IDS:
            await update.message.reply_text("❌ У вас нет прав администратора")
            return
        
        if hasattr(self, 'log_monitor') and self.log_monitor:
            self.log_monitor.send_daily_summary()
            await update.message.reply_text("📊 Сводка по мониторингу отправлена!")
        else:
            await update.message.reply_text("❌ Система мониторинга не инициализирована")
    
    async def monitor_errors(self, update: Update, context):
        """Показывает последние ошибки из отчетов"""
        user_id = update.effective_user.id
        
        if user_id not in ADMIN_USER_IDS:
            await update.message.reply_text("❌ У вас нет прав администратора")
            return
        
        try:
            # Проверяем наличие папки с отчетами
            reports_dir = Path("error_reports")
            if not reports_dir.exists():
                await update.message.reply_text("📁 Папка с отчетами об ошибках не найдена")
                return
            
            # Получаем последние отчеты
            report_files = list(reports_dir.glob("error_report_*.txt"))
            report_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            if not report_files:
                await update.message.reply_text("📄 Отчеты об ошибках не найдены")
                return
            
            # Показываем последние 5 ошибок
            errors_info = "🚨 **ПОСЛЕДНИЕ ОШИБКИ**\n\n"
            
            for i, report_file in enumerate(report_files[:5], 1):
                try:
                    with open(report_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    # Извлекаем основную информацию
                    lines = content.split('\n')
                    error_type = "Неизвестно"
                    error_message = "Неизвестно"
                    timestamp = "Неизвестно"
                    
                    for line in lines:
                        if "🔍 Тип:" in line:
                            error_type = line.split(":", 1)[1].strip()
                        elif "❌ Ошибка:" in line:
                            error_message = line.split(":", 1)[1].strip()
                        elif "📅 Время:" in line:
                            timestamp = line.split(":", 1)[1].strip()
                    
                    errors_info += f"{i}. **{error_type}**\n"
                    errors_info += f"   📅 {timestamp}\n"
                    errors_info += f"   ❌ {error_message[:50]}{'...' if len(error_message) > 50 else ''}\n\n"
                    
                except Exception as e:
                    errors_info += f"{i}. ❌ Ошибка чтения отчета: {str(e)}\n\n"
            
            errors_info += f"📊 Всего отчетов: {len(report_files)}"
            
            await update.message.reply_text(errors_info, parse_mode='Markdown')
            
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка при получении отчетов: {str(e)}")
    
    async def monitor_clear(self, update: Update, context):
        """Очищает старые отчеты об ошибках"""
        user_id = update.effective_user.id
        
        if user_id not in ADMIN_USER_IDS:
            await update.message.reply_text("❌ У вас нет прав администратора")
            return
        
        try:
            # Проверяем наличие папки с отчетами
            reports_dir = Path("error_reports")
            if not reports_dir.exists():
                await update.message.reply_text("📁 Папка с отчетами об ошибках не найдена")
                return
            
            # Получаем все отчеты
            report_files = list(reports_dir.glob("error_report_*.txt"))
            
            if not report_files:
                await update.message.reply_text("📄 Отчеты об ошибках не найдены")
                return
            
            # Удаляем отчеты старше 7 дней
            from datetime import datetime, timedelta
            cutoff_date = datetime.now() - timedelta(days=7)
            deleted_count = 0
            
            for report_file in report_files:
                file_time = datetime.fromtimestamp(report_file.stat().st_mtime)
                if file_time < cutoff_date:
                    report_file.unlink()
                    deleted_count += 1
            
            if deleted_count > 0:
                await update.message.reply_text(f"🗑️ Удалено {deleted_count} старых отчетов об ошибках")
            else:
                await update.message.reply_text("📄 Старые отчеты не найдены (все отчеты новее 7 дней)")
            
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка при очистке отчетов: {str(e)}")

    async def button_callback(self, update: Update, context):
        """Обработчик нажатий на кнопки"""
        query = update.callback_query
        await query.answer()  # Убираем "часики" у кнопки
        
        user_id = query.from_user.id
        
        # Проверяем права администратора
        if user_id not in ADMIN_USER_IDS:
            await query.edit_message_text("❌ У вас нет прав администратора")
            return
        
        callback_data = query.data
        
        if callback_data.startswith("group_"):
            # Выбрана конкретная группа
            chat_id = int(callback_data.split("_")[1])
            await self.show_group_menu(query, chat_id)
        
        elif callback_data == "all_reports":
            # Показать отчеты по всем группам
            await self.show_all_reports(query)
        
        elif callback_data == "all_temperature":
            # Показать температуру всех групп
            await self.show_all_temperature(query)
        
        elif callback_data == "back_to_groups":
            # Вернуться к списку групп
            await self.show_groups_from_callback(query)
        
        elif callback_data.startswith("action_"):
            # Действие с группой
            parts = callback_data.split("_")
            action = parts[1]
            chat_id = int(parts[2])
            
            if action == "report":
                await self.show_group_report(query, chat_id)
            elif action == "activity":
                await self.show_group_activity(query, chat_id)
            elif action == "mentions":
                await self.show_group_mentions(query, chat_id)
            elif action == "temperature":
                await self.show_group_temperature(query, chat_id)
            elif action == "back":
                await self.show_group_menu(query, chat_id)

    async def show_group_menu(self, query, chat_id: int):
        """Показывает меню действий для конкретной группы"""
        # Получаем информацию о группе
        chat_info = self.db.get_chat_info(chat_id)
        group_title = chat_info.get('title', f'Группа {chat_id}') if chat_info else f'Группа {chat_id}'
        
        # Получаем базовую статистику
        messages = self.db.get_messages_for_period(chat_id, 7)
        user_stats = self.db.get_user_activity_stats(chat_id, 7)
        
        menu_text = f"""
📋 **МЕНЮ ГРУППЫ**

🏷️ **Название:** {group_title}
🆔 **ID:** `{chat_id}`

📊 **Статистика за неделю:**
• 💬 Сообщений: {len(messages)}
• 👥 Активных пользователей: {len(user_stats)}

💡 **Выберите действие:**
        """
        
        keyboard = [
            [
                InlineKeyboardButton("📊 Отчет", callback_data=f"action_report_{chat_id}"),
                InlineKeyboardButton("👥 Активность", callback_data=f"action_activity_{chat_id}")
            ],
            [
                InlineKeyboardButton("🌡️ Температура", callback_data=f"action_temperature_{chat_id}"),
                InlineKeyboardButton("📢 Упоминания", callback_data=f"action_mentions_{chat_id}")
            ],
            [
                InlineKeyboardButton("🔙 Назад к группам", callback_data="back_to_groups")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(menu_text, parse_mode='Markdown', reply_markup=reply_markup)

    async def show_group_report(self, query, chat_id: int):
        """Показывает отчет по группе"""
        try:
            # Получаем данные группы
            messages = self.db.get_messages_for_period(chat_id, 7)
            user_stats = self.db.get_user_activity_stats(chat_id, 7)
            mention_stats = self.db.get_mention_stats(chat_id, 7)
            task_stats = self.db.get_task_stats(chat_id, 7)
            
            if not messages:
                await query.edit_message_text("❌ Нет данных для отчета")
                return
            
            # Анализируем данные
            texts = [msg['text'] for msg in messages if msg['text']]
            topic_distribution = self.text_analyzer.get_topic_distribution(texts)
            hourly_activity = timezone_manager.get_activity_hours(messages, 'Europe/Moscow')
            
            chat_data = {
                'total_messages': len(messages),
                'active_users': len(user_stats),
                'total_mentions': sum(m['mention_count'] for m in mention_stats),
                'top_users': user_stats[:5],
                'popular_topics': sorted(topic_distribution.items(), key=lambda x: x[1], reverse=True)[:5],
                'task_stats': task_stats,
                'hourly_activity': hourly_activity
            }
            
            report = self.report_generator.generate_daily_report(chat_data)
            
            # Получаем информацию о группе
            chat_info = self.db.get_chat_info(chat_id)
            group_title = chat_info.get('title', f'Группа {chat_id}') if chat_info else f'Группа {chat_id}'
            
            full_report = f"📊 **ОТЧЕТ ПО ГРУППЕ**\n📋 **{group_title}**\n🆔 ID: `{chat_id}`\n📅 Период: последние 7 дней\n\n{report}"
            
            keyboard = [[InlineKeyboardButton("🔙 Назад к меню", callback_data=f"action_back_{chat_id}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(full_report, parse_mode='Markdown', reply_markup=reply_markup)
            
        except Exception as e:
            await query.edit_message_text(f"❌ Ошибка при генерации отчета: {str(e)}")

    async def show_group_temperature(self, query, chat_id: int):
        """Показывает анализ температуры группы"""
        try:
            # Получаем сообщения для анализа
            messages = self.db.get_messages_for_period(chat_id, 7)
            
            if not messages:
                await query.edit_message_text("❌ Нет данных для анализа температуры")
                return
            
            # Анализируем температуру
            analysis = self.conversation_analyzer.analyze_conversation_temperature(messages, 7)
            
            # Получаем информацию о группе
            chat_info = self.db.get_chat_info(chat_id)
            group_title = chat_info.get('title', f'Группа {chat_id}') if chat_info else f'Группа {chat_id}'
            
            temperature_emoji = self.conversation_analyzer.get_temperature_emoji(analysis['temperature'])
            
            report = f"""
🌡️ **АНАЛИЗ ТЕМПЕРАТУРЫ БЕСЕДЫ**

📋 **Группа:** {group_title}
🆔 **ID:** `{chat_id}`
📅 **Период:** последние 7 дней

{temperature_emoji} **Температура:** **{analysis['temperature']}/10**
📊 **Уверенность:** {analysis['confidence'] * 100:.0f}%

📝 **Описание:**
{analysis['description']}

📈 **Детали анализа:**
• 💬 Всего сообщений: {analysis['details']['total_messages']}
• 😊 Позитивных: {analysis['details']['emotion_distribution']['positive']}
• 😔 Негативных: {analysis['details']['emotion_distribution']['negative']}
• 😐 Нейтральных: {analysis['details']['emotion_distribution']['neutral']}
• ⚡ Срочных: {analysis['details']['urgency_messages']}
• ❓ Вопросов: {analysis['details']['question_messages']}
• ✅ Решений: {analysis['details']['resolution_messages']}

💡 **Рекомендации:**
{self._get_temperature_recommendations(analysis)}
"""
            
            keyboard = [[InlineKeyboardButton("🔙 Назад к меню", callback_data=f"action_back_{chat_id}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(report, parse_mode='Markdown', reply_markup=reply_markup)
            
        except Exception as e:
            await query.edit_message_text(f"❌ Ошибка при анализе температуры: {str(e)}")

    async def show_group_activity(self, query, chat_id: int):
        """Показывает активность пользователей в группе"""
        try:
            # Получаем статистику активности
            user_stats = self.db.get_user_activity_stats(chat_id, 7)
            
            if not user_stats:
                await query.edit_message_text("❌ Нет данных об активности")
                return
            
            # Получаем информацию о группе
            chat_info = self.db.get_chat_info(chat_id)
            group_title = chat_info.get('title', f'Группа {chat_id}') if chat_info else f'Группа {chat_id}'
            
            activity_info = f"👥 **АКТИВНОСТЬ ПОЛЬЗОВАТЕЛЕЙ В ГРУППЕ**\n\n📋 **{group_title}**\n🆔 ID: `{chat_id}`\n📅 Период: последние 7 дней\n\n"
            
            for i, user in enumerate(user_stats[:10], 1):  # Топ 10 пользователей
                # Получаем отображаемое имя пользователя
                display_name = user.get('display_name', '')
                username = user.get('username', '')
                first_name = user.get('first_name', '')
                last_name = user.get('last_name', '')
                
                # Формируем красивое имя
                if display_name and display_name != f"Пользователь {user['user_id']}":
                    user_name = display_name
                elif username:
                    user_name = f"@{username}"
                elif first_name and last_name:
                    user_name = f"{first_name} {last_name}"
                elif first_name:
                    user_name = first_name
                else:
                    user_name = f"Пользователь {user['user_id']}"
                
                messages_count = user['messages_count']
                total_time = user.get('total_time_minutes', 0)
                
                activity_info += f"{i}. **{user_name}**\n"
                activity_info += f"   💬 Сообщений: {messages_count}\n"
                activity_info += f"   ⏱ Время в чате: {total_time:.1f} мин\n\n"
            
            keyboard = [[InlineKeyboardButton("🔙 Назад к меню", callback_data=f"action_back_{chat_id}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(activity_info, parse_mode='Markdown', reply_markup=reply_markup)
            
        except Exception as e:
            await query.edit_message_text(f"❌ Ошибка при получении активности: {str(e)}")

    async def show_group_mentions(self, query, chat_id: int):
        """Показывает статистику упоминаний в группе"""
        try:
            # Получаем статистику упоминаний
            mention_stats = self.db.get_mention_stats(chat_id, 7)
            
            if not mention_stats:
                await query.edit_message_text("❌ Нет данных об упоминаниях")
                return
            
            # Получаем информацию о группе
            chat_info = self.db.get_chat_info(chat_id)
            group_title = chat_info.get('title', f'Группа {chat_id}') if chat_info else f'Группа {chat_id}'
            
            mentions_info = f"📢 **СТАТИСТИКА УПОМИНАНИЙ В ГРУППЕ**\n\n📋 **{group_title}**\n🆔 ID: `{chat_id}`\n📅 Период: последние 7 дней\n\n"
            
            for i, mention in enumerate(mention_stats[:10], 1):  # Топ 10 упоминаний
                username = mention.get('mentioned_username', 'Неизвестно')
                mention_count = mention['mention_count']
                
                mentions_info += f"{i}. **@{username}**\n"
                mentions_info += f"   📊 Упоминаний: {mention_count}\n\n"
            
            keyboard = [[InlineKeyboardButton("🔙 Назад к меню", callback_data=f"action_back_{chat_id}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(mentions_info, parse_mode='Markdown', reply_markup=reply_markup)
            
        except Exception as e:
            await query.edit_message_text(f"❌ Ошибка при получении упоминаний: {str(e)}")

    async def show_all_reports(self, query):
        """Показывает краткие отчеты по всем группам"""
        try:
            groups = self.db.get_monitored_groups()
            
            if not groups:
                await query.edit_message_text("❌ Нет групп для анализа")
                return
            
            all_reports = "📊 **ОТЧЕТЫ ПО ВСЕМ ГРУППАМ**\n\n"
            
            for group in groups:
                chat_id = group['chat_id']
                group_title = group.get('title', f'Группа {chat_id}')
                messages_count = group.get('messages_count', 0)
                users_count = group.get('users_count', 0)
                
                all_reports += f"📋 **{group_title}**\n"
                all_reports += f"🆔 ID: `{chat_id}`\n"
                all_reports += f"💬 Сообщений: {messages_count}\n"
                all_reports += f"👥 Пользователей: {users_count}\n\n"
            
            keyboard = [[InlineKeyboardButton("🔙 Назад к группам", callback_data="back_to_groups")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(all_reports, parse_mode='Markdown', reply_markup=reply_markup)
            
        except Exception as e:
            await query.edit_message_text(f"❌ Ошибка при получении отчетов: {str(e)}")

    async def show_all_temperature(self, query):
        """Показывает температуру всех групп"""
        try:
            groups = self.db.get_monitored_groups()
            
            if not groups:
                await query.edit_message_text("❌ Нет групп для анализа")
                return
            
            all_temperature = "🌡️ **ТЕМПЕРАТУРА ВСЕХ ГРУПП**\n\n"
            
            for group in groups:
                chat_id = group['chat_id']
                group_title = group.get('title', f'Группа {chat_id}')
                
                # Получаем сообщения для анализа
                messages = self.db.get_messages_for_period(chat_id, 7)
                
                if messages:
                    analysis = self.conversation_analyzer.analyze_conversation_temperature(messages, 7)
                    temperature_emoji = self.conversation_analyzer.get_temperature_emoji(analysis['temperature'])
                    
                    all_temperature += f"📋 **{group_title}**\n"
                    all_temperature += f"{temperature_emoji} Температура: **{analysis['temperature']}/10**\n"
                    all_temperature += f"💬 Сообщений: {len(messages)}\n\n"
                else:
                    all_temperature += f"📋 **{group_title}**\n"
                    all_temperature += f"❄️ Нет данных\n\n"
            
            keyboard = [[InlineKeyboardButton("🔙 Назад к группам", callback_data="back_to_groups")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(all_temperature, parse_mode='Markdown', reply_markup=reply_markup)
            
        except Exception as e:
            await query.edit_message_text(f"❌ Ошибка при анализе температуры: {str(e)}")

    async def show_groups_from_callback(self, query):
        """Показывает список групп из callback"""
        try:
            # Получаем список групп из базы данных
            groups = self.db.get_monitored_groups()
            
            if not groups:
                await query.edit_message_text("📋 Пока нет данных о группах. Используйте команду `/collect_history` в группе для начала мониторинга.")
                return
            
            groups_info = "📋 **ГРУППЫ ПОД МОНИТОРИНГОМ:**\n\n"
            
            for i, group in enumerate(groups, 1):
                group_id = group['chat_id']
                group_title = group.get('title', f'Группа {group_id}')
                chat_type = group.get('chat_type', 'группа')
                messages_count = group.get('messages_count', 0)
                users_count = group.get('users_count', 0)
                member_count = group.get('member_count', 0)
                last_activity = group.get('last_activity', 'Неизвестно')
                
                groups_info += f"{i}. **{group_title}**\n"
                groups_info += f"   📋 Тип: {chat_type}\n"
                groups_info += f"   🆔 ID: `{group_id}`\n"
                groups_info += f"   💬 Сообщений: {messages_count}\n"
                groups_info += f"   👥 Активных пользователей: {users_count}\n"
                if member_count:
                    groups_info += f"   👤 Всего участников: {member_count}\n"
                groups_info += f"   ⏰ Последняя активность: {last_activity}\n\n"
            
            groups_info += "💡 **Выберите группу для анализа:**\n"
            
            # Создаем кнопки для каждой группы
            keyboard = []
            for group in groups:
                group_id = group['chat_id']
                group_title = group.get('title', f'Группа {group_id}')
                # Ограничиваем длину названия для кнопки
                button_text = group_title[:30] + "..." if len(group_title) > 30 else group_title
                keyboard.append([InlineKeyboardButton(button_text, callback_data=f"group_{group_id}")])
            
            # Добавляем кнопки для общих действий
            keyboard.append([
                InlineKeyboardButton("📊 Все отчеты", callback_data="all_reports"),
                InlineKeyboardButton("🌡️ Температура всех", callback_data="all_temperature")
            ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(groups_info, parse_mode='Markdown', reply_markup=reply_markup)
            
        except Exception as e:
            await query.edit_message_text(f"❌ Ошибка при получении групп: {str(e)}")

# Создаем экземпляр бота
try:
    bot = CloudChatAnalyzerBot()
    logger.info("Бот успешно инициализирован")
except Exception as e:
    logger.error(f"Ошибка при инициализации бота: {e}")
    bot = None

@app.route('/health')
def health_check():
    """Health check для Railway"""
    try:
        bot_status = "running" if bot else "initializing"
        return jsonify({
            "status": "healthy", 
            "bot": bot_status, 
            "timestamp": datetime.now().isoformat(),
            "port": os.environ.get('PORT', '5000')
        })
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/webhook', methods=['POST'])
def webhook():
    """Обработчик webhook от Telegram"""
    if request.method == 'POST':
        # Проверяем, инициализирован ли бот
        if bot is None:
            logger.error("Бот не инициализирован")
            return jsonify({"status": "error", "message": "Bot not initialized"}), 500
        
        update_dict = request.get_json()
        
        # Логируем входящий webhook
        update_id = update_dict.get('update_id', 'unknown')
        logger.info(f"Получен webhook: {update_id}")
        
        # Проверяем, не обрабатывали ли мы уже это обновление
        if update_id in bot.processed_updates:
            logger.info(f"Пропускаем дублированное обновление: {update_id}")
            return jsonify({"status": "duplicate"})
        
        # Добавляем ID обновления в обработанные сразу
        bot.processed_updates.add(update_id)
        
        # Обрабатываем обновление синхронно для надежности
        try:
            import asyncio
            
            # Создаем новый event loop для каждого webhook
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # Обрабатываем webhook
                loop.run_until_complete(bot.handle_webhook(update_dict))
            except Exception as e:
                logger.error(f"Ошибка при обработке webhook: {e}")
            finally:
                # Закрываем loop
                try:
                    if not loop.is_closed():
                        loop.close()
                except:
                    pass
            
            logger.info(f"Webhook {update_id} успешно обработан")
        except Exception as e:
            logger.error(f"Ошибка при обработке webhook {update_id}: {e}")
            # Удаляем из обработанных в случае ошибки
            bot.processed_updates.discard(update_id)
            return jsonify({"status": "error", "message": str(e)})
        
        return jsonify({"status": "ok"})

@app.route('/')
def home():
    """Главная страница"""
    try:
        bot_status = "✅ Работает" if bot else "⏳ Инициализация"
        return f"""
        <h1>🤖 Chat Analyzer Bot</h1>
        <p>Бот для анализа активности в рабочих чатах</p>
        <p>Статус: <strong>{bot_status}</strong></p>
        <p>Версия: 1.0.0</p>
        <p>Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p>Порт: {os.environ.get('PORT', '5000')}</p>
        <p><a href="/health">Health Check</a></p>
        """
    except Exception as e:
        return f"<h1>🤖 Chat Analyzer Bot</h1><p>Ошибка: {str(e)}</p>"

@app.route('/ping')
def ping():
    """Простой ping для проверки"""
    return jsonify({"pong": True, "timestamp": datetime.now().isoformat()})

if __name__ == '__main__':
    # Получаем порт из переменной окружения
    port = int(os.environ.get('PORT', 5000))
    
    logger.info(f"Запуск Flask приложения на порту {port}")
    
    try:
        # Настраиваем webhook для Telegram
        webhook_url = os.environ.get('WEBHOOK_URL')
        if webhook_url:
            # Устанавливаем webhook
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(bot.application.bot.set_webhook(url=f"{webhook_url}/webhook"))
            loop.close()
            logger.info(f"Webhook установлен: {webhook_url}/webhook")
        
        # Запускаем Flask приложение
        app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
    except Exception as e:
        logger.error(f"Ошибка при запуске приложения: {e}")
        raise
