from django.contrib import admin
from .models import ShoppingList, ShoppingListItem

@admin.register(ShoppingList)
class ShoppingListAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'user', 'created_at')
    search_fields = ('title', 'user__email')

@admin.register(ShoppingListItem)
class ShoppingListItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'shopping_list', 'ingredient', 'recipe', 'quantity', 'unit', 'is_purchased')
    list_filter = ('is_purchased',)
