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
        
        # Используем новый модуль для сбора реальной истории
        from telegram_history_collector import TelegramHistoryCollector
        
        collector = TelegramHistoryCollector(self.bot_token, self.db, self.text_analyzer)
        return await collector.collect_real_chat_history(chat_id, days)
    
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
