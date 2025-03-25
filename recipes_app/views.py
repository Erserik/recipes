from django.db.models import Q
from rest_framework import viewsets, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import Recipe, Ingredient, RecipeIngredient, Comment
from .serializers import (
    RecipeSerializer,
    IngredientSerializer,
    RecipeIngredientSerializer,
    CommentSerializer
)

# ====== 1) CRUD по Рецептам (уже было) ====== #
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

    # Ниже пример Swagger-описаний
    @swagger_auto_schema(
        operation_summary="Получение списка рецептов",
        operation_description="Возвращает список рецептов. Публичные видны всем, личные – только автору.",
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Создание рецепта",
        operation_description="Позволяет авторизованному пользователю создать новый рецепт.",
        request_body=RecipeSerializer,
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Получение рецепта",
        operation_description="Возвращает данные рецепта по его ID.",
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Обновление рецепта",
        operation_description="Позволяет автору обновить данные рецепта.",
        request_body=RecipeSerializer,
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Удаление рецепта",
        operation_description="Позволяет автору удалить рецепт.",
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)


# ====== 2) Добавление / удаление ингредиентов ====== #

class RecipeIngredientView(APIView):
    """POST: Добавляет ингредиент к рецепту.
       GET: (опционально) Получает список ингредиентов рецепта.
    """
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Добавление ингредиента в рецепт",
        operation_description="Добавляет ингредиент (name, quantity, unit) к указанному рецепту (recipe_id).",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['name', 'quantity', 'unit'],
            properties={
                'name': openapi.Schema(type=openapi.TYPE_STRING, description='Название ингредиента'),
                'quantity': openapi.Schema(type=openapi.TYPE_NUMBER, description='Количество'),
                'unit': openapi.Schema(type=openapi.TYPE_STRING, description='Единица измерения'),
            },
        ),
        responses={
            201: openapi.Response(
                description="Ингредиент успешно добавлен",
                examples={"application/json": {
                    "id": 101,
                    "name": "Сыр",
                    "quantity": 50,
                    "unit": "г"
                }}
            ),
            400: "Ошибка валидации",
            403: "Вы не автор рецепта"
        }
    )
    def post(self, request, recipe_id):
        """Добавляем ингредиент к рецепту."""
        # 1. Проверяем, существует ли рецепт
        try:
            recipe = Recipe.objects.get(pk=recipe_id)
        except Recipe.DoesNotExist:
            return Response({"detail": "Рецепт не найден."}, status=status.HTTP_404_NOT_FOUND)

        # 2. Проверяем, что текущий пользователь = автор
        if recipe.author != request.user:
            return Response({"detail": "Вы не автор рецепта."}, status=status.HTTP_403_FORBIDDEN)

        # 3. Достаем поля (name, quantity, unit)
        data = request.data
        name = data.get('name')
        quantity = data.get('quantity')
        unit = data.get('unit')

        if not name or not quantity or not unit:
            return Response({"detail": "Необходимо указать name, quantity, unit."}, status=status.HTTP_400_BAD_REQUEST)

        # 4. Проверяем / создаем сам ингредиент
        ingredient, created = Ingredient.objects.get_or_create(name=name)

        # 5. Создаем RecipeIngredient
        recipe_ingredient = RecipeIngredient.objects.create(
            recipe=recipe,
            ingredient=ingredient,
            quantity=quantity,
            unit=unit
        )

        # 6. Возвращаем сериализованные данные
        serializer = RecipeIngredientSerializer(recipe_ingredient)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        operation_summary="Список ингредиентов рецепта",
        operation_description="Возвращает список ингредиентов для указанного рецепта (recipe_id).",
        responses={
            200: openapi.Response(
                description="Список ингредиентов",
                examples={"application/json": [
                    {
                        "id": 101,
                        "ingredient": {"id": 1, "name": "Сыр"},
                        "quantity": 50,
                        "unit": "г"
                    }
                ]}
            ),
            404: "Рецепт не найден"
        }
    )
    def get(self, request, recipe_id):
        """Возвращает список ингредиентов для рецепта."""
        try:
            recipe = Recipe.objects.get(pk=recipe_id)
        except Recipe.DoesNotExist:
            return Response({"detail": "Рецепт не найден."}, status=status.HTTP_404_NOT_FOUND)

        recipe_ingredients = recipe.recipe_ingredients.select_related('ingredient').all()
        serializer = RecipeIngredientSerializer(recipe_ingredients, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class RecipeIngredientDetailView(APIView):
    """DELETE: Удаление конкретного ингредиента (ingredient_id) из рецепта (recipe_id)."""
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Удаление ингредиента из рецепта",
        operation_description="Удаляет ингредиент (ingredient_id) из рецепта (recipe_id).",
        responses={
            204: "Ингредиент успешно удален",
            403: "Вы не автор рецепта",
            404: "Ингредиент не найден"
        }
    )
    def delete(self, request, recipe_id, ingredient_id):
        # 1. Ищем рецепт
        try:
            recipe = Recipe.objects.get(pk=recipe_id)
        except Recipe.DoesNotExist:
            return Response({"detail": "Рецепт не найден."}, status=status.HTTP_404_NOT_FOUND)

        # 2. Проверяем автора
        if recipe.author != request.user:
            return Response({"detail": "Вы не автор рецепта."}, status=status.HTTP_403_FORBIDDEN)

        # 3. Ищем RecipeIngredient
        try:
            recipe_ingredient = RecipeIngredient.objects.get(pk=ingredient_id, recipe=recipe)
        except RecipeIngredient.DoesNotExist:
            return Response({"detail": "Ингредиент не найден."}, status=status.HTTP_404_NOT_FOUND)

        # 4. Удаляем
        recipe_ingredient.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ====== 3) Комментарии ====== #

