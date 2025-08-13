from decimal import Decimal

from django.db import transaction
from rest_framework import viewsets, status, permissions, serializers
from rest_framework.decorators import action
from rest_framework.response import Response

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import ShoppingList, ShoppingListItem
from .serializers import ShoppingListSerializer, ShoppingListItemSerializer


class ShoppingListViewSet(viewsets.ModelViewSet):
    """
    CRUD для списков покупок пользователя.
    """
    serializer_class = ShoppingListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ShoppingList.objects.filter(user=self.request.user).prefetch_related('items')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ShoppingListItemViewSet(viewsets.ModelViewSet):
    """
    ViewSet для управления элементами списка покупок.
    """
    queryset = ShoppingListItem.objects.all()
    serializer_class = ShoppingListItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Показываем только те items, которые принадлежат спискам текущего пользователя.
        """
        return ShoppingListItem.objects.filter(shopping_list__user=self.request.user)

    # ---------- CREATE ----------
    @swagger_auto_schema(
        operation_summary="Создание элемента списка покупок",
        operation_description=(
            "Добавляет ингредиент (ingredient_id, quantity, unit) в список покупок.\n"
            "Варианты:\n"
            "• Передайте shopping_list_id — добавим туда.\n"
            "• ЛИБО НЕ передавайте shopping_list_id, но передайте recipe_id — "
            "тогда список будет создан/взят по названию рецепта (recipe.title) для текущего пользователя."
        ),
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['ingredient_id', 'quantity', 'unit'],
            properties={
                'shopping_list_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID списка покупок (опционально)'),
                'ingredient_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID ингредиента',),
                'quantity': openapi.Schema(type=openapi.TYPE_NUMBER, description='Количество'),
                'unit': openapi.Schema(type=openapi.TYPE_STRING, description='Единица измерения'),
                'recipe_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID рецепта (обязательно, если нет shopping_list_id)'),
            },
        ),
        responses={
            201: openapi.Response(description="Элемент успешно добавлен"),
            400: "Некорректные данные",
            404: "Список покупок / ингредиент / рецепт не найден"
        }
    )
    def create(self, request, *args, **kwargs):
        """
        POST /api/v1/shopping-list/items/
        """
        data = request.data

        ingredient_id = data.get('ingredient_id')
        quantity = data.get('quantity')
        unit = data.get('unit')
        if not ingredient_id or quantity is None or unit in (None, ""):
            return Response({"detail": "Нужны поля: ingredient_id, quantity, unit."}, status=400)

        from recipes_app.models import Ingredient, Recipe

        # 1) Определяем/создаём целевой список
        shopping_list = None
        shopping_list_id = data.get('shopping_list_id')
        if shopping_list_id:
            try:
                shopping_list = ShoppingList.objects.get(id=shopping_list_id, user=request.user)
            except ShoppingList.DoesNotExist:
                return Response({"detail": "Список покупок не найден."}, status=404)
        else:
            recipe_id = data.get('recipe_id')
            if not recipe_id:
                return Response({"detail": "Либо передайте shopping_list_id, либо recipe_id."}, status=400)
            try:
                recipe = Recipe.objects.get(id=recipe_id)
            except Recipe.DoesNotExist:
                return Response({"detail": "Рецепт не найден."}, status=404)
            # Автосоздание/получение списка по названию рецепта
            shopping_list, _ = ShoppingList.objects.get_or_create(user=request.user, title=recipe.title)

        # 2) Проверка ингредиента
        try:
            ingredient = Ingredient.objects.get(id=ingredient_id)
        except Ingredient.DoesNotExist:
            return Response({"detail": "Ингредиент не найден."}, status=404)

        # 3) Привязка к рецепту (опционально)
        recipe = None
        recipe_id = data.get('recipe_id')
        if recipe_id:
            from recipes_app.models import Recipe as _Recipe
            try:
                recipe = _Recipe.objects.get(id=recipe_id)
            except _Recipe.DoesNotExist:
                return Response({"detail": "Рецепт не найден."}, status=404)

        # 4) Создание элемента
        serializer = self.get_serializer(data={
            "shopping_list": shopping_list.id,
            "ingredient": ingredient.id,
            "recipe": recipe.id if recipe else None,
            "quantity": quantity,
            "unit": unit,
            "is_purchased": False
        })
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    # ---------- ADD-RECIPE-BY-TITLE (bulk из рецепта) ----------
    class AddRecipeByTitleSerializer(serializers.Serializer):
        recipe_id = serializers.IntegerField()
        title = serializers.CharField(required=False, allow_blank=True)  # если не задано — будет recipe.title
        multiply = serializers.DecimalField(max_digits=8, decimal_places=2, required=False, default=Decimal("1"))

    @swagger_auto_schema(
        method='post',
        operation_summary="Добавить все ингредиенты рецепта в список (по названию)",
        operation_description=(
            "Создаёт/берёт список текущего пользователя с названием `title` "
            "(если не указать — используется название рецепта) и добавляет ВСЕ ингредиенты `recipe_id`.\n"
            "Параметр `multiply` умножает количества."
        ),
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['recipe_id'],
            properties={
                'recipe_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                'title': openapi.Schema(type=openapi.TYPE_STRING, description='Название списка (опционально)'),
                'multiply': openapi.Schema(type=openapi.TYPE_NUMBER, description='Множитель порций (опц., по умолчанию 1)'),
            }
        ),
        responses={201: "Добавлено", 404: "Рецепт не найден"}
    )
    @action(detail=False, methods=['post'], url_path='add-recipe-by-title')
    def add_recipe_by_title(self, request, *args, **kwargs):
        from recipes_app.models import Recipe, RecipeIngredient

        ser = self.AddRecipeByTitleSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        recipe_id = ser.validated_data['recipe_id']
        custom_title = ser.validated_data.get('title')
        multiply = ser.validated_data.get('multiply') or Decimal("1")

        try:
            recipe = Recipe.objects.get(id=recipe_id)
        except Recipe.DoesNotExist:
            return Response({"detail": "Рецепт не найден."}, status=404)

        title = (custom_title or recipe.title).strip() or recipe.title
        shopping_list, _ = ShoppingList.objects.get_or_create(user=request.user, title=title)

        recipe_ings = RecipeIngredient.objects.filter(recipe=recipe).select_related('ingredient')

        created_or_updated = []
        with transaction.atomic():
            for ri in recipe_ings:
                qty = (ri.quantity or 0) * multiply
                obj, created = ShoppingListItem.objects.get_or_create(
                    shopping_list=shopping_list,
                    ingredient=ri.ingredient,
                    recipe=recipe,
                    defaults={"quantity": qty, "unit": ri.unit, "is_purchased": False}
                )
                if not created:
                    # Политика слияния: суммируем количество, обновляем unit последним значением
                    obj.quantity = obj.quantity + qty
                    obj.unit = ri.unit
                    obj.save(update_fields=['quantity', 'unit'])
                created_or_updated.append(obj)

        return Response(ShoppingListItemSerializer(created_or_updated, many=True).data, status=201)

    # ---------- DESTROY ----------
    @swagger_auto_schema(
        operation_summary="Удаление элемента списка покупок",
        operation_description="Удаляет элемент (item_id) из списка покупок текущего пользователя.",
        responses={204: "Успешно удалён", 404: "Элемент не найден"}
    )
    def destroy(self, request, *args, **kwargs):
        """
        DELETE /api/v1/shopping-list/items/{item_id}/
        """
        return super().destroy(request, *args, **kwargs)

    # ---------- PARTIAL UPDATE ----------
    @swagger_auto_schema(
        operation_summary="Изменение статуса куплено/не куплено",
        operation_description="Меняет поле is_purchased в ShoppingListItem.",
        manual_parameters=[
            openapi.Parameter('item_id', openapi.IN_PATH, description="ID элемента списка", type=openapi.TYPE_INTEGER),
        ],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['is_purchased'],
            properties={'is_purchased': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Статус куплено/не куплено')},
        ),
        responses={200: "Статус обновлён", 404: "Элемент не найден"}
    )
    def partial_update(self, request, *args, **kwargs):
        """
        PATCH /api/v1/shopping-list/items/{item_id}/
        """
        return super().partial_update(request, *args, **kwargs)

    # ---------- LIST ----------
    @swagger_auto_schema(
        operation_summary="Получение элементов списка покупок пользователя",
        operation_description="Возвращает все элементы (ShoppingListItem) текущего пользователя."
    )
    def list(self, request, *args, **kwargs):
        """
        GET /api/v1/shopping-list/items/
        """
        return super().list(request, *args, **kwargs)
