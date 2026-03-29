from django.db import models
from django_ckeditor_5.fields import CKEditor5Field


# ==================================================
# BLOQUE 1 - MODELO DE PROGRAMAS
# ==================================================
class Programa(models.Model):
    SECCIONES_PROGRAMA = [
        ("menor", "Sección Menor"),
        ("media", "Sección Media"),
        ("intermedia", "Sección Intermedia"),
        ("mayor", "Sección Mayor"),
        ("dirigentes", "Formación de Dirigentes"),
    ]

    nombre = models.CharField(max_length=200)
    descripcion = CKEditor5Field("Descripción", config_name="extends")
    seccion = models.CharField(max_length=20, choices=SECCIONES_PROGRAMA)

    class Meta:
        ordering = ["seccion", "nombre"]
        verbose_name = "Programa"
        verbose_name_plural = "Programas"

    def __str__(self):
        return self.nombre


# ==================================================
# BLOQUE 2 - MODELO DE ÁREAS DE PROGRAMA
# ==================================================
class AreaPrograma(models.Model):
    programa = models.ForeignKey(
        Programa,
        on_delete=models.CASCADE,
        related_name="areas",
    )
    titulo = models.CharField(max_length=200)
    descripcion = CKEditor5Field("Descripción", config_name="extends", blank=True)
    orden = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["orden", "id"]
        verbose_name = "Área de programa"
        verbose_name_plural = "Áreas de programa"

    def __str__(self):
        return f"{self.programa.nombre} - {self.titulo}"


# ==================================================
# BLOQUE 3 - MODELO DE CATEGORÍAS DE BIBLIOTECA
# ==================================================
class CategoriaBiblioteca(models.Model):
    nombre = models.CharField(max_length=200)

    padre = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="subcategorias",
        verbose_name="Categoría padre",
    )

    orden = models.PositiveIntegerField(default=1)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["orden", "nombre", "id"]
        verbose_name = "Categoría de biblioteca"
        verbose_name_plural = "Categorías de biblioteca"

    def __str__(self):
        if self.padre:
            return f"{self.padre.nombre} > {self.nombre}"
        return self.nombre


# ==================================================
# BLOQUE 4 - MODELO DE MATERIALES
# ==================================================
class Material(models.Model):
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    archivo = models.FileField(upload_to="materiales/", null=True, blank=True)

    mostrar_en_biblioteca = models.BooleanField(
        default=True,
        verbose_name="Mostrar en biblioteca",
    )

    categoria_biblioteca = models.ForeignKey(
        CategoriaBiblioteca,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="materiales",
        verbose_name="Categoría de biblioteca",
    )

    programas = models.ManyToManyField(Programa, blank=True)
    areas_programa = models.ManyToManyField(AreaPrograma, blank=True)

    class Meta:
        ordering = ["titulo"]
        verbose_name = "Material"
        verbose_name_plural = "Materiales"

    def __str__(self):
        return self.titulo


# ==================================================
# BLOQUE 5 - MODELO DE PÁGINAS
# ==================================================
class Pagina(models.Model):
    titulo = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    contenido = CKEditor5Field("Contenido", config_name="extends", blank=True)

    pagina_padre = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="subpaginas",
        verbose_name="Página padre",
    )

    materiales = models.ManyToManyField(
        Material,
        blank=True,
        related_name="paginas",
    )

    imagen_portada = models.ImageField(
        upload_to="paginas/",
        blank=True,
        null=True,
    )

    orden = models.PositiveIntegerField(default=1)
    publicado = models.BooleanField(default=True)
    mostrar_en_menu = models.BooleanField(default=False)

    class Meta:
        ordering = ["orden", "titulo"]
        verbose_name = "Página"
        verbose_name_plural = "Páginas"

    def __str__(self):
        return self.titulo


