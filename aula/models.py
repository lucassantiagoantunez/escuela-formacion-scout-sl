from django.conf import settings
from django.db import models


class Curso(models.Model):
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    publicado = models.BooleanField(default=False)
    formadores = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name='cursos_asignados')

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
    video_url = models.URLField(blank=True, help_text='Enlace HTTPS al video educativo.')
    orden = models.PositiveIntegerField(default=0)
    publicada = models.BooleanField(default=False)
    obligatoria = models.BooleanField(default=True)

    class Meta:
        ordering = ['orden', 'pk']

    def __str__(self):
        return self.titulo


class Progreso(models.Model):
    cursante = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    leccion = models.ForeignKey(Leccion, on_delete=models.CASCADE)
    completada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['cursante', 'leccion'], name='aula_progreso_unico')]
