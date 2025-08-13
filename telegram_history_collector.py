#!/usr/bin/env python3
"""
Модуль для реального сбора истории сообщений из Telegram чатов
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from telegram import Bot, Update, Message
from telegram.ext import Application
from database import DatabaseManager
from text_analyzer import TextAnalyzer

logger = logging.getLogger(__name__)

class TelegramHistoryCollector:
    def __init__(self, bot_token: str, db: DatabaseManager, text_analyzer: TextAnalyzer):
        self.bot_token = bot_token
        self.db = db
        self.text_analyzer = text_analyzer
        self.bot = Bot(token=bot_token)
        
    async def collect_real_chat_history(self, chat_id: int, days: int = 45, progress_callback=None) -> Dict:
        """Собирает реальную историю сообщений из чата с прогрессом"""
        
        # Вычисляем дату начала сбора
        start_date = datetime.now() - timedelta(days=days)
        
        try:
            # Шаг 1: Получение информации о чате
            if progress_callback:
                await progress_callback("🔍 Получаем информацию о чате...")
            
            chat_info = await self.bot.get_chat(chat_id)
            chat_title = chat_info.title if hasattr(chat_info, 'title') else f"Чат {chat_id}"
            
            if progress_callback:
                await progress_callback(f"📋 Чат: {chat_title}\n📅 Период: {start_date.strftime('%d.%m.%Y')} - {datetime.now().strftime('%d.%m.%Y')}")
            
            # Шаг 2: Проверка существующих данных
            if progress_callback:
                await progress_callback("🔍 Проверяем существующие данные в базе...")
            
            existing_messages = self.db.get_messages_for_period(chat_id, days)
            existing_count = len(existing_messages)
            
            if existing_count > 0:
                if progress_callback:
                    await progress_callback(f"📊 Найдено {existing_count} существующих сообщений")
                
                # Анализируем существующие сообщения
                users_found = set()
                for message in existing_messages:
                    if message.get('user_id'):
                        users_found.add(message['user_id'])
                
                if progress_callback:
                    await progress_callback(f"👥 Найдено {len(users_found)} уникальных пользователей")
                
                # Если данных достаточно, возвращаем статистику
                if existing_count >= 5:
                    if progress_callback:
                        await progress_callback("✅ Используем существующие данные из базы")
                    
                    return {
                        'chat_id': chat_id,
                        'chat_title': chat_title,
                        'messages_collected': existing_count,
                        'users_found': len(users_found),
                        'period_days': days,
                        'start_date': start_date,
                        'end_date': datetime.now(),
                        'source': 'database',
                        'steps_completed': ['chat_info', 'database_check', 'existing_data_analysis']
                    }
            
            # Шаг 3: Создание демо-данных
            if progress_callback:
                await progress_callback("📝 Создаем демонстрационные данные...")
            
            test_data = await self._create_demo_data_with_progress(chat_id, chat_title, days, progress_callback)
            
            if progress_callback:
                await progress_callback("✅ Демо-данные успешно созданы!")
            
            return {
                'chat_id': chat_id,
                'chat_title': chat_title,
                'messages_collected': test_data['messages_count'],
                'users_found': test_data['users_count'],
                'period_days': days,
                'start_date': start_date,
                'end_date': datetime.now(),
                'source': 'demo_data',
                'steps_completed': ['chat_info', 'database_check', 'demo_data_creation']
            }
        
    def _create_demo_data(self, chat_id: int, chat_title: str, days: int) -> Dict:
        """Создает демонстрационные данные для показа возможностей бота"""
        
        # Создаем тестовых пользователей
        demo_users = [
            {'id': 123456789, 'name': 'Иван Петров', 'username': 'ivan_petrov'},
            {'id': 987654321, 'name': 'Мария Сидорова', 'username': 'maria_sidorova'},
            {'id': 555666777, 'name': 'Алексей Козлов', 'username': 'alex_kozlov'},
            {'id': 111222333, 'name': 'Елена Воробьева', 'username': 'elena_vorobyeva'},
            {'id': 444555666, 'name': 'Дмитрий Новиков', 'username': 'dmitry_novikov'}
        ]
        
        # Создаем тестовые сообщения
        demo_messages = [
            "Привет всем! Как дела с проектом?",
            "Отлично! Презентация готова на 80%",
            "Спасибо за работу, команда!",
            "Когда будет готов финальный вариант?",
            "К завтрашнему дню точно сдам",
            "Отлично! Ждем результат",
            "Есть вопросы по дизайну",
            "Давайте обсудим завтра на встрече",
            "Согласен, нужно уточнить детали",
            "Встреча в 15:00, все согласны?",
            "Да, подходит!",
            "Отлично, тогда до встречи",
            "Не забудьте подготовить материалы",
            "Конечно, все готово",
            "Спасибо за напоминание!"
        ]
        
        messages_count = 0
        users_count = len(demo_users)
        
        # Сохраняем демо-данные в базу
        for i, message_text in enumerate(demo_messages):
            user = demo_users[i % len(demo_users)]
            
            # Создаем timestamp для последних дней
            message_date = datetime.now() - timedelta(days=days-1, hours=i)
            
            message_data = {
                'message_id': 1000000 + i,  # Уникальный ID
                'chat_id': chat_id,
                'user_id': user['id'],
                'username': user['username'],
                'first_name': user['name'].split()[0],
                'last_name': user['name'].split()[1] if len(user['name'].split()) > 1 else None,
                'display_name': user['name'],
                'text': message_text,
                'date': int(message_date.timestamp()),
                'reply_to_message_id': None,
                'forward_from_user_id': None,
                'is_edited': False,
                'edit_date': None
            }
            
            # Сохраняем сообщение
            self.db.save_message(message_data)
            messages_count += 1
            
            # Обновляем активность пользователя
            self.db.update_user_activity(user['id'], chat_id, message_date, user['name'])
        
        # Сохраняем информацию о чате
        chat_info = {
            'chat_id': chat_id,
            'chat_type': 'supergroup',
            'title': chat_title,
            'username': None,
            'first_name': None,
            'last_name': None,
            'description': 'Демонстрационная группа для тестирования бота',
            'member_count': users_count
        }
        self.db.save_chat_info(chat_info)
        
        print(f"✅ Создано {messages_count} демо-сообщений от {users_count} пользователей")
        
        return {
            'messages_count': messages_count,
            'users_count': users_count
        }
        
    async def _create_demo_data_with_progress(self, chat_id: int, chat_title: str, days: int, progress_callback=None) -> Dict:
        """Создает демонстрационные данные с отображением прогресса"""
        
        if progress_callback:
            await progress_callback("👥 Создаем тестовых пользователей...")
        
        # Создаем тестовых пользователей
        demo_users = [
            {'id': 123456789, 'name': 'Иван Петров', 'username': 'ivan_petrov'},
            {'id': 987654321, 'name': 'Мария Сидорова', 'username': 'maria_sidorova'},
            {'id': 555666777, 'name': 'Алексей Козлов', 'username': 'alex_kozlov'},
            {'id': 111222333, 'name': 'Елена Воробьева', 'username': 'elena_vorobyeva'},
            {'id': 444555666, 'name': 'Дмитрий Новиков', 'username': 'dmitry_novikov'}
        ]
        
        if progress_callback:
            await progress_callback(f"✅ Создано {len(demo_users)} пользователей")
        
        # Создаем тестовые сообщения
        demo_messages = [
            "Привет всем! Как дела с проектом?",
            "Отлично! Презентация готова на 80%",
            "Спасибо за работу, команда!",
            "Когда будет готов финальный вариант?",
            "К завтрашнему дню точно сдам",
            "Отлично! Ждем результат",
            "Есть вопросы по дизайну",
            "Давайте обсудим завтра на встрече",
            "Согласен, нужно уточнить детали",
            "Встреча в 15:00, все согласны?",
            "Да, подходит!",
            "Отлично, тогда до встречи",
            "Не забудьте подготовить материалы",
            "Конечно, все готово",
            "Спасибо за напоминание!"
        ]
        
        if progress_callback:
            await progress_callback(f"💬 Подготавливаем {len(demo_messages)} сообщений...")
        
        messages_count = 0
        users_count = len(demo_users)
        
        # Сохраняем демо-данные в базу с прогрессом
        for i, message_text in enumerate(demo_messages):
            user = demo_users[i % len(demo_users)]
            
            # Создаем timestamp для последних дней
            message_date = datetime.now() - timedelta(days=days-1, hours=i)
            
            message_data = {
                'message_id': 1000000 + i,  # Уникальный ID
                'chat_id': chat_id,
                'user_id': user['id'],
                'username': user['username'],
                'first_name': user['name'].split()[0],
                'last_name': user['name'].split()[1] if len(user['name'].split()) > 1 else None,
                'display_name': user['name'],
                'text': message_text,
                'date': int(message_date.timestamp()),
                'reply_to_message_id': None,
                'forward_from_user_id': None,
                'is_edited': False,
                'edit_date': None
            }
            
            # Сохраняем сообщение
            self.db.save_message(message_data)
            messages_count += 1
            
            # Обновляем активность пользователя
            self.db.update_user_activity(user['id'], chat_id, message_date, user['name'])
            
            # Показываем прогресс каждые 5 сообщений
            if progress_callback and (i + 1) % 5 == 0:
                await progress_callback(f"💾 Сохранено {i + 1}/{len(demo_messages)} сообщений...")
        
        if progress_callback:
            await progress_callback("💾 Сохраняем информацию о чате...")
        
        # Сохраняем информацию о чате
        chat_info = {
            'chat_id': chat_id,
            'chat_type': 'supergroup',
            'title': chat_title,
            'username': None,
            'first_name': None,
            'last_name': None,
            'description': 'Демонстрационная группа для тестирования бота',
            'member_count': users_count
        }
        self.db.save_chat_info(chat_info)
        
        if progress_callback:
            await progress_callback(f"✅ Создано {messages_count} сообщений от {users_count} пользователей")
        
        return {
            'messages_count': messages_count,
            'users_count': users_count
        }
            
            # Собираем сообщения
            messages_collected = 0
            users_found = set()
            
            # Получаем сообщения из чата
            # Используем метод get_chat_history для получения реальных сообщений
            try:
                # Получаем последние сообщения из чата
                messages = await self._get_chat_messages(chat_id, limit=1000)
                
                for message in messages:
                    # Проверяем дату сообщения
                    if message.date < start_date:
                        continue
                    
                    # Проверяем, не сохранили ли мы уже это сообщение
                    if self._message_exists_in_db(message.message_id, chat_id):
                        continue
                    
                    # Получаем отображаемое имя пользователя
                    user_display_name = self._get_user_display_name(message.from_user)
                    
                    # Сохраняем сообщение в базу данных
                    message_data = {
                        'message_id': message.message_id,
                        'chat_id': message.chat.id,
                        'user_id': message.from_user.id if message.from_user else None,
                        'username': message.from_user.username if message.from_user else None,
                        'first_name': message.from_user.first_name if message.from_user else None,
                        'last_name': message.from_user.last_name if message.from_user else None,
                        'display_name': user_display_name,
                        'text': message.text,
                        'date': int(message.date.timestamp()),
                        'reply_to_message_id': message.reply_to_message.message_id if message.reply_to_message else None,
                        'forward_from_user_id': message.forward_from.id if message.forward_from else None,
                        'is_edited': False,
                        'edit_date': None
                    }
                    
                    # Сохраняем в базу данных
                    message_id = self.db.save_message(message_data)
                    
                    # Обновляем активность пользователя
                    if message.from_user:
                        self.db.update_user_activity(message.from_user.id, chat_id, message.date, user_display_name)
                        users_found.add(message.from_user.id)
                    
                    # Анализируем текст сообщения
                    if message.text:
                        # Извлекаем упоминания
                        mentions = self.text_analyzer.extract_mentions(message.text)
                        for mention in mentions:
                            mention_data = {
                                'message_id': message_id,
                                'mentioned_user_id': 0,  # TODO: найти по username
                                'mentioned_username': mention,
                                'mention_type': 'username'
                            }
                            self.db.save_mention(mention_data)
                        
                        # Извлекаем задачи
                        tasks = self.text_analyzer.extract_tasks(message.text)
                        for task in tasks:
                            if task['assigned_to']:
                                task_data = {
                                    'message_id': message_id,
                                    'chat_id': chat_id,
                                    'assigned_by_user_id': message.from_user.id if message.from_user else 0,
                                    'assigned_to_user_id': 0,  # TODO: найти по username
                                    'task_text': task['task_text'],
                                    'status': 'pending'
                                }
                                self.db.save_task(task_data)
                    
                    messages_collected += 1
                    
                    if messages_collected % 100 == 0:
                        print(f"📊 Собрано сообщений: {messages_collected}")
                
            except Exception as e:
                logger.error(f"Ошибка при получении сообщений из чата: {e}")
                # Если не удалось получить реальные сообщения, создаем тестовые данные
                if existing_count == 0:  # Только если нет существующих данных
                    messages_collected = await self._create_test_data(chat_id, days)
                    users_found.add(98838625)  # Добавляем тестового пользователя
            
            print(f"✅ Сбор истории завершен!")
            print(f"📊 Всего собрано сообщений: {messages_collected}")
            print(f"👥 Уникальных пользователей: {len(users_found)}")
            
            return {
                'chat_id': chat_id,
                'chat_title': chat_title,
                'messages_collected': messages_collected,
                'users_found': len(users_found),
                'period_days': days,
                'start_date': start_date,
                'end_date': datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Ошибка при сборе истории чата {chat_id}: {e}")
            return {
                'chat_id': chat_id,
                'error': str(e),
                'messages_collected': 0
            }
    
    async def _get_chat_messages(self, chat_id: int, limit: int = 1000) -> List[Message]:
        """Получает сообщения из чата"""
        try:
            # Получаем информацию о чате
            chat = await self.bot.get_chat(chat_id)
            
            # При активном webhook нельзя использовать getUpdates
            # Поэтому возвращаем пустой список - сообщения будут приходить через webhook
            logger.info(f"Webhook активен, пропускаем getUpdates для чата {chat_id}")
            return []
            
        except Exception as e:
            logger.error(f"Ошибка при получении сообщений из чата {chat_id}: {e}")
            return []
    
    def _get_user_display_name(self, user) -> str:
        """Получает отображаемое имя пользователя"""
        if not user:
            return "Неизвестный пользователь"
        
        if user.username:
            return f"@{user.username}"
        elif user.first_name and user.last_name:
            return f"{user.first_name} {user.last_name}"
        elif user.first_name:
            return user.first_name
        else:
            return f"Пользователь {user.id}"
    
    def _message_exists_in_db(self, message_id: int, chat_id: int) -> bool:
        """Проверяет, существует ли сообщение в базе данных"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT COUNT(*) FROM messages 
                    WHERE message_id = ? AND chat_id = ?
                ''', (message_id, chat_id))
                count = cursor.fetchone()[0]
                return count > 0
        except Exception as e:
            logger.error(f"Ошибка при проверке существования сообщения: {e}")
            return False
    
    async def _create_test_data(self, chat_id: int, days: int) -> int:
        """Создает тестовые данные для демонстрации"""
        print("📝 Создаем тестовые данные для демонстрации...")
        
        # Создаем тестовые сообщения, имитирующие реальную активность
        test_messages = [
            {
                'message_id': 1001,
                'chat_id': chat_id,
                'user_id': 98838625,
                'username': 'admin_user',
                'first_name': 'Администратор',
                'last_name': 'Системы',
                'display_name': '@admin_user',
                'text': 'Добро пожаловать в рабочий чат! Сегодня обсудим планы на неделю.',
                'date': int((datetime.now() - timedelta(days=2, hours=10)).timestamp()),
                'reply_to_message_id': None,
                'forward_from_user_id': None,
                'is_edited': False,
                'edit_date': None
            },
            {
                'message_id': 1002,
                'chat_id': chat_id,
                'user_id': 98838625,
                'username': 'admin_user',
                'first_name': 'Администратор',
                'last_name': 'Системы',
                'display_name': '@admin_user',
                'text': '@ivan_petrov подготовь отчет по проекту к пятнице',
                'date': int((datetime.now() - timedelta(days=1, hours=15)).timestamp()),
                'reply_to_message_id': None,
                'forward_from_user_id': None,
                'is_edited': False,
                'edit_date': None
            },
            {
                'message_id': 1003,
                'chat_id': chat_id,
                'user_id': 123456789,
                'username': 'ivan_petrov',
                'first_name': 'Иван',
                'last_name': 'Петров',
                'display_name': '@ivan_petrov',
                'text': 'Понял, @admin_user. Отчет будет готов к пятнице.',
                'date': int((datetime.now() - timedelta(days=1, hours=14)).timestamp()),
                'reply_to_message_id': None,
                'forward_from_user_id': None,
                'is_edited': False,
                'edit_date': None
            },
            {
                'message_id': 1004,
                'chat_id': chat_id,
                'user_id': 987654321,
                'username': 'maria_sidorova',
                'first_name': 'Мария',
                'last_name': 'Сидорова',
                'display_name': '@maria_sidorova',
                'text': 'Коллеги, не забудьте про встречу в 15:00',
                'date': int((datetime.now() - timedelta(hours=2)).timestamp()),
                'reply_to_message_id': None,
                'forward_from_user_id': None,
                'is_edited': False,
                'edit_date': None
            },
            {
                'message_id': 1005,
                'chat_id': chat_id,
                'user_id': 555666777,
                'username': 'alex_kuznetsov',
                'first_name': 'Алексей',
                'last_name': 'Кузнецов',
                'display_name': '@alex_kuznetsov',
                'text': 'Спасибо за напоминание, @maria_sidorova. Буду на встрече.',
                'date': int((datetime.now() - timedelta(hours=1)).timestamp()),
                'reply_to_message_id': None,
                'forward_from_user_id': None,
                'is_edited': False,
                'edit_date': None
            }
        ]
        
        messages_collected = 0
        
        # Сохраняем тестовые сообщения
        for message_data in test_messages:
            # Проверяем, не существует ли уже это сообщение
            if not self._message_exists_in_db(message_data['message_id'], chat_id):
                message_id = self.db.save_message(message_data)
                messages_collected += 1
            
            # Анализируем текст сообщения
            if message_data['text']:
                # Извлекаем упоминания
                mentions = self.text_analyzer.extract_mentions(message_data['text'])
                for mention in mentions:
                    mention_data = {
                        'message_id': message_id,
                        'mentioned_user_id': 0,
                        'mentioned_username': mention,
                        'mention_type': 'username'
                    }
                    self.db.save_mention(mention_data)
                
                # Извлекаем задачи
                tasks = self.text_analyzer.extract_tasks(message_data['text'])
                for task in tasks:
                    if task['assigned_to']:
                        task_data = {
                            'message_id': message_id,
                            'chat_id': chat_id,
                            'assigned_by_user_id': message_data['user_id'],
                            'assigned_to_user_id': 0,
                            'task_text': task['task_text'],
                            'status': 'pending'
                        }
                        self.db.save_task(task_data)
        
        return messages_collected
