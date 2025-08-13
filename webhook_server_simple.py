#!/usr/bin/env python3
"""
Chat Analyzer Bot - Упрощенный Webhook Server
Исправлены проблемы с event loop и синтаксические ошибки
"""

import os
import json
import logging
import asyncio
import threading
from datetime import datetime
from typing import Dict, Set
from flask import Flask, request, jsonify
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.constants import ParseMode

# Импорты проекта
from config import BOT_TOKEN, ADMIN_USER_IDS, DATABASE_PATH
from database import DatabaseManager
from text_analyzer import TextAnalyzer
from report_generator import ReportGenerator
from task_manager import TaskManager
from conversation_analyzer import ConversationAnalyzer
from timezone_utils import TimezoneManager
from telegram_history_collector import TelegramHistoryCollector

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SimpleChatBot:
    """Упрощенный класс бота с исправленными проблемами"""
    
    def __init__(self):
        """Инициализация бота"""
        self.bot_token = BOT_TOKEN
        self.admin_user_ids = ADMIN_USER_IDS
        
        # Инициализация компонентов
        self.db = DatabaseManager(DATABASE_PATH)
        self.text_analyzer = TextAnalyzer()
        self.report_generator = ReportGenerator(self.db, self.text_analyzer)
        self.task_manager = TaskManager(self.db)
        self.conversation_analyzer = ConversationAnalyzer()
        self.timezone_manager = TimezoneManager()
        self.history_collector = TelegramHistoryCollector(self.db, self.text_analyzer, self.bot_token)
        
        # Инициализация Telegram приложения
        self.application = Application.builder().token(self.bot_token).build()
        
        # Настройка обработчиков
        self._setup_handlers()
        
        # Кэш для предотвращения дублирования
        self.processed_updates: Set[int] = set()
        
        logger.info("Бот успешно инициализирован")
    
    def _setup_handlers(self):
        """Настройка обработчиков команд"""
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("myid", self.myid_command))
        self.application.add_handler(CommandHandler("report", self.report_command))
        self.application.add_handler(CommandHandler("activity", self.activity_command))
        self.application.add_handler(CommandHandler("wordcloud", self.wordcloud_command))
        self.application.add_handler(CommandHandler("temperature", self.temperature_command))
        self.application.add_handler(CommandHandler("collect_history", self.collect_history_command))
        self.application.add_handler(CommandHandler("groups", self.groups_command))
        self.application.add_handler(CommandHandler("group_report", self.group_report_command))
        self.application.add_handler(CommandHandler("group_activity", self.group_activity_command))
        self.application.add_handler(CommandHandler("group_mentions", self.group_mentions_command))
        
        logger.info("Обработчики команд настроены")
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        user = update.effective_user
        welcome_message = f"""
🤖 **Добро пожаловать в Chat Analyzer Bot!**

👤 **Пользователь:** {user.first_name} {user.last_name or ''}
🆔 **ID:** {user.id}

📋 **Основные команды:**
• `/report` - Ежедневный отчет
• `/activity` - Статистика активности
• `/wordcloud` - Облако слов
• `/temperature` - Анализ настроения
• `/collect_history` - Сбор истории
• `/myid` - Информация о пользователе
• `/help` - Справка

💡 **Использование:** Отправьте команду в группе или в личных сообщениях.
        """
        await update.message.reply_text(welcome_message, parse_mode=ParseMode.MARKDOWN)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help"""
        help_text = """
📚 **СПРАВКА ПО КОМАНДАМ**

**📊 АНАЛИТИКА:**
• `/report` - Ежедневный отчет с графиками
• `/activity` - Топ активных пользователей
• `/wordcloud` - Популярные слова в чате
• `/temperature` - Оценка настроения (1-10)

**🔧 УПРАВЛЕНИЕ:**
• `/collect_history [дни]` - Сбор истории (по умолчанию 45)
• `/myid` - Ваши данные и права доступа

**👥 АДМИН-КОМАНДЫ:**
• `/groups` - Список отслеживаемых групп
• `/group_report [ID группы] [дни]` - Отчет по группе
• `/group_activity [ID группы] [дни]` - Активность в группе
• `/group_mentions [ID группы] [дни]` - Упоминания в группе

