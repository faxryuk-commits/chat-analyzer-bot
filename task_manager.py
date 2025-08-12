import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import logging
from database import DatabaseManager
from text_analyzer import TextAnalyzer

logger = logging.getLogger(__name__)

class TaskManager:
    def __init__(self, db: DatabaseManager, text_analyzer: TextAnalyzer):
        self.db = db
        self.text_analyzer = text_analyzer
        
        # Паттерны для извлечения задач
        self.task_patterns = [
            # @username задача
            r'@(\w+)\s+(.+?)(?:\.|$|!)',
            # имя нужно/должен сделать
            r'(\w+)\s+(?:нужно|должен|сделай|выполни|подготовь)\s+(.+?)(?:\.|$|!)',
            # задача: описание
            r'(?:задача|поручение|дело|задание):\s*(.+?)(?:\.|$|!)',
            # попроси имя сделать
            r'(?:попроси|попросите)\s+(\w+)\s+(.+?)(?:\.|$|!)',
            # к завтра/к пятнице
            r'(.+?)\s+к\s+(?:завтра|понедельнику|вторнику|среде|четвергу|пятнице|субботе|воскресенью)',
            # до времени
            r'(.+?)\s+до\s+(\d{1,2}[.:]\d{2})',
            # срочно
            r'(?:срочно|немедленно|быстро)\s+(.+?)(?:\.|$|!)'
        ]
    
    def extract_tasks_from_message(self, message_text: str, message_id: int, 
                                  chat_id: int, user_id: int) -> List[Dict]:
        """Извлекает задачи из сообщения"""
        tasks = []
        
        for pattern in self.task_patterns:
            matches = re.findall(pattern, message_text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    if len(match) == 2:
                        # Паттерн с двумя группами (например, @username задача)
                        assigned_to = match[0]
                        task_text = match[1].strip()
                    else:
                        continue
                else:
                    # Паттерн с одной группой
                    assigned_to = None
                    task_text = match.strip()
                
                # Очищаем текст задачи
                task_text = self._clean_task_text(task_text)
                
                if task_text and len(task_text) > 3:
                    # Извлекаем дедлайн
                    deadline = self._extract_deadline(message_text)
                    
                    # Определяем приоритет
                    priority = self._determine_priority(message_text)
                    
                    task_data = {
                        'message_id': message_id,
                        'chat_id': chat_id,
                        'assigned_by_user_id': user_id,
                        'assigned_to_username': assigned_to,
                        'task_text': task_text,
                        'priority': priority,
                        'deadline': deadline,
                        'status': 'pending',
                        'created_at': datetime.now()
                    }
                    
                    tasks.append(task_data)
        
        return tasks
    
    def _clean_task_text(self, text: str) -> str:
        """Очищает текст задачи от лишних символов"""
        # Убираем лишние пробелы
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Убираем эмодзи
        text = re.sub(r'[^\w\sа-яА-Я.,!?]', '', text)
        
        return text
    
    def _extract_deadline(self, text: str) -> Optional[datetime]:
        """Извлекает дедлайн из текста"""
        deadline_patterns = [
            # к завтра
            r'к\s+завтра',
            # к пятнице
            r'к\s+(?:понедельнику|вторнику|среде|четвергу|пятнице|субботе|воскресенью)',
            # до 18:00
            r'до\s+(\d{1,2}[.:]\d{2})',
            # к 18:00
            r'к\s+(\d{1,2}[.:]\d{2})',
            # сегодня
            r'сегодня',
            # завтра
            r'завтра'
        ]
        
        text_lower = text.lower()
        
        for pattern in deadline_patterns:
            if re.search(pattern, text_lower):
                if 'завтра' in text_lower:
                    return datetime.now() + timedelta(days=1)
                elif 'сегодня' in text_lower:
                    return datetime.now().replace(hour=18, minute=0, second=0, microsecond=0)
                elif 'до' in text_lower or 'к' in text_lower:
                    time_match = re.search(r'(\d{1,2})[.:](\d{2})', text)
                    if time_match:
                        hour = int(time_match.group(1))
                        minute = int(time_match.group(2))
                        deadline = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
                        if deadline < datetime.now():
                            deadline += timedelta(days=1)
                        return deadline
        
        return None
    
    def _determine_priority(self, text: str) -> str:
        """Определяет приоритет задачи"""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ['срочно', 'немедленно', 'быстро', 'сейчас же']):
            return 'high'
        elif any(word in text_lower for word in ['важно', 'критично', 'авария']):
            return 'medium'
        else:
            return 'low'
    
    def create_task(self, task_data: Dict) -> int:
        """Создает новую задачу"""
        # Находим user_id по username
        assigned_to_user_id = self._find_user_id_by_username(
            task_data['assigned_to_username'], 
            task_data['chat_id']
        )
        
        if not assigned_to_user_id:
            logger.warning(f"Пользователь {task_data['assigned_to_username']} не найден")
            return None
        
        # Обновляем данные задачи
        task_data['assigned_to_user_id'] = assigned_to_user_id
        del task_data['assigned_to_username']
        
        # Сохраняем в базу данных
        return self.db.save_task(task_data)
    
    def _find_user_id_by_username(self, username: str, chat_id: int) -> Optional[int]:
        """Находит user_id по username"""
        if not username:
            return None
        
        # Ищем в базе данных по username
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT DISTINCT user_id FROM messages 
                WHERE chat_id = ? AND username = ?
                ORDER BY date DESC LIMIT 1
            ''', (chat_id, username))
            
            result = cursor.fetchone()
            return result['user_id'] if result else None
    
    def get_user_tasks(self, user_id: int, chat_id: int, status: str = None) -> List[Dict]:
        """Получает задачи пользователя"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            
            query = '''
                SELECT t.*, m.username as assigned_by_username, m.first_name, m.last_name
                FROM tasks t
                JOIN messages m ON t.message_id = m.id
                WHERE t.assigned_to_user_id = ? AND t.chat_id = ?
            '''
            params = [user_id, chat_id]
            
            if status:
                query += ' AND t.status = ?'
                params.append(status)
            
            query += ' ORDER BY t.created_at DESC'
            
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_overdue_tasks(self, chat_id: int) -> List[Dict]:
        """Получает просроченные задачи"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT t.*, m.username as assigned_by_username, m.first_name, m.last_name
                FROM tasks t
                JOIN messages m ON t.message_id = m.id
                WHERE t.chat_id = ? AND t.status = 'pending' 
                AND t.deadline IS NOT NULL AND t.deadline < datetime('now')
                ORDER BY t.deadline ASC
            ''', (chat_id,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_task_statistics(self, chat_id: int, days: int = 30) -> Dict:
        """Получает статистику по задачам"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # Общая статистика
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_tasks,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_tasks,
                    SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending_tasks,
                    SUM(CASE WHEN priority = 'high' THEN 1 ELSE 0 END) as high_priority,
                    SUM(CASE WHEN priority = 'medium' THEN 1 ELSE 0 END) as medium_priority,
                    SUM(CASE WHEN priority = 'low' THEN 1 ELSE 0 END) as low_priority
                FROM tasks
                WHERE chat_id = ? AND created_at >= ?
            ''', (chat_id, cutoff_date))
            
            stats = dict(cursor.fetchone())
            
            # Статистика по пользователям
            cursor.execute('''
                SELECT 
                    t.assigned_to_user_id,
                    m.username,
                    m.first_name,
                    m.last_name,
                    COUNT(*) as total_assigned,
                    SUM(CASE WHEN t.status = 'completed' THEN 1 ELSE 0 END) as completed,
                    AVG(CASE WHEN t.status = 'completed' 
                        THEN (julianday(t.completed_at) - julianday(t.created_at)) * 24 * 60
                        ELSE NULL END) as avg_completion_time
                FROM tasks t
                JOIN messages m ON t.message_id = m.id
                WHERE t.chat_id = ? AND t.created_at >= ?
                GROUP BY t.assigned_to_user_id
                ORDER BY total_assigned DESC
            ''', (chat_id, cutoff_date))
            
            user_stats = [dict(row) for row in cursor.fetchall()]
            
            return {
                'general': stats,
                'by_user': user_stats
            }
    
    def mark_task_completed(self, task_id: int, user_id: int) -> bool:
        """Отмечает задачу как выполненную"""
        try:
            self.db.mark_task_completed(task_id)
            
            # Добавляем запись о выполнении
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE tasks 
                    SET completed_by_user_id = ?, completed_at = datetime('now')
                    WHERE id = ?
                ''', (user_id, task_id))
            
            return True
        except Exception as e:
            logger.error(f"Ошибка при отметке задачи как выполненной: {e}")
            return False
    
    def update_task_priority(self, task_id: int, priority: str) -> bool:
        """Обновляет приоритет задачи"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE tasks 
                    SET priority = ?
                    WHERE id = ?
                ''', (priority, task_id))
            
            return True
        except Exception as e:
            logger.error(f"Ошибка при обновлении приоритета: {e}")
            return False
    
    def add_task_comment(self, task_id: int, user_id: int, comment: str) -> bool:
        """Добавляет комментарий к задаче"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO task_comments (task_id, user_id, comment, created_at)
                    VALUES (?, ?, ?, datetime('now'))
                ''', (task_id, user_id, comment))
            
            return True
        except Exception as e:
            logger.error(f"Ошибка при добавлении комментария: {e}")
            return False
    
    def get_task_comments(self, task_id: int) -> List[Dict]:
        """Получает комментарии к задаче"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT tc.*, m.username, m.first_name, m.last_name
                FROM task_comments tc
                JOIN messages m ON tc.user_id = m.user_id
                WHERE tc.task_id = ?
                ORDER BY tc.created_at ASC
            ''', (task_id,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def check_task_responses(self, message_id: int, user_id: int) -> Optional[int]:
        """Проверяет, является ли сообщение ответом на задачу"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Ищем задачу, на которую может быть ответ
            cursor.execute('''
                SELECT t.id FROM tasks t
                JOIN messages m ON t.message_id = m.id
                WHERE m.message_id = ? AND t.assigned_to_user_id = ?
            ''', (message_id, user_id))
            
            result = cursor.fetchone()
            return result['id'] if result else None
    
    def get_task_reminders(self) -> List[Dict]:
        """Получает задачи для напоминаний"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Задачи с дедлайном в ближайшие 2 часа
            reminder_time = datetime.now() + timedelta(hours=2)
            
            cursor.execute('''
                SELECT t.*, m.username, m.first_name, m.last_name
                FROM tasks t
                JOIN messages m ON t.message_id = m.id
                WHERE t.status = 'pending' 
                AND t.deadline IS NOT NULL 
                AND t.deadline <= ? 
                AND t.deadline > datetime('now')
                ORDER BY t.deadline ASC
            ''', (reminder_time,))
            
            return [dict(row) for row in cursor.fetchall()]
