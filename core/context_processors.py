from .models import Pagina


def paginas_menu(request):
    paginas_personalizadas_menu = Pagina.objects.filter(
        publicado=True,
        mostrar_en_menu=True,
        pagina_padre__isnull=True,
    ).order_by("orden", "titulo")

    return {
        "paginas_personalizadas_menu": paginas_personalizadas_menu,
    }