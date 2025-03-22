from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from .views import CurrentUserView, ChangePasswordView, \
    UserRegistrationView  # Если UserRegistrationView уже реализовано

urlpatterns = [
    # Пример регистрации (если реализовано в accounts/views.py)
    path('register/', UserRegistrationView.as_view(), name='register'),

    # Авторизация: получение JWT-токенов
    path('login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),

    # Обновление токена
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # Получение данных о текущем пользователе
    path('user/', CurrentUserView.as_view(), name='current_user'),

    # Смена пароля
    path('change-password/', ChangePasswordView.as_view(), name='change_password'),
]