**💡 ПРИМЕРЫ:**
• `/collect_history 30` - собрать историю за 30 дней
• `/group_report -1001234567890 7` - отчет по группе за неделю
        """
        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)
    
    async def myid_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает информацию о пользователе"""
        user = update.effective_user
        is_admin = user.id in self.admin_user_ids
        admin_list = ", ".join(map(str, self.admin_user_ids))
        
        message = f"""
🆔 **Информация о пользователе:**

👤 **Ваш ID:** {user.id}
👤 **Имя:** {user.first_name}
👤 **Фамилия:** {user.last_name or 'не указана'}
👤 **Username:** @{user.username or 'не указан'}

🔧 **Права администратора:** {'✅ Да' if is_admin else '❌ Нет'}

📋 **Текущие администраторы:** {admin_list}
        """
        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
    
    async def report_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Генерирует ежедневный отчет"""
        chat_id = update.effective_chat.id
        
        try:
            messages = self.db.get_messages_for_period(chat_id, 7)
            
            if not messages:
                await update.message.reply_text("📊 Нет данных для отчета за последние 7 дней")
                return
            
            report = self.report_generator.generate_daily_report(chat_id, 7)
            await update.message.reply_text(report, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            logger.error(f"Ошибка при генерации отчета: {e}")
            await update.message.reply_text(f"❌ Ошибка при генерации отчета: {e}")
    
    async def activity_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает активность пользователей"""
        chat_id = update.effective_chat.id
        
        try:
            user_stats = self.db.get_user_activity_stats(chat_id, 7)
            
            if not user_stats:
                await update.message.reply_text("📊 Нет данных об активности пользователей")
                return
            
            activity_report = "📊 **АКТИВНОСТЬ ПОЛЬЗОВАТЕЛЕЙ**\n\n"
            activity_report += f"📅 **Период:** Последние 7 дней\n\n"
            
            for i, user in enumerate(user_stats[:10], 1):
                display_name = user.get('display_name', '')
                username = user.get('username', '')
                first_name = user.get('first_name', '')
                last_name = user.get('last_name', '')
                
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
                
                activity_report += f"{i}. **{user_name}**\n"
                activity_report += f"   💬 Сообщений: {messages_count}\n"
                activity_report += f"   ⏱ Время в чате: {total_time:.1f} мин\n\n"
            
            await update.message.reply_text(activity_report, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            logger.error(f"Ошибка при получении активности: {e}")
            await update.message.reply_text(f"❌ Ошибка при получении активности: {e}")
    
    async def wordcloud_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает облако слов"""
        chat_id = update.effective_chat.id
        
        try:
            messages = self.db.get_messages_for_period(chat_id, 7)
            texts = [msg['text'] for msg in messages if msg['text']]
            word_data = self.text_analyzer.generate_word_cloud_data(texts)
            
            if not word_data:
                await update.message.reply_text("☁️ Недостаточно данных для создания облака слов")
                return
            
            wordcloud_report = "☁️ **ОБЛАКО СЛОВ**\n\n"
            wordcloud_report += f"📊 **Популярные слова в чате за последние 7 дней:**\n\n"
            
            for i, (word, count) in enumerate(word_data[:15], 1):
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
            
            await update.message.reply_text(wordcloud_report, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            logger.error(f"Ошибка при создании облака слов: {e}")
            await update.message.reply_text(f"❌ Ошибка при создании облака слов: {e}")
    
    async def temperature_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Анализирует температуру беседы"""
        chat_id = update.effective_chat.id
        
        try:
            messages = self.db.get_messages_for_period(chat_id, 1)
            
            if not messages:
                await update.message.reply_text("🌡️ Нет данных для анализа температуры беседы")
                return
            
            texts = [msg['text'] for msg in messages if msg['text']]
            temperature_result = self.conversation_analyzer.analyze_conversation_temperature(texts)
            
            temp_report = f"""
🌡️ **ТЕМПЕРАТУРА БЕСЕДЫ**

📊 **Оценка:** {temperature_result['temperature']}/10 {temperature_result['emoji']}
📝 **Описание:** {temperature_result['description']}
🎯 **Уверенность:** {temperature_result['confidence']:.1f}%

💡 **Рекомендации:**
{temperature_result['recommendations']}
            """
            
            await update.message.reply_text(temp_report, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            logger.error(f"Ошибка при анализе температуры: {e}")
            await update.message.reply_text(f"❌ Ошибка при анализе температуры: {e}")
    
    async def collect_history_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Собирает историю сообщений"""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        if user_id not in self.admin_user_ids:
            await update.message.reply_text("❌ У вас нет прав администратора")
            return
        
        days = 45
        if context.args:
            try:
                days = int(context.args[0])
                if days <= 0 or days > 365:
                    await update.message.reply_text("❌ Количество дней должно быть от 1 до 365")
                    return
            except ValueError:
                await update.message.reply_text("❌ Неверный формат количества дней")
                return
        
        try:
            status_message = await update.message.reply_text(
                f"🔄 Начинаем сбор истории за {days} дней..."
            )
            
            async def progress_callback(message: str):
                try:
                    await status_message.edit_text(message)
                except:
                    pass
            
            result = await self.history_collector.collect_real_chat_history(
                chat_id, days, progress_callback
            )
            
            final_report = f"""
✅ **СБОР ИСТОРИИ ЗАВЕРШЕН!**

📊 **Результаты:**
• Сообщений собрано: {result['messages_collected']}
• Пользователей найдено: {result['users_found']}
• Период: {result['period_days']} дней
• Источник: {result['source']}

🎯 **Следующие шаги:**
• Используйте `/report` для получения отчета
• Используйте `/activity` для анализа активности
            """
            
            await status_message.edit_text(final_report, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            logger.error(f"Ошибка при сборе истории: {e}")
            await update.message.reply_text(f"❌ Ошибка при сборе истории: {e}")
    
    async def groups_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает список групп"""
        user_id = update.effective_user.id
        
        if user_id not in self.admin_user_ids:
            await update.message.reply_text("❌ У вас нет прав администратора")
            return
        
        try:
            groups = self.db.get_monitored_groups()
            
            if not groups:
                await update.message.reply_text("📋 Нет отслеживаемых групп")
                return
            
            groups_text = "📋 **ОТСЛЕЖИВАЕМЫЕ ГРУППЫ**\n\n"
            
            for i, group in enumerate(groups, 1):
                title = group.get('title', f'Группа {group["chat_id"]}')
                groups_text += f"{i}. **{title}**\n"
                groups_text += f"   🆔 ID: `{group['chat_id']}`\n\n"
            
            await update.message.reply_text(groups_text, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            logger.error(f"Ошибка при получении групп: {e}")
            await update.message.reply_text(f"❌ Ошибка при получении групп: {e}")
    
    async def group_report_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Генерирует отчет по конкретной группе"""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        if user_id not in self.admin_user_ids:
            await update.message.reply_text("❌ У вас нет прав администратора")
            return
        
        if chat_id < 0:  # Это группа
            target_chat_id = chat_id
            days = 7
            if context.args:
                try:
                    days = int(context.args[0])
                except ValueError:
                    await update.message.reply_text("❌ Неверный формат количества дней")
                    return
        else:  # Это личные сообщения
            if not context.args:
                await self.groups_command(update, context)
                return
            
            try:
                target_chat_id = int(context.args[0])
                days = int(context.args[1]) if len(context.args) > 1 else 7
            except ValueError:
                await update.message.reply_text("❌ Неверный формат параметров")
                return
        
        try:
            messages = self.db.get_messages_for_period(target_chat_id, days)
            user_stats = self.db.get_user_activity_stats(target_chat_id, days)
            
            if not messages:
                await update.message.reply_text(f"❌ Нет данных для группы {target_chat_id} за последние {days} дней.")
                return
            
            chat_info = self.db.get_chat_info(target_chat_id)
            group_title = chat_info.get('title', f'Группа {target_chat_id}') if chat_info else f'Группа {target_chat_id}'
            
            report = f"""
📊 **ОТЧЕТ ПО ГРУППЕ: {group_title}**

📅 **Период:** Последние {days} дней
💬 **Сообщений:** {len(messages)}
👥 **Активных пользователей:** {len(user_stats)}

**👤 ТОП-5 АКТИВНЫХ ПОЛЬЗОВАТЕЛЕЙ:**
"""
            
            for i, user in enumerate(user_stats[:5], 1):
                display_name = user.get('display_name', '')
                username = user.get('username', '')
                first_name = user.get('first_name', '')
                last_name = user.get('last_name', '')
                
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
                report += f"{i}. **{user_name}** - {messages_count} сообщений\n"
            
            await update.message.reply_text(report, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            logger.error(f"Ошибка при генерации отчета группы: {e}")
            await update.message.reply_text(f"❌ Ошибка при генерации отчета: {e}")
    
    async def group_activity_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает активность в конкретной группе"""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        if user_id not in self.admin_user_ids:
            await update.message.reply_text("❌ У вас нет прав администратора")
            return
        
        if chat_id < 0:  # Это группа
            target_chat_id = chat_id
            days = 7
            if context.args:
                try:
                    days = int(context.args[0])
                except ValueError:
                    await update.message.reply_text("❌ Неверный формат количества дней")
                    return
        else:  # Это личные сообщения
            if not context.args:
                await update.message.reply_text("❌ Укажите ID группы")
                return
            
            try:
                target_chat_id = int(context.args[0])
                days = int(context.args[1]) if len(context.args) > 1 else 7
            except ValueError:
                await update.message.reply_text("❌ Неверный формат параметров")
                return
        
        try:
            user_stats = self.db.get_user_activity_stats(target_chat_id, days)
            chat_info = self.db.get_chat_info(target_chat_id)
            group_title = chat_info.get('title', f'Группа {target_chat_id}') if chat_info else f'Группа {target_chat_id}'
            
            if not user_stats:
                await update.message.reply_text(f"📊 Нет данных об активности в группе {group_title}")
                return
            
            activity_info = f"📊 **АКТИВНОСТЬ В ГРУППЕ: {group_title}**\n\n"
            activity_info += f"📅 **Период:** Последние {days} дней\n\n"
            
            for i, user in enumerate(user_stats[:10], 1):
                display_name = user.get('display_name', '')
                username = user.get('username', '')
                first_name = user.get('first_name', '')
                last_name = user.get('last_name', '')
                
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
            
            await update.message.reply_text(activity_info, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            logger.error(f"Ошибка при получении активности группы: {e}")
            await update.message.reply_text(f"❌ Ошибка при получении активности: {e}")
    
    async def group_mentions_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает упоминания в конкретной группе"""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        if user_id not in self.admin_user_ids:
            await update.message.reply_text("❌ У вас нет прав администратора")
            return
        
        if chat_id < 0:  # Это группа
            target_chat_id = chat_id
            days = 7
            if context.args:
                try:
                    days = int(context.args[0])
                except ValueError:
                    await update.message.reply_text("❌ Неверный формат количества дней")
                    return
        else:  # Это личные сообщения
            if not context.args:
                await update.message.reply_text("❌ Укажите ID группы")
                return
            
            try:
                target_chat_id = int(context.args[0])
                days = int(context.args[1]) if len(context.args) > 1 else 7
            except ValueError:
                await update.message.reply_text("❌ Неверный формат параметров")
                return
        
        try:
            mention_stats = self.db.get_mention_stats(target_chat_id, days)
            chat_info = self.db.get_chat_info(target_chat_id)
            group_title = chat_info.get('title', f'Группа {target_chat_id}') if chat_info else f'Группа {target_chat_id}'
            
            if not mention_stats:
                await update.message.reply_text(f"📢 Нет данных об упоминаниях в группе {group_title}")
                return
            
            mentions_info = f"📢 **УПОМИНАНИЯ В ГРУППЕ: {group_title}**\n\n"
            mentions_info += f"📅 **Период:** Последние {days} дней\n\n"
            
            for i, mention in enumerate(mention_stats[:10], 1):
                username = mention.get('username', f"Пользователь {mention['user_id']}")
                count = mention['count']
                
                mentions_info += f"{i}. **@{username}** - {count} упоминаний\n"
            
            await update.message.reply_text(mentions_info, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            logger.error(f"Ошибка при получении упоминаний группы: {e}")
            await update.message.reply_text(f"❌ Ошибка при получении упоминаний: {e}")
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик всех сообщений"""
        try:
            message = update.message
            if not message or not message.text:
                return
            
            chat_id = message.chat.id
            user_id = message.from_user.id
            text = message.text
            message_id = message.message_id
            date = message.date
            
            display_name = self._get_user_display_name(message.from_user)
            
            # Сохраняем сообщение
            self.db.save_message(
                chat_id=chat_id,
                user_id=user_id,
                message_id=message_id,
                text=text,
                date=date,
                display_name=display_name
            )
            
            # Сохраняем информацию о чате
            if message.chat.type in ['group', 'supergroup']:
                self.db.save_chat_info(
                    chat_id=chat_id,
                    title=message.chat.title,
                    chat_type=message.chat.type,
                    member_count=getattr(message.chat, 'member_count', None)
                )
            
            # Обновляем активность
            self.db.update_user_activity(
                chat_id=chat_id,
                user_id=user_id,
                display_name=display_name
            )
            
            # Анализируем текст
            mentions = self.text_analyzer.extract_mentions(text)
            tasks = self.text_analyzer.extract_tasks(text)
            
            # Сохраняем упоминания
            for mention in mentions:
                self.db.save_mention(
                    chat_id=chat_id,
                    user_id=user_id,
                    mentioned_user_id=mention['user_id'],
                    message_id=message_id,
                    date=date
                )
            
            # Сохраняем задачи
            for task in tasks:
                self.task_manager.create_task(
                    chat_id=chat_id,
                    creator_id=user_id,
                    assignee_id=task.get('assignee_id'),
                    description=task['description'],
                    priority=task.get('priority', 'medium'),
                    deadline=task.get('deadline')
                )
            
        except Exception as e:
            logger.error(f"Ошибка при обработке сообщения: {e}")
    
    def _get_user_display_name(self, user) -> str:
        """Получает отображаемое имя пользователя"""
        if user.first_name and user.last_name:
            return f"{user.first_name} {user.last_name}"
        elif user.first_name:
            return user.first_name
        elif user.username:
            return f"@{user.username}"
        else:
            return f"Пользователь {user.id}"
    
    async def handle_webhook(self, update_dict: Dict):
        """Обработчик webhook"""
        try:
            update = Update.de_json(update_dict, self.application.bot)
            
            if update.update_id in self.processed_updates:
                return
            
            self.processed_updates.add(update.update_id)
            
            if len(self.processed_updates) > 1000:
                self.processed_updates.clear()
            
            user_id = update.effective_user.id if update.effective_user else 'неизвестно'
            chat_id = update.effective_chat.id if update.effective_chat else 'неизвестно'
            logger.info(f"Обрабатываем обновление {update.update_id}: пользователь {user_id} в чате {chat_id}")
            
            if update.message:
                await self.handle_message(update, None)
            
            if update.message and update.message.text and update.message.text.startswith('/'):
                await self.application.process_update(update)
            
            logger.info(f"Обновление {update.update_id} успешно обработано")
            
        except Exception as e:
            logger.error(f"Ошибка при обработке обновления: {e}")

# Создаем экземпляр бота
bot = SimpleChatBot()

# Создаем Flask приложение
app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    """Обработчик webhook от Telegram"""
    try:
        update_dict = request.get_json()
        
        if not update_dict:
            return jsonify({'status': 'error', 'message': 'No data received'}), 400
        
        update_id = update_dict.get('update_id', 'неизвестно')
        logger.info(f"Получен webhook: {update_id}")
        
        # Обрабатываем webhook синхронно
        def process_webhook():
            try:
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                try:
                    loop.run_until_complete(bot.handle_webhook(update_dict))
                finally:
                    if not loop.is_closed():
                        loop.close()
                        
            except Exception as e:
                logger.error(f"Ошибка при обработке webhook: {e}")
        
        # Запускаем в отдельном потоке
        thread = threading.Thread(target=process_webhook)
        thread.daemon = True
        thread.start()
        
        logger.info(f"Webhook {update_id} успешно обработан")
        return jsonify({'status': 'ok'}), 200
        
    except Exception as e:
        logger.error(f"Ошибка в webhook endpoint: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Проверка здоровья сервиса"""
    try:
        db_status = "healthy" if bot.db else "unhealthy"
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'database': db_status,
            'version': '2.0-simple'
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/', methods=['GET'])
def home():
    """Главная страница"""
    return jsonify({
        'service': 'Chat Analyzer Bot (Simple)',
        'status': 'running',
        'version': '2.0-simple',
        'timestamp': datetime.now().isoformat()
    }), 200

if __name__ == '__main__':
    logger.info("Запуск упрощенного Flask приложения на порту 8080")
    app.run(host='0.0.0.0', port=8080, threaded=True)
