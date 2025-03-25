from django.contrib import admin
from .models import CustomUser  # Если у вас есть кастомная модель пользователя

@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('id', 'email', 'username', 'avatar', 'bio', 'is_staff', 'is_superuser')
    search_fields = ('email', 'username')
    list_filter = ('is_staff', 'is_superuser')
