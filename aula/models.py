from django.conf import settings
from django.db import models
from django.utils.html import linebreaks, strip_tags
from html import unescape
from django.utils.safestring import mark_safe
from uuid import uuid4
from .almacenamiento import privado, ruta_archivo
from .contenido import limpiar_html, youtube_embed


def ruta_foto(instance, filename):
    return f'perfiles/{uuid4().hex}.jpg'


class Perfil(models.Model):
    AVATARES = [('', 'Mi foto o mis iniciales'), ('brujula', '🧭 Brújula'),
                ('carpa', '⛺ Carpa'), ('montana', '🏔️ Montaña'), ('arbol', '🌳 Árbol'),
                ('fogata', '🔥 Fogata'), ('estrella', '⭐ Estrella'), ('lobo', '🐺 Lobo')]
    avatar = models.CharField('Elegir avatar', max_length=20, choices=AVATARES, blank=True)
    compartir_foto = models.BooleanField('Mostrar mi foto a los compañeros y formadores de mis cursos', default=False)
    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='perfil_aula')
    dni = models.CharField('DNI', max_length=16, blank=True)
    fecha_nacimiento = models.DateField('Fecha de nacimiento', null=True, blank=True)
    direccion = models.CharField('Dirección', max_length=250, blank=True)
    localidad = models.CharField('Localidad', max_length=150, blank=True)
    codigo_postal = models.CharField('Código postal', max_length=20, blank=True)
    telefono = models.CharField('Teléfono', max_length=40, blank=True)
    estado_civil = models.CharField('Estado civil', max_length=80, blank=True)
    cantidad_hijos = models.PositiveSmallIntegerField('Cantidad de hijos', null=True, blank=True)
    profesion = models.CharField('Profesión / trabajo', max_length=200, blank=True)
    asociacion = models.CharField('Asociación', max_length=200, blank=True)
    grupo = models.CharField('Grupo al que pertenecés', max_length=200, blank=True)
    fecha_ingreso_grupo = models.DateField('Fecha de ingreso al grupo', null=True, blank=True)
    fecha_ingreso_movimiento = models.DateField('Fecha de ingreso al Movimiento Scout', null=True, blank=True)
    sacramentos = models.CharField('Sacramentos', max_length=250, blank=True)
    fecha_promesa = models.DateField('Fecha de promesa', null=True, blank=True)
    cargo = models.CharField('Cargo que desempeñás', max_length=200, blank=True)
    actualizado = models.DateTimeField(auto_now=True)
    foto = models.ImageField('Foto de perfil', storage=privado, upload_to=ruta_foto, blank=True)
    cambiar_clave = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'perfil privado'
        verbose_name_plural = 'perfiles privados'

    @property
    def edad(self):
        from django.utils import timezone
        if not self.fecha_nacimiento:
            return None
        hoy = timezone.localdate()
        return hoy.year - self.fecha_nacimiento.year - ((hoy.month, hoy.day) < (self.fecha_nacimiento.month, self.fecha_nacimiento.day))

    def __str__(self):
        return self.usuario.get_full_name() or self.usuario.username


def ruta_plantilla(instance, filename):
    from pathlib import Path
    return f'certificados/plantillas/{uuid4().hex}{Path(filename).suffix.lower()}'


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


class AccesoCurso(models.Model):
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE, related_name='accesos')
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='accesos_aula')
    habilitado = models.BooleanField(default=True)
    dias = models.PositiveSmallIntegerField('Días desde el primer ingreso', null=True, blank=True)
    inicio = models.DateTimeField('Inicio del acceso', null=True, blank=True)
    fin = models.DateTimeField('Fin del acceso', null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['curso', 'usuario'], name='aula_acceso_unico')]
        verbose_name = 'acceso al curso'
        verbose_name_plural = 'accesos por fechas'

    @property
    def vigente(self):
        from django.utils import timezone
        ahora = timezone.now()
        return self.habilitado and (not self.inicio or self.inicio <= ahora) and (not self.fin or ahora < self.fin)

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.dias is not None and not 1 <= self.dias <= 3650:
            raise ValidationError({'dias': 'Indicá entre 1 y 3650 días, o dejá vacío para acceso sin límite.'})
        if self.inicio and self.fin and self.fin <= self.inicio:
            raise ValidationError({'fin': 'El fin debe ser posterior al inicio.'})

    def __str__(self):
        return f'{self.usuario} — {self.curso}'


