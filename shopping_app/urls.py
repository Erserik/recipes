from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ShoppingListItemViewSet

router = DefaultRouter()
router.register(r'items', ShoppingListItemViewSet, basename='shoppinglistitem')

urlpatterns = [
    path('', include(router.urls)),
]
