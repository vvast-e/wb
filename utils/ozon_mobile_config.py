#!/usr/bin/env python3
"""
Конфигурация мобильных заголовков и настроек для Ozon парсера

Содержит различные профили устройств и ротацию заголовков
для максимального обхода антибот систем
"""

import random
import uuid
from typing import Dict, List, Tuple

class OzonMobileConfig:
    """Конфигурация мобильных устройств для Ozon парсера"""
    
    # Реальные User-Agent различных мобильных устройств
    MOBILE_USER_AGENTS = [
        # Samsung Galaxy серия
        'Mozilla/5.0 (Linux; Android 12; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.210 Mobile Safari/537.36',
        'Mozilla/5.0 (Linux; Android 13; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.6045.194 Mobile Safari/537.36',
        'Mozilla/5.0 (Linux; Android 11; SM-A715F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.5993.48 Mobile Safari/537.36',
        
        # iPhone серия 
        'Mozilla/5.0 (iPhone; CPU iPhone OS 17_1_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1',
        'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
        'Mozilla/5.0 (iPhone; CPU iPhone OS 15_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.6 Mobile/15E148 Safari/604.1',
        
        # Xiaomi серия
        'Mozilla/5.0 (Linux; Android 12; Mi 11) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.43 Mobile Safari/537.36',
        'Mozilla/5.0 (Linux; Android 13; Redmi Note 12) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.6045.66 Mobile Safari/537.36',
        
        # Huawei серия
        'Mozilla/5.0 (Linux; Android 10; HarmonyOS; NOH-NX9) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.5993.80 Mobile Safari/537.36',
        'Mozilla/5.0 (Linux; Android 12; HarmonyOS; ANA-NX9) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.6045.123 Mobile Safari/537.36',
    ]
    
    # Соответствующие sec-ch-ua заголовки для User-Agent'ов
    SEC_CH_UA_MAP = {
        'Chrome/120': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        'Chrome/119': '"Not-A.Brand";v="24", "Chromium";v="119", "Google Chrome";v="119"', 
        'Chrome/118': '"Chromium";v="118", "Google Chrome";v="118", "Not=A?Brand";v="24"',
        'Safari': '"Not-A.Brand";v="24", "Safari";v="17.1"',
    }
    
    # Мобильные разрешения экранов
    MOBILE_VIEWPORTS = [
        (390, 844),   # iPhone 12/13/14
        (414, 896),   # iPhone 11 Pro Max
        (375, 667),   # iPhone SE
        (360, 760),   # Samsung Galaxy S21
        (393, 851),   # Samsung Galaxy S22
        (412, 869),   # Pixel 6
        (360, 780),   # Xiaomi
    ]
    
    # Языки для Accept-Language (русскоязычные пользователи)
    ACCEPT_LANGUAGES = [
        'ru-RU,ru;q=0.9,en;q=0.8',
        'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        'ru,en-US;q=0.9,en;q=0.8',
        'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
    ]
    
    # Часовые пояса России
    TIMEZONES = [
        'Europe/Moscow',
        'Europe/Samara', 
        'Asia/Yekaterinburg',
        'Asia/Novosibirsk',
        'Asia/Krasnoyarsk',
        'Europe/Kaliningrad',
    ]
    
    @classmethod
    def generate_mobile_profile(cls) -> Dict:
        """Генерирует случайный профиль мобильного устройства"""
        user_agent = random.choice(cls.MOBILE_USER_AGENTS)
        viewport = random.choice(cls.MOBILE_VIEWPORTS)
        accept_language = random.choice(cls.ACCEPT_LANGUAGES)
        timezone = random.choice(cls.TIMEZONES)
        
        # Определяем тип браузера для sec-ch-ua
        sec_ch_ua = cls.SEC_CH_UA_MAP['Chrome/120']  # По умолчанию
        for browser_version, sec_header in cls.SEC_CH_UA_MAP.items():
            if browser_version in user_agent:
                sec_ch_ua = sec_header
                break
        
        # Определяем платформу
        if 'iPhone' in user_agent or 'iPad' in user_agent:
            platform = 'iOS'
            sec_ch_ua_platform = '"iOS"'
        else:
            platform = 'Android'
            sec_ch_ua_platform = '"Android"'
        
        return {
            'user_agent': user_agent,
            'viewport': viewport,
            'accept_language': accept_language,
            'timezone': timezone,
            'platform': platform,
            'sec_ch_ua': sec_ch_ua,
            'sec_ch_ua_platform': sec_ch_ua_platform,
            'device_id': str(uuid.uuid4()),
            'session_id': str(uuid.uuid4()),
        }
    
    @classmethod
    def get_ozon_headers(cls, profile: Dict, referer: str = None) -> Dict:
        """Формирует заголовки для Ozon API на основе профиля устройства"""
        headers = {
            'User-Agent': profile['user_agent'],
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': profile['accept_language'],
            'Accept-Encoding': 'gzip, deflate, br',
            'Origin': 'https://www.ozon.ru',
            'Referer': referer or 'https://www.ozon.ru/',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Dest': 'empty',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            
            # Ozon специфичные заголовки
            'x-o3-app-name': 'mobile_web',
            'x-o3-app-version': '1.0.0',
            'x-o3-device-type': 'mobile',
            'x-o3-device-id': profile['device_id'],
            'x-o3-session-id': profile['session_id'],
            'x-requested-with': 'XMLHttpRequest',
            
            # Современные Chrome заголовки
            'sec-ch-ua': profile['sec_ch_ua'],
            'sec-ch-ua-mobile': '?1',
            'sec-ch-ua-platform': profile['sec_ch_ua_platform'],
            
            # Дополнительные stealth заголовки
            'sec-ch-ua-full-version-list': cls._generate_full_version_list(profile['user_agent']),
            'sec-ch-viewport-width': str(profile['viewport'][0]),
            'sec-ch-viewport-height': str(profile['viewport'][1]),
        }
        
        return headers
    
    @classmethod 
    def _generate_full_version_list(cls, user_agent: str) -> str:
        """Генерирует полный список версий браузера"""
        if 'Chrome/120' in user_agent:
            return '"Not_A Brand";v="8.0.0.0", "Chromium";v="120.0.6099.210", "Google Chrome";v="120.0.6099.210"'
        elif 'Chrome/119' in user_agent:
            return '"Not-A.Brand";v="24.0.0.0", "Chromium";v="119.0.6045.194", "Google Chrome";v="119.0.6045.194"'
        elif 'Safari' in user_agent:
            return '"Not-A.Brand";v="24.0.0.0", "Safari";v="17.1.0"'
        else:
            return '"Chromium";v="118.0.5993.48", "Google Chrome";v="118.0.5993.48", "Not=A?Brand";v="24.0.0.0"'

    @classmethod
    def get_ozon_mobile_endpoints(cls) -> Dict[str, str]:
        """Возвращает мобильные endpoints Ozon"""
        return {
            'base': 'https://www.ozon.ru',
            'mobile_api': 'https://www.ozon.ru/api',
            'entrypoint': 'https://www.ozon.ru/api/entrypoint-api.bx',
            'composer': 'https://www.ozon.ru/api/composer-api.bx',
            'search': 'https://www.ozon.ru/api/composer-api.bx/page/json/v2',
            'product': 'https://www.ozon.ru/api/entrypoint-api.bx/page/json/v2',
            'reviews': 'https://www.ozon.ru/api/entrypoint-api.bx/page/json/v2',
            'cdn': 'https://cdn1.ozon.ru/api',
        }
    
    @classmethod
    def get_stealth_settings(cls) -> Dict:
        """Настройки для максимальной stealth"""
        return {
            'request_delay_range': (2.0, 5.0),
            'page_delay_range': (8.0, 15.0), 
            'retry_attempts': 3,
            'retry_delay_base': 5.0,
            'timeout': 30,
            'warmup_pages': [
                '/',
                '/category',
                '/brand',
                '/seller',
            ],
            'curl_cffi_impersonate': 'chrome120_android',
            'tls_ciphers': [
                'ECDHE+AESGCM',
                'ECDHE+CHACHA20',
                'DHE+AESGCM',
                'DHE+CHACHA20',
                '!aNULL',
                '!eNULL',
                '!EXPORT',
                '!DES',
                '!RC4',
                '!MD5',
                '!PSK',
                '!SRP',
                '!CAMELLIA'
            ]
        }


