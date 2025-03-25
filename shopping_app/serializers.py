from rest_framework import serializers
from .models import Recipe, Ingredient, RecipeIngredient, Comment

class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ('id', 'name')


class RecipeIngredientSerializer(serializers.ModelSerializer):
    # Показываем название ингредиента через вложенный сериализатор
    ingredient = IngredientSerializer()

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'ingredient', 'quantity', 'unit')


class CommentSerializer(serializers.ModelSerializer):
    author = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ('id', 'text', 'author', 'created_at')

    def get_author(self, obj):
        return {
            "id": obj.user.id,
            "username": obj.user.username
        }


class RecipeSerializer(serializers.ModelSerializer):
    author = serializers.StringRelatedField(read_only=True)
    recipe_ingredients = RecipeIngredientSerializer(many=True, read_only=True)
    comments = CommentSerializer(many=True, read_only=True)

    class Meta:
        model = Recipe
        fields = (
            'id',
            'author',
            'title',
            'description',
            'is_public',
            'created_at',
            'updated_at',
            'recipe_ingredients',  # список ингредиентов
            'comments'             # список комментариев
        )