class Modulo(models.Model):
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE, related_name='modulos')
    titulo = models.CharField(max_length=200)
    orden = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['orden', 'pk']

    def __str__(self):
        return f'{self.curso}: {self.titulo}'


class ClasesVigentes(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(eliminada=False)


class Leccion(models.Model):
    objects = ClasesVigentes()
    todas = models.Manager()
    modulo = models.ForeignKey(Modulo, on_delete=models.CASCADE, related_name='lecciones')
    titulo = models.CharField(max_length=200)
    texto = models.TextField(blank=True)
    texto_enriquecido = models.BooleanField(default=False, editable=False)
    video_url = models.URLField(blank=True, help_text='Enlace HTTPS al video educativo.')
    orden = models.PositiveIntegerField(default=0)
    publicada = models.BooleanField(default=False)
    obligatoria = models.BooleanField(default=True)
    eliminada = models.BooleanField(default=False, editable=False)

    class Meta:
        ordering = ['orden', 'pk']

    def __str__(self):
        return self.titulo


    @property
    def contenido_html(self):
        contenido = limpiar_html(self.texto) if self.texto_enriquecido else linebreaks(self.texto, autoescape=True)
        # Empty editor paragraphs should not push attached presentations down.
        # Keep deliberate tables/rules and leave the saved author content intact.
        if not unescape(strip_tags(contenido)).strip() and not any(tag in contenido for tag in ('<table', '<hr')):
            return ''
        return mark_safe(contenido)

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
    explicacion = models.TextField(blank=True)
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


class PermisoFormador(models.Model):
    curso = models.ForeignKey(Curso,on_delete=models.CASCADE)
    formador = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE)
    responder_foro = models.BooleanField('Participar en el foro',default=True)
    moderar_foro = models.BooleanField('Moderar el foro',default=False)
    ver_seguimiento = models.BooleanField('Ver seguimiento de cursantes',default=True)
    corregir = models.BooleanField('Corregir evaluaciones',default=True)
    validar = models.BooleanField('Validar aprobación y registrar actas',default=False)
    emitir = models.BooleanField('Emitir, descargar y revocar certificados',default=False)
    disenar = models.BooleanField('Editar plantillas de certificados',default=False)

    class Meta:
        constraints=[models.UniqueConstraint(fields=['curso','formador'],name='aula_permiso_formador_unico')]
        verbose_name='permisos de un formador'
        verbose_name_plural='permisos de formadores por curso'

    def __str__(self):
        return f'{self.formador} — {self.curso}'

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.curso_id and self.formador_id and not self.curso.formadores.filter(pk=self.formador_id).exists():
            raise ValidationError('Primero asigná esta persona como formador del curso.')


class TemaForo(models.Model):
    curso=models.ForeignKey(Curso,on_delete=models.PROTECT,related_name='temas_foro')
    autor=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    titulo=models.CharField(max_length=160)
    texto=models.TextField()
    creado=models.DateTimeField(auto_now_add=True)
    actualizado=models.DateTimeField(auto_now_add=True)
    resuelto=models.BooleanField(default=False)
    cerrado=models.BooleanField(default=False)
    oculto=models.BooleanField(default=False)

    class Meta:
        ordering=['-actualizado','-pk']


class RespuestaForo(models.Model):
    tema=models.ForeignKey(TemaForo,on_delete=models.PROTECT,related_name='respuestas')
    autor=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    texto=models.TextField()
    creado=models.DateTimeField(auto_now_add=True)
    oculto=models.BooleanField(default=False)

    class Meta:
        ordering=['creado','pk']


class DisenoCertificado(models.Model):
    curso=models.ForeignKey(Curso,on_delete=models.PROTECT)
    tipo=models.CharField(max_length=20,choices=Certificado._meta.get_field('tipo').choices)
    activo=models.BooleanField(default=True)
    fondo=models.FileField(storage=privado,upload_to=ruta_plantilla,blank=True)
    configuracion=models.JSONField(default=dict)
    actualizado=models.DateTimeField(auto_now=True)

    class Meta:
        constraints=[models.UniqueConstraint(fields=['curso','tipo'],name='aula_diseno_certificado_unico')]
