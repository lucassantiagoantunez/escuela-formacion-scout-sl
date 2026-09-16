"""Read-only workspaces and bounded lists for the Aula."""
from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Count, Exists, OuterRef, Q, F
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from .models import (Curso, Inscripcion, Leccion, Modulo, Progreso, Prueba,
                     IntentoPrueba, TemaForo, RespuestaForo, CierreCurso, Certificado)
from .permisos import permisos


def pagina(request, queryset, size=10):
    page = Paginator(queryset, size).get_page(request.GET.get('pagina'))
    params = request.GET.copy()
    params.pop('pagina', None)
    return {'pagina': page, 'parametros': params.urlencode()}


def ruta(curso, seccion='resumen', **kwargs):
    return reverse('aula:gestion_curso', args=[curso.pk]) + '?' + urlencode({'seccion': seccion, **kwargs})


def consultas_pendientes(curso):
    respuestas = RespuestaForo.objects.filter(tema=OuterRef('pk'), oculto=False).filter(
        Q(autor__is_superuser=True) | Q(autor__cursos_asignados=curso))
    return TemaForo.objects.filter(curso=curso, oculto=False, cerrado=False, resuelto=False).annotate(
        respondida=Exists(respuestas)).filter(respondida=False)


def ficha_datos(curso, inscripciones):
    """Batch learning requirements; never interpret reading as approval."""
    inscripciones = list(inscripciones)
    usuarios = [i.cursante_id for i in inscripciones]
    lecturas = Leccion.objects.filter(modulo__curso=curso, publicada=True, obligatoria=True, prueba__isnull=True)
    total = lecturas.count()
    hechas = dict(Progreso.objects.filter(cursante_id__in=usuarios, leccion__in=lecturas).values(
        'cursante_id').annotate(n=Count('id')).values_list('cursante_id', 'n'))
    pruebas = list(Prueba.objects.filter(leccion__modulo__curso=curso, leccion__eliminada=False,
                                        leccion__publicada=True, obligatoria=True).select_related('leccion'))
    aprobadas = set(IntentoPrueba.objects.filter(cursante_id__in=usuarios, prueba__in=pruebas,
        revision=F('prueba__revision'), aprobado=True).values_list('cursante_id', 'prueba_id'))
    cierres = {c.inscripcion_id: c for c in CierreCurso.objects.filter(inscripcion__in=inscripciones)}
    emitidos = set(Certificado.objects.filter(inscripcion__in=inscripciones, revocado=False,
                                             tipo='aprobacion').values_list('inscripcion_id', flat=True))
    for i in inscripciones:
        i.hechas = hechas.get(i.cursante_id, 0)
        i.total = total
        i.porcentaje = round(100 * i.hechas / total) if total else 0
        i.faltan_lecturas = total - i.hechas
        i.faltan_pruebas = [p.leccion.titulo for p in pruebas if (i.cursante_id, p.pk) not in aprobadas]
        i.total_pruebas = len(pruebas)
        i.pruebas_aprobadas = len(pruebas) - len(i.faltan_pruebas)
        i.cierre_actual = cierres.get(i.pk)
        cierre = i.cierre_actual
        if not i.activa:
            i.estado = 'pausada'
            i.estado_nombre = 'Inscripción pausada'
        elif cierre and cierre.aprobado:
            if i.pk in emitidos:
                i.estado, i.estado_nombre = 'emitido', 'Certificado emitido'
            elif curso.requiere_acta and not all([cierre.libro, cierre.acta, cierre.folio, cierre.fecha_acta]):
                i.estado, i.estado_nombre = 'acta', 'Acta pendiente'
            else:
                i.estado, i.estado_nombre = 'aprobado', 'Aprobación registrada'
        elif i.faltan_lecturas or i.faltan_pruebas:
            i.estado, i.estado_nombre = 'pendientes', 'Faltan requisitos'
        else:
            i.estado, i.estado_nombre = 'revisar', 'Para revisar'
    return inscripciones


def resumen_equipo(curso, user):
    p = permisos(user, curso)
    ve = p['ver_seguimiento'] or p['validar'] or p['emitir']
    curso.acciones = p
    curso.cantidad_cursantes = curso.inscripciones.filter(activa=True).count() if ve else None
    curso.cantidad_aprobados = CierreCurso.objects.filter(inscripcion__curso=curso,
        inscripcion__activa=True, aprobado=True).count() if ve else None
    curso.por_corregir = IntentoPrueba.objects.filter(prueba__leccion__modulo__curso=curso,
        estado='pendiente').count() if p['corregir'] or p['ver_seguimiento'] else None
    curso.consultas = consultas_pendientes(curso).count()
    return curso


@login_required
def panel(request):
    user = request.user
    equipo = user.is_superuser or Curso.objects.filter(formadores=user).exists()
    trabajo = equipo and request.GET.get('vista') != 'formacion'
    datos = {'equipo_disponible': equipo, 'trabajo': trabajo}
    if trabajo:
        cursos = Curso.objects.all() if user.is_superuser else Curso.objects.filter(formadores=user)
        q = request.GET.get('buscar', '')[:160]
        cursos = cursos.filter(titulo__icontains=q).order_by('titulo', 'pk')
        datos.update(pagina(request, cursos, 9))
        datos['pagina'].object_list = [resumen_equipo(c, user) for c in datos['pagina']]
        datos['buscar'] = q
    else:
        inscripciones = Inscripcion.objects.filter(cursante=user, activa=True).select_related('curso').order_by('curso__titulo')
        datos.update(pagina(request, inscripciones, 9))
        datos['pagina'].object_list = [ficha_datos(i.curso, [i])[0] for i in datos['pagina']]
        datos['certificados'] = Certificado.objects.filter(inscripcion__cursante=user, revocado=False).select_related('inscripcion__curso')
    return render(request, 'aula/panel.html', datos)


