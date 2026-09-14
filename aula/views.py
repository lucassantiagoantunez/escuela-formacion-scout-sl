from django.contrib.auth.decorators import login_required
from django.db.models import Q, Prefetch
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import Curso, Leccion, Modulo, Progreso, RecursoLeccion


def cursos_permitidos(user):
    if user.is_superuser:
        return Curso.objects.all()
    return Curso.objects.filter(
        Q(formadores=user) | Q(publicado=True, inscripciones__cursante=user, inscripciones__activa=True)
    ).distinct()


@login_required
def panel(request):
    cursos = cursos_permitidos(request.user)
    # Mostrar solo la inscripción propia, sin abrir contenidos en preparación.
    pendientes = Curso.objects.filter(
        publicado=False, inscripciones__cursante=request.user, inscripciones__activa=True,
    ).exclude(pk__in=cursos).only('pk', 'titulo').distinct()
    return render(request, 'aula/panel.html', {'cursos': cursos, 'pendientes': pendientes})


@login_required
def curso(request, pk):
    curso = get_object_or_404(cursos_permitidos(request.user), pk=pk)
    equipo = request.user.is_superuser or curso.formadores.filter(pk=request.user.pk).exists()
    lecciones = Leccion.objects.filter(modulo__curso=curso).prefetch_related(
        Prefetch('recursos', queryset=RecursoLeccion.objects.filter(activo=True), to_attr='recursos_visibles'))
    if not equipo:
        lecciones = lecciones.filter(publicada=True)
    modulos = Modulo.objects.filter(curso=curso).prefetch_related(Prefetch('lecciones', queryset=lecciones))
    completadas = set(Progreso.objects.filter(cursante=request.user, leccion__in=lecciones).values_list('leccion_id', flat=True))
    total = lecciones.filter(obligatoria=True).count()
    hechas = lecciones.filter(obligatoria=True, pk__in=completadas).count()
    return render(request, 'aula/curso.html', {
        'curso': curso, 'modulos': modulos, 'completadas': completadas,
        'total': total, 'hechas': hechas, 'porcentaje': round(100 * hechas / total) if total else 0,
        'equipo': equipo,
    })


@login_required
@require_POST
def completar(request, pk):
    leccion = get_object_or_404(Leccion, pk=pk, publicada=True, modulo__curso__publicado=True,
        modulo__curso__inscripciones__cursante=request.user, modulo__curso__inscripciones__activa=True)
    Progreso.objects.get_or_create(cursante=request.user, leccion=leccion)
    return redirect('aula:curso', pk=leccion.modulo.curso_id)
