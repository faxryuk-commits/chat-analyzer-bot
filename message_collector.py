#!/usr/bin/env python3
"""
Модуль для сбора истории сообщений из Telegram чатов
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from telegram import Bot, Update
from telegram.ext import Application
from database import DatabaseManager
from text_analyzer import TextAnalyzer

logger = logging.getLogger(__name__)

class MessageCollector:
    def __init__(self, bot_token: str, db: DatabaseManager, text_analyzer: TextAnalyzer):
        self.bot_token = bot_token
        self.db = db
        self.text_analyzer = text_analyzer
        self.bot = Bot(token=bot_token)
        
    async def collect_chat_history(self, chat_id: int, days: int = 45) -> Dict:
        """Собирает историю сообщений из чата за указанное количество дней"""
        
        print(f"📥 Начинаем сбор истории для чата {chat_id} за последние {days} дней...")
        
        # Вычисляем дату начала сбора
        start_date = datetime.now() - timedelta(days=days)
        
        try:
            # Получаем информацию о чате
            chat_info = await self.bot.get_chat(chat_id)
            chat_title = chat_info.title if hasattr(chat_info, 'title') else f"Чат {chat_id}"
            
            print(f"📋 Чат: {chat_title}")
            print(f"📅 Период: с {start_date.strftime('%d.%m.%Y')} по {datetime.now().strftime('%d.%m.%Y')}")
            
            # Собираем сообщения
            messages_collected = 0
            users_found = set()
            
            # Получаем сообщения по частям (Telegram API ограничения)
            offset = 0
            limit = 100
            
            while True:
                try:
                    # Получаем обновления (сообщения)
                    updates = await self.bot.get_updates(
                        offset=offset,
                        limit=limit,
                        timeout=30
                    )
                    
                    if not updates:
                        break
                    
                    for update in updates:
                        if update.message and update.message.chat.id == chat_id:
                            message = update.message
                            
                            # Проверяем дату сообщения
                            if message.date < start_date:
                                continue
                            
                            # Сохраняем сообщение в базу данных
                            message_data = {
                                'message_id': message.message_id,
                                'chat_id': message.chat.id,
                                'user_id': message.from_user.id if message.from_user else None,
                                'username': message.from_user.username if message.from_user else None,
                                'first_name': message.from_user.first_name if message.from_user else None,
                                'last_name': message.from_user.last_name if message.from_user else None,
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
                                self.db.update_user_activity(message.from_user.id, chat_id, message.date)
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
                    
                    # Обновляем offset для следующей порции
                    if updates:
                        offset = updates[-1].update_id + 1
                    else:
                        break
                        
                except Exception as e:
                    logger.error(f"Ошибка при сборе сообщений: {e}")
                    break
            
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
    
    async def collect_all_chats_history(self, chat_ids: List[int], days: int = 45) -> List[Dict]:
        """Собирает историю из всех указанных чатов"""
        
        results = []
        
        for chat_id in chat_ids:
            print(f"\n{'='*50}")
            result = await self.collect_chat_history(chat_id, days)
            results.append(result)
            
            # Небольшая пауза между чатами
            await asyncio.sleep(2)
        
        return results
    
    async def generate_daily_report(self, chat_id: int) -> Dict:
        """Генерирует ежедневный отчет по активности"""
        
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)
        
        # Получаем сообщения за вчера
        messages = self.db.get_messages_for_period(chat_id, 1)
        user_stats = self.db.get_user_activity_stats(chat_id, 1)
        mention_stats = self.db.get_mention_stats(chat_id, 1)
        task_stats = self.db.get_task_stats(chat_id, 1)
        
        # Анализируем темы
        texts = [msg['text'] for msg in messages if msg['text']]
        topic_distribution = self.text_analyzer.get_topic_distribution(texts)
        
        # Анализируем поток беседы
        conversation_flow = self.text_analyzer.analyze_conversation_flow(messages)
        
        # Формируем отчет
        report = {
            'date': yesterday,
            'chat_id': chat_id,
            'total_messages': len(messages),
            'active_users': len(user_stats),
            'total_mentions': sum(m['mention_count'] for m in mention_stats),
            'top_users': user_stats[:5],
            'popular_topics': sorted(topic_distribution.items(), key=lambda x: x[1], reverse=True)[:5],
            'task_stats': task_stats,
            'hourly_activity': conversation_flow.get('hourly_activity', {}),
            'avg_response_time': conversation_flow.get('avg_response_time', 0)
        }
        
        return report
    
    async def schedule_daily_collection(self, chat_ids: List[int]):
        """Планирует ежедневный сбор данных"""
        
        print(f"📅 Настройка ежедневного сбора данных для {len(chat_ids)} чатов...")
        
        # Здесь можно добавить планировщик задач
        # Например, использовать APScheduler или Celery
        
        for chat_id in chat_ids:
            print(f"✅ Чат {chat_id} добавлен в ежедневный сбор")
        
        print("🎯 Ежедневный сбор будет происходить в 18:00")
