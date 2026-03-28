from django.contrib import admin
from django.http import HttpResponse
import csv

from .models import (
    AreaPrograma,
    BloquePagina,
    ComponenteInteractivo,
    ContenidoInicio,
    EligeCamino,
    EscenaCamino,
    EtapaOrdenaPasos,
    ImagenBloquePagina,
    InteresCurso,
    Material,
    Noticia,
    OpcionEscenaCamino,
    OpcionRespuesta,
    OrdenaPasos,
    Pagina,
    PasoOrdenaPasos,
    Pregunta,
    Programa,
    ResultadoOrdenaPasos,
    ResultadoTrivia,
    RuletaDesafio,
    SectorRuleta,
    Trivia,
)


# ==================================================
# BLOQUE 1 - FUNCIÓN AUXILIAR PARA EXPORTAR CSV
# ==================================================
def exportar_intereses_a_csv(modeladmin, request, queryset):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="intereses_cursos.csv"'

    writer = csv.writer(response)
    writer.writerow(["Nombre", "Email", "Sección", "Curso de interés", "Detalle", "Fecha"])

    for item in queryset:
        writer.writerow([
            item.nombre,
            item.email,
            item.seccion,
            item.curso_interes,
            item.detalle,
            item.fecha.strftime("%d/%m/%Y %H:%M"),
        ])

    return response


exportar_intereses_a_csv.short_description = "Exportar seleccionados a CSV"


# ==================================================
# BLOQUE 2 - ADMIN DE PROGRAMAS
# ==================================================
@admin.register(Programa)
class ProgramaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "seccion")
    list_filter = ("seccion",)
    search_fields = ("nombre",)
    ordering = ("seccion", "nombre")
    fieldsets = (
        ("Datos básicos del programa", {
            "fields": ("nombre", "seccion"),
        }),
        ("Descripción del programa", {
            "fields": ("descripcion",),
        }),
    )


@admin.register(AreaPrograma)
class AreaProgramaAdmin(admin.ModelAdmin):
    list_display = ("titulo", "programa", "orden")
    list_filter = ("programa__seccion", "programa")
    search_fields = ("titulo", "programa__nombre")
    ordering = ("programa", "orden", "titulo")
    fieldsets = (
        ("Relación con programa", {
            "fields": ("programa", "orden"),
        }),
        ("Contenido del área", {
            "fields": ("titulo", "descripcion"),
        }),
    )


# ==================================================
# BLOQUE 3 - ADMIN DE MATERIALES
# ==================================================
@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = ("titulo", "seccion", "mostrar_programas")
    list_filter = ("seccion", "programas")
    search_fields = ("titulo", "descripcion")
    filter_horizontal = ("programas", "areas_programa")
    fieldsets = (
        ("Datos básicos del material", {
            "fields": ("titulo", "descripcion", "seccion", "archivo"),
        }),
        ("Relación con formación", {
            "fields": ("programas", "areas_programa"),
        }),
    )

    def mostrar_programas(self, obj):
        return ", ".join(programa.nombre for programa in obj.programas.all())

    mostrar_programas.short_description = "Programas"


# ==================================================
# BLOQUE 4 - INLINE DE OPCIONES DE RESPUESTA
# ==================================================
class OpcionRespuestaInline(admin.TabularInline):
    model = OpcionRespuesta
    extra = 1


# ==================================================
# BLOQUE 5 - INLINE DE IMÁGENES DE GALERÍA
# ==================================================
class ImagenBloquePaginaInline(admin.TabularInline):
    model = ImagenBloquePagina
    extra = 1
    fields = ("imagen", "titulo", "texto_alternativo", "orden")


# ==================================================
# BLOQUE 6 - INLINE DE BLOQUES DE PÁGINA
# ==================================================
class BloquePaginaInline(admin.StackedInline):
    model = BloquePagina
    extra = 1
    autocomplete_fields = ("componente_interactivo",)
    filter_horizontal = ("materiales",)
    fields = (
        ("tipo", "orden", "activo"),
        "titulo",
        "subtitulo",
        "contenido",
        "imagen",
        "video_url",
        "materiales",
        "componente_interactivo",
    )


# ==================================================
# BLOQUE 7 - INLINE DE ETAPAS DE ORDENA LOS PASOS
# ==================================================
class EtapaOrdenaPasosInline(admin.TabularInline):
    model = EtapaOrdenaPasos
    extra = 1
    fields = ("titulo", "orden", "tiempo_limite_segundos", "activo")