class RecipeCommentView(APIView):
    """POST: Добавляет комментарий к рецепту, GET: список комментариев."""
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    @swagger_auto_schema(
        operation_summary="Добавление комментария к рецепту",
        operation_description="Оставляет комментарий к рецепту (recipe_id).",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['text'],
            properties={
                'text': openapi.Schema(type=openapi.TYPE_STRING, description='Текст комментария'),
            },
        ),
        responses={
            201: openapi.Response(
                description="Комментарий успешно добавлен",
                examples={"application/json": {
                    "id": 3,
                    "text": "Очень вкусно!",
                    "author": {"id": 1, "username": "User1"},
                    "created_at": "2025-03-19T10:00:00Z"
                }}
            ),
            400: "Ошибка валидации"
        }
    )
    def post(self, request, recipe_id):
        """Создаёт новый комментарий для рецепта."""
        try:
            recipe = Recipe.objects.get(pk=recipe_id)
        except Recipe.DoesNotExist:
            return Response({"detail": "Рецепт не найден."}, status=status.HTTP_404_NOT_FOUND)

        text = request.data.get('text')
        if not text:
            return Response({"text": ["Комментарий не может быть пустым."]}, status=status.HTTP_400_BAD_REQUEST)

        comment = Comment.objects.create(
            recipe=recipe,
            user=request.user,
            text=text
        )

        serializer = CommentSerializer(comment)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        operation_summary="Список комментариев к рецепту",
        operation_description="Возвращает все комментарии для рецепта (recipe_id).",
        responses={
            200: openapi.Response(
                description="Список комментариев",
                examples={"application/json": [
                    {
                        "id": 3,
                        "text": "Очень вкусно!",
                        "author": {"id": 1, "username": "User1"},
                        "created_at": "2025-03-19T10:00:00Z"
                    }
                ]}
            ),
            404: "Рецепт не найден"
        }
    )
    def get(self, request, recipe_id):
        """Возвращает список комментариев для рецепта."""
        try:
            recipe = Recipe.objects.get(pk=recipe_id)
        except Recipe.DoesNotExist:
            return Response({"detail": "Рецепт не найден."}, status=status.HTTP_404_NOT_FOUND)

        comments = recipe.comments.select_related('user').all().order_by('-created_at')
        serializer = CommentSerializer(comments, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
