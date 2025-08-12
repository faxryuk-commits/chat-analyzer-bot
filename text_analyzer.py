import re
import nltk
from collections import Counter, defaultdict
from typing import List, Dict, Tuple, Set
import logging
from textblob import TextBlob
from config import STOP_WORDS_RU, MIN_WORD_LENGTH
from datetime import datetime

# Загружаем необходимые данные для NLTK
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

logger = logging.getLogger(__name__)

class TextAnalyzer:
    def __init__(self):
        self.stop_words = set(STOP_WORDS_RU)
        self.topic_keywords = {
            'работа': ['задача', 'проект', 'дедлайн', 'встреча', 'отчет', 'план', 'выполнить'],
            'техника': ['компьютер', 'программа', 'система', 'оборудование', 'технология', 'интернет'],
            'встречи': ['встреча', 'совещание', 'звонок', 'конференция', 'презентация'],
            'документы': ['документ', 'файл', 'отчет', 'письмо', 'договор', 'соглашение'],
            'клиенты': ['клиент', 'заказчик', 'покупатель', 'партнер', 'сотрудничество'],
            'финансы': ['бюджет', 'стоимость', 'оплата', 'расходы', 'доходы', 'финансы'],
            'персонал': ['сотрудник', 'коллега', 'команда', 'найм', 'увольнение', 'обучение'],
            'обучение': ['обучение', 'тренинг', 'курс', 'знания', 'навыки', 'развитие'],
            'проблемы': ['проблема', 'ошибка', 'сбой', 'неполадка', 'исправить', 'решить'],
            'общение': ['обсудить', 'поговорить', 'связаться', 'сообщить', 'информировать']
        }
    
    def clean_text(self, text: str) -> str:
        """Очищает текст от лишних символов"""
        if not text:
            return ""
        
        # Убираем URL
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
        
        # Убираем эмодзи и специальные символы
        text = re.sub(r'[^\w\sа-яА-Я]', ' ', text)
        
        # Убираем множественные пробелы
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip().lower()
    
    def extract_words(self, text: str) -> List[str]:
        """Извлекает слова из текста"""
        cleaned_text = self.clean_text(text)
        words = re.findall(r'\b[а-яА-Яa-zA-Z]+\b', cleaned_text)
        
        # Фильтруем слова по длине и стоп-словам
        filtered_words = [
            word for word in words 
            if len(word) >= MIN_WORD_LENGTH and word not in self.stop_words
        ]
        
        return filtered_words
    
    def detect_topics(self, text: str) -> List[Tuple[str, float]]:
        """Определяет темы в тексте"""
        words = self.extract_words(text)
        if not words:
            return []
        
        topic_scores = defaultdict(float)
        
        for topic, keywords in self.topic_keywords.items():
            score = 0
            for keyword in keywords:
                if keyword in words:
                    score += 1
            
            if score > 0:
                # Нормализуем оценку
                topic_scores[topic] = score / len(keywords)
        
        # Сортируем по убыванию оценки
        sorted_topics = sorted(topic_scores.items(), key=lambda x: x[1], reverse=True)
        
        # Возвращаем только темы с оценкой выше 0.1
        return [(topic, score) for topic, score in sorted_topics if score > 0.1]
    
    def analyze_sentiment(self, text: str) -> Dict[str, float]:
        """Анализирует тональность текста"""
        if not text:
            return {'polarity': 0.0, 'subjectivity': 0.0}
        
        try:
            blob = TextBlob(text)
            return {
                'polarity': blob.sentiment.polarity,
                'subjectivity': blob.sentiment.subjectivity
            }
        except Exception as e:
            logger.warning(f"Ошибка анализа тональности: {e}")
            return {'polarity': 0.0, 'subjectivity': 0.0}
    
    def extract_mentions(self, text: str) -> List[str]:
        """Извлекает упоминания пользователей из текста"""
        if not text:
            return []
        
        # Ищем упоминания в формате @username
        mentions = re.findall(r'@(\w+)', text)
        
        # Ищем упоминания в формате "имя фамилия"
        name_mentions = re.findall(r'([А-Я][а-я]+ [А-Я][а-я]+)', text)
        
        return mentions + name_mentions
    
    def extract_tasks(self, text: str) -> List[Dict]:
        """Извлекает задачи из текста"""
        tasks = []
        
        # Паттерны для поиска задач
        task_patterns = [
            r'@(\w+)\s+(.+?)(?:\.|$)',  # @username задача
            r'(\w+)\s+(?:нужно|должен|сделай|выполни)\s+(.+?)(?:\.|$)',  # имя нужно сделать
            r'(?:задача|поручение|дело):\s*(.+?)(?:\.|$)',  # задача: описание
            r'(?:попроси|попросите)\s+(\w+)\s+(.+?)(?:\.|$)'  # попроси имя сделать
        ]
        
        for pattern in task_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if len(match) == 2:
                    tasks.append({
                        'assigned_to': match[0],
                        'task_text': match[1].strip()
                    })
                elif len(match) == 1:
                    tasks.append({
                        'assigned_to': None,
                        'task_text': match[0].strip()
                    })
        
        return tasks
    
    def get_most_common_words(self, texts: List[str], top_n: int = 20) -> List[Tuple[str, int]]:
        """Получает самые частые слова из списка текстов"""
        all_words = []
        for text in texts:
            words = self.extract_words(text)
            all_words.extend(words)
        
        word_counts = Counter(all_words)
        return word_counts.most_common(top_n)
    
    def get_topic_distribution(self, texts: List[str]) -> Dict[str, int]:
        """Получает распределение тем по текстам"""
        topic_counts = defaultdict(int)
        
        for text in texts:
            topics = self.detect_topics(text)
            for topic, score in topics:
                if score > 0.3:  # Порог для определения основной темы
                    topic_counts[topic] += 1
        
        return dict(topic_counts)
    
    def analyze_conversation_flow(self, messages: List[Dict]) -> Dict:
        """Анализирует поток беседы"""
        if not messages:
            return {}
        
        # Группируем сообщения по часам
        hourly_activity = defaultdict(int)
        user_activity = defaultdict(int)
        response_times = []
        
        for i, message in enumerate(messages):
            # Активность по часам
            hour = datetime.fromtimestamp(message['date']).hour
            hourly_activity[hour] += 1
            
            # Активность пользователей
            user_activity[message['user_id']] += 1
            
            # Время ответа (если есть ответ на предыдущее сообщение)
            if i > 0 and message.get('reply_to_message_id'):
                prev_message = messages[i-1]
                response_time = message['date'] - prev_message['date']
                if response_time > 0:
                    response_times.append(response_time)
        
        return {
            'hourly_activity': dict(hourly_activity),
            'user_activity': dict(user_activity),
            'avg_response_time': sum(response_times) / len(response_times) if response_times else 0,
            'total_messages': len(messages),
            'unique_users': len(user_activity)
        }
    
    def generate_word_cloud_data(self, texts: List[str]) -> Dict[str, int]:
        """Генерирует данные для облака слов"""
        return dict(self.get_most_common_words(texts, 50))
    
    def detect_urgent_messages(self, text: str) -> bool:
        """Определяет срочные сообщения"""
        urgent_keywords = [
            'срочно', 'немедленно', 'быстро', 'сейчас же', 'как можно скорее',
            'неотложно', 'важно', 'критично', 'авария', 'проблема', 'ошибка'
        ]
        
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in urgent_keywords)
    
    def extract_deadlines(self, text: str) -> List[str]:
        """Извлекает дедлайны из текста"""
        deadline_patterns = [
            r'до\s+(\d{1,2}[.:]\d{2})',  # до 18:00
            r'к\s+(\d{1,2}[.:]\d{2})',   # к 18:00
            r'(\d{1,2}[.:]\d{2})',       # 18:00
            r'до\s+(\d{1,2}\s+(?:января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря))',
            r'к\s+(\d{1,2}\s+(?:января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря))'
        ]
        
        deadlines = []
        for pattern in deadline_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            deadlines.extend(matches)
        
        return deadlines