# ==================================================
# BLOQUE 8 - INLINE DE PASOS DE CADA ETAPA
# ==================================================
class PasoOrdenaPasosInline(admin.StackedInline):
    model = PasoOrdenaPasos
    extra = 1


# ==================================================
# BLOQUE 9 - INLINE DE SECTORES DE RULETA
# ==================================================
class SectorRuletaInline(admin.TabularInline):
    model = SectorRuleta
    extra = 1
    fields = ("texto", "tipo", "orden", "activo")


# ==================================================
# BLOQUE 10 - INLINE DE ESCENAS DE ELIGE EL CAMINO
# ==================================================
class EscenaCaminoInline(admin.TabularInline):
    model = EscenaCamino
    extra = 1
    fields = ("titulo", "orden", "es_inicio", "es_final", "tipo_final", "activo")


# ==================================================
# BLOQUE 11 - INLINE DE OPCIONES DE CADA ESCENA
# ==================================================
class OpcionEscenaCaminoInline(admin.TabularInline):
    model = OpcionEscenaCamino
    fk_name = "escena_origen"
    extra = 1
    autocomplete_fields = ("escena_destino",)
    fields = ("texto_opcion", "escena_destino", "orden", "activo")


# ==================================================
# BLOQUE 12 - ADMIN DE PÁGINAS
# ==================================================
@admin.register(Pagina)
class PaginaAdmin(admin.ModelAdmin):
    list_display = (
        "titulo",
        "pagina_padre",
        "orden",
        "publicado",
        "mostrar_en_menu",
        "cantidad_bloques",
    )
    list_filter = ("publicado", "mostrar_en_menu", "pagina_padre")
    search_fields = ("titulo", "slug", "contenido")
    ordering = ("orden", "titulo")
    prepopulated_fields = {"slug": ("titulo",)}
    autocomplete_fields = ("pagina_padre",)
    filter_horizontal = ("materiales",)
    inlines = [BloquePaginaInline]

    fieldsets = (
        ("Datos básicos de la página", {
            "fields": ("titulo", "slug", "contenido"),
        }),
        ("Jerarquía y relaciones", {
            "fields": ("pagina_padre", "materiales"),
        }),
        ("Presentación", {
            "fields": ("imagen_portada", "orden"),
        }),
        ("Publicación y menú", {
            "fields": ("publicado", "mostrar_en_menu"),
        }),
    )

    def cantidad_bloques(self, obj):
        return obj.bloques.count()

    cantidad_bloques.short_description = "Bloques"


# ==================================================
# BLOQUE 13 - ADMIN DE COMPONENTES INTERACTIVOS
# ==================================================
@admin.register(ComponenteInteractivo)
class ComponenteInteractivoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "slug", "alto_iframe", "publicado")
    list_filter = ("publicado",)
    search_fields = ("nombre", "slug", "descripcion", "html", "css", "javascript")
    ordering = ("nombre",)
    prepopulated_fields = {"slug": ("nombre",)}

    fieldsets = (
        ("Datos básicos del componente", {
            "fields": ("nombre", "slug", "descripcion"),
        }),
        ("Código del componente", {
            "fields": ("html", "css", "javascript"),
        }),
        ("Configuración", {
            "fields": ("alto_iframe", "publicado"),
        }),
    )


# ==================================================
# BLOQUE 14 - ADMIN DE BLOQUES DE PÁGINA
# ==================================================
@admin.register(BloquePagina)
class BloquePaginaAdmin(admin.ModelAdmin):
    list_display = (
        "titulo_admin",
        "pagina",
        "tipo",
        "orden",
        "activo",
        "componente_interactivo",
    )
    list_filter = ("tipo", "activo", "pagina")
    search_fields = (
        "titulo",
        "subtitulo",
        "contenido",
        "pagina__titulo",
        "componente_interactivo__nombre",
    )
    ordering = ("pagina", "orden", "id")
    autocomplete_fields = ("pagina", "componente_interactivo")
    filter_horizontal = ("materiales",)
    inlines = [ImagenBloquePaginaInline]

    fieldsets = (
        ("Relación con la página", {
            "fields": ("pagina", "tipo", "orden", "activo"),
        }),
        ("Contenido principal del bloque", {
            "fields": ("titulo", "subtitulo", "contenido"),
        }),
        ("Contenido complementario", {
            "fields": ("imagen", "video_url", "materiales", "componente_interactivo"),
        }),
    )

    def titulo_admin(self, obj):
        return obj.titulo or f"Bloque {obj.get_tipo_display()}"

    titulo_admin.short_description = "Bloque"


