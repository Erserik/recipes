# models.py
import uuid
from django.db import models
from django.conf import settings

class Recipe(models.Model):
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='recipes'
    )
    title = models.CharField(max_length=255)
    description = models.TextField()
    is_public = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # 🔐 UUID идемпотентности запроса на создание
    request_uuid = models.UUIDField(null=True, blank=True, unique=True, db_index=True)

    def __str__(self):
        return self.title


class Ingredient(models.Model):
    name = models.CharField(max_length=100, unique=True)
    def __str__(self):
        return self.name


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='recipe_ingredients')
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE, related_name='ingredient_in_recipes')
    quantity = models.FloatField()
    unit = models.CharField(max_length=50)

    # для идемпотентного добавления конкретной связки в рецепт
    request_uuid = models.UUIDField(null=True, blank=True, unique=True, db_index=True)

    def __str__(self):
        return f"{self.ingredient.name} ({self.quantity} {self.unit}) для {self.recipe.title}"


class Comment(models.Model):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='comments')
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    # идемпотентность создания комментария
    request_uuid = models.UUIDField(null=True, blank=True, unique=True, db_index=True)

    def __str__(self):
        return f"Комментарий от {self.user} к {self.recipe.title}"
