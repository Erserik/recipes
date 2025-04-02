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

# ====== 1) CRUD по Рецептам (с пагинацией и фильтрами) ====== #
class RecipeViewSet(viewsets.ModelViewSet):
    """
    ViewSet для управления рецептами (CRUD) и вывода списка рецептов с пагинацией.
    """
    serializer_class = RecipeSerializer
    queryset = Recipe.objects.all()
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def perform_create(self, serializer):
        """
        При создании рецепта автоматически проставляем автора из request.user.
        """
        serializer.save(author=self.request.user)

    def get_queryset(self):
        """
        Возвращаем QuerySet с учётом фильтрации:
         - Если пользователь авторизован, показываем публичные рецепты и его личные;
         - Иначе показываем только публичные.
         - Фильтры: search (по названию), is_public (true/false), author (ID).
        """
        queryset = Recipe.objects.all()
        user = self.request.user

        # Публичные + свои личные (если авторизован)
        if user.is_authenticated:
            queryset = queryset.filter(Q(is_public=True) | Q(author=user))
        else:
            queryset = queryset.filter(is_public=True)

        # Поиск по названию: ?search=...
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(title__icontains=search)

        # Фильтр по is_public=true/false
        is_public = self.request.query_params.get('is_public')
        if is_public is not None:
            if is_public.lower() == 'true':
                queryset = queryset.filter(is_public=True)
            elif is_public.lower() == 'false':
                queryset = queryset.filter(is_public=False)

        # Фильтр по автору: ?author=1
        author = self.request.query_params.get('author')
        if author:
            queryset = queryset.filter(author__id=author)

        return queryset

    @swagger_auto_schema(
        operation_summary="Получение списка рецептов",
        operation_description=(
            "Возвращает список рецептов с пагинацией. "
            "Параметры:\n"
            "- page (номер страницы, по умолч. 1)\n"
            "- page_size (количество рецептов на странице, по умолч. 20, макс. 100)\n"
            "- search (поиск по названию)\n"
            "- is_public (true/false) – фильтр по доступности\n"
            "- author (ID автора)\n\n"
            "Если page и page_size не указаны, используются значения по умолчанию."
        ),
        manual_parameters=[
            openapi.Parameter('page', openapi.IN_QUERY, description="Номер страницы (по умолч. 1)", type=openapi.TYPE_INTEGER),
            openapi.Parameter('page_size', openapi.IN_QUERY, description="Количество рецептов на странице (макс 100, по умолч. 20)", type=openapi.TYPE_INTEGER),
            openapi.Parameter('search', openapi.IN_QUERY, description="Поиск по названию рецепта", type=openapi.TYPE_STRING),
            openapi.Parameter('is_public', openapi.IN_QUERY, description="Фильтр по доступности (true/false)", type=openapi.TYPE_STRING),
            openapi.Parameter('author', openapi.IN_QUERY, description="Фильтр по ID автора", type=openapi.TYPE_INTEGER),
        ],
        responses={
            200: openapi.Response(
                description="Список рецептов (с пагинацией)",
                examples={
                    "application/json": {
                        "count": 48,
                        "page": 1,
                        "page_size": 20,
                        "total_pages": 3,
                        "next": "https://example.com/api/v1/recipes/?page=2&page_size=20",
                        "previous": None,
                        "results": [
                            {
                                "id": 12,
                                "title": "Паста Карбонара",
                                "author": {
                                    "id": 1,
                                    "username": "User1"
                                },
                                "is_public": True,
                                "ingredients": [
                                    {"name": "Спагетти", "quantity": 200, "unit": "г"},
                                    {"name": "Бекон", "quantity": 100, "unit": "г"}
                                ]
                            },
                            {
                                "id": 14,
                                "title": "Паста Болоньезе",
                                "author": {
                                    "id": 2,
                                    "username": "User2"
                                },
                                "is_public": True,
                                "ingredients": [
                                    {"name": "Спагетти", "quantity": 250, "unit": "г"},
                                    {"name": "Фарш мясной", "quantity": 200, "unit": "г"}
                                ]
                            }
                        ]
                    }
                }
            )
        }
    )
    def list(self, request, *args, **kwargs):
        """
        GET /api/v1/recipes/?page=1&page_size=20&search=...&is_public=...&author=...
        Выводит список рецептов с учётом фильтров и пагинации.
        """
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Создание рецепта",
        operation_description="Позволяет авторизованному пользователю создать новый рецепт.",
        request_body=RecipeSerializer,
    )
    def create(self, request, *args, **kwargs):
        """
        POST /api/v1/recipes/
        Создаёт новый рецепт. Поля: title, description, is_public и т.д.
        """
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Получение рецепта",
        operation_description="Возвращает данные рецепта по его ID."
    )
    def retrieve(self, request, *args, **kwargs):
        """
        GET /api/v1/recipes/{recipe_id}/
        Возвращает информацию о конкретном рецепте (если он публичный или принадлежит автору).
        """
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Обновление рецепта",
        operation_description="Позволяет автору обновить данные рецепта (PUT).",
        request_body=RecipeSerializer,
    )
    def update(self, request, *args, **kwargs):
        """
        PUT /api/v1/recipes/{recipe_id}/
        Полностью обновляет рецепт (только автор).
        """
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Удаление рецепта",
        operation_description="Позволяет автору удалить рецепт."
    )
    def destroy(self, request, *args, **kwargs):
        """
        DELETE /api/v1/recipes/{recipe_id}/
        Удаляет рецепт (только автор).
        """
        return super().destroy(request, *args, **kwargs)