# ==================================================
# BLOQUE 15 - ADMIN DE TRIVIAS
# ==================================================
@admin.register(Trivia)
class TriviaAdmin(admin.ModelAdmin):
    list_display = (
        "titulo",
        "material_recomendado",
        "porcentaje_minimo_recomendacion",
    )
    list_filter = ("material_recomendado",)
    search_fields = (
        "titulo",
        "descripcion",
        "material_recomendado__titulo",
        "video_recomendado_url",
    )
    ordering = ("titulo",)

    fieldsets = (
        ("Datos básicos de la trivia", {
            "fields": ("titulo", "descripcion"),
        }),
        ("Recomendación posterior al resultado", {
            "fields": (
                "material_recomendado",
                "video_recomendado_url",
                "porcentaje_minimo_recomendacion",
            ),
        }),
    )


@admin.register(Pregunta)
class PreguntaAdmin(admin.ModelAdmin):
    list_display = ("texto", "trivia", "orden")
    list_filter = ("trivia",)
    search_fields = ("texto", "trivia__titulo")
    ordering = ("trivia", "orden")
    inlines = [OpcionRespuestaInline]

    fieldsets = (
        ("Datos de la pregunta", {
            "fields": ("trivia", "texto", "orden"),
        }),
    )


@admin.register(ResultadoTrivia)
class ResultadoTriviaAdmin(admin.ModelAdmin):
    list_display = (
        "nombre",
        "trivia",
        "puntaje",
        "total_preguntas",
        "porcentaje",
        "tiempo_total_segundos",
        "fecha",
    )
    list_filter = ("trivia", "fecha")
    search_fields = ("nombre", "trivia__titulo")
    ordering = ("-fecha",)
    readonly_fields = (
        "nombre",
        "trivia",
        "puntaje",
        "total_preguntas",
        "porcentaje",
        "tiempo_total_segundos",
        "fecha",
    )

    fieldsets = (
        ("Datos del participante", {
            "fields": ("nombre", "trivia"),
        }),
        ("Resultado obtenido", {
            "fields": ("puntaje", "total_preguntas", "porcentaje", "tiempo_total_segundos"),
        }),
        ("Registro", {
            "fields": ("fecha",),
        }),
    )


# ==================================================
# BLOQUE 16 - ADMIN DE TEMAS DE ORDENA LOS PASOS
# ==================================================
@admin.register(OrdenaPasos)
class OrdenaPasosAdmin(admin.ModelAdmin):
    list_display = (
        "titulo",
        "activo",
        "cantidad_etapas",
        "material_recomendado",
        "porcentaje_minimo_recomendacion",
        "fecha_creacion",
    )
    list_filter = ("activo", "fecha_creacion", "material_recomendado")
    search_fields = (
        "titulo",
        "descripcion",
        "material_recomendado__titulo",
        "video_recomendado_url",
    )
    ordering = ("titulo",)
    readonly_fields = ("fecha_creacion",)
    inlines = [EtapaOrdenaPasosInline]

    fieldsets = (
        ("Datos básicos del tema", {
            "fields": ("titulo", "descripcion"),
        }),
        ("Recomendación posterior al resultado", {
            "fields": (
                "material_recomendado",
                "video_recomendado_url",
                "porcentaje_minimo_recomendacion",
            ),
        }),
        ("Estado", {
            "fields": ("activo",),
        }),
        ("Registro", {
            "fields": ("fecha_creacion",),
        }),
    )

    def cantidad_etapas(self, obj):
        return obj.etapas.count()

    cantidad_etapas.short_description = "Cantidad de etapas"


# ==================================================
# BLOQUE 17 - ADMIN DE ETAPAS DE ORDENA LOS PASOS
# ==================================================
@admin.register(EtapaOrdenaPasos)
class EtapaOrdenaPasosAdmin(admin.ModelAdmin):
    list_display = ("titulo", "tema", "orden", "tiempo_limite_segundos", "activo", "cantidad_pasos")
    list_filter = ("tema", "activo")
    search_fields = ("titulo", "descripcion", "tema__titulo")
    ordering = ("tema", "orden", "id")
    inlines = [PasoOrdenaPasosInline]

    fieldsets = (
        ("Relación con el tema", {
            "fields": ("tema", "titulo", "orden"),
        }),
        ("Contenido de la etapa", {
            "fields": ("descripcion",),
        }),
        ("Configuración", {
            "fields": ("tiempo_limite_segundos", "activo"),
        }),
    )

    def cantidad_pasos(self, obj):
        return obj.pasos.count()

    cantidad_pasos.short_description = "Cantidad de pasos"


