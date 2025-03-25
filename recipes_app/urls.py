from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    RecipeViewSet,
    RecipeIngredientView,
    RecipeIngredientDetailView,
    RecipeCommentView
)

router = DefaultRouter()
router.register(r'', RecipeViewSet, basename='recipe')

urlpatterns = [
    # CRUD по рецептам
    path('', include(router.urls)),

    # 1. Добавление / список ингредиентов
    path('<int:recipe_id>/ingredients/', RecipeIngredientView.as_view(), name='recipe_ingredient_list_create'),

    # 2. Удаление ингредиента
    path('<int:recipe_id>/ingredients/<int:ingredient_id>/', RecipeIngredientDetailView.as_view(), name='recipe_ingredient_detail'),

    # 3. Комментарии (POST + GET)
    path('<int:recipe_id>/comments/', RecipeCommentView.as_view(), name='recipe_comment_list_create'),
]
