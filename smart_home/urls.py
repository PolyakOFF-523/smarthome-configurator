from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from catalog import views
from catalog.decorators import rate_limit
from catalog.forms import CustomAuthenticationForm 

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('catalog.urls')),
    
    # ================ АУТЕНТИФИКАЦИЯ ================
    # Используем кастомную форму с rate limiting
    path('login/', 
         rate_limit(key='ip', rate='5/m', method='POST')(
             auth_views.LoginView.as_view(
                 template_name='catalog/login.html',
                 authentication_form=CustomAuthenticationForm  # ДОБАВИТЬ
             )
         ),
         name='login'),
    
    path('logout/', auth_views.LogoutView.as_view(next_page='index'), name='logout'),
    path('register/', views.register, name='register'),
    
    # ================ ВОССТАНОВЛЕНИЕ ПАРОЛЯ ================
    path('password-reset/',
         auth_views.PasswordResetView.as_view(
             template_name='catalog/password_reset.html',
             email_template_name='catalog/password_reset_email.html',
             subject_template_name='catalog/password_reset_subject.txt',
             success_url='/password-reset/done/'
         ),
         name='password_reset'),
    
    path('password-reset/done/',
         auth_views.PasswordResetDoneView.as_view(
             template_name='catalog/password_reset_done.html'
         ),
         name='password_reset_done'),
    
    path('reset/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(
             template_name='catalog/password_reset_confirm.html',
             success_url='/reset/done/'
         ),
         name='password_reset_confirm'),
    
    path('reset/done/',
         auth_views.PasswordResetCompleteView.as_view(
             template_name='catalog/password_reset_complete.html'
         ),
         name='password_reset_complete'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)