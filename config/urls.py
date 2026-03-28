from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

from core import views


# ==================================================
# BLOQUE 1 - RUTAS DEL ADMIN Y HERRAMIENTAS
# ==================================================
urlpatterns = [
    path("admin/", admin.site.urls),
    path("ckeditor5/", include("django_ckeditor_5.urls")),

    # ==================================================
    # BLOQUE 2 - RUTAS PRINCIPALES DEL SITIO
    # ==================================================
    path("", views.inicio, name="inicio"),
    path("biblioteca/", views.biblioteca, name="biblioteca"),
    path("programas/", views.programas, name="programas"),
    path("juegos/", views.juegos_y_trivias, name="juegos_y_trivias"),
    path("trivias/", views.trivias, name="trivias"),
    path("ordena-pasos/", views.ordena_pasos, name="ordena_pasos"),
    path("ruletas/", views.ruletas, name="ruletas"),
    path("elige-camino/", views.caminos, name="caminos"),
    path("noticias/", views.noticias, name="noticias"),
    path("quiero-aprender/", views.quiero_aprender, name="quiero_aprender"),

    # ==================================================
    # BLOQUE 3 - RUTAS DE DETALLE
    # ==================================================
    path("programas/<int:programa_id>/", views.detalle_programa, name="detalle_programa"),
    path("trivias/<int:trivia_id>/", views.detalle_trivia, name="detalle_trivia"),
    path("ordena-pasos/<int:tema_id>/", views.detalle_ordena_pasos, name="detalle_ordena_pasos"),
    path("ruletas/<int:ruleta_id>/", views.detalle_ruleta, name="detalle_ruleta"),
    path("elige-camino/<int:camino_id>/", views.detalle_camino, name="detalle_camino"),
    path("noticias/<int:noticia_id>/", views.detalle_noticia, name="detalle_noticia"),

    # ==================================================
    # BLOQUE 4 - RUTAS DE PÁGINAS Y COMPONENTES
    # ==================================================
    path(
        "componentes/<slug:slug>/",
        views.render_componente_interactivo,
        name="render_componente_interactivo",
    ),
    path("<slug:slug>/", views.detalle_pagina, name="detalle_pagina"),
]


# ==================================================
# BLOQUE 5 - ARCHIVOS MEDIA
# ==================================================
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    urlpatterns += [
        re_path(
            r"^media/(?P<path>.*)$",
            serve,
            {"document_root": settings.MEDIA_ROOT},
        ),
    ]