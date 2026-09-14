from django.conf import settings
from django.db import models
from django.utils.html import linebreaks
from django.utils.safestring import mark_safe
from uuid import uuid4
from .almacenamiento import privado, ruta_archivo
from .contenido import limpiar_html, youtube_embed


class Curso(models.Model):
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    publicado = models.BooleanField(default=False)
    formadores = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name='cursos_asignados')
    certificacion_configurada = models.BooleanField(default=False)
    requiere_acta = models.BooleanField(default=False)
    referencia_formacion = models.CharField(max_length=200, blank=True)
    fecha_inicio = models.DateField(null=True, blank=True)
    fecha_fin = models.DateField(null=True, blank=True)
    horas = models.PositiveIntegerField(null=True, blank=True)
    responsable_certificados = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return self.titulo


class Inscripcion(models.Model):
    curso = models.ForeignKey(Curso, on_delete=models.PROTECT, related_name='inscripciones')
    cursante = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='inscripciones_aula')
    tutor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name='tutorias_aula', help_text='EDiFoS verifica la acreditación Scouter/Maestro Scout y el acuerdo del Jefe de Grupo.')
    activa = models.BooleanField(default=True)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['curso', 'cursante'], name='aula_inscripcion_unica')]

    def __str__(self):
        return f'{self.cursante} — {self.curso}'


class Modulo(models.Model):
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE, related_name='modulos')
    titulo = models.CharField(max_length=200)
    orden = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['orden', 'pk']

    def __str__(self):
        return f'{self.curso}: {self.titulo}'


class Leccion(models.Model):
    modulo = models.ForeignKey(Modulo, on_delete=models.CASCADE, related_name='lecciones')
    titulo = models.CharField(max_length=200)
    texto = models.TextField(blank=True)
    texto_enriquecido = models.BooleanField(default=False, editable=False)
    video_url = models.URLField(blank=True, help_text='Enlace HTTPS al video educativo.')
    orden = models.PositiveIntegerField(default=0)
    publicada = models.BooleanField(default=False)
    obligatoria = models.BooleanField(default=True)

    class Meta:
        ordering = ['orden', 'pk']

    def __str__(self):
        return self.titulo


    @property
    def contenido_html(self):
        return mark_safe(limpiar_html(self.texto) if self.texto_enriquecido else linebreaks(self.texto, autoescape=True))

    @property
    def video_embed(self):
        return youtube_embed(self.video_url)


class RecursoLeccion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    leccion = models.ForeignKey(Leccion, on_delete=models.CASCADE, related_name='recursos')
    nombre = models.CharField(max_length=255)
    tipo = models.CharField(max_length=12, choices=[('documento', 'Documento'), ('video', 'Video'), ('imagen', 'Imagen')])
    archivo = models.FileField(storage=privado, upload_to=ruta_archivo)
    vista_pdf = models.FileField(storage=privado, upload_to=ruta_archivo, blank=True)
    mime = models.CharField(max_length=100)
    orden = models.PositiveIntegerField(default=0)
    activo = models.BooleanField(default=True)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['orden', 'creado']

    def __str__(self):
        return self.nombre


class Progreso(models.Model):
    cursante = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    leccion = models.ForeignKey(Leccion, on_delete=models.CASCADE)
    completada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['cursante', 'leccion'], name='aula_progreso_unico')]


TIPOS_PRUEBA = [('trivia', 'Trivia / quiz'), ('ordenar', 'Ordenar pasos'),
    ('memoria', 'Relacionar parejas'), ('palabra', 'Palabra secreta'),
    ('camino', 'Elegir un camino'), ('ruleta', 'Ruleta de retos'), ('rompecabezas', 'Rompecabezas')]


class Prueba(models.Model):
    leccion = models.OneToOneField(Leccion, on_delete=models.PROTECT, related_name='prueba')
    tipo = models.CharField(max_length=20, choices=TIPOS_PRUEBA)
    instrucciones = models.TextField(blank=True)
    minimo = models.PositiveIntegerField(default=70)
    max_intentos = models.PositiveIntegerField(default=3)
    obligatoria = models.BooleanField(default=True)
    origen = models.CharField(max_length=250, blank=True)
    revision = models.PositiveIntegerField(default=1)
    contenido = models.JSONField(default=dict)

    def __str__(self):
        return self.leccion.titulo


class ItemPrueba(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    prueba = models.ForeignKey(Prueba, on_delete=models.CASCADE, related_name='items')
    texto = models.TextField()
    opciones = models.JSONField(default=list)
    respuesta = models.TextField(blank=True)
    orden = models.PositiveIntegerField(default=1)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['orden', 'id']


class IntentoPrueba(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    prueba = models.ForeignKey(Prueba, on_delete=models.PROTECT, related_name='intentos')
    cursante = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    numero = models.PositiveIntegerField()
    revision = models.PositiveIntegerField()
    estructura = models.JSONField()
    respuestas = models.JSONField(default=dict)
    estado = models.CharField(max_length=16, default='abierto', choices=[('abierto','En curso'),('pendiente','Por corregir'),('corregido','Corregido')])
    puntaje = models.PositiveIntegerField(null=True)
    minimo = models.PositiveIntegerField()
    aprobado = models.BooleanField(default=False)
    iniciado = models.DateTimeField(auto_now_add=True)
    entregado = models.DateTimeField(null=True)

    class Meta:
        ordering = ['-iniciado']
        constraints = [models.UniqueConstraint(fields=['prueba','cursante','numero'], name='aula_intento_numero_unico')]


class CorreccionPrueba(models.Model):
    intento = models.ForeignKey(IntentoPrueba, on_delete=models.PROTECT, related_name='correcciones')
    responsable = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    puntaje = models.PositiveIntegerField()
    devolucion = models.TextField()
    fecha = models.DateTimeField(auto_now_add=True)


class CierreCurso(models.Model):
    inscripcion = models.OneToOneField(Inscripcion, on_delete=models.PROTECT, related_name='cierre')
    nombre_certificado = models.CharField(max_length=200)
    participacion_validada = models.BooleanField(default=False)
    requisitos_validados = models.BooleanField(default=False)
    aprobado = models.BooleanField(default=False)
    observaciones = models.TextField(blank=True)
    libro = models.CharField(max_length=100, blank=True)
    acta = models.CharField(max_length=100, blank=True)
    folio = models.CharField(max_length=100, blank=True)
    fecha_acta = models.DateField(null=True, blank=True)
    responsable = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    actualizado = models.DateTimeField(auto_now=True)


class MovimientoAcademico(models.Model):
    cierre = models.ForeignKey(CierreCurso, on_delete=models.PROTECT, related_name='historial')
    responsable = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    datos = models.JSONField()
    fecha = models.DateTimeField(auto_now_add=True)


class Certificado(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    inscripcion = models.ForeignKey(Inscripcion, on_delete=models.PROTECT, related_name='certificados')
    tipo = models.CharField(max_length=20, choices=[('participacion','Participación'),('aprobacion','Participación y aprobación')])
    datos = models.JSONField()
    emitido = models.DateTimeField(auto_now_add=True)
    responsable = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    revocado = models.BooleanField(default=False)
    motivo_revocacion = models.TextField(blank=True)
    fecha_revocacion = models.DateTimeField(null=True)
    revocado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT, related_name='certificados_revocados')
