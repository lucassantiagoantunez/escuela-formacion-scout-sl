from functools import wraps

from django.contrib import messages
from django.contrib.admin.models import ADDITION, CHANGE, LogEntry
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Count, Max
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from .forms import CursoForm, InscribirForm, LeccionForm, ModuloForm, PersonaForm
from .models import Curso, Inscripcion, Leccion, Modulo, Progreso


def direccion(view):
    @login_required
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_active or not request.user.is_superuser:
            raise PermissionDenied
        return view(request, *args, **kwargs)
    return wrapped


def registrar(request, objeto, accion, texto):
    # Registro institucional sin contraseñas ni contenido del formulario.
    LogEntry.objects.create(user=request.user, content_type=ContentType.objects.get_for_model(objeto),
                            object_id=str(objeto.pk), object_repr=str(objeto)[:200],
                            action_flag=accion, change_message=texto)


@direccion
def inicio(request):
    return render(request, 'aula/gestion/inicio.html', {'cursos': Curso.objects.order_by('titulo')})


@direccion
def detalle(request, pk):
    curso = get_object_or_404(Curso, pk=pk)
    inscripciones = list(curso.inscripciones.select_related('cursante', 'tutor').order_by('cursante__first_name', 'cursante__username'))
    publicadas = Leccion.objects.filter(modulo__curso=curso, publicada=True, obligatoria=True)
    total = publicadas.count()
    progresos = dict(Progreso.objects.filter(leccion__in=publicadas).values('cursante_id').annotate(n=Count('id')).values_list('cursante_id', 'n'))
    for inscripcion in inscripciones:
        inscripcion.hechas = progresos.get(inscripcion.cursante_id, 0)
    return render(request, 'aula/gestion/curso.html', {
        'curso': curso, 'modulos': curso.modulos.prefetch_related('lecciones'),
        'inscripciones': inscripciones, 'total': total, 'formadores': curso.formadores.all(),
        'modulo_abierto': request.GET.get('modulo', ''),
    })


def formulario(request, form, titulo, descripcion, volver, boton='Guardar cambios'):
    return render(request, 'aula/gestion/form.html', {
        'form': form, 'titulo': titulo, 'descripcion': descripcion, 'volver': volver, 'boton': boton,
    })


@direccion
@require_http_methods(['GET', 'POST'])
def editar_curso(request, pk=None):
    curso = get_object_or_404(Curso, pk=pk) if pk else None
    form = CursoForm(request.POST if request.method == 'POST' else None, instance=curso)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            curso = form.save()
            registrar(request, curso, CHANGE if pk else ADDITION, 'Curso guardado desde Gestión.')
        messages.success(request, 'Curso guardado. Ya podés preparar sus clases y agregar personas.')
        return redirect('aula:gestion_curso', pk=curso.pk)
    return formulario(request, form, 'Editar curso' if pk else 'Crear un curso',
                      'Empezá por el nombre. Después podrás agregar módulos, clases y participantes.',
                      reverse('aula:gestion_curso', args=[pk]) if pk else reverse('aula:gestion'),
                      'Guardar curso' if pk else 'Crear curso')


@direccion
@require_http_methods(['GET', 'POST'])
def editar_modulo(request, curso_pk, pk=None):
    curso = get_object_or_404(Curso, pk=curso_pk)
    modulo = get_object_or_404(Modulo, pk=pk, curso=curso) if pk else Modulo(curso=curso)
    form = ModuloForm(request.POST if request.method == 'POST' else None, instance=modulo)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            # Serializa el agregado para conservar el orden del curso.
            Curso.objects.select_for_update().get(pk=curso.pk)
            if not pk:
                form.instance.orden = (curso.modulos.aggregate(n=Max('orden'))['n'] or 0) + 1
            modulo = form.save()
            registrar(request, modulo, CHANGE if pk else ADDITION, 'Módulo guardado desde Gestión.')
        messages.success(request, 'Módulo guardado. Ahora podés agregarle clases.')
        return redirect('aula:gestion_curso', pk=curso.pk)
    return formulario(request, form, 'Editar módulo' if pk else 'Agregar un módulo',
                      f'Curso: {curso.titulo}. Un módulo agrupa clases sobre un mismo tema.',
                      reverse('aula:gestion_curso', args=[curso.pk]), 'Guardar módulo')