# ====== 2) Добавление / удаление ингредиентов ====== #
class RecipeIngredientView(APIView):
    """
    POST: Добавляет ингредиент к рецепту.
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
                    "ingredient": {
                        "id": 1,
                        "name": "Сыр"
                    },
                    "quantity": 50,
                    "unit": "г"
                }}
            ),
            400: "Ошибка валидации",
            403: "Вы не автор рецепта"
        }
    )
    def post(self, request, recipe_id):
        """
        POST /api/v1/recipes/{recipe_id}/ingredients/
        Добавляем ингредиент к рецепту (только автор).
        """
        try:
            recipe = Recipe.objects.get(pk=recipe_id)
        except Recipe.DoesNotExist:
            return Response({"detail": "Рецепт не найден."}, status=status.HTTP_404_NOT_FOUND)

        if recipe.author != request.user:
            return Response({"detail": "Вы не автор рецепта."}, status=status.HTTP_403_FORBIDDEN)

        data = request.data
        name = data.get('name')
        quantity = data.get('quantity')
        unit = data.get('unit')

        if not name or not quantity or not unit:
            return Response({"detail": "Необходимо указать name, quantity, unit."}, status=status.HTTP_400_BAD_REQUEST)

        ingredient, created = Ingredient.objects.get_or_create(name=name)

        recipe_ingredient = RecipeIngredient.objects.create(
            recipe=recipe,
            ingredient=ingredient,
            quantity=quantity,
            unit=unit
        )

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
        """
        GET /api/v1/recipes/{recipe_id}/ingredients/
        Возвращает список ингредиентов рецепта (только автор).
        """
        try:
            recipe = Recipe.objects.get(pk=recipe_id)
        except Recipe.DoesNotExist:
            return Response({"detail": "Рецепт не найден."}, status=status.HTTP_404_NOT_FOUND)

        recipe_ingredients = recipe.recipe_ingredients.select_related('ingredient').all()
        serializer = RecipeIngredientSerializer(recipe_ingredients, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class RecipeIngredientDetailView(APIView):
    """
    DELETE: Удаление конкретного ингредиента (ingredient_id) из рецепта (recipe_id).
    """
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
        """
        DELETE /api/v1/recipes/{recipe_id}/ingredients/{ingredient_id}/
        Удаляет ингредиент (только автор).
        """
        try:
            recipe = Recipe.objects.get(pk=recipe_id)
        except Recipe.DoesNotExist:
            return Response({"detail": "Рецепт не найден."}, status=status.HTTP_404_NOT_FOUND)

        if recipe.author != request.user:
            return Response({"detail": "Вы не автор рецепта."}, status=status.HTTP_403_FORBIDDEN)

        try:
            recipe_ingredient = RecipeIngredient.objects.get(pk=ingredient_id, recipe=recipe)
        except RecipeIngredient.DoesNotExist:
            return Response({"detail": "Ингредиент не найден."}, status=status.HTTP_404_NOT_FOUND)

        recipe_ingredient.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ====== 3) Комментарии ====== #
class RecipeCommentView(APIView):
    """
    POST: Добавляет комментарий к рецепту,
    GET: Список комментариев рецепта.
    """
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
        """
        POST /api/v1/recipes/{recipe_id}/comments/
        Создаёт новый комментарий (только для авторизованных).
        """
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
        """
        GET /api/v1/recipes/{recipe_id}/comments/
        Возвращает список комментариев рецепта (доступно всем).
        """
        try:
            recipe = Recipe.objects.get(pk=recipe_id)
        except Recipe.DoesNotExist:
            return Response({"detail": "Рецепт не найден."}, status=status.HTTP_404_NOT_FOUND)

        comments = recipe.comments.select_related('user').all().order_by('-created_at')
        serializer = CommentSerializer(comments, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
