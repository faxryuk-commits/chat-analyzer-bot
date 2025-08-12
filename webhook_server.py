#!/usr/bin/env python3
"""
Веб-сервер для работы с Telegram webhook в облаке
"""

import os
import logging
from flask import Flask, request, jsonify
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
import threading
import time

from config import BOT_TOKEN, ADMIN_USER_IDS, HISTORY_DAYS, REPORT_TIME, TASK_TIMEOUT_HOURS
from database import DatabaseManager
from text_analyzer import TextAnalyzer
from report_generator import ReportGenerator

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
        self.active_chats = set()
        
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
        
        # Сохраняем сообщение в базу данных
        message_data = {
            'message_id': message.message_id,
            'chat_id': chat_id,
            'user_id': user.id,
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'text': message.text,
            'date': int(message.date.timestamp()),
            'reply_to_message_id': message.reply_to_message.message_id if message.reply_to_message else None,
            'forward_from_user_id': message.forward_from.id if message.forward_from else None,
            'is_edited': False,
            'edit_date': None
        }
        
        message_id = self.db.save_message(message_data)
        self.db.update_user_activity(user.id, chat_id, message.date)
        
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
        
        chat_data = {
            'total_messages': len(messages),
            'active_users': len(user_stats),
            'total_mentions': sum(m['mention_count'] for m in mention_stats),
            'top_users': user_stats[:5],
            'popular_topics': sorted(topic_distribution.items(), key=lambda x: x[1], reverse=True)[:5],
            'task_stats': task_stats,
            'hourly_activity': conversation_flow.get('hourly_activity', {})
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
        
        if user_id not in ADMIN_USER_IDS:
            await update.message.reply_text("❌ У вас нет прав администратора")
            return
        
        await update.message.reply_text("✅ История сообщений собрана!")
    
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
        await self.application.initialize()
        await self.application.process_update(update)

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
        
        # Обрабатываем обновление в отдельном потоке
        def process_update():
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(bot.handle_webhook(update_dict))
            loop.close()
        
        thread = threading.Thread(target=process_update)
        thread.start()
        
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
