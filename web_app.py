#!/usr/bin/env python3
"""
Веб-приложение для управления Chat Analyzer Bot
"""

from flask import Flask, render_template, jsonify, request, redirect, url_for
import sqlite3
import json
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key')

# Конфигурация
DATABASE_PATH = 'chat_analyzer.db'
ADMIN_USER_IDS = [int(id) for id in os.getenv('ADMIN_USER_IDS', '').split(',') if id]

class DatabaseManager:
    def __init__(self, db_path):
        self.db_path = db_path
    
    def get_connection(self):
        return sqlite3.connect(self.db_path)
    
    def get_all_chats(self):
        """Получает все группы"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT chat_id, title, chat_type, member_count, created_at
                FROM chats 
                ORDER BY created_at DESC
            ''')
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def get_chat_stats(self, chat_id, days=7):
        """Получает статистику по группе"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Количество сообщений
            cursor.execute('''
                SELECT COUNT(*) FROM messages 
                WHERE chat_id = ? AND date >= ?
            ''', (chat_id, int((datetime.now() - timedelta(days=days)).timestamp())))
            messages_count = cursor.fetchone()[0]
            
            # Количество пользователей
            cursor.execute('''
                SELECT COUNT(DISTINCT user_id) FROM messages 
                WHERE chat_id = ? AND date >= ?
            ''', (chat_id, int((datetime.now() - timedelta(days=days)).timestamp())))
            users_count = cursor.fetchone()[0]
            
            # Топ пользователей
            cursor.execute('''
                SELECT user_id, display_name, COUNT(*) as message_count
                FROM messages 
                WHERE chat_id = ? AND date >= ?
                GROUP BY user_id
                ORDER BY message_count DESC
                LIMIT 5
            ''', (chat_id, int((datetime.now() - timedelta(days=days)).timestamp())))
            top_users = [{'user_id': row[0], 'name': row[1], 'count': row[2]} for row in cursor.fetchall()]
            
            return {
                'messages_count': messages_count,
                'users_count': users_count,
                'top_users': top_users
            }
    
    def get_system_status(self):
        """Получает статус системы"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Общая статистика
            cursor.execute('SELECT COUNT(*) FROM chats')
            total_chats = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM messages')
            total_messages = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(DISTINCT user_id) FROM messages')
            total_users = cursor.fetchone()[0]
            
            # Последние сообщения
            cursor.execute('''
                SELECT m.text, m.date, c.title, u.display_name
                FROM messages m
                JOIN chats c ON m.chat_id = c.chat_id
                LEFT JOIN users u ON m.user_id = u.user_id
                ORDER BY m.date DESC
                LIMIT 10
            ''')
            recent_messages = []
            for row in cursor.fetchall():
                recent_messages.append({
                    'text': row[0][:100] + '...' if len(row[0]) > 100 else row[0],
                    'date': datetime.fromtimestamp(row[1]).strftime('%d.%m.%Y %H:%M'),
                    'chat': row[2],
                    'user': row[3] or 'Неизвестный'
                })
            
            return {
                'total_chats': total_chats,
                'total_messages': total_messages,
                'total_users': total_users,
                'recent_messages': recent_messages
            }

db = DatabaseManager(DATABASE_PATH)

@app.route('/')
def index():
    """Главная страница"""
    return render_template('index.html')

@app.route('/api/chats')
def get_chats():
    """API для получения списка групп"""
    try:
        chats = db.get_all_chats()
        return jsonify({'success': True, 'data': chats})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/chat/<int:chat_id>/stats')
def get_chat_stats(chat_id):
    """API для получения статистики группы"""
    try:
        days = request.args.get('days', 7, type=int)
        stats = db.get_chat_stats(chat_id, days)
        return jsonify({'success': True, 'data': stats})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/system/status')
def get_system_status():
    """API для получения статуса системы"""
    try:
        status = db.get_system_status()
        return jsonify({'success': True, 'data': status})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/dashboard')
def dashboard():
    """Панель управления"""
    return render_template('dashboard.html')

@app.route('/chats')
def chats():
    """Страница групп"""
    return render_template('chats.html')

@app.route('/chat/<int:chat_id>')
def chat_detail(chat_id):
    """Детальная страница группы"""
    return render_template('chat_detail.html', chat_id=chat_id)

@app.route('/analytics')
def analytics():
    """Страница аналитики"""
    return render_template('analytics.html')

@app.route('/settings')
def settings():
    """Страница настроек"""
    return render_template('settings.html')

if __name__ == '__main__':
    # Получаем порт из переменной окружения (для облачных платформ)
    port = int(os.environ.get('PORT', 8080))
    app.run(debug=False, host='0.0.0.0', port=port)
