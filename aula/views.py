from django.contrib.auth.decorators import login_required
from django.db.models import Q, Prefetch
from django.shortcuts import get_object_or_404, redirect, render
from django.http import Http404
from django.urls import reverse
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
    modulos = list(Modulo.objects.filter(curso=curso).prefetch_related(Prefetch('lecciones', queryset=lecciones)))
    completadas = set(Progreso.objects.filter(cursante=request.user, leccion__in=lecciones).values_list('leccion_id', flat=True))
    total = lecciones.filter(obligatoria=True).count()
    hechas = lecciones.filter(obligatoria=True, pk__in=completadas).count()
    ordenadas = []
    for modulo in modulos:
        modulo.clases = list(modulo.lecciones.all())
        ordenadas.extend(modulo.clases)
        obligatorias = [clase for clase in modulo.clases if clase.obligatoria]
        modulo.total_lecturas = len(obligatorias)
        modulo.lecturas_hechas = sum(clase.pk in completadas for clase in obligatorias)
        modulo.porcentaje = round(100 * modulo.lecturas_hechas / len(obligatorias)) if obligatorias else 0
    seleccion = request.GET.get('clase')
    actual = None
    if seleccion:
        actual = next((clase for clase in ordenadas if str(clase.pk) == seleccion), None)
        if actual is None:
            raise Http404
    elif ordenadas:
        actual = next((clase for clase in ordenadas if clase.pk not in completadas), ordenadas[0])
    posicion = ordenadas.index(actual) if actual else -1
    vista = request.GET.get('vista', 'contenido')
    if vista not in {'contenido', 'materiales', 'avance'}:
        vista = 'contenido'
    return render(request, 'aula/campus.html', {
        'curso': curso, 'modulos': modulos, 'completadas': completadas,
        'total': total, 'hechas': hechas, 'porcentaje': round(100 * hechas / total) if total else 0,
        'equipo': equipo,
        'actual': actual, 'vista': vista, 'cantidad_clases': len(ordenadas),
        'hay_materiales': any(clase.recursos_visibles for clase in ordenadas),
        'posicion_clase': posicion + 1,
        'anterior': ordenadas[posicion - 1] if posicion > 0 else None,
        'siguiente': ordenadas[posicion + 1] if 0 <= posicion < len(ordenadas) - 1 else None,
    })


@login_required
@require_POST
def completar(request, pk):
    leccion = get_object_or_404(Leccion, pk=pk, publicada=True, modulo__curso__publicado=True,
        modulo__curso__inscripciones__cursante=request.user, modulo__curso__inscripciones__activa=True)
    Progreso.objects.get_or_create(cursante=request.user, leccion=leccion)
    if request.POST.get('seguir') == '1':
        clases = list(Leccion.objects.filter(modulo__curso=leccion.modulo.curso, publicada=True)
                      .order_by('modulo__orden', 'modulo__pk', 'orden', 'pk').values_list('pk', flat=True))
        posicion = clases.index(leccion.pk)
        destino = f'?clase={clases[posicion + 1]}' if posicion + 1 < len(clases) else '?vista=avance'
        return redirect(reverse('aula:curso', args=[leccion.modulo.curso_id]) + destino)
    return redirect('aula:curso', pk=leccion.modulo.curso_id)