# ==================================================
# BLOQUE 6 - MODELO DE COMPONENTES INTERACTIVOS
# ==================================================
class ComponenteInteractivo(models.Model):
    nombre = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    descripcion = models.TextField(blank=True)

    html = models.TextField(blank=True)
    css = models.TextField(blank=True)
    javascript = models.TextField(blank=True)

    alto_iframe = models.PositiveIntegerField(default=500)
    publicado = models.BooleanField(default=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "Componente interactivo"
        verbose_name_plural = "Componentes interactivos"

    def __str__(self):
        return self.nombre


# ==================================================
# BLOQUE 7 - MODELO DE BLOQUES DE PÁGINA
# ==================================================
class BloquePagina(models.Model):
    TIPOS_BLOQUE = [
        ("titulo", "Título"),
        ("texto", "Texto"),
        ("imagen", "Imagen"),
        ("galeria", "Galería"),
        ("video", "Video"),
        ("materiales", "Materiales"),
        ("separador", "Separador"),
        ("interactivo", "Interactivo"),
    ]

    pagina = models.ForeignKey(
        Pagina,
        on_delete=models.CASCADE,
        related_name="bloques",
    )
    tipo = models.CharField(max_length=20, choices=TIPOS_BLOQUE)
    titulo = models.CharField(max_length=200, blank=True)
    subtitulo = models.CharField(max_length=250, blank=True)
    contenido = CKEditor5Field("Contenido del bloque", config_name="extends", blank=True)

    imagen = models.ImageField(
        upload_to="bloques_pagina/",
        blank=True,
        null=True,
    )
    video_url = models.URLField(blank=True)

    materiales = models.ManyToManyField(
        Material,
        blank=True,
        related_name="bloques_pagina",
    )

    componente_interactivo = models.ForeignKey(
        ComponenteInteractivo,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bloques_usados",
    )

    orden = models.PositiveIntegerField(default=1)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["orden", "id"]
        verbose_name = "Bloque de página"
        verbose_name_plural = "Bloques de página"

    def __str__(self):
        return f"{self.pagina.titulo} - {self.get_tipo_display()} ({self.orden})"


# ==================================================
# BLOQUE 8 - MODELO DE IMÁGENES DE GALERÍA
# ==================================================
class ImagenBloquePagina(models.Model):
    bloque = models.ForeignKey(
        BloquePagina,
        on_delete=models.CASCADE,
        related_name="imagenes_galeria",
    )
    imagen = models.ImageField(upload_to="bloques_galeria/")
    titulo = models.CharField(max_length=200, blank=True)
    texto_alternativo = models.CharField(max_length=200, blank=True)
    orden = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["orden", "id"]
        verbose_name = "Imagen de galería"
        verbose_name_plural = "Imágenes de galería"

    def __str__(self):
        return f"{self.bloque.pagina.titulo} - Imagen {self.orden}"


# ==================================================
# BLOQUE 9 - MODELO DE TRIVIAS
# ==================================================
class Trivia(models.Model):
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)

    material_recomendado = models.ForeignKey(
        Material,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="trivias_recomendadas",
    )
    video_recomendado_url = models.URLField(blank=True)
    porcentaje_minimo_recomendacion = models.PositiveIntegerField(default=60)

    class Meta:
        ordering = ["titulo"]
        verbose_name = "Trivia"
        verbose_name_plural = "Trivias"

    def __str__(self):
        return self.titulo


# ==================================================
# BLOQUE 10 - MODELO DE PREGUNTAS
# ==================================================
class Pregunta(models.Model):
    trivia = models.ForeignKey(
        Trivia,
        on_delete=models.CASCADE,
        related_name="preguntas",
    )
    texto = models.TextField()
    orden = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["orden", "id"]
        verbose_name = "Pregunta"
        verbose_name_plural = "Preguntas"

    def __str__(self):
        return f"{self.trivia.titulo} - Pregunta {self.orden}"


# ==================================================
# BLOQUE 11 - MODELO DE OPCIONES DE RESPUESTA
# ==================================================
class OpcionRespuesta(models.Model):
    pregunta = models.ForeignKey(
        Pregunta,
        on_delete=models.CASCADE,
        related_name="opciones",
    )
    texto = models.CharField(max_length=300)
    es_correcta = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Opción de respuesta"
        verbose_name_plural = "Opciones de respuesta"

    def __str__(self):
        return self.texto


# ==================================================
# BLOQUE 12 - MODELO DE RESULTADOS DE TRIVIA
# ==================================================
class ResultadoTrivia(models.Model):
    trivia = models.ForeignKey(
        Trivia,
        on_delete=models.CASCADE,
        related_name="resultados",
    )
    nombre = models.CharField(max_length=100)
    puntaje = models.PositiveIntegerField()
    total_preguntas = models.PositiveIntegerField()
    porcentaje = models.PositiveIntegerField()
    tiempo_total_segundos = models.PositiveIntegerField(default=0)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-porcentaje", "-puntaje", "tiempo_total_segundos", "fecha"]
        verbose_name = "Resultado de trivia"
        verbose_name_plural = "Resultados de trivia"

    def __str__(self):
        return f"{self.nombre} - {self.trivia.titulo} ({self.porcentaje}%)"


