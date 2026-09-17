from functools import wraps

from django.contrib import messages
from django.contrib.admin.models import ADDITION, CHANGE, LogEntry
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Count, Max
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from .forms import CursoForm, InscribirForm, LeccionForm, ModuloForm, PersonaForm
from .models import Curso, Inscripcion, Leccion, Modulo, Progreso, RecursoLeccion
from .archivos import preparar_recursos, guardar_recursos


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
    from .tableros import pagina
    buscar = request.GET.get('buscar', '')[:160]
    cursos = Curso.objects.filter(titulo__icontains=buscar).order_by('titulo', 'pk')
    return render(request, 'aula/gestion/inicio.html', {
        **pagina(request, cursos, 6), 'buscar': buscar,
    })


@direccion
def detalle(request, pk):
    from .tableros import gestion_curso
    return gestion_curso(request, get_object_or_404(Curso, pk=pk))


def formulario(request, form, titulo, descripcion, volver, boton='Guardar cambios'):
    candidato = request.POST.get('volver') or request.GET.get('volver', '')
    base = volver.split('?')[0]
    if candidato.startswith(base + '?'):
        volver = candidato
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
    form = LeccionForm(request.POST if request.method == 'POST' else None, request.FILES if request.method == 'POST' else None, instance=leccion, curso=curso,
                       initial={'modulo': modulo.pk} if modulo else None)
    if modulo:
        form.fields['modulo'].disabled = True
        form.fields['modulo'].help_text = 'La clase se guardará en este módulo.'
    if request.method == 'POST' and form.is_valid():
        guardados = []
        try:
            preparados = preparar_recursos(form.cleaned_data['archivos'])
            with transaction.atomic():
                Curso.objects.select_for_update().get(pk=curso.pk)
                if not pk or 'modulo' in form.changed_data:
                    form.instance.orden = (form.cleaned_data['modulo'].lecciones.aggregate(n=Max('orden'))['n'] or 0) + 1
                form.instance.texto_enriquecido = True
                if pk and hasattr(form.instance,'prueba'):
                    from .pruebas_motor import preparar
                    if form.instance.publicada:
                        preparar(form.instance.prueba)
                    form.instance.obligatoria=False
                leccion = form.save()
                guardar_recursos(leccion, preparados, guardados)
                registrar(request, leccion, CHANGE if pk else ADDITION, 'Clase y recursos guardados desde Gestión.')
        except Exception as exc:
            for campo in guardados:
                try:
                    campo.storage.delete(campo.name)
                except OSError:
                    pass
            if not isinstance(exc, (ValidationError, OSError)):
                raise
            form.add_error('archivos', exc if isinstance(exc, ValidationError) else 'No pudimos guardar los archivos. Intentá nuevamente; la clase no se modificó.')
        else:
            messages.success(request, 'Clase guardada.' if leccion.publicada else 'Clase guardada como borrador.')
            if request.POST.get('continuar') == '1':
                return redirect('aula:gestion_leccion_editar', curso_pk=curso.pk, pk=leccion.pk)
            volver = request.POST.get('volver', '')
            if volver.startswith(reverse('aula:gestion_curso', args=[curso.pk]) + '?'):
                return redirect(volver)
            return redirect(f"{reverse('aula:gestion_curso', args=[curso.pk])}?modulo={leccion.modulo_id}#modulo-{leccion.modulo_id}")
    return formulario(request, form, 'Editar clase' if pk else 'Agregar una clase',
                      f'Curso: {curso.titulo}. ' + (f'Módulo: {modulo.titulo}. ' if modulo else '') + 'Combiná texto, documentos, imágenes y videos en tu clase.',
                      reverse('aula:gestion_curso', args=[curso.pk]) + '?seccion=contenido' + (f'&modulo={leccion.modulo_id}' if leccion else (f'&modulo={modulo.pk}' if modulo else '')), 'Guardar clase')


@direccion
@require_http_methods(['POST'])
def retirar_recurso(request, pk):
    recurso = get_object_or_404(RecursoLeccion, pk=pk, activo=True)
    with transaction.atomic():
        recurso.activo = False
        recurso.save(update_fields=['activo'])
        registrar(request, recurso, CHANGE, 'Recurso retirado de la clase; archivo conservado.')
    messages.success(request, 'El archivo ya no se muestra en la clase.')
    return redirect('aula:gestion_leccion_editar', curso_pk=recurso.leccion.modulo.curso_id, pk=recurso.leccion_id)


