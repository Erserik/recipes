from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ShoppingListViewSet, ShoppingListItemViewSet

router = DefaultRouter()
router.register(r'items', ShoppingListItemViewSet, basename='shoppinglistitem')
router.register(r'', ShoppingListViewSet, basename='shoppinglist')


urlpatterns = [path('', include(router.urls))]