# Предустановленные профили для разных регионов России
REGIONAL_PROFILES = {
    'moscow': {
        'timezone': 'Europe/Moscow',
        'accept_language': 'ru-RU,ru;q=0.9,en;q=0.8',
        'region_headers': {
            'x-o3-region': 'moscow',
            'x-o3-timezone': 'Europe/Moscow',
        }
    },
    'spb': {
        'timezone': 'Europe/Moscow', 
        'accept_language': 'ru-RU,ru;q=0.9,en;q=0.8',
        'region_headers': {
            'x-o3-region': 'spb',
            'x-o3-timezone': 'Europe/Moscow',
        }
    },
    'ekaterinburg': {
        'timezone': 'Asia/Yekaterinburg',
        'accept_language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        'region_headers': {
            'x-o3-region': 'ekaterinburg',
            'x-o3-timezone': 'Asia/Yekaterinburg',
        }
    },
    'novosibirsk': {
        'timezone': 'Asia/Novosibirsk',
        'accept_language': 'ru,en-US;q=0.9,en;q=0.8',
        'region_headers': {
            'x-o3-region': 'novosibirsk', 
            'x-o3-timezone': 'Asia/Novosibirsk',
        }
    }
}


def get_regional_profile(region: str = 'moscow') -> Dict:
    """Получить профиль для конкретного региона"""
    base_profile = OzonMobileConfig.generate_mobile_profile()
    regional_settings = REGIONAL_PROFILES.get(region, REGIONAL_PROFILES['moscow'])
    
    # Обновляем профиль региональными настройками
    base_profile.update({
        'timezone': regional_settings['timezone'],
        'accept_language': regional_settings['accept_language'],
        'region': region,
        'region_headers': regional_settings['region_headers']
    })
    
    return base_profile