# ==================================================
# BLOQUE 18 - ADMIN DE PASOS DE ORDENA LOS PASOS
# ==================================================
@admin.register(PasoOrdenaPasos)
class PasoOrdenaPasosAdmin(admin.ModelAdmin):
    list_display = ("texto", "etapa", "tema", "orden_correcto")
    list_filter = ("etapa__tema", "etapa")
    search_fields = ("texto", "etapa__titulo", "etapa__tema__titulo")
    ordering = ("etapa__tema", "etapa", "orden_correcto", "id")

    fieldsets = (
        ("Relación con la etapa", {
            "fields": ("etapa", "orden_correcto"),
        }),
        ("Contenido del paso", {
            "fields": ("texto", "imagen"),
        }),
    )

    def tema(self, obj):
        return obj.etapa.tema

    tema.short_description = "Tema"


# ==================================================
# BLOQUE 19 - ADMIN DE RESULTADOS DE ORDENA LOS PASOS
# ==================================================
@admin.register(ResultadoOrdenaPasos)
class ResultadoOrdenaPasosAdmin(admin.ModelAdmin):
    list_display = (
        "nombre",
        "tema",
        "puntaje",
        "total_pasos",
        "porcentaje",
        "tiempo_total_segundos",
        "fecha",
    )
    list_filter = ("tema", "fecha")
    search_fields = ("nombre", "tema__titulo")
    ordering = ("-fecha",)
    readonly_fields = (
        "nombre",
        "tema",
        "puntaje",
        "total_pasos",
        "porcentaje",
        "tiempo_total_segundos",
        "fecha",
    )

    fieldsets = (
        ("Datos del participante", {
            "fields": ("nombre", "tema"),
        }),
        ("Resultado obtenido", {
            "fields": ("puntaje", "total_pasos", "porcentaje", "tiempo_total_segundos"),
        }),
        ("Registro", {
            "fields": ("fecha",),
        }),
    )


# ==================================================
# BLOQUE 20 - ADMIN DE RULETAS DE DESAFÍOS
# ==================================================
@admin.register(RuletaDesafio)
class RuletaDesafioAdmin(admin.ModelAdmin):
    list_display = ("titulo", "activo", "cantidad_sectores", "fecha_creacion")
    list_filter = ("activo", "fecha_creacion")
    search_fields = ("titulo", "descripcion")
    ordering = ("titulo",)
    readonly_fields = ("fecha_creacion",)
    inlines = [SectorRuletaInline]

    fieldsets = (
        ("Datos básicos de la ruleta", {
            "fields": ("titulo", "descripcion"),
        }),
        ("Estado", {
            "fields": ("activo",),
        }),
        ("Registro", {
            "fields": ("fecha_creacion",),
        }),
    )

    def cantidad_sectores(self, obj):
        return obj.sectores.count()

    cantidad_sectores.short_description = "Cantidad de sectores"


@admin.register(SectorRuleta)
class SectorRuletaAdmin(admin.ModelAdmin):
    list_display = ("texto", "ruleta", "tipo", "orden", "activo")
    list_filter = ("ruleta", "tipo", "activo")
    search_fields = ("texto", "ruleta__titulo")
    ordering = ("ruleta", "orden", "id")

    fieldsets = (
        ("Relación con la ruleta", {
            "fields": ("ruleta", "orden", "activo"),
        }),
        ("Contenido del sector", {
            "fields": ("texto", "tipo"),
        }),
    )


# ==================================================
# BLOQUE 21 - ADMIN DE ELIGE EL CAMINO
# ==================================================
@admin.register(EligeCamino)
class EligeCaminoAdmin(admin.ModelAdmin):
    list_display = ("titulo", "activo", "cantidad_escenas", "fecha_creacion")
    list_filter = ("activo", "fecha_creacion")
    search_fields = ("titulo", "descripcion")
    ordering = ("titulo",)
    readonly_fields = ("fecha_creacion",)
    inlines = [EscenaCaminoInline]

    fieldsets = (
        ("Datos básicos del juego", {
            "fields": ("titulo", "descripcion"),
        }),
        ("Estado", {
            "fields": ("activo",),
        }),
        ("Registro", {
            "fields": ("fecha_creacion",),
        }),
    )

    def cantidad_escenas(self, obj):
        return obj.escenas.count()

    cantidad_escenas.short_description = "Cantidad de escenas"


