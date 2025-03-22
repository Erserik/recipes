from rest_framework import viewsets, permissions
from django.db.models import Q
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .models import Recipe
from .serializers import RecipeSerializer

class RecipeViewSet(viewsets.ModelViewSet):
    serializer_class = RecipeSerializer
    queryset = Recipe.objects.all()
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            return Recipe.objects.filter(Q(is_public=True) | Q(author=user))
        return Recipe.objects.filter(is_public=True)

    @swagger_auto_schema(
        operation_summary="Получение списка рецептов",
        operation_description="Возвращает список рецептов. Публичные рецепты видны всем, личные – только автору.",
        manual_parameters=[
            openapi.Parameter('page', openapi.IN_QUERY, description="Номер страницы", type=openapi.TYPE_INTEGER),
            openapi.Parameter('page_size', openapi.IN_QUERY, description="Количество рецептов на странице", type=openapi.TYPE_INTEGER),
            openapi.Parameter('search', openapi.IN_QUERY, description="Поиск по названию", type=openapi.TYPE_STRING),
            openapi.Parameter('is_public', openapi.IN_QUERY, description="Фильтр по доступности", type=openapi.TYPE_BOOLEAN),
            openapi.Parameter('author', openapi.IN_QUERY, description="Фильтр по ID автора", type=openapi.TYPE_INTEGER),
        ],
        responses={
            200: openapi.Response(
                description="Список рецептов",
                examples={"application/json": {
                    "count": 48,
                    "page": 1,
                    "page_size": 20,
                    "total_pages": 3,
                    "next": "http://localhost:8000/api/v1/recipes/?page=2&page_size=20",
                    "previous": None,
                    "results": [
                        {
                            "id": 12,
                            "title": "Паста Карбонара",
                            "author": "User1",
                            "is_public": True,
                            "created_at": "2025-03-19T10:00:00Z",
                            "updated_at": "2025-03-19T10:00:00Z"
                        }
                    ]
                }}
            )
        }
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Создание рецепта",
        operation_description="Позволяет авторизованному пользователю создать новый рецепт.",
        request_body=RecipeSerializer,
        responses={
            201: openapi.Response(
                description="Рецепт успешно создан",
                examples={"application/json": {
                    "id": 12,
                    "title": "Паста Карбонара",
                    "author": "User1",
                    "is_public": True,
                    "created_at": "2025-03-19T10:00:00Z",
                    "updated_at": "2025-03-19T10:00:00Z"
                }}
            ),
            400: "Ошибка валидации"
        }
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Получение рецепта",
        operation_description="Возвращает данные рецепта по его ID.",
        responses={
            200: openapi.Response(
                description="Данные рецепта",
                examples={"application/json": {
                    "id": 12,
                    "title": "Паста Карбонара",
                    "author": "User1",
                    "is_public": True,
                    "created_at": "2025-03-19T10:00:00Z",
                    "updated_at": "2025-03-19T10:00:00Z"
                }}
            ),
            404: "Рецепт не найден"
        }
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Обновление рецепта",
        operation_description="Позволяет автору обновить данные рецепта.",
        request_body=RecipeSerializer,
        responses={
            200: openapi.Response(
                description="Рецепт успешно обновлен",
                examples={"application/json": {"message": "Рецепт успешно обновлен."}}
            ),
            403: "Доступ запрещён",
            400: "Ошибка валидации"
        }
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Удаление рецепта",
        operation_description="Позволяет автору удалить рецепт.",
        responses={
            204: "Рецепт успешно удален",
            403: "Доступ запрещен"
        }
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)