# ==================================================
# BLOQUE 13 - MODELO DE TEMAS DE ORDENA LOS PASOS
# ==================================================
class OrdenaPasos(models.Model):
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)

    material_recomendado = models.ForeignKey(
        Material,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="temas_ordena_pasos",
    )
    video_recomendado_url = models.URLField(blank=True)
    porcentaje_minimo_recomendacion = models.PositiveIntegerField(default=60)

    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["titulo"]
        verbose_name = "Tema de ordena los pasos"
        verbose_name_plural = "Temas de ordena los pasos"

    def __str__(self):
        return self.titulo


# ==================================================
# BLOQUE 14 - MODELO DE ETAPAS DEL TEMA
# ==================================================
class EtapaOrdenaPasos(models.Model):
    tema = models.ForeignKey(
        OrdenaPasos,
        on_delete=models.CASCADE,
        related_name="etapas",
    )
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    orden = models.PositiveIntegerField(default=1)
    tiempo_limite_segundos = models.PositiveIntegerField(default=60)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["orden", "id"]
        verbose_name = "Etapa de ordena los pasos"
        verbose_name_plural = "Etapas de ordena los pasos"

    def __str__(self):
        return f"{self.tema.titulo} - {self.titulo}"


# ==================================================
# BLOQUE 15 - MODELO DE PASOS DE CADA ETAPA
# ==================================================
class PasoOrdenaPasos(models.Model):
    etapa = models.ForeignKey(
        EtapaOrdenaPasos,
        on_delete=models.CASCADE,
        related_name="pasos",
    )
    texto = models.CharField(max_length=300)
    imagen = models.ImageField(
        upload_to="ordena_pasos/",
        blank=True,
        null=True,
    )
    orden_correcto = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["orden_correcto", "id"]
        verbose_name = "Paso de ordena los pasos"
        verbose_name_plural = "Pasos de ordena los pasos"

    def __str__(self):
        return f"{self.etapa.titulo} - Paso {self.orden_correcto}"


# ==================================================
# BLOQUE 16 - MODELO DE RESULTADOS POR TEMA
# ==================================================
class ResultadoOrdenaPasos(models.Model):
    tema = models.ForeignKey(
        OrdenaPasos,
        on_delete=models.CASCADE,
        related_name="resultados",
    )
    nombre = models.CharField(max_length=100)
    puntaje = models.PositiveIntegerField()
    total_pasos = models.PositiveIntegerField()
    porcentaje = models.PositiveIntegerField()
    tiempo_total_segundos = models.PositiveIntegerField(default=0)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-porcentaje", "-puntaje", "tiempo_total_segundos", "fecha"]
        verbose_name = "Resultado de ordena los pasos"
        verbose_name_plural = "Resultados de ordena los pasos"

    def __str__(self):
        return f"{self.nombre} - {self.tema.titulo} ({self.porcentaje}%)"


# ==================================================
# BLOQUE 17 - MODELO DE RULETAS DE DESAFÍOS
# ==================================================
class RuletaDesafio(models.Model):
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["titulo"]
        verbose_name = "Ruleta de desafío"
        verbose_name_plural = "Ruletas de desafíos"

    def __str__(self):
        return self.titulo


# ==================================================
# BLOQUE 18 - MODELO DE SECTORES DE RULETA
# ==================================================
class SectorRuleta(models.Model):
    TIPOS_SECTOR = [
        ("prenda_castigo", "Prenda o castigo"),
        ("buena_accion", "Buena acción diaria"),
    ]

    ruleta = models.ForeignKey(
        RuletaDesafio,
        on_delete=models.CASCADE,
        related_name="sectores",
    )
    texto = models.CharField(max_length=300)
    tipo = models.CharField(max_length=20, choices=TIPOS_SECTOR, default="prenda_castigo")
    orden = models.PositiveIntegerField(default=1)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["orden", "id"]
        verbose_name = "Sector de ruleta"
        verbose_name_plural = "Sectores de ruleta"

    def __str__(self):
        return f"{self.ruleta.titulo} - Sector {self.orden}"


# ==================================================
# BLOQUE 19 - MODELO DE JUEGOS ELIGE EL CAMINO
# ==================================================
class EligeCamino(models.Model):
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["titulo"]
        verbose_name = "Juego elige el camino"
        verbose_name_plural = "Juegos elige el camino"

    def __str__(self):
        return self.titulo


