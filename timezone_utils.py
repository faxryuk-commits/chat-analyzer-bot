#!/usr/bin/env python3
"""
Утилиты для работы с часовыми поясами
"""

import pytz
from datetime import datetime, timezone
from typing import Optional
import requests
import logging

logger = logging.getLogger(__name__)

class TimezoneManager:
    def __init__(self):
        # Основные часовые пояса для России и СНГ
        self.common_timezones = {
            'MSK': 'Europe/Moscow',      # Москва
            'SPB': 'Europe/Moscow',      # Санкт-Петербург
            'EKB': 'Asia/Yekaterinburg', # Екатеринбург
            'NOV': 'Asia/Novosibirsk',   # Новосибирск
            'VLA': 'Asia/Vladivostok',   # Владивосток
            'TAS': 'Asia/Tashkent',      # Ташкент
            'ALA': 'Asia/Almaty',        # Алматы
            'BIS': 'Asia/Bishkek',       # Бишкек
            'DUS': 'Asia/Dushanbe',      # Душанбе
            'ASH': 'Asia/Ashgabat',      # Ашхабад
            'BAK': 'Asia/Baku',          # Баку
            'TBI': 'Asia/Tbilisi',       # Тбилиси
            'YER': 'Asia/Yerevan',       # Ереван
            'MNS': 'Asia/Ulaanbaatar',   # Улан-Батор
        }
    
    def get_timezone_by_ip(self, ip_address: str) -> Optional[str]:
        """Определяет часовой пояс по IP адресу"""
        try:
            # Используем бесплатный сервис для определения геолокации
            response = requests.get(f"http://ip-api.com/json/{ip_address}", timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    timezone_name = data.get('timezone')
                    if timezone_name:
                        return timezone_name
        except Exception as e:
            logger.warning(f"Не удалось определить часовой пояс по IP {ip_address}: {e}")
        
        return None
    
    def get_timezone_by_region(self, region: str) -> Optional[str]:
        """Получает часовой пояс по региону"""
        region_upper = region.upper()
        
        # Проверяем основные регионы
        if region_upper in ['МОСКВА', 'MOSCOW', 'MSK']:
            return 'Europe/Moscow'
        elif region_upper in ['СПБ', 'САНКТ-ПЕТЕРБУРГ', 'SPB', 'SAINT PETERSBURG']:
            return 'Europe/Moscow'
        elif region_upper in ['ЕКАТЕРИНБУРГ', 'EKB', 'YEKATERINBURG']:
            return 'Asia/Yekaterinburg'
        elif region_upper in ['НОВОСИБИРСК', 'NOV', 'NOVOSIBIRSK']:
            return 'Asia/Novosibirsk'
        elif region_upper in ['ВЛАДИВОСТОК', 'VLA', 'VLADIVOSTOK']:
            return 'Asia/Vladivostok'
        elif region_upper in ['ТАШКЕНТ', 'TAS', 'TASHKENT']:
            return 'Asia/Tashkent'
        elif region_upper in ['АЛМАТЫ', 'ALA', 'ALMATY']:
            return 'Asia/Almaty'
        elif region_upper in ['БИШКЕК', 'BIS', 'BISHKEK']:
            return 'Asia/Bishkek'
        elif region_upper in ['ДУШАНБЕ', 'DUS', 'DUSHANBE']:
            return 'Asia/Dushanbe'
        elif region_upper in ['АШХАБАД', 'ASH', 'ASHGABAT']:
            return 'Asia/Ashgabat'
        elif region_upper in ['БАКУ', 'BAK', 'BAKU']:
            return 'Asia/Baku'
        elif region_upper in ['ТБИЛИСИ', 'TBI', 'TBILISI']:
            return 'Asia/Tbilisi'
        elif region_upper in ['ЕРЕВАН', 'YER', 'YEREVAN']:
            return 'Asia/Yerevan'
        elif region_upper in ['УЛАН-БАТОР', 'MNS', 'ULAANBAATAR']:
            return 'Asia/Ulaanbaatar'
        
        return None
    
    def convert_utc_to_local(self, utc_timestamp: int, timezone_name: str = 'Europe/Moscow') -> datetime:
        """Конвертирует UTC timestamp в локальное время"""
        try:
            tz = pytz.timezone(timezone_name)
            utc_time = datetime.fromtimestamp(utc_timestamp, tz=timezone.utc)
            local_time = utc_time.astimezone(tz)
            return local_time
        except Exception as e:
            logger.error(f"Ошибка конвертации времени: {e}")
            # Возвращаем UTC время как fallback
            return datetime.fromtimestamp(utc_timestamp, tz=timezone.utc)
    
    def get_local_time(self, timezone_name: str = 'Europe/Moscow') -> datetime:
        """Получает текущее локальное время"""
        try:
            tz = pytz.timezone(timezone_name)
            return datetime.now(tz)
        except Exception as e:
            logger.error(f"Ошибка получения локального времени: {e}")
            return datetime.now()
    
    def format_time(self, dt: datetime, format_str: str = '%H:%M') -> str:
        """Форматирует время в строку"""
        return dt.strftime(format_str)
    
    def get_hour_from_timestamp(self, timestamp: int, timezone_name: str = 'Europe/Moscow') -> int:
        """Получает час из timestamp в указанном часовом поясе"""
        local_time = self.convert_utc_to_local(timestamp, timezone_name)
        return local_time.hour
    
    def get_activity_hours(self, messages: list, timezone_name: str = 'Europe/Moscow') -> dict:
        """Анализирует активность по часам в указанном часовом поясе"""
        hourly_activity = {}
        
        for message in messages:
            timestamp = message.get('date', 0)
            if timestamp:
                hour = self.get_hour_from_timestamp(timestamp, timezone_name)
                hourly_activity[hour] = hourly_activity.get(hour, 0) + 1
        
        return hourly_activity
    
    def get_peak_activity_hour(self, hourly_activity: dict) -> tuple:
        """Находит пик активности"""
        if not hourly_activity:
            return (0, 0)
        
        peak_hour = max(hourly_activity, key=hourly_activity.get)
        peak_count = hourly_activity[peak_hour]
        
        return (peak_hour, peak_count)

# Глобальный экземпляр менеджера часовых поясов
timezone_manager = TimezoneManager()
