import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import logging
from config import DATABASE_PATH

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self):
        """Создает соединение с базой данных"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_database(self):
        """Инициализирует таблицы базы данных"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Таблица сообщений
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id INTEGER NOT NULL,
                    chat_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    display_name TEXT,
                    text TEXT,
                    date INTEGER NOT NULL,
                    reply_to_message_id INTEGER,
                    forward_from_user_id INTEGER,
                    is_edited BOOLEAN DEFAULT FALSE,
                    edit_date INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица упоминаний
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS mentions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id INTEGER NOT NULL,
                    mentioned_user_id INTEGER NOT NULL,
                    mentioned_username TEXT,
                    mention_type TEXT DEFAULT 'username',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (message_id) REFERENCES messages (id)
                )
            ''')
            
            # Таблица задач
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id INTEGER NOT NULL,
                    chat_id INTEGER NOT NULL,
                    assigned_by_user_id INTEGER NOT NULL,
                    assigned_to_user_id INTEGER NOT NULL,
                    task_text TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    deadline TIMESTAMP,
                    FOREIGN KEY (message_id) REFERENCES messages (id)
                )
            ''')
            
            # Таблица реакций на задачи
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_responses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL,
                    response_message_id INTEGER NOT NULL,
                    response_user_id INTEGER NOT NULL,
                    response_text TEXT,
                    response_type TEXT DEFAULT 'reply',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks (id),
                    FOREIGN KEY (response_message_id) REFERENCES messages (id)
                )
            ''')
            
            # Таблица активности пользователей
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_activity (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    chat_id INTEGER NOT NULL,
                    date DATE NOT NULL,
                    messages_count INTEGER DEFAULT 0,
                    first_message_time TIMESTAMP,
                    last_message_time TIMESTAMP,
                    total_time_minutes INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, chat_id, date)
                )
            ''')
            
            # Таблица тем сообщений
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS message_topics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id INTEGER NOT NULL,
                    topic TEXT NOT NULL,
                    confidence REAL DEFAULT 0.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (message_id) REFERENCES messages (id)
                )
            ''')
            
            # Индексы для оптимизации
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_chat_date ON messages(chat_id, date)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_user ON messages(user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_mentions_user ON mentions(mentioned_user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_tasks_assigned_to ON tasks(assigned_to_user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_activity_user_date ON user_activity(user_id, date)')
            
            conn.commit()
    
    def save_message(self, message_data: Dict) -> int:
        """Сохраняет сообщение в базу данных"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO messages (
                    message_id, chat_id, user_id, username, first_name, last_name, display_name,
                    text, date, reply_to_message_id, forward_from_user_id, is_edited, edit_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                message_data['message_id'],
                message_data['chat_id'],
                message_data['user_id'],
                message_data.get('username'),
                message_data.get('first_name'),
                message_data.get('last_name'),
                message_data.get('display_name', ''),
                message_data.get('text'),
                message_data['date'],
                message_data.get('reply_to_message_id'),
                message_data.get('forward_from_user_id'),
                message_data.get('is_edited', False),
                message_data.get('edit_date')
            ))
            
            return cursor.lastrowid
    
    def save_mention(self, mention_data: Dict) -> int:
        """Сохраняет упоминание пользователя"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO mentions (
                    message_id, mentioned_user_id, mentioned_username, mention_type
                ) VALUES (?, ?, ?, ?)
            ''', (
                mention_data['message_id'],
                mention_data['mentioned_user_id'],
                mention_data.get('mentioned_username'),
                mention_data.get('mention_type', 'username')
            ))
            
            return cursor.lastrowid
    
    def save_task(self, task_data: Dict) -> int:
        """Сохраняет задачу"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO tasks (
                    message_id, chat_id, assigned_by_user_id, assigned_to_user_id,
                    task_text, status, deadline
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                task_data['message_id'],
                task_data['chat_id'],
                task_data['assigned_by_user_id'],
                task_data['assigned_to_user_id'],
                task_data['task_text'],
                task_data.get('status', 'pending'),
                task_data.get('deadline')
            ))
            
            return cursor.lastrowid
    
    def save_task_response(self, response_data: Dict) -> int:
        """Сохраняет ответ на задачу"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO task_responses (
                    task_id, response_message_id, response_user_id, response_text, response_type
                ) VALUES (?, ?, ?, ?, ?)
            ''', (
                response_data['task_id'],
                response_data['response_message_id'],
                response_data['response_user_id'],
                response_data.get('response_text'),
                response_data.get('response_type', 'reply')
            ))
            
            return cursor.lastrowid
    
    def update_user_activity(self, user_id: int, chat_id: int, message_time: datetime, display_name: str = None):
        """Обновляет активность пользователя"""
        date = message_time.date()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Проверяем существующую запись
            cursor.execute('''
                SELECT * FROM user_activity 
                WHERE user_id = ? AND chat_id = ? AND date = ?
            ''', (user_id, chat_id, date))
            
            existing = cursor.fetchone()
            
            if existing:
                # Обновляем существующую запись
                cursor.execute('''
                    UPDATE user_activity SET
                        messages_count = messages_count + 1,
                        last_message_time = ?,
                        total_time_minutes = CASE 
                            WHEN first_message_time IS NOT NULL 
                            THEN (julianday(?) - julianday(first_message_time)) * 24 * 60
                            ELSE 0
                        END
                    WHERE user_id = ? AND chat_id = ? AND date = ?
                ''', (message_time, message_time, user_id, chat_id, date))
            else:
                # Создаем новую запись
                cursor.execute('''
                    INSERT INTO user_activity (
                        user_id, chat_id, date, messages_count, first_message_time, last_message_time
                    ) VALUES (?, ?, ?, 1, ?, ?)
                ''', (user_id, chat_id, date, message_time, message_time))
    
    def get_messages_for_period(self, chat_id: int, days: int = 45) -> List[Dict]:
        """Получает сообщения за указанный период"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cutoff_date = datetime.now() - timedelta(days=days)
            cutoff_timestamp = int(cutoff_date.timestamp())
            
            cursor.execute('''
                SELECT * FROM messages 
                WHERE chat_id = ? AND date >= ?
                ORDER BY date DESC
            ''', (chat_id, cutoff_timestamp))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_user_activity_stats(self, chat_id: int, days: int = 45) -> List[Dict]:
        """Получает статистику активности пользователей"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cutoff_date = datetime.now() - timedelta(days=days)
            
            cursor.execute('''
                SELECT 
                    ua.user_id,
                    ua.messages_count,
                    ua.total_time_minutes,
                    ua.first_message_time,
                    ua.last_message_time,
                    m.username,
                    m.first_name,
                    m.last_name,
                    m.display_name
                FROM user_activity ua
                LEFT JOIN (
                    SELECT DISTINCT user_id, username, first_name, last_name, display_name 
                    FROM messages 
                    WHERE chat_id = ?
                ) m ON ua.user_id = m.user_id
                WHERE ua.chat_id = ? AND ua.date >= ?
                ORDER BY ua.messages_count DESC
            ''', (chat_id, chat_id, cutoff_date))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_mention_stats(self, chat_id: int, days: int = 45) -> List[Dict]:
        """Получает статистику упоминаний"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cutoff_date = datetime.now() - timedelta(days=days)
            cutoff_timestamp = int(cutoff_date.timestamp())
            
            cursor.execute('''
                SELECT 
                    m.mentioned_user_id,
                    m.mentioned_username,
                    COUNT(*) as mention_count,
                    msg.username,
                    msg.first_name,
                    msg.last_name
                FROM mentions m
                JOIN messages msg ON m.message_id = msg.id
                WHERE msg.chat_id = ? AND msg.date >= ?
                GROUP BY m.mentioned_user_id
                ORDER BY mention_count DESC
            ''', (chat_id, cutoff_timestamp))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_monitored_groups(self) -> List[Dict]:
        """Получает список групп, которые мониторит бот"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT 
                    chat_id,
                    COUNT(*) as messages_count,
                    COUNT(DISTINCT user_id) as users_count,
                    MAX(datetime(date, 'unixepoch')) as last_activity
                FROM messages 
                GROUP BY chat_id
                ORDER BY messages_count DESC
            ''')
            
            groups = []
            for row in cursor.fetchall():
                groups.append({
                    'chat_id': row['chat_id'],
                    'messages_count': row['messages_count'],
                    'users_count': row['users_count'],
                    'last_activity': row['last_activity']
                })
            
            return groups
    
    def get_task_stats(self, chat_id: int, days: int = 45) -> Dict:
        """Получает статистику задач"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cutoff_date = datetime.now() - timedelta(days=days)
            
            cursor.execute('''
                SELECT 
                    status,
                    COUNT(*) as count
                FROM tasks
                WHERE chat_id = ? AND created_at >= ?
                GROUP BY status
            ''', (chat_id, cutoff_date))
            
            status_stats = {row['status']: row['count'] for row in cursor.fetchall()}
            
            # Получаем задачи с истекшим сроком
            cursor.execute('''
                SELECT COUNT(*) as overdue_count
                FROM tasks
                WHERE chat_id = ? AND status = 'pending' 
                AND deadline IS NOT NULL AND deadline < datetime('now')
            ''', (chat_id,))
            
            overdue_count = cursor.fetchone()['overdue_count']
            
            return {
                'status_stats': status_stats,
                'overdue_count': overdue_count,
                'total_tasks': sum(status_stats.values())
            }
    
    def get_pending_tasks(self, chat_id: int) -> List[Dict]:
        """Получает список незавершенных задач"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT 
                    t.*,
                    m.username as assigned_by_username,
                    m.first_name as assigned_by_first_name,
                    m.last_name as assigned_by_last_name
                FROM tasks t
                JOIN messages m ON t.message_id = m.id
                WHERE t.chat_id = ? AND t.status = 'pending'
                ORDER BY t.created_at DESC
            ''', (chat_id,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def mark_task_completed(self, task_id: int):
        """Отмечает задачу как выполненную"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE tasks 
                SET status = 'completed', completed_at = datetime('now')
                WHERE id = ?
            ''', (task_id,))
    
    def get_daily_stats(self, chat_id: int, date: datetime.date) -> Dict:
        """Получает статистику за день"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Общее количество сообщений
            cursor.execute('''
                SELECT COUNT(*) as total_messages
                FROM messages
                WHERE chat_id = ? AND date(date, 'unixepoch') = ?
            ''', (chat_id, date))
            
            total_messages = cursor.fetchone()['total_messages']
            
            # Активные пользователи
            cursor.execute('''
                SELECT COUNT(DISTINCT user_id) as active_users
                FROM messages
                WHERE chat_id = ? AND date(date, 'unixepoch') = ?
            ''', (chat_id, date))
            
            active_users = cursor.fetchone()['active_users']
            
            # Упоминания
            cursor.execute('''
                SELECT COUNT(*) as total_mentions
                FROM mentions m
                JOIN messages msg ON m.message_id = msg.id
                WHERE msg.chat_id = ? AND date(msg.date, 'unixepoch') = ?
            ''', (chat_id, date))
            
            total_mentions = cursor.fetchone()['total_mentions']
            
            return {
                'date': date,
                'total_messages': total_messages,
                'active_users': active_users,
                'total_mentions': total_mentions
            }
