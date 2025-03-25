from django.contrib import admin
from .models import Recipe, Ingredient, RecipeIngredient, Comment

@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'author', 'is_public', 'created_at')
    search_fields = ('title', 'author__email')
    list_filter = ('is_public', 'created_at')

@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)

@admin.register(RecipeIngredient)
class RecipeIngredientAdmin(admin.ModelAdmin):
    list_display = ('id', 'recipe', 'ingredient', 'quantity', 'unit')

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('id', 'recipe', 'user', 'created_at')
    search_fields = ('recipe__title', 'user__email')
