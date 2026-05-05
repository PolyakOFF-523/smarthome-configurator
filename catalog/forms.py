# catalog/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError


# ================ ФОРМА РЕГИСТРАЦИИ ================
class CustomUserCreationForm(UserCreationForm):
    """Улучшенная форма регистрации"""
    
    username = forms.CharField(
        label='Имя пользователя',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'например: smart_user123',
            'autocomplete': 'off'
        }),
        help_text='Только буквы, цифры и символы @/./+/-/_.'
    )
    
    email = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'your@email.com',
            'autocomplete': 'email'
        }),
        required=True,
        help_text='Укажите реальный email для восстановления пароля'
    )
    
    password1 = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': '••••••••',
            'autocomplete': 'new-password'
        })
    )
    
    password2 = forms.CharField(
        label='Подтверждение пароля',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': '••••••••',
            'autocomplete': 'new-password'
        })
    )
    
    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(email=email).exists():
            raise ValidationError('Пользователь с таким email уже существует')
        return email
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if username and User.objects.filter(username=username).exists():
            raise ValidationError('Пользователь с таким именем уже существует')
        return username
    
    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise ValidationError('Введенные пароли не совпадают')
        return password2
    
    def clean_password1(self):
        password = self.cleaned_data.get('password1')
        if not password:
            return password
        if len(password) < 8:
            raise ValidationError('Пароль должен содержать не менее 8 символов')
        if password.isdigit():
            raise ValidationError('Пароль не может состоять только из цифр')
        return password
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].help_text = ""
        self.fields['password2'].help_text = ""


# ================ ФОРМА ВХОДА ================
class CustomAuthenticationForm(AuthenticationForm):
    """Кастомная форма входа с русскими сообщениями"""
    
    username = forms.CharField(
        label='Имя пользователя',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите имя пользователя',
            'autocomplete': 'username'
        })
    )
    
    password = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': '••••••••',
            'autocomplete': 'current-password'
        })
    )
    
    error_messages = {
        'invalid_login': '❌ Неверное имя пользователя или пароль. Попробуйте ещё раз.',
        'inactive': '❌ Этот аккаунт отключён. Обратитесь к администратору.',
    }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs['placeholder'] = 'Введите имя пользователя'
        self.fields['password'].widget.attrs['placeholder'] = 'Введите пароль'