@admin.register(EscenaCamino)
class EscenaCaminoAdmin(admin.ModelAdmin):
    list_display = (
        "titulo",
        "camino",
        "orden",
        "es_inicio",
        "es_final",
        "tipo_final",
        "activo",
        "cantidad_opciones",
    )
    list_filter = ("camino", "es_inicio", "es_final", "tipo_final", "activo")
    search_fields = ("titulo", "texto", "camino__titulo")
    ordering = ("camino", "orden", "id")
    autocomplete_fields = ("material_recomendado",)
    inlines = [OpcionEscenaCaminoInline]

    fieldsets = (
        ("Relación con el juego", {
            "fields": ("camino", "titulo", "orden", "activo"),
        }),
        ("Contenido de la escena", {
            "fields": ("texto",),
        }),
        ("Tipo de escena", {
            "fields": ("es_inicio", "es_final", "tipo_final"),
        }),
        ("Recomendación para finales no buenos", {
            "fields": ("material_recomendado", "video_recomendado_url"),
        }),
    )

    def cantidad_opciones(self, obj):
        return obj.opciones.count()

    cantidad_opciones.short_description = "Opciones"


@admin.register(OpcionEscenaCamino)
class OpcionEscenaCaminoAdmin(admin.ModelAdmin):
    list_display = ("texto_opcion", "escena_origen", "camino", "escena_destino", "orden", "activo")
    list_filter = ("escena_origen__camino", "activo")
    search_fields = (
        "texto_opcion",
        "escena_origen__titulo",
        "escena_destino__titulo",
        "escena_origen__camino__titulo",
    )
    ordering = ("escena_origen__camino", "escena_origen", "orden", "id")
    autocomplete_fields = ("escena_origen", "escena_destino")

    fieldsets = (
        ("Relación entre escenas", {
            "fields": ("escena_origen", "escena_destino", "orden", "activo"),
        }),
        ("Texto de la decisión", {
            "fields": ("texto_opcion",),
        }),
    )

    def camino(self, obj):
        return obj.escena_origen.camino

    camino.short_description = "Camino"


# ==================================================
# BLOQUE 22 - ADMIN DE NOTICIAS
# ==================================================
@admin.register(Noticia)
class NoticiaAdmin(admin.ModelAdmin):
    list_display = ("titulo", "publicada", "destacada", "fecha_creacion")
    list_filter = ("publicada", "destacada", "fecha_creacion")
    search_fields = ("titulo", "resumen", "contenido")
    ordering = ("-fecha_creacion",)
    readonly_fields = ("fecha_creacion",)

    fieldsets = (
        ("Contenido principal", {
            "fields": ("titulo", "resumen", "contenido", "imagen"),
        }),
        ("Estado de publicación", {
            "fields": ("publicada", "destacada"),
        }),
        ("Registro", {
            "fields": ("fecha_creacion",),
        }),
    )


# ==================================================
# BLOQUE 23 - ADMIN DEL INICIO
# ==================================================
@admin.register(ContenidoInicio)
class ContenidoInicioAdmin(admin.ModelAdmin):
    list_display = (
        "titulo_inicio",
        "titulo_quienes_somos",
        "titulo_quiero_aprender",
        "activo",
    )
    list_filter = ("activo",)
    search_fields = (
        "titulo_inicio",
        "subtitulo_inicio",
        "titulo_quienes_somos",
        "texto_quienes_somos",
        "titulo_quiero_aprender",
        "subtitulo_quiero_aprender",
    )

    fieldsets = (
        ("Encabezado del inicio", {
            "fields": ("titulo_inicio", "subtitulo_inicio"),
        }),
        ("Bloque quiénes somos", {
            "fields": ("titulo_quienes_somos", "texto_quienes_somos", "imagen_quienes_somos"),
        }),
        ("Encabezado de Quiero aprender", {
            "fields": ("titulo_quiero_aprender", "subtitulo_quiero_aprender"),
        }),
        ("Estado del bloque", {
            "fields": ("activo",),
        }),
    )


# ==================================================
# BLOQUE 24 - ADMIN DE QUIERO APRENDER
# ==================================================
@admin.register(InteresCurso)
class InteresCursoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "curso_interes", "seccion", "email", "fecha")
    list_filter = ("seccion", "fecha")
    search_fields = ("nombre", "curso_interes", "email", "detalle")
    ordering = ("-fecha",)
    actions = [exportar_intereses_a_csv]
    readonly_fields = ("fecha",)

    fieldsets = (
        ("Datos de la persona", {
            "fields": ("nombre", "email", "seccion"),
        }),
        ("Interés formativo", {
            "fields": ("curso_interes", "detalle"),
        }),
        ("Registro", {
            "fields": ("fecha",),
        }),
    )