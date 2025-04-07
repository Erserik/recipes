from rest_framework import serializers
from .models import ShoppingList, ShoppingListItem

class ShoppingListItemSerializer(serializers.ModelSerializer):
    ingredient_name = serializers.CharField(source='ingredient.name', read_only=True)
    recipe_title = serializers.CharField(source='recipe.title', read_only=True)

    class Meta:
        model = ShoppingListItem
        fields = (
            'id',
            'shopping_list',
            'ingredient',
            'ingredient_name',
            'recipe',
            'recipe_title',
            'quantity',
            'unit',
            'is_purchased'
        )

class ShoppingListSerializer(serializers.ModelSerializer):
    items = ShoppingListItemSerializer(many=True, read_only=True)

    class Meta:
        model = ShoppingList
        fields = ('id', 'user', 'title', 'created_at', 'items')
