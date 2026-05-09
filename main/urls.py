"""
URL configuration for main project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include

# Swagger ve OpenApi için gerekli modüller
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from drf_yasg.generators import OpenAPISchemaGenerator

# Ayarlar ve çevre değişkenleri için importlar
from django.conf import settings
from django.conf.urls.static import static
try:
    from decouple import config
except ImportError:
    # Eğer decouple yüklü değilse os.environ kullanabilirsin
    import os
    def config(key, default=None):
        return os.environ.get(key, default)

# Swagger arayüzünde 'Authorization' kutusunu açan ve HTTPS protokolünü düzelten sınıf
class JWTSchemaGenerator(OpenAPISchemaGenerator):
    def get_schema(self, request=None, public=False):
        schema = super().get_schema(request, public)

        # PythonAnywhere üzerindeysek veya prod ise HTTPS öncelikli olmalı
        # request.get_host() ile nerede olduğumuzu anlayabiliriz
        host = request.get_host() if request else ""

        if "pythonanywhere" in host or config("ENV_NAME", default="dev") == "prod":
            schema.schemes = ["https", "http"]
        else:
            schema.schemes = ["http", "https"]

        # Token bazlı yetkilendirme (Token <key>) tanımı
        schema.security_definitions = {
            'Token': {
                'type': 'apiKey',
                'name': 'Authorization',
                'in': 'header',
                'description': 'Lütfen "Token <key>" formatında giriniz.'
            }
        }
        schema.security = [{"Token": []}]
        return schema


schema_view = get_schema_view(
   openapi.Info(
      title="Rent-a-Car REST API",
      default_version='V.01',
      description="Professional Car Rental Management API with JWT Authentication and Full CRUD Support",
      contact=openapi.Contact(email="developerumit@gmail.com"),
      license=openapi.License(name="BSD License"),
   ),
   public=True,
   permission_classes=[permissions.AllowAny],
   generator_class=JWTSchemaGenerator, # Hazırladığımız generator'ı buraya bağladık
)

# 1. Sabit URL Yolları
urlpatterns = [
    path("admin/", admin.site.urls),
    path("users/", include("users.urls")),
    path("api/", include("car.urls")),
]

# 2. Şartlı Swagger Yolları (Sadece ENV_NAME 'prod' değilse aktif olur)
if config("ENV_NAME", default="dev") != "prod":
    urlpatterns += [
        path("swagger/", schema_view.with_ui("swagger", cache_timeout=0), name="schema-swagger-ui"),
        path("redoc/", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"),
    ]

# 3. Media Dosyaları (Geliştirme aşamasında resimlerin görünmesi için)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
