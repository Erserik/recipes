from django.contrib import admin
from django.urls import path, include, re_path
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions
from django.conf import settings
from django.conf.urls.static import static
schema_view = get_schema_view(
   openapi.Info(
      title="Recipes API",
      default_version='v1',
      description="Документация для API (рецепты, список покупок и т.д.)",
   ),
   public=True,
   permission_classes=(permissions.AllowAny,),
)
urlpatterns = [
    path('admin/', admin.site.urls),
    # Приложение для регистрации/авторизации (accounts)
    path('api/v1/auth/', include('accounts.urls')),
    # Приложение для рецептов (recipes_app)
    path('api/v1/recipes/', include('recipes_app.urls')),
    # Новое приложение shopping_app
    path('api/v1/shopping-list/', include('shopping_app.urls')),
    # Swagger
    re_path(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)