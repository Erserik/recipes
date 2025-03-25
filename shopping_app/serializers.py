from rest_framework import serializers
from .models import ShoppingList, ShoppingListItem
# Если Ingredient и Recipe сериализаторы нужны, импортируйте их из другого приложения или сделайте свои

class ShoppingListItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShoppingListItem
        fields = (
            'id',
            'shopping_list',
            'ingredient',
            'recipe',
            'quantity',
            'unit',
            'is_purchased'
        )

class ShoppingListSerializer(serializers.ModelSerializer):
    items = ShoppingListItemSerializer(many=True, read_only=True)

    class Meta:
        model = ShoppingList
        fields = ('id', 'user', 'title', 'created_at', 'items')
