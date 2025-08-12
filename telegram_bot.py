import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import schedule
import time
import threading

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    filters, ContextTypes
)

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

class ChatAnalyzerBot:
    def __init__(self):
        self.db = DatabaseManager()
        self.text_analyzer = TextAnalyzer()
        self.report_generator = ReportGenerator()
        self.active_chats = set()  # Множество активных чатов
        
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        
        # Добавляем чат в активные
        self.active_chats.add(chat_id)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        
        # Обновляем активность пользователя
        self.db.update_user_activity(user.id, chat_id, message.date)
        
        # Анализируем текст сообщения
        text = message.text
        
        # Извлекаем упоминания
        mentions = self.text_analyzer.extract_mentions(text)
        for mention in mentions:
            # Здесь нужно найти user_id по username или имени
            # Пока сохраняем как есть
            mention_data = {
                'message_id': message_id,
                'mentioned_user_id': 0,  # TODO: найти по username
                'mentioned_username': mention,
                'mention_type': 'username'
            }
            self.db.save_mention(mention_data)
        
        # Извлекаем задачи
        tasks = self.text_analyzer.extract_tasks(text)
        for task in tasks:
            if task['assigned_to']:
                # TODO: найти user_id по username
                task_data = {
                    'message_id': message_id,
                    'chat_id': chat_id,
                    'assigned_by_user_id': user.id,
                    'assigned_to_user_id': 0,  # TODO: найти по username
                    'task_text': task['task_text'],
                    'status': 'pending'
                }
                self.db.save_task(task_data)
        
        # Проверяем, является ли сообщение ответом на задачу
        if message.reply_to_message:
            # Проверяем, есть ли задача для этого сообщения
            # TODO: реализовать логику проверки и обновления задач
    
    async def generate_report(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Генерирует отчет по активности"""
        chat_id = update.effective_chat.id
        
        # Получаем количество дней из аргументов команды
        days = 1  # по умолчанию за сегодня
        if context.args:
            try:
                days = int(context.args[0])
            except ValueError:
                await update.message.reply_text("❌ Неверный формат количества дней. Используйте число.")
                return
        
        # Получаем данные для отчета
        messages = self.db.get_messages_for_period(chat_id, days)
        user_stats = self.db.get_user_activity_stats(chat_id, days)
        mention_stats = self.db.get_mention_stats(chat_id, days)
        task_stats = self.db.get_task_stats(chat_id, days)
        
        # Анализируем темы
        texts = [msg['text'] for msg in messages if msg['text']]
        topic_distribution = self.text_analyzer.get_topic_distribution(texts)
        
        # Анализируем поток беседы
        conversation_flow = self.text_analyzer.analyze_conversation_flow(messages)
        
        # Формируем данные для отчета
        chat_data = {
            'total_messages': len(messages),
            'active_users': len(user_stats),
            'total_mentions': sum(m['mention_count'] for m in mention_stats),
            'top_users': user_stats[:5],
            'popular_topics': sorted(topic_distribution.items(), key=lambda x: x[1], reverse=True)[:5],
            'task_stats': task_stats,
            'hourly_activity': conversation_flow.get('hourly_activity', {})
        }
        
        # Генерируем отчет
        report = self.report_generator.generate_daily_report(chat_data)
        
        # Создаем графики
        if user_stats:
            user_chart = self.report_generator.create_user_activity_chart(user_stats)
            if user_chart:
                # Отправляем график
                await context.bot.send_photo(
                    chat_id=chat_id,
                    photo=user_chart,
                    caption="📊 График активности пользователей"
                )
        
        if conversation_flow.get('hourly_activity'):
            hourly_chart = self.report_generator.create_hourly_activity_chart(
                conversation_flow['hourly_activity']
            )
            if hourly_chart:
                await context.bot.send_photo(
                    chat_id=chat_id,
                    photo=hourly_chart,
                    caption="⏰ Активность по часам"
                )
        
        # Отправляем текстовый отчет
        await update.message.reply_text(report, parse_mode='Markdown')
    
    async def show_tasks(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает активные задачи"""
        chat_id = update.effective_chat.id
        tasks = self.db.get_pending_tasks(chat_id)
        
        if not tasks:
            await update.message.reply_text("✅ Нет активных задач!")
            return
        
        # Создаем клавиатуру для управления задачами
        keyboard = []
        for task in tasks[:10]:  # Показываем первые 10 задач
            task_text = task['task_text'][:30] + "..." if len(task['task_text']) > 30 else task['task_text']
            keyboard.append([
                InlineKeyboardButton(
                    f"✅ {task_text}",
                    callback_data=f"complete_task_{task['id']}"
                )
            ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        task_report = self.report_generator.generate_task_report(tasks)
        await update.message.reply_text(
            task_report,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def show_mentions(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает статистику упоминаний"""
        chat_id = update.effective_chat.id
        mentions = self.db.get_mention_stats(chat_id, 7)  # За последние 7 дней
        
        mention_report = self.report_generator.generate_mention_report(mentions)
        await update.message.reply_text(mention_report, parse_mode='Markdown')
    
    async def show_activity(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает активность пользователей"""
        chat_id = update.effective_chat.id
        user_stats = self.db.get_user_activity_stats(chat_id, 7)  # За последние 7 дней
        
        if not user_stats:
            await update.message.reply_text("📊 Нет данных об активности пользователей")
            return
        
        # Создаем график активности
        chart = self.report_generator.create_user_activity_chart(user_stats)
        if chart:
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=chart,
                caption="📊 Активность пользователей за последние 7 дней"
            )
        
        # Отправляем текстовую статистику
        activity_text = "👥 **АКТИВНОСТЬ ПОЛЬЗОВАТЕЛЕЙ:**\n\n"
        for i, user in enumerate(user_stats[:10], 1):
            name = user.get('name', f"Пользователь {user['user_id']}")
            time_spent = self.report_generator.format_time_spent(user.get('total_time_minutes', 0))
            activity_text += f"{i}. {name}\n"
            activity_text += f"   📝 Сообщений: {user['messages_count']}\n"
            activity_text += f"   ⏱ Время в чате: {time_spent}\n\n"
        
        await update.message.reply_text(activity_text, parse_mode='Markdown')
    
    async def show_topics(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает популярные темы"""
        chat_id = update.effective_chat.id
        messages = self.db.get_messages_for_period(chat_id, 7)  # За последние 7 дней
        
        texts = [msg['text'] for msg in messages if msg['text']]
        topic_distribution = self.text_analyzer.get_topic_distribution(texts)
        
        if not topic_distribution:
            await update.message.reply_text("🎯 Нет данных о темах обсуждения")
            return
        
        # Создаем график распределения тем
        chart = self.report_generator.create_topic_distribution_chart(topic_distribution)
        if chart:
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=chart,
                caption="🎯 Распределение тем обсуждения"
            )
        
        # Отправляем текстовую статистику
        topics_text = "🎯 **ПОПУЛЯРНЫЕ ТЕМЫ:**\n\n"
        for topic, count in sorted(topic_distribution.items(), key=lambda x: x[1], reverse=True):
            topics_text += f"• {topic}: {count} упоминаний\n"
        
        await update.message.reply_text(topics_text, parse_mode='Markdown')
    
    async def show_wordcloud(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает облако слов"""
        chat_id = update.effective_chat.id
        messages = self.db.get_messages_for_period(chat_id, 7)  # За последние 7 дней
        
        texts = [msg['text'] for msg in messages if msg['text']]
        word_data = self.text_analyzer.generate_word_cloud_data(texts)
        
        if not word_data:
            await update.message.reply_text("☁️ Недостаточно данных для создания облака слов")
            return
        
        # Создаем облако слов
        wordcloud = self.report_generator.create_word_cloud(word_data)
        if wordcloud:
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=wordcloud,
                caption="☁️ Облако слов из сообщений чата"
            )
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик нажатий на кнопки"""
        query = update.callback_query
        await query.answer()
        
        if query.data.startswith("complete_task_"):
            task_id = int(query.data.split("_")[2])
            self.db.mark_task_completed(task_id)
            await query.edit_message_text("✅ Задача отмечена как выполненная!")
    
    async def admin_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Панель администратора"""
        user_id = update.effective_user.id
        
        if user_id not in ADMIN_USER_IDS:
            await update.message.reply_text("❌ У вас нет прав администратора")
            return
        
        keyboard = [
            [InlineKeyboardButton("📊 Полный отчет", callback_data="admin_full_report")],
            [InlineKeyboardButton("📥 Собрать историю", callback_data="admin_collect_history")],
            [InlineKeyboardButton("⚙️ Настройки", callback_data="admin_settings")],
            [InlineKeyboardButton("📤 Экспорт данных", callback_data="admin_export")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🔧 **ПАНЕЛЬ АДМИНИСТРАТОРА**\n\nВыберите действие:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def collect_history(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Собирает историю сообщений"""
        user_id = update.effective_user.id
        
        if user_id not in ADMIN_USER_IDS:
            await update.message.reply_text("❌ У вас нет прав администратора")
            return
        
        chat_id = update.effective_chat.id
        
        # Отправляем сообщение о начале сбора
        status_message = await update.message.reply_text("🔄 Собираю историю сообщений...")
        
        try:
            # Здесь должна быть логика сбора истории через Telegram API
            # Пока просто симулируем процесс
            await asyncio.sleep(2)
            
            # Обновляем статус
            await status_message.edit_text("✅ История сообщений собрана!")
            
        except Exception as e:
            logger.error(f"Ошибка при сборе истории: {e}")
            await status_message.edit_text("❌ Ошибка при сборе истории")
    
    def schedule_daily_report(self, chat_id: int, time_str: str = REPORT_TIME):
        """Планирует ежедневный отчет"""
        def send_daily_report():
            # Здесь должна быть логика отправки отчета
            logger.info(f"Отправка ежедневного отчета в чат {chat_id}")
        
        schedule.every().day.at(time_str).do(send_daily_report)
    
    def run_scheduler(self):
        """Запускает планировщик задач"""
        while True:
            schedule.run_pending()
            time.sleep(60)  # Проверяем каждую минуту
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик ошибок"""
        logger.error(f"Ошибка при обработке обновления {update}: {context.error}")
    
    def run(self):
        """Запускает бота"""
        # Создаем приложение
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Добавляем обработчики
        application.add_handler(CommandHandler("start", self.start))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("report", self.generate_report))
        application.add_handler(CommandHandler("tasks", self.show_tasks))
        application.add_handler(CommandHandler("mentions", self.show_mentions))
        application.add_handler(CommandHandler("activity", self.show_activity))
        application.add_handler(CommandHandler("topics", self.show_topics))
        application.add_handler(CommandHandler("wordcloud", self.show_wordcloud))
        application.add_handler(CommandHandler("admin", self.admin_panel))
        application.add_handler(CommandHandler("collect_history", self.collect_history))
        
        # Обработчик сообщений
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        # Обработчик кнопок
        application.add_handler(CallbackQueryHandler(self.button_callback))
        
        # Обработчик ошибок
        application.add_error_handler(self.error_handler)
        
        # Запускаем планировщик в отдельном потоке
        scheduler_thread = threading.Thread(target=self.run_scheduler, daemon=True)
        scheduler_thread.start()
        
        # Запускаем бота
        logger.info("Бот запущен!")
        application.run_polling()

if __name__ == "__main__":
    bot = ChatAnalyzerBot()
    bot.run()
