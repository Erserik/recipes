from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .models import ShoppingList, ShoppingListItem
from .serializers import ShoppingListItemSerializer

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
        user = self.request.user
        return ShoppingListItem.objects.filter(shopping_list__user=user)

    @swagger_auto_schema(
        operation_summary="Создание элемента списка покупок",
        operation_description="Добавляет ингредиент (ingredient_id, quantity, unit) в указанный shopping_list_id. "
                              "Можно передать recipe_id (необязательно).",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['shopping_list_id', 'ingredient_id', 'quantity', 'unit'],
            properties={
                'shopping_list_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID списка покупок'),
                'ingredient_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID ингредиента'),
                'quantity': openapi.Schema(type=openapi.TYPE_NUMBER, description='Количество'),
                'unit': openapi.Schema(type=openapi.TYPE_STRING, description='Единица измерения'),
                'recipe_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID рецепта (опционально)'),
            },
        ),
        responses={
            201: openapi.Response(
                description="Элемент успешно добавлен",
                examples={"application/json": {
                    "id": 201,
                    "ingredient": 101,
                    "quantity": 2,
                    "unit": "шт",
                    "is_purchased": False
                }}
            ),
            400: "Некорректные данные",
            404: "Список покупок или ингредиент не найден"
        }
    )
    def create(self, request, *args, **kwargs):
        """
        POST /api/v1/shopping-list/items/
        """
        data = request.data
        shopping_list_id = data.get('shopping_list_id')
        ingredient_id = data.get('ingredient_id')
        recipe_id = data.get('recipe_id', None)

        # Проверки
        if not shopping_list_id or not ingredient_id:
            return Response({"detail": "Не указаны shopping_list_id или ingredient_id."}, status=status.HTTP_400_BAD_REQUEST)

        # Проверяем, что shopping_list принадлежит текущему пользователю
        try:
            shopping_list = ShoppingList.objects.get(id=shopping_list_id, user=request.user)
        except ShoppingList.DoesNotExist:
            return Response({"detail": "Список покупок не найден."}, status=status.HTTP_404_NOT_FOUND)

        # Проверяем, что ingredient существует
        from recipes_app.models import Ingredient  # или импортируйте наверху
        try:
            ingredient = Ingredient.objects.get(id=ingredient_id)
        except Ingredient.DoesNotExist:
            return Response({"detail": "Ингредиент не найден."}, status=status.HTTP_404_NOT_FOUND)

        # Если recipe_id передан, проверяем
        recipe = None
        if recipe_id:
            from recipes_app.models import Recipe
            try:
                recipe = Recipe.objects.get(id=recipe_id)
            except Recipe.DoesNotExist:
                # Можем вернуть 404 или просто проигнорировать
                return Response({"detail": "Рецепт не найден."}, status=status.HTTP_404_NOT_FOUND)

        # Создаём ShoppingListItem
        serializer = self.get_serializer(data={
            "shopping_list": shopping_list.id,
            "ingredient": ingredient.id,
            "recipe": recipe.id if recipe else None,
            "quantity": data.get('quantity'),
            "unit": data.get('unit'),
            "is_purchased": False
        })
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        operation_summary="Удаление элемента списка покупок",
        operation_description="Удаляет элемент (item_id) из списка покупок текущего пользователя.",
        responses={
            204: "Успешно удалён",
            404: "Элемент не найден"
        }
    )
    def destroy(self, request, *args, **kwargs):
        """
        DELETE /api/v1/shopping-list/items/{item_id}/
        """
        return super().destroy(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Изменение статуса куплено/не куплено",
        operation_description="Меняет поле is_purchased в ShoppingListItem.",
        manual_parameters=[
            openapi.Parameter('item_id', openapi.IN_PATH, description="ID элемента списка", type=openapi.TYPE_INTEGER),
        ],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['is_purchased'],
            properties={
                'is_purchased': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Статус куплено/не куплено'),
            },
        ),
        responses={
            200: openapi.Response(
                description="Статус обновлён",
                examples={"application/json": {
                    "id": 45,
                    "ingredient": 101,
                    "quantity": 3,
                    "unit": "шт",
                    "is_purchased": True
                }}
            ),
            404: "Элемент не найден"
        }
    )
    def partial_update(self, request, *args, **kwargs):
        """
        PATCH /api/v1/shopping-list/items/{item_id}/
        """
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Получение списка покупок",
        operation_description="Возвращает все элементы списка покупок (ShoppingListItem) текущего пользователя.",
        responses={
            200: openapi.Response(
                description="Список элементов",
                examples={"application/json": [
                    {
                        "id": 45,
                        "ingredient": 101,
                        "quantity": 3,
                        "unit": "шт",
                        "is_purchased": False
                    }
                ]}
            )
        }
    )
    def list(self, request, *args, **kwargs):
        """
        GET /api/v1/shopping-list/items/
        """
        return super().list(request, *args, **kwargs)
