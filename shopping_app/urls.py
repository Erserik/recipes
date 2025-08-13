from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ShoppingListViewSet, ShoppingListItemViewSet

router = DefaultRouter()
router.register(r'', ShoppingListViewSet, basename='shoppinglist')
router.register(r'items', ShoppingListItemViewSet, basename='shoppinglistitem')

urlpatterns = [path('', include(router.urls))]
