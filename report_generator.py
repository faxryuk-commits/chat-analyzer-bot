import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging
from collections import defaultdict
import numpy as np
from wordcloud import WordCloud
import io
import base64

# Настройка для русского языка
plt.rcParams['font.family'] = ['DejaVu Sans', 'Arial Unicode MS', 'sans-serif']

logger = logging.getLogger(__name__)

class ReportGenerator:
    def __init__(self):
        self.colors = {
            'primary': '#2E86AB',
            'secondary': '#A23B72',
            'accent': '#F18F01',
            'success': '#C73E1D',
            'light': '#F8F9FA',
            'dark': '#343A40'
        }
        
        # Настройка стиля графиков
        sns.set_style("whitegrid")
        plt.style.use('seaborn-v0_8')
    
    def generate_daily_report(self, chat_data: Dict) -> str:
        """Генерирует ежедневный отчет"""
        report = []
        report.append("📊 **ЕЖЕДНЕВНЫЙ ОТЧЕТ ПО АКТИВНОСТИ**")
        report.append(f"📅 Дата: {datetime.now().strftime('%d.%m.%Y')}")
        report.append("=" * 50)
        
        # Общая статистика
        report.append("\n📈 **ОБЩАЯ СТАТИСТИКА:**")
        report.append(f"• Всего сообщений: {chat_data.get('total_messages', 0)}")
        report.append(f"• Активных пользователей: {chat_data.get('active_users', 0)}")
        report.append(f"• Упоминаний: {chat_data.get('total_mentions', 0)}")
        
        # Топ активных пользователей
        if chat_data.get('top_users'):
            report.append("\n👥 **ТОП АКТИВНЫХ ПОЛЬЗОВАТЕЛЕЙ:**")
            for i, user in enumerate(chat_data['top_users'][:5], 1):
                name = user.get('name', f"Пользователь {user['user_id']}")
                report.append(f"{i}. {name}: {user['messages_count']} сообщений")
        
        # Популярные темы
        if chat_data.get('popular_topics'):
            report.append("\n🎯 **ПОПУЛЯРНЫЕ ТЕМЫ:**")
            for topic, count in chat_data['popular_topics'][:5]:
                report.append(f"• {topic}: {count} упоминаний")
        
        # Статистика задач
        if chat_data.get('task_stats'):
            task_stats = chat_data['task_stats']
            report.append("\n✅ **СТАТИСТИКА ЗАДАЧ:**")
            report.append(f"• Всего задач: {task_stats.get('total_tasks', 0)}")
            report.append(f"• Выполнено: {task_stats.get('status_stats', {}).get('completed', 0)}")
            report.append(f"• В работе: {task_stats.get('status_stats', {}).get('pending', 0)}")
            report.append(f"• Просрочено: {task_stats.get('overdue_count', 0)}")
        
        # Активность по часам
        if chat_data.get('hourly_activity'):
            report.append("\n⏰ **АКТИВНОСТЬ ПО ЧАСАМ:**")
            peak_hour = max(chat_data['hourly_activity'].items(), key=lambda x: x[1])
            report.append(f"• Пик активности: {peak_hour[0]}:00 ({peak_hour[1]} сообщений)")
        
        # Рекомендации
        report.append("\n💡 **РЕКОМЕНДАЦИИ:**")
        if chat_data.get('total_messages', 0) < 10:
            report.append("• Низкая активность в чате. Рассмотрите возможность стимулирования общения.")
        
        if chat_data.get('task_stats', {}).get('overdue_count', 0) > 0:
            report.append("• Есть просроченные задачи. Необходимо проверить их статус.")
        
        if chat_data.get('total_mentions', 0) > 20:
            report.append("• Высокая активность упоминаний. Команда активно взаимодействует.")
        
        return "\n".join(report)
    
    def generate_weekly_report(self, chat_data: Dict) -> str:
        """Генерирует еженедельный отчет"""
        report = []
        report.append("📊 **ЕЖЕНЕДЕЛЬНЫЙ ОТЧЕТ ПО АКТИВНОСТИ**")
        report.append(f"📅 Период: {datetime.now().strftime('%d.%m.%Y')}")
        report.append("=" * 50)
        
        # Тренды активности
        if chat_data.get('activity_trends'):
            report.append("\n📈 **ТРЕНДЫ АКТИВНОСТИ:**")
            trends = chat_data['activity_trends']
            if trends.get('growth_rate', 0) > 0:
                report.append(f"• Рост активности: +{trends['growth_rate']:.1f}%")
            else:
                report.append(f"• Снижение активности: {trends['growth_rate']:.1f}%")
        
        # Анализ эффективности
        if chat_data.get('efficiency_metrics'):
            metrics = chat_data['efficiency_metrics']
            report.append("\n⚡ **МЕТРИКИ ЭФФЕКТИВНОСТИ:**")
            report.append(f"• Среднее время ответа: {metrics.get('avg_response_time', 0):.1f} мин")
            report.append(f"• Процент выполненных задач: {metrics.get('task_completion_rate', 0):.1f}%")
        
        return "\n".join(report)
    
    def create_user_activity_chart(self, user_data: List[Dict]) -> str:
        """Создает график активности пользователей"""
        if not user_data:
            return ""
        
        plt.figure(figsize=(12, 8))
        
        # Подготавливаем данные
        users = []
        messages = []
        colors = []
        
        for i, user in enumerate(user_data[:10]):  # Топ 10 пользователей
            name = user.get('name', f"Пользователь {user['user_id']}")
            users.append(name)
            messages.append(user['messages_count'])
            colors.append(self.colors['primary'] if i < 3 else self.colors['secondary'])
        
        # Создаем график
        bars = plt.bar(users, messages, color=colors, alpha=0.8)
        plt.title('Активность пользователей', fontsize=16, fontweight='bold')
        plt.xlabel('Пользователи', fontsize=12)
        plt.ylabel('Количество сообщений', fontsize=12)
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        
        # Добавляем значения на столбцы
        for bar, msg_count in zip(bars, messages):
            plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                    str(msg_count), ha='center', va='bottom', fontweight='bold')
        
        # Сохраняем график в base64
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', dpi=300, bbox_inches='tight')
        img_buffer.seek(0)
        img_str = base64.b64encode(img_buffer.getvalue()).decode()
        plt.close()
        
        return img_str
    
    def create_hourly_activity_chart(self, hourly_data: Dict) -> str:
        """Создает график активности по часам"""
        if not hourly_data:
            return ""
        
        plt.figure(figsize=(12, 6))
        
        hours = list(range(24))
        activity = [hourly_data.get(hour, 0) for hour in hours]
        
        plt.plot(hours, activity, marker='o', linewidth=3, markersize=8, 
                color=self.colors['primary'])
        plt.fill_between(hours, activity, alpha=0.3, color=self.colors['primary'])
        
        plt.title('Активность по часам', fontsize=16, fontweight='bold')
        plt.xlabel('Час дня', fontsize=12)
        plt.ylabel('Количество сообщений', fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.xticks(hours[::2])
        plt.tight_layout()
        
        # Сохраняем график
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', dpi=300, bbox_inches='tight')
        img_buffer.seek(0)
        img_str = base64.b64encode(img_buffer.getvalue()).decode()
        plt.close()
        
        return img_str
    
    def create_topic_distribution_chart(self, topic_data: Dict) -> str:
        """Создает график распределения тем"""
        if not topic_data:
            return ""
        
        plt.figure(figsize=(10, 8))
        
        topics = list(topic_data.keys())
        counts = list(topic_data.values())
        
        # Создаем круговую диаграмму
        colors = plt.cm.Set3(np.linspace(0, 1, len(topics)))
        wedges, texts, autotexts = plt.pie(counts, labels=topics, autopct='%1.1f%%',
                                          colors=colors, startangle=90)
        
        plt.title('Распределение тем обсуждения', fontsize=16, fontweight='bold')
        plt.axis('equal')
        
        # Сохраняем график
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', dpi=300, bbox_inches='tight')
        img_buffer.seek(0)
        img_str = base64.b64encode(img_buffer.getvalue()).decode()
        plt.close()
        
        return img_str
    
    def create_task_status_chart(self, task_stats: Dict) -> str:
        """Создает график статуса задач"""
        if not task_stats:
            return ""
        
        plt.figure(figsize=(8, 8))
        
        statuses = list(task_stats.get('status_stats', {}).keys())
        counts = list(task_stats.get('status_stats', {}).values())
        
        if not statuses:
            return ""
        
        colors = [self.colors['success'] if status == 'completed' else 
                 self.colors['accent'] if status == 'pending' else 
                 self.colors['secondary'] for status in statuses]
        
        wedges, texts, autotexts = plt.pie(counts, labels=statuses, autopct='%1.1f%%',
                                          colors=colors, startangle=90)
        
        plt.title('Статус задач', fontsize=16, fontweight='bold')
        plt.axis('equal')
        
        # Сохраняем график
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', dpi=300, bbox_inches='tight')
        img_buffer.seek(0)
        img_str = base64.b64encode(img_buffer.getvalue()).decode()
        plt.close()
        
        return img_str
    
    def create_word_cloud(self, word_data: Dict) -> str:
        """Создает облако слов"""
        if not word_data:
            return ""
        
        plt.figure(figsize=(12, 8))
        
        wordcloud = WordCloud(
            width=800, height=600,
            background_color='white',
            colormap='viridis',
            max_words=100,
            relative_scaling=0.5
        ).generate_from_frequencies(word_data)
        
        plt.imshow(wordcloud, interpolation='bilinear')
        plt.axis('off')
        plt.title('Облако слов', fontsize=16, fontweight='bold', pad=20)
        
        # Сохраняем график
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', dpi=300, bbox_inches='tight')
        img_buffer.seek(0)
        img_str = base64.b64encode(img_buffer.getvalue()).decode()
        plt.close()
        
        return img_str
    
    def generate_task_report(self, tasks: List[Dict]) -> str:
        """Генерирует отчет по задачам"""
        if not tasks:
            return "📋 Нет активных задач"
        
        report = []
        report.append("📋 **ОТЧЕТ ПО ЗАДАЧАМ**")
        report.append("=" * 30)
        
        # Группируем задачи по статусу
        pending_tasks = [t for t in tasks if t['status'] == 'pending']
        completed_tasks = [t for t in tasks if t['status'] == 'completed']
        
        if pending_tasks:
            report.append(f"\n⏳ **В РАБОТЕ ({len(pending_tasks)}):**")
            for task in pending_tasks[:5]:  # Показываем первые 5
                assignee = task.get('assigned_to_name', f"Пользователь {task['assigned_to_user_id']}")
                report.append(f"• {task['task_text'][:50]}... (назначено: {assignee})")
        
        if completed_tasks:
            report.append(f"\n✅ **ВЫПОЛНЕНО ({len(completed_tasks)}):**")
            for task in completed_tasks[:3]:  # Показываем первые 3
                assignee = task.get('assigned_to_name', f"Пользователь {task['assigned_to_user_id']}")
                report.append(f"• {task['task_text'][:50]}... (выполнил: {assignee})")
        
        return "\n".join(report)
    
    def generate_mention_report(self, mentions: List[Dict]) -> str:
        """Генерирует отчет по упоминаниям"""
        if not mentions:
            return "👥 Нет упоминаний за период"
        
        report = []
        report.append("👥 **ОТЧЕТ ПО УПОМИНАНИЯМ**")
        report.append("=" * 30)
        
        report.append(f"\n📊 **ТОП УПОМИНАЕМЫХ ПОЛЬЗОВАТЕЛЕЙ:**")
        for i, mention in enumerate(mentions[:5], 1):
            name = mention.get('name', f"Пользователь {mention['mentioned_user_id']}")
            report.append(f"{i}. {name}: {mention['mention_count']} упоминаний")
        
        return "\n".join(report)
    
    def format_time_spent(self, minutes: int) -> str:
        """Форматирует время, проведенное в чате"""
        if minutes < 60:
            return f"{minutes} мин"
        elif minutes < 1440:  # меньше дня
            hours = minutes // 60
            mins = minutes % 60
            return f"{hours}ч {mins}мин"
        else:
            days = minutes // 1440
            hours = (minutes % 1440) // 60
            return f"{days}д {hours}ч"
