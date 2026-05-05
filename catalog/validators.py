# catalog/validators.py
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

class RussianMinimumLengthValidator:
    """Используется в settings.py, но НЕ в форме"""
    def __init__(self, min_length=8):
        self.min_length = min_length

    def validate(self, password, user=None):
        if len(password) < self.min_length:
            raise ValidationError(
                f'Пароль должен содержать не менее {self.min_length} символов.',
                code='password_too_short'
            )

    def get_help_text(self):
        return f'Пароль должен содержать не менее {self.min_length} символов.'


class RussianNumericPasswordValidator:
    """Используется в settings.py, но НЕ в форме"""
    def validate(self, password, user=None):
        if password.isdigit():
            raise ValidationError(
                'Пароль не может состоять только из цифр.',
                code='password_entirely_numeric'
            )

    def get_help_text(self):
        return 'Пароль не может состоять только из цифр.'


# ================ ВАЛИДАЦИЯ ФАЙЛОВ ДЛЯ ASVS V14 ================
def validate_image_file(value):
    """
    Проверка что загружаемый файл - безопасное изображение
    Требование OWASP ASVS 5.0 L1 (V14): Защита от загрузки вредоносных файлов
    """
    import io
    from PIL import Image
    
    allowed_mimes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
    
    # Проверка MIME типа
    if hasattr(value, 'content_type'):
        if value.content_type not in allowed_mimes:
            raise ValidationError(
                f'❌ Неверный тип файла. Разрешены: JPEG, PNG, GIF, WebP'
            )
    
    # Проверка максимального размера (5 MB)
    max_size = 5 * 1024 * 1024  # 5 MB
    if value.size > max_size:
        raise ValidationError(
            f'❌ Файл слишком большой. Максимальный размер: 5 MB'
        )
    
    # Проверка что файл действительно является изображением
    try:
        img = Image.open(io.BytesIO(value.read()))
        img.verify()  # Проверка целостности
        value.seek(0)  # Сброс указателя для дальнейшего чтения
    except Exception:
        raise ValidationError(
            '❌ Файл повреждён или не является изображением'
        )