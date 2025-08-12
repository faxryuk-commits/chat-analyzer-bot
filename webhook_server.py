#!/usr/bin/env python3
"""
Веб-сервер для работы с Telegram webhook в облаке
"""

import os
import logging
import time
from flask import Flask, request, jsonify
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
import threading

from config import BOT_TOKEN, ADMIN_USER_IDS, HISTORY_DAYS, REPORT_TIME, TASK_TIMEOUT_HOURS
from database import DatabaseManager
from text_analyzer import TextAnalyzer
from report_generator import ReportGenerator
from message_collector import MessageCollector
from timezone_utils import timezone_manager

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
        self.active_chats = set()
        self.processed_updates = set()  # Для предотвращения дублирования
        self.last_commands = {}  # Для отслеживания последних команд пользователей
        
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
        self.application.add_handler(CommandHandler("setup_monitoring", self.setup_monitoring))
        
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
        
        welcome_message = f"""
🤖 **Добро пожаловать в Chat Analyzer Bot!**

Привет, {user.first_name}! Я помогу вам анализировать активность в рабочих чатах.

**Что я умею:**
📊 Собирать историю переписки за последние {HISTORY_DAYS} дней
📈 Анализировать активность пользователей
🎯 Определять популярные темы обсуждения
✅ Отслеживать задачи и их выполнение
👥 Анализировать упоминания пользователей
📋 Генерировать подробные отчеты

**Основные команды:**
/start - показать это сообщение
/help - справка по командам
/report - получить отчет по активности
/tasks - показать активные задачи
/mentions - статистика упоминаний
/activity - активность пользователей
/settings - настройки бота

**Для администраторов:**
/admin - панель администратора
/collect_history - собрать историю сообщений
/schedule_report - настроить автоматические отчеты
        """
        
        await update.message.reply_text(welcome_message, parse_mode='Markdown')
        self.active_chats.add(chat_id)
    
    async def help_command(self, update: Update, context):
        """Обработчик команды /help"""
        help_text = """
📚 **СПРАВКА ПО КОМАНДАМ**

**Основные команды:**
/report [дни] - получить отчет по активности (по умолчанию за сегодня)
/tasks - показать активные задачи
/mentions - статистика упоминаний пользователей
/activity - активность пользователей по дням
/topics - популярные темы обсуждения
/wordcloud - облако слов из сообщений

**Команды для задач:**
/task_add @username описание - добавить задачу
/task_complete ID - отметить задачу как выполненную
/task_list - список всех задач

**Команды для администраторов:**
/admin - панель администратора
/collect_history - собрать историю сообщений
/schedule_report время - настроить автоматические отчеты
/export_data - экспорт данных в CSV

**Примеры использования:**
/report 7 - отчет за последние 7 дней
/task_add @ivan подготовить презентацию к завтра
/task_complete 5 - отметить задачу с ID 5 как выполненную
        """
        
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
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
        await update.message.reply_text(report, parse_mode='Markdown')
    
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
        
        await update.message.reply_text("☁️ Облако слов сгенерировано!")
    
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
            
            # Запускаем сбор истории
            result = await self.message_collector.collect_chat_history(chat_id, days)
            
            if result.get('error'):
                await status_message.edit_text(f"❌ Ошибка при сборе истории: {result['error']}")
            else:
                # Формируем отчет о результатах
                report = f"""
✅ **Сбор истории завершен!**

📋 **Результаты:**
• Чат: {result.get('chat_title', f'ID: {chat_id}')}
• Период: {result.get('period_days', days)} дней
• Собрано сообщений: {result.get('messages_collected', 0)}
• Уникальных пользователей: {result.get('users_found', 0)}

📅 **Период сбора:**
• С: {result.get('start_date', '').strftime('%d.%m.%Y') if result.get('start_date') else 'N/A'}
• По: {result.get('end_date', '').strftime('%d.%m.%Y') if result.get('end_date') else 'N/A'}

🎯 **Теперь вы можете использовать команды:**
• `/report` - получить отчет по активности
• `/activity` - активность пользователей
• `/mentions` - статистика упоминаний
• `/topics` - популярные темы
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
            # Обрабатываем обновление
            await self.application.process_update(update)
            logger.info(f"Обновление {update.update_id} успешно обработано")
        except Exception as e:
            logger.error(f"Ошибка при обработке обновления {update.update_id}: {e}")
            raise
    
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

# Создаем экземпляр бота
bot = CloudChatAnalyzerBot()

@app.route('/health')
def health_check():
    """Health check для Railway"""
    return jsonify({"status": "healthy", "bot": "running"})

@app.route('/webhook', methods=['POST'])
def webhook():
    """Обработчик webhook от Telegram"""
    if request.method == 'POST':
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
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(bot.handle_webhook(update_dict))
            loop.close()
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
    return """
    <h1>🤖 Chat Analyzer Bot</h1>
    <p>Бот для анализа активности в рабочих чатах</p>
    <p>Статус: <strong>Работает</strong></p>
    <p>Версия: 1.0.0</p>
    """

if __name__ == '__main__':
    # Получаем порт из переменной окружения
    port = int(os.environ.get('PORT', 5000))
    
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
    app.run(host='0.0.0.0', port=port, debug=False)