@direccion
@require_http_methods(['GET','POST'])
def eliminar_leccion(request,curso_pk,pk):
    leccion=get_object_or_404(Leccion,pk=pk,modulo__curso_id=curso_pk)
    if request.method=='POST':
        with transaction.atomic():
            Curso.objects.select_for_update().get(pk=curso_pk)
            leccion.eliminada=True;leccion.publicada=False
            leccion.save(update_fields=['eliminada','publicada'])
            registrar(request,leccion,CHANGE,'Clase enviada a papelera; archivos y registros conservados.')
        messages.success(request,'Clase eliminada del curso. Podés recuperarla desde la papelera.')
        return redirect('aula:gestion_curso',pk=curso_pk)
    return render(request,'aula/gestion/eliminar_clase.html',{'leccion':leccion,'curso':leccion.modulo.curso})


@direccion
@require_http_methods(['POST'])
def restaurar_leccion(request,curso_pk,pk):
    with transaction.atomic():
        Curso.objects.select_for_update().get(pk=curso_pk)
        leccion=get_object_or_404(Leccion.todas,pk=pk,modulo__curso_id=curso_pk,eliminada=True)
        leccion.eliminada=False;leccion.publicada=False
        leccion.save(update_fields=['eliminada','publicada'])
        registrar(request,leccion,CHANGE,'Clase recuperada como borrador desde papelera.')
    messages.success(request,'Clase recuperada como borrador. Revisala antes de publicarla.')
    return redirect('aula:gestion_leccion_editar',curso_pk=curso_pk,pk=pk)


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


@direccion
@require_http_methods(['POST'])
def organizar_clase(request, curso_pk, pk):
    from .tableros import ruta
    with transaction.atomic():
        curso = get_object_or_404(Curso.objects.select_for_update(), pk=curso_pk)
        clase = get_object_or_404(Leccion, pk=pk, modulo__curso=curso)
        accion = request.POST.get('accion')
        if accion == 'duplicar' and not hasattr(clase, 'prueba'):
            copia = Leccion.objects.create(modulo=clase.modulo, titulo=(clase.titulo[:185] + ' (copia)'),
                texto=clase.texto, texto_enriquecido=clase.texto_enriquecido, video_url=clase.video_url,
                obligatoria=clase.obligatoria, publicada=False,
                orden=(clase.modulo.lecciones.aggregate(n=Max('orden'))['n'] or 0) + 1)
            for recurso in clase.recursos.filter(activo=True):
                # Private stored files are immutable and are not deleted when a resource is retired.
                RecursoLeccion.objects.create(leccion=copia, nombre=recurso.nombre, tipo=recurso.tipo,
                    archivo=recurso.archivo.name, vista_pdf=recurso.vista_pdf.name, mime=recurso.mime, orden=recurso.orden)
            registrar(request, copia, ADDITION, 'Clase duplicada como borrador, sin progreso ni resultados.')
            messages.success(request, 'Copia creada como borrador. Revisala antes de publicarla.')
            return redirect('aula:gestion_leccion_editar', curso_pk=curso.pk, pk=copia.pk)
        if accion not in ('subir', 'bajar'):
            from django.http import HttpResponseBadRequest
            return HttpResponseBadRequest('Elegí una acción válida.')
        clases = list(clase.modulo.lecciones.all())
        posicion = next(i for i, c in enumerate(clases) if c.pk == clase.pk)
        destino = posicion + (-1 if accion == 'subir' else 1)
        if 0 <= destino < len(clases):
            clases[posicion], clases[destino] = clases[destino], clases[posicion]
            for orden, c in enumerate(clases, 1):
                c.orden = orden
            Leccion.objects.bulk_update(clases, ['orden'])
            registrar(request, clase, CHANGE, 'Orden de la clase actualizado.')
    return redirect(ruta(curso, 'contenido', modulo=clase.modulo_id))


@direccion
@require_http_methods(['GET', 'POST'])
def inscripcion_editar(request, pk):
    from django import forms
    from django.contrib.auth import get_user_model
    from .forms import PersonaChoiceField
    class InscripcionForm(forms.ModelForm):
        tutor = PersonaChoiceField(queryset=get_user_model().objects.filter(is_active=True).order_by('first_name', 'username'),
            required=False, label='Tutor asignado', help_text='Dirección verifica su acreditación y el acuerdo correspondiente.')
        class Meta:
            model = Inscripcion
            fields = ['activa', 'tutor']
            labels = {'activa': 'Inscripción activa'}
    inscripcion = get_object_or_404(Inscripcion.objects.select_related('curso', 'cursante'), pk=pk)
    form = InscripcionForm(request.POST if request.method == 'POST' else None, instance=inscripcion)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            objeto = form.save()
            registrar(request, objeto, CHANGE, 'Inscripción y tutor actualizados desde la ficha.')
        messages.success(request, 'Datos de la inscripción guardados.')
        return redirect('aula:ficha_cursante', pk=pk)
    return formulario(request, form, 'Inscripción y tutor', str(inscripcion), reverse('aula:ficha_cursante', args=[pk]))
