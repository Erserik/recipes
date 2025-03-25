from django.db import models
from django.conf import settings
# Предположим, что Ingredient и Recipe у вас уже есть в другом приложении (например, recipes_app).
# Подкорректируйте import под ваш проект.
from recipes_app.models import Ingredient, Recipe

class ShoppingList(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='shopping_lists'
    )
    title = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} (User: {self.user})"

class ShoppingListItem(models.Model):
    shopping_list = models.ForeignKey(
        ShoppingList,
        on_delete=models.CASCADE,
        related_name='items'
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        related_name='shopping_items'
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='shopping_items'
    )
    quantity = models.FloatField()
    unit = models.CharField(max_length=50)
    is_purchased = models.BooleanField(default=False)

    def __str__(self):
        return f"Item {self.ingredient.name} in {self.shopping_list.title}"
