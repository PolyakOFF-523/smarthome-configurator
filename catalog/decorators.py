# catalog/decorators.py
from functools import wraps
from django.core.cache import cache
from django.shortcuts import redirect
from django.contrib import messages


class RateLimitExceeded(Exception):
    pass


def rate_limit(key='ip', rate='5/m', method='POST', message=None):
    """
    Декоратор для ограничения частоты запросов
    key: 'ip' или 'user'
    rate: '5/h' (5 в час), '10/m' (10 в минуту)
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            # Определяем ключ для кэша
            if key == 'user' and request.user.is_authenticated:
                identifier = f"user_{request.user.id}"
            else:
                identifier = f"ip_{request.META.get('REMOTE_ADDR', 'unknown')}"
            
            # Проверяем только для указанного метода
            if method == 'ALL' or request.method == method:
                cache_key = f"ratelimit_{identifier}_{view_func.__name__}"
                
                # Парсим rate
                limit, period = parse_rate(rate)
                
                # Получаем текущее количество неудачных попыток
                attempts = cache.get(cache_key, 0)
                
                if attempts >= limit:
                    msg = message or f"Слишком много попыток. Попробуйте через {period//60} минут."
                    messages.error(request, msg)
                    return redirect(request.META.get('HTTP_REFERER', '/'))
                
                # Выполняем view
                response = view_func(request, *args, **kwargs)
                
                # Если ответ 200 (успешный вход), сбрасываем счётчик
                if response.status_code == 302 and request.path == '/login/':
                    # Успешный вход - сбрасываем попытки
                    cache.delete(cache_key)
                elif response.status_code == 200 and 'login' in request.path:
                    # Неудачный вход - увеличиваем счётчик
                    cache.set(cache_key, attempts + 1, timeout=period)
                
                return response
            
            return view_func(request, *args, **kwargs)
        return wrapped_view
    return decorator


def parse_rate(rate):
    """Парсит строку типа '5/h' в (limit, seconds)"""
    value, unit = rate.split('/')
    limit = int(value)
    
    if unit == 's':
        seconds = 1
    elif unit == 'm':
        seconds = 60
    elif unit == 'h':
        seconds = 3600
    elif unit == 'd':
        seconds = 86400
    else:
        seconds = 60
    
    return limit, seconds