def create_rotated_headers(count: int = 5) -> List[Dict]:
    """Создает набор ротируемых заголовков"""
    headers_list = []
    
    for _ in range(count):
        profile = OzonMobileConfig.generate_mobile_profile()
        headers = OzonMobileConfig.get_ozon_headers(profile)
        headers_list.append(headers)
    
    return headers_list


# Пример использования
if __name__ == "__main__":
    print("🔧 Демонстрация Ozon Mobile Config")
    
    # Генерируем профиль
    profile = OzonMobileConfig.generate_mobile_profile()
    print(f"📱 Устройство: {profile['user_agent'][:50]}...")
    print(f"📏 Разрешение: {profile['viewport']}")
    print(f"🌍 Язык: {profile['accept_language']}")
    print(f"⏰ Часовой пояс: {profile['timezone']}")
    
    # Получаем заголовки
    headers = OzonMobileConfig.get_ozon_headers(profile)
    print(f"\n📨 Заголовков сгенерировано: {len(headers)}")
    
    # Региональный профиль
    moscow_profile = get_regional_profile('moscow')
    print(f"\n🏛️ Московский профиль: {moscow_profile['region']}")
    
    # Эндпоинты
    endpoints = OzonMobileConfig.get_ozon_mobile_endpoints()
    print(f"\n🌐 Эндпоинтов: {len(endpoints)}")
    
    print("\n✅ Конфигурация готова к использованию!")