@direccion
@require_http_methods(['GET', 'POST'])
def editar_leccion(request, curso_pk, pk=None, modulo_pk=None):
    curso = get_object_or_404(Curso, pk=curso_pk)
    modulo = get_object_or_404(Modulo, pk=modulo_pk, curso=curso) if modulo_pk else None
    leccion = get_object_or_404(Leccion, pk=pk, modulo__curso=curso) if pk else None
    if not curso.modulos.exists():
        messages.info(request, 'Primero agregá un módulo para organizar las clases.')
        return redirect('aula:gestion_modulo_nuevo', curso_pk=curso.pk)
    form = LeccionForm(request.POST if request.method == 'POST' else None, instance=leccion, curso=curso,
                       initial={'modulo': modulo.pk} if modulo else None)
    if modulo:
        form.fields['modulo'].disabled = True
        form.fields['modulo'].help_text = 'La clase se guardará en este módulo.'
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            Curso.objects.select_for_update().get(pk=curso.pk)
            if not pk or 'modulo' in form.changed_data:
                form.instance.orden = (form.cleaned_data['modulo'].lecciones.aggregate(n=Max('orden'))['n'] or 0) + 1
            leccion = form.save()
            registrar(request, leccion, CHANGE if pk else ADDITION, 'Clase guardada desde Gestión.')
        messages.success(request, 'Clase guardada.' if leccion.publicada else 'Clase guardada como borrador.')
        return redirect(f"{reverse('aula:gestion_curso', args=[curso.pk])}?modulo={leccion.modulo_id}#modulo-{leccion.modulo_id}")
    return formulario(request, form, 'Editar clase' if pk else 'Agregar una clase',
                      f'Curso: {curso.titulo}. ' + (f'Módulo: {modulo.titulo}. ' if modulo else '') + 'Escribí el contenido y, si tenés un video, pegá su enlace.',
                      reverse('aula:gestion_curso', args=[curso.pk]), 'Guardar clase')


def asignar(request, curso, persona, rol):
    if rol == 'formador':
        curso.formadores.add(persona)
        registrar(request, curso, CHANGE, f'Formador asignado: usuario {persona.pk}.')
    else:
        inscripcion, creada = Inscripcion.objects.update_or_create(curso=curso, cursante=persona, defaults={'activa': True})
        registrar(request, inscripcion, ADDITION if creada else CHANGE, 'Inscripción activada desde Gestión.')


@direccion
@require_http_methods(['GET', 'POST'])
def agregar_persona(request, curso_pk, existente=False):
    curso = get_object_or_404(Curso, pk=curso_pk)
    form_class = InscribirForm if existente else PersonaForm
    form = form_class(request.POST if request.method == 'POST' else None, initial={'rol': 'cursante'})
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            persona = form.cleaned_data['persona'] if existente else form.save()
            if not existente:
                registrar(request, persona, ADDITION, 'Cuenta creada desde Gestión.')
            asignar(request, curso, persona, form.cleaned_data['rol'])
        messages.success(request, f'{persona.get_full_name() or persona.username} ya tiene acceso asignado a {curso.titulo}. Usuario para ingresar: {persona.username}.')
        if not curso.publicado and form.cleaned_data['rol'] == 'cursante':
            messages.info(request, 'La inscripción está lista. El curso aparecerá como «En preparación» hasta que habilites su acceso en «Editar presentación y acceso».')
        return redirect('aula:gestion_curso', pk=curso.pk)
    descripcion = (f'Curso: {curso.titulo}. Elegí a alguien que ya tenga cuenta. Si su inscripción estaba pausada, se reactivará.' if existente else
                   f'Curso: {curso.titulo}. Creá su cuenta y agregala al curso en un solo paso. Compartí el usuario y la contraseña de forma privada; todavía no enviamos invitaciones por correo.')
    return formulario(request, form, 'Agregar alguien que ya tiene cuenta' if existente else 'Agregar una persona nueva',
                      descripcion, reverse('aula:gestion_curso', args=[curso.pk]),
                      'Agregar al curso' if existente else 'Crear cuenta y agregar al curso')
