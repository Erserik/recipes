# recipes_app/serializers.py

from rest_framework import serializers
from .models import Recipe

class RecipeSerializer(serializers.ModelSerializer):
    author = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Recipe
        fields = ('id', 'author', 'title', 'description', 'is_public', 'created_at', 'updated_at')