# ==================================================
# BLOQUE 20 - MODELO DE ESCENAS DEL CAMINO
# ==================================================
class EscenaCamino(models.Model):
    TIPOS_FINAL = [
        ("bueno", "Bueno"),
        ("neutro", "Neutro"),
        ("malo", "Malo"),
    ]

    camino = models.ForeignKey(
        EligeCamino,
        on_delete=models.CASCADE,
        related_name="escenas",
    )
    titulo = models.CharField(max_length=200)
    texto = models.TextField()
    orden = models.PositiveIntegerField(default=1)
    es_inicio = models.BooleanField(default=False)
    es_final = models.BooleanField(default=False)
    tipo_final = models.CharField(max_length=10, choices=TIPOS_FINAL, blank=True)

    material_recomendado = models.ForeignKey(
        Material,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="escenas_camino_recomendadas",
    )
    video_recomendado_url = models.URLField(blank=True)

    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["orden", "id"]
        verbose_name = "Escena de camino"
        verbose_name_plural = "Escenas de camino"

    def __str__(self):
        return f"{self.camino.titulo} - {self.titulo}"


# ==================================================
# BLOQUE 21 - MODELO DE OPCIONES DE CADA ESCENA
# ==================================================
class OpcionEscenaCamino(models.Model):
    escena_origen = models.ForeignKey(
        EscenaCamino,
        on_delete=models.CASCADE,
        related_name="opciones",
    )
    texto_opcion = models.CharField(max_length=300)
    escena_destino = models.ForeignKey(
        EscenaCamino,
        on_delete=models.CASCADE,
        related_name="opciones_que_llegan",
    )
    orden = models.PositiveIntegerField(default=1)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["orden", "id"]
        verbose_name = "Opción de escena"
        verbose_name_plural = "Opciones de escena"

    def __str__(self):
        return f"{self.escena_origen.titulo} -> {self.texto_opcion}"


# ==================================================
# BLOQUE 22 - MODELO DE NOTICIAS
# ==================================================
class Noticia(models.Model):
    titulo = models.CharField(max_length=200)
    resumen = models.TextField()
    contenido = CKEditor5Field("Contenido", config_name="default")
    imagen = models.ImageField(upload_to="noticias/", blank=True, null=True)
    publicada = models.BooleanField(default=True)
    destacada = models.BooleanField(default=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha_creacion"]
        verbose_name = "Noticia"
        verbose_name_plural = "Noticias"

    def __str__(self):
        return self.titulo


# ==================================================
# BLOQUE 23 - MODELO DE CONTENIDO DEL INICIO
# ==================================================
class ContenidoInicio(models.Model):
    titulo_inicio = models.CharField(
        max_length=200,
        default="Escuela de Formación Scout",
    )
    subtitulo_inicio = models.TextField(
        default="Plataforma de formación y crecimiento scout",
    )

    titulo_quienes_somos = models.CharField(
        max_length=200,
        default="Quiénes somos",
    )
    texto_quienes_somos = CKEditor5Field(
        "Texto quiénes somos",
        config_name="default",
    )
    imagen_quienes_somos = models.ImageField(
        upload_to="inicio/",
        blank=True,
        null=True,
    )

    titulo_quiero_aprender = models.CharField(
        max_length=200,
        default="Quiero aprender",
    )
    subtitulo_quiero_aprender = models.TextField(
        default="Este espacio permite proponer cursos, talleres o temas de formación que te gustaría realizar. La idea es conocer mejor los intereses de la comunidad y organizar propuestas útiles y concretas.",
    )

    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Contenido de inicio"
        verbose_name_plural = "Contenido de inicio"

    def __str__(self):
        return "Contenido principal del inicio"


# ==================================================
# BLOQUE 24 - MODELO DE INTERÉS EN CURSOS
# ==================================================
class InteresCurso(models.Model):
    nombre = models.CharField(max_length=150)
    email = models.EmailField(blank=True, null=True)
    seccion = models.CharField(max_length=100, blank=True)
    curso_interes = models.CharField(max_length=200)
    detalle = models.TextField(blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha"]
        verbose_name = "Interés en curso"
        verbose_name_plural = "Intereses en cursos"

    def __str__(self):
        return f"{self.nombre} - {self.curso_interes}"