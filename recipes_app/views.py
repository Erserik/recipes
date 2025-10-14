from django.db.models import Q
from django.db import IntegrityError, transaction
from rest_framework import viewsets, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import Recipe, Ingredient, RecipeIngredient, Comment
from .serializers import (
    RecipeSerializer,
    RecipeIngredientSerializer,
    CommentSerializer
)

# ---------- ИДЕМПОТЕНТНОСТЬ: утилита для детерминированного UUID ----------
import uuid, json
from typing import Any, Dict, Optional

_IDEMP_NAMESPACE = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")  # фиксированный namespace

def _canonical(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

def make_request_uuid(
    body: Dict[str, Any],
    *,
    path: str,
    user_id: Optional[int] = None,
    extra: Optional[Dict[str, Any]] = None
) -> uuid.UUID:
    payload = {
        "path": path,
        "user_id": user_id,
        "body": body or {},
        "extra": extra or {},
    }
    return uuid.uuid5(_IDEMP_NAMESPACE, _canonical(payload))


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
        (не используется в override create, оставлено для совместимости)
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
            if str(is_public).lower() == 'true':
                queryset = queryset.filter(is_public=True)
            elif str(is_public).lower() == 'false':
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
    )
    def list(self, request, *args, **kwargs):
        """
        GET /api/v1/recipes/?page=1&page_size=20&search=...&is_public=...&author=...
        Выводит список рецептов с учётом фильтров и пагинации.
        """
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Создание рецепта (идемпотентно по body)",
        operation_description="Создаёт рецепт. Повтор с тем же телом не создаст дубликат.",
        request_body=RecipeSerializer,
    )
    def create(self, request, *args, **kwargs):
        """
        POST /api/v1/recipes/
        Создаёт новый рецепт. Поля: title, description, is_public и т.д.
        Идемпотентность: UUID из (title, description, is_public) + user + path.
        """
        if not request.user or not request.user.is_authenticated:
            return Response({"detail": "Authentication required."}, status=status.HTTP_401_UNAUTHORIZED)

        body_for_uuid = {
            "title": request.data.get("title"),
            "description": request.data.get("description"),
            "is_public": bool(request.data.get("is_public", True)),
        }
        req_uuid = make_request_uuid(
            body_for_uuid,
            path="/api/v1/recipes/",
            user_id=request.user.id,
        )

        existing = Recipe.objects.filter(request_uuid=req_uuid).first()
        if existing:
            data = self.get_serializer(existing).data
            return Response(data, status=status.HTTP_200_OK)

        try:
            with transaction.atomic():
                serializer = self.get_serializer(data=request.data)
                serializer.is_valid(raise_exception=True)
                instance = serializer.save(author=request.user, request_uuid=req_uuid)
        except IntegrityError:
            instance = Recipe.objects.get(request_uuid=req_uuid)

        headers = self.get_success_headers(RecipeSerializer(instance).data)
        return Response(RecipeSerializer(instance).data, status=status.HTTP_201_CREATED, headers=headers)

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
    GET: Возвращает список ингредиентов рецепта.
    """
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Добавление ингредиента в рецепт (идемпотентно)",
        operation_description="Добавляет ингредиент (name, quantity, unit) к указанному рецепту (recipe_id). "
                              "Повтор с теми же полями не создаст дубликат.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['name', 'quantity', 'unit'],
            properties={
                'name': openapi.Schema(type=openapi.TYPE_STRING, description='Название ингредиента'),
                'quantity': openapi.Schema(type=openapi.TYPE_NUMBER, description='Количество'),
                'unit': openapi.Schema(type=openapi.TYPE_STRING, description='Единица измерения'),
            },
        ),
        responses={201: "Created / Idempotent"}
    )
    def post(self, request, recipe_id):
        """
        POST /api/v1/recipes/{recipe_id}/ingredients/
        Добавляем ингредиент к рецепту (только автор). Идемпотентно по body.
        """
        try:
            recipe = Recipe.objects.get(pk=recipe_id)
        except Recipe.DoesNotExist:
            return Response({"detail": "Рецепт не найден."}, status=status.HTTP_404_NOT_FOUND)

        if recipe.author != request.user:
            return Response({"detail": "Вы не автор рецепта."}, status=status.HTTP_403_FORBIDDEN)

        name = (request.data.get('name') or "").strip()
        quantity = request.data.get('quantity')
        unit = (request.data.get('unit') or "").strip()

        if not name or quantity is None or not unit:
            return Response({"detail": "Необходимо указать name, quantity, unit."}, status=status.HTTP_400_BAD_REQUEST)

        body_for_uuid = {"name": name, "quantity": float(quantity), "unit": unit}
        req_uuid = make_request_uuid(
            body_for_uuid,
            path=f"/api/v1/recipes/{recipe_id}/ingredients/",
            user_id=request.user.id,
            extra={"recipe_id": recipe_id},
        )

        existing = RecipeIngredient.objects.filter(request_uuid=req_uuid).first()
        if existing:
            return Response(RecipeIngredientSerializer(existing).data, status=status.HTTP_200_OK)

        ingredient, _ = Ingredient.objects.get_or_create(name=name)

        try:
            with transaction.atomic():
                ri = RecipeIngredient.objects.create(
                    recipe=recipe,
                    ingredient=ingredient,
                    quantity=quantity,
                    unit=unit,
                    request_uuid=req_uuid
                )
        except IntegrityError:
            ri = RecipeIngredient.objects.get(request_uuid=req_uuid)

        return Response(RecipeIngredientSerializer(ri).data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        operation_summary="Список ингредиентов рецепта",
        operation_description="Возвращает список ингредиентов для указанного рецепта (recipe_id)."
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

        if recipe.author != request.user and not recipe.is_public:
            # если рецепт приватный — ограничим доступ
            return Response({"detail": "Доступ запрещён."}, status=status.HTTP_403_FORBIDDEN)

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
        responses={204: "No Content"}
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
    POST: Добавляет комментарий к рецепту (идемпотентно),
    GET: Список комментариев рецепта.
    """
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    @swagger_auto_schema(
        operation_summary="Добавление комментария к рецепту (идемпотентно)",
        operation_description="Оставляет комментарий к рецепту (recipe_id). "
                              "Повтор с тем же текстом от того же пользователя к тому же рецепту не создаст дубликат.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['text'],
            properties={
                'text': openapi.Schema(type=openapi.TYPE_STRING, description='Текст комментария'),
            },
        ),
        responses={201: "Created / Idempotent"}
    )
    def post(self, request, recipe_id):
        """
        POST /api/v1/recipes/{recipe_id}/comments/
        Создаёт новый комментарий (только для авторизованных).
        Идемпотентность: UUID из (text) + user + recipe + path.
        """
        try:
            recipe = Recipe.objects.get(pk=recipe_id)
        except Recipe.DoesNotExist:
            return Response({"detail": "Рецепт не найден."}, status=status.HTTP_404_NOT_FOUND)

        if not request.user or not request.user.is_authenticated:
            return Response({"detail": "Authentication required."}, status=status.HTTP_401_UNAUTHORIZED)

        text = (request.data.get('text') or "").strip()
        if not text:
            return Response({"text": ["Комментарий не может быть пустым."]}, status=status.HTTP_400_BAD_REQUEST)

        body_for_uuid = {"text": text}
        req_uuid = make_request_uuid(
            body_for_uuid,
            path=f"/api/v1/recipes/{recipe_id}/comments/",
            user_id=request.user.id,
            extra={"recipe_id": recipe_id},
        )

        existing = Comment.objects.filter(request_uuid=req_uuid).first()
        if existing:
            return Response(CommentSerializer(existing).data, status=status.HTTP_200_OK)

        try:
            with transaction.atomic():
                comment = Comment.objects.create(
                    recipe=recipe,
                    user=request.user,
                    text=text,
                    request_uuid=req_uuid
                )
        except IntegrityError:
            comment = Comment.objects.get(request_uuid=req_uuid)

        return Response(CommentSerializer(comment).data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        operation_summary="Список комментариев к рецепту",
        operation_description="Возвращает все комментарии для рецепта (recipe_id)."
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

from rest_framework.parsers import JSONParser
from rest_framework_xml.parsers import XMLParser
from rest_framework.renderers import JSONRenderer
from rest_framework_xml.renderers import XMLRenderer
class JsonXmlConverterView(APIView):
    """
    Универсальный конвертер JSON <-> XML
    """
    permission_classes = [permissions.AllowAny]
    parser_classes = [JSONParser, XMLParser]
    renderer_classes = [JSONRenderer, XMLRenderer]

    @swagger_auto_schema(
        operation_summary="Конвертация JSON ↔ XML",
        operation_description=(
            "Принимает JSON или XML и возвращает оба формата: "
            "исходный и преобразованный. "
            "Пример:\n"
            "- Отправь JSON, получишь XML и обратно."
        ),
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            description="JSON или XML данные для конвертации"
        ),
        responses={200: "Converted successfully"}
    )
    def post(self, request, *args, **kwargs):
        try:
            # определяем, какой формат был на входе
            content_type = request.content_type.lower()
            data = request.data

            if "xml" in content_type:
                input_format = "xml"
                converted_bytes = JSONRenderer().render(data)
                converted = converted_bytes.decode("utf-8") if isinstance(converted_bytes, bytes) else converted_bytes
            else:
                input_format = "json"
                converted_bytes = XMLRenderer().render(data)
                converted = converted_bytes.decode("utf-8") if isinstance(converted_bytes, bytes) else converted_bytes

            return Response({
                "input_format": input_format,
                "input_data": data,
                "converted_data": converted
            }, content_type="application/json", status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)