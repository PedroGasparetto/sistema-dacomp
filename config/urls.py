from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("nucleo.urls")),
    path("conta/", include("contas.urls")),
    path("produtos/", include("catalogo.urls")),
    path("vendas/", include("vendas.urls")),
]