def gestion_curso(request, curso):
    seccion = request.GET.get('seccion', 'contenido' if request.GET.get('modulo') else 'resumen')
    if seccion not in {'resumen', 'contenido', 'personas', 'equipo', 'configuracion', 'papelera'}:
        seccion = 'resumen'
    q = request.GET.get('buscar', '')[:160]
    datos = {'curso': curso, 'seccion': seccion, 'buscar': q, 'acciones': permisos(request.user, curso)}
    datos['papelera_total'] = Leccion.todas.filter(modulo__curso=curso, eliminada=True).count()
    if seccion == 'resumen':
        resumen_equipo(curso, request.user)
        datos['modulos_total'] = curso.modulos.count()
        datos['clases_total'] = Leccion.objects.filter(modulo__curso=curso).count()
        datos['borradores'] = Leccion.objects.filter(modulo__curso=curso, publicada=False).count()
        datos['sin_tutor'] = curso.inscripciones.filter(activa=True, tutor=None).count()
    elif seccion == 'contenido':
        modulo_id = request.GET.get('modulo')
        modulo = get_object_or_404(Modulo, curso=curso, pk=modulo_id) if modulo_id and modulo_id.isdigit() else None
        datos['modulo'] = modulo
        datos['estado'] = request.GET.get('estado', '')
        if modulo or q or datos['estado']:
            clases = Leccion.objects.filter(modulo__curso=curso).select_related('modulo', 'prueba').order_by('modulo__orden', 'modulo_id', 'orden', 'pk')
            if modulo:
                clases = clases.filter(modulo=modulo)
            if q:
                clases = clases.filter(Q(titulo__icontains=q) | Q(modulo__titulo__icontains=q))
            if datos['estado'] in ('publicada', 'borrador'):
                clases = clases.filter(publicada=datos['estado'] == 'publicada')
            elif datos['estado'] == 'pruebas':
                clases = clases.filter(prueba__isnull=False)
            datos.update(pagina(request, clases))
            datos['lista_clases'] = True
        else:
            modulos = curso.modulos.annotate(cantidad=Count('lecciones', filter=Q(lecciones__eliminada=False))).order_by('orden', 'pk')
            datos.update(pagina(request, modulos))
    elif seccion == 'personas':
        personas = curso.inscripciones.select_related('cursante', 'tutor').filter(
            Q(cursante__first_name__icontains=q) | Q(cursante__last_name__icontains=q) | Q(cursante__username__icontains=q)).order_by('cursante__first_name', 'cursante__username')
        datos.update(pagina(request, personas))
        datos['pagina'].object_list = ficha_datos(curso, datos['pagina'])
    elif seccion == 'equipo':
        datos.update(pagina(request, curso.formadores.filter(Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(username__icontains=q)).order_by('first_name', 'username')))
        for persona in datos['pagina']:
            persona.acciones_curso = permisos(persona, curso)
    elif seccion == 'papelera':
        datos.update(pagina(request, Leccion.todas.filter(modulo__curso=curso, eliminada=True).select_related('modulo').order_by('titulo', 'pk')))
    return render(request, 'aula/gestion/curso.html', datos)


@login_required
def ficha(request, pk):
    inscripcion = get_object_or_404(Inscripcion.objects.select_related('curso', 'cursante', 'tutor'), pk=pk)
    curso = inscripcion.curso
    p = permisos(request.user, curso)
    if not any(p[a] for a in ('ver_seguimiento', 'validar', 'emitir')):
        raise PermissionDenied
    i = ficha_datos(curso, [inscripcion])[0]
    from .certificados import validar_aprobacion
    from django.core.exceptions import ValidationError
    from django.utils import timezone
    comunes = []
    if not curso.certificacion_configurada or not curso.fecha_inicio or not curso.fecha_fin or not curso.responsable_certificados:
        comunes.append('Falta configurar las fechas y la autoridad de certificación del curso.')
    if curso.fecha_fin and curso.fecha_fin > timezone.localdate():
        comunes.append('La fecha de finalización del curso todavía no llegó.')
    c = i.cierre_actual
    if not c or not c.participacion_validada or not c.nombre_certificado.strip():
        comunes.append('Falta validar la participación y el nombre del certificado.')
    aprobacion = list(comunes)
    try:
        validar_aprobacion(inscripcion)
    except ValidationError as exc:
        aprobacion.extend(exc.messages)
    if not c or not c.aprobado or not c.requisitos_validados:
        aprobacion.append('Falta confirmar la aprobación y sus requisitos.')
    if curso.requiere_acta and (not c or not all([c.libro, c.acta, c.folio, c.fecha_acta])):
        aprobacion.append('Falta registrar y verificar el asiento real en el libro de actas.')
    return render(request, 'aula/gestion/ficha.html', {'curso': curso, 'inscripcion': i,
        'acciones': p, 'seccion': 'personas', 'certificados': i.certificados.all().order_by('-emitido'),
        'bloqueos_participacion': comunes, 'bloqueos_aprobacion': aprobacion,
        'historial': i.cierre_actual.historial.select_related('responsable').order_by('-fecha') if i.cierre_actual and request.user.is_superuser else []})
