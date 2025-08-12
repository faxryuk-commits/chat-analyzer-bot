#!/usr/bin/env python3
"""
Модуль для анализа качества бесед и коммуникации
"""

import re
import logging
from typing import List, Dict, Tuple
from datetime import datetime, timedelta
from collections import Counter

logger = logging.getLogger(__name__)

class ConversationAnalyzer:
    """Анализатор качества бесед"""
    
    def __init__(self):
        # Эмоциональные маркеры для определения температуры
        self.positive_markers = [
            'спасибо', 'благодарю', 'отлично', 'хорошо', 'супер', 'круто', 'здорово',
            'согласен', 'поддерживаю', 'правильно', 'верно', 'точно', 'да', 'давайте',
            'поможем', 'решим', 'сделаем', 'готов', 'можно', 'возможно', 'попробуем',
            '👍', '✅', '🎉', '😊', '😄', '🙂', '👏', '🔥', '💪', '🚀'
        ]
        
        self.negative_markers = [
            'проблема', 'ошибка', 'неправильно', 'плохо', 'ужасно', 'кошмар',
            'нельзя', 'невозможно', 'неправильно', 'ошибочно', 'неверно',
            'не согласен', 'против', 'нет', 'нельзя', 'запрещено', 'стоп',
            'хватит', 'достаточно', 'надоело', 'устал', 'бесит', 'раздражает',
            '😡', '😠', '😤', '😞', '😔', '😢', '😭', '💔', '👎', '❌', '🚫'
        ]
        
        self.urgent_markers = [
            'срочно', 'немедленно', 'быстро', 'сейчас же', 'как можно скорее',
            'не терпит отлагательств', 'критично', 'важно', 'приоритет',
            'deadline', 'дедлайн', 'срок', 'время', 'торопимся', 'спешим',
            '🔥', '⚡', '🚨', '⚠️', '❗', '‼️'
        ]
        
        self.question_markers = [
            '?', 'вопрос', 'как', 'что', 'где', 'когда', 'почему', 'зачем',
            'кто', 'какой', 'какая', 'какое', 'какие', 'сколько', 'откуда',
            'куда', 'откуда', 'зачем', 'почему', 'каким образом'
        ]
        
        self.resolution_markers = [
            'решили', 'договорились', 'согласовали', 'утвердили', 'приняли',
            'готово', 'сделано', 'выполнено', 'завершено', 'окончено',
            'итог', 'результат', 'вывод', 'заключение', 'финал',
            '✅', '🎯', '🏁', '🎉', '💯'
        ]
    
    def analyze_conversation_temperature(self, messages: List[Dict], period_days: int = 7) -> Dict:
        """
        Анализирует температуру беседы по 10-балльной шкале
        
        Args:
            messages: Список сообщений
            period_days: Период анализа в днях
            
        Returns:
            Dict с результатами анализа
        """
        if not messages:
            return {
                'temperature': 5.0,
                'confidence': 0.0,
                'message': 'Нет данных для анализа',
                'details': {}
            }
        
        # Анализируем каждое сообщение
        message_scores = []
        emotion_counts = {'positive': 0, 'negative': 0, 'neutral': 0}
        urgency_count = 0
        question_count = 0
        resolution_count = 0
        
        for message in messages:
            text = message.get('text', '').lower()
            if not text:
                continue
            
            # Анализируем эмоциональную окраску
            positive_score = self._count_markers(text, self.positive_markers)
            negative_score = self._count_markers(text, self.negative_markers)
            
            # Определяем доминирующую эмоцию
            if positive_score > negative_score:
                emotion_counts['positive'] += 1
                score = min(10, 5 + positive_score - negative_score)
            elif negative_score > positive_score:
                emotion_counts['negative'] += 1
                score = max(0, 5 - (negative_score - positive_score))
            else:
                emotion_counts['neutral'] += 1
                score = 5.0
            
            message_scores.append(score)
            
            # Анализируем срочность
            if self._count_markers(text, self.urgent_markers) > 0:
                urgency_count += 1
            
            # Анализируем вопросы
            if self._count_markers(text, self.question_markers) > 0:
                question_count += 1
            
            # Анализируем решения
            if self._count_markers(text, self.resolution_markers) > 0:
                resolution_count += 1
        
        # Вычисляем общую температуру
        if message_scores:
            avg_temperature = sum(message_scores) / len(message_scores)
        else:
            avg_temperature = 5.0
        
        # Корректируем температуру на основе дополнительных факторов
        temperature = self._adjust_temperature(
            avg_temperature, 
            emotion_counts, 
            urgency_count, 
            question_count, 
            resolution_count,
            len(messages)
        )
        
        # Определяем уровень уверенности
        confidence = self._calculate_confidence(len(messages), emotion_counts)
        
        # Формируем описание
        description = self._generate_temperature_description(temperature, emotion_counts)
        
        return {
            'temperature': round(temperature, 1),
            'confidence': round(confidence, 1),
            'description': description,
            'details': {
                'total_messages': len(messages),
                'emotion_distribution': emotion_counts,
                'urgency_messages': urgency_count,
                'question_messages': question_count,
                'resolution_messages': resolution_count,
                'positive_ratio': emotion_counts['positive'] / max(1, len(messages)),
                'negative_ratio': emotion_counts['negative'] / max(1, len(messages))
            }
        }
    
    def _count_markers(self, text: str, markers: List[str]) -> int:
        """Подсчитывает количество маркеров в тексте"""
        count = 0
        for marker in markers:
            count += text.count(marker)
        return count
    
    def _adjust_temperature(self, base_temp: float, emotions: Dict, urgency: int, 
                          questions: int, resolutions: int, total_messages: int) -> float:
        """Корректирует температуру на основе дополнительных факторов"""
        temperature = base_temp
        
        # Корректировка на основе срочности (повышает температуру)
        if urgency > 0:
            urgency_factor = min(2.0, urgency / max(1, total_messages) * 10)
            temperature += urgency_factor * 0.3
        
        # Корректировка на основе решений (снижает температуру)
        if resolutions > 0:
            resolution_factor = min(2.0, resolutions / max(1, total_messages) * 10)
            temperature -= resolution_factor * 0.2
        
        # Корректировка на основе эмоционального баланса
        positive_ratio = emotions['positive'] / max(1, total_messages)
        negative_ratio = emotions['negative'] / max(1, total_messages)
        
        if positive_ratio > 0.3:
            temperature += 0.5
        if negative_ratio > 0.3:
            temperature -= 0.5
        
        return max(0.0, min(10.0, temperature))
    
    def _calculate_confidence(self, total_messages: int, emotions: Dict) -> float:
        """Вычисляет уровень уверенности в анализе"""
        if total_messages < 5:
            return 0.3
        elif total_messages < 10:
            return 0.6
        elif total_messages < 20:
            return 0.8
        else:
            return 0.9
    
    def _generate_temperature_description(self, temperature: float, emotions: Dict) -> str:
        """Генерирует описание температуры беседы"""
        if temperature >= 8.0:
            return "🔥 Очень высокая температура - бурное обсуждение с сильными эмоциями"
        elif temperature >= 6.5:
            return "⚡ Повышенная температура - активное обсуждение с эмоциями"
        elif temperature >= 4.5:
            return "😐 Нормальная температура - спокойное конструктивное общение"
        elif temperature >= 3.0:
            return "😔 Пониженная температура - вялое или напряженное общение"
        else:
            return "❄️ Низкая температура - холодное или конфликтное общение"
    
    def get_temperature_emoji(self, temperature: float) -> str:
        """Возвращает эмодзи для температуры"""
        if temperature >= 8.0:
            return "🔥"
        elif temperature >= 6.5:
            return "⚡"
        elif temperature >= 4.5:
            return "😐"
        elif temperature >= 3.0:
            return "😔"
        else:
            return "❄️"
