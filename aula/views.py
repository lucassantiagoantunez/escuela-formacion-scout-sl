from django.contrib.auth.decorators import login_required
from django.db.models import Q, Prefetch
from django.shortcuts import get_object_or_404, redirect, render
from django.http import Http404
from django.urls import reverse
from django.views.decorators.http import require_POST

from .models import Curso, Leccion, Modulo, Progreso, RecursoLeccion, Prueba, IntentoPrueba, Inscripcion, Certificado
from .pruebas_motor import escena_actual, devolucion_automatica
from .permisos import puede_seguimiento


def cursos_permitidos(user):
    from .accesos import bloqueados
    if user.is_superuser:
        return Curso.objects.all()
    return Curso.objects.filter(
        Q(formadores=user) | Q(publicado=True, inscripciones__cursante=user, inscripciones__activa=True)
    ).exclude(pk__in=bloqueados(user)).distinct()


@login_required
def panel(request):
    from .tableros import panel as tablero
    return tablero(request)


@login_required
def curso(request, pk, intento=None, foro_extra=None):
    curso = get_object_or_404(cursos_permitidos(request.user), pk=pk)
    equipo = request.user.is_superuser or curso.formadores.filter(pk=request.user.pk).exists()
    lecciones = Leccion.objects.filter(modulo__curso=curso).select_related('prueba').prefetch_related(
        Prefetch('recursos', queryset=RecursoLeccion.objects.filter(activo=True), to_attr='recursos_visibles'))
    if not equipo:
        lecciones = lecciones.filter(publicada=True)
    modulos = list(Modulo.objects.filter(curso=curso).prefetch_related(Prefetch('lecciones', queryset=lecciones)))
    completadas = set(Progreso.objects.filter(cursante=request.user, leccion__in=lecciones).values_list('leccion_id', flat=True))
    total = lecciones.filter(obligatoria=True,prueba__isnull=True).count()
    hechas = lecciones.filter(obligatoria=True,prueba__isnull=True, pk__in=completadas).count()
    pruebas=list(Prueba.objects.filter(leccion__in=lecciones).select_related('leccion'))
    historial=list(IntentoPrueba.objects.filter(prueba__in=pruebas,cursante=request.user).select_related('prueba'))
    for prueba in pruebas:
        prueba.historial=[i for i in historial if i.prueba_id==prueba.pk]
        prueba.aprobada=any(i.aprobado and i.revision==prueba.revision for i in prueba.historial)
        if prueba.aprobada:
            completadas.add(prueba.leccion_id)
    ordenadas = []
    for modulo in modulos:
        modulo.clases = list(modulo.lecciones.all())
        ordenadas.extend(modulo.clases)
        obligatorias = [clase for clase in modulo.clases if clase.obligatoria and not hasattr(clase,'prueba')]
        modulo.total_lecturas = len(obligatorias)
        modulo.lecturas_hechas = sum(clase.pk in completadas for clase in obligatorias)
        modulo.porcentaje = round(100 * modulo.lecturas_hechas / len(obligatorias)) if obligatorias else 0
    seleccion = str(intento.prueba.leccion_id) if intento else request.GET.get('clase')
    actual = None
    if seleccion:
        actual = next((clase for clase in ordenadas if str(clase.pk) == seleccion), None)
        if actual is None:
            raise Http404
    elif ordenadas:
        actual = next((clase for clase in ordenadas if clase.pk not in completadas), ordenadas[0])
    posicion = ordenadas.index(actual) if actual else -1
    vista = request.GET.get('vista', 'contenido')
    if vista not in {'contenido', 'materiales', 'avance', 'foro'}:
        vista = 'contenido'
    if intento:
        vista='contenido'
    if foro_extra is not None:
        vista='foro'
    from .foro import contexto
    foro_contexto=contexto(request,curso,foro_extra) if vista=='foro' else {}
    prueba_actual=next((p for p in pruebas if actual and p.leccion_id==actual.pk),None)
    inscripcion=Inscripcion.objects.filter(curso=curso,cursante=request.user).first()
    return render(request, 'aula/campus.html', {
        'curso': curso, 'modulos': modulos, 'completadas': completadas,
        'total': total, 'hechas': hechas, 'porcentaje': round(100 * hechas / total) if total else 0,
        'equipo': equipo,'puede_seguimiento':puede_seguimiento(request.user,curso),**foro_contexto,
        'actual': actual, 'vista': vista, 'cantidad_clases': len(ordenadas),
        'hay_materiales': any(clase.recursos_visibles for clase in ordenadas),
        'posicion_clase': posicion + 1,
        'anterior': ordenadas[posicion - 1] if posicion > 0 else None,
        'siguiente': ordenadas[posicion + 1] if 0 <= posicion < len(ordenadas) - 1 else None,
        'pruebas':pruebas,'prueba_actual':prueba_actual,'intento':intento,
        'devolucion_automatica': devolucion_automatica(intento),
        'escena':escena_actual(intento)[1] if intento and intento.estructura.get('grafo') else None,
        'certificados':inscripcion.certificados.filter(revocado=False) if inscripcion else [],
    })


@login_required
@require_POST
def completar(request, pk):
    leccion = get_object_or_404(Leccion, pk=pk, publicada=True, prueba__isnull=True, modulo__curso__publicado=True,
        modulo__curso__inscripciones__cursante=request.user, modulo__curso__inscripciones__activa=True,
        modulo__curso__in=cursos_permitidos(request.user))
    Progreso.objects.get_or_create(cursante=request.user, leccion=leccion)
    if request.POST.get('seguir') == '1':
        clases = list(Leccion.objects.filter(modulo__curso=leccion.modulo.curso, publicada=True)
                      .order_by('modulo__orden', 'modulo__pk', 'orden', 'pk').values_list('pk', flat=True))
        posicion = clases.index(leccion.pk)
        destino = f'?clase={clases[posicion + 1]}' if posicion + 1 < len(clases) else '?vista=avance'
        return redirect(reverse('aula:curso', args=[leccion.modulo.curso_id]) + destino)
    return redirect('aula:curso', pk=leccion.modulo.curso_id)
