"""Direction-only account management. Never reset an existing password on import."""
import csv
import io
import secrets
from datetime import timedelta
from django import forms
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.admin.models import ADDITION, CHANGE, DELETION
from django.core.exceptions import ValidationError, PermissionDenied
from django.db import transaction
from django.db.models import Q, ProtectedError
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from .gestion import direccion, registrar, formulario
from .models import AccesoCurso, Curso, Perfil, Inscripcion, PermisoFormador
from .forms import PersonaForm
from .tableros import pagina

User = get_user_model()


class AccesoForm(forms.ModelForm):
    recalcular = forms.BooleanField(label='Recalcular el vencimiento con estos días y la fecha de inicio', required=False)
    class Meta:
        model = AccesoCurso
        fields = ['habilitado', 'dias', 'inicio', 'fin']
        widgets = {n: forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M') for n in ('inicio', 'fin')}
        help_texts = {'dias': 'Sin inicio ni fin: empieza en el primer ingreso. Dejá días y fin vacíos para quitar el límite.',
                      'fin': 'Se suspende el curso en este momento; no se borra la cuenta ni su historial.'}

    def clean(self):
        d = super().clean()
        if d.get('recalcular'):
            d['fin'] = d['inicio'] + timedelta(days=d['dias']) if d.get('inicio') and d.get('dias') else None
        return d


class ImportarForm(forms.Form):
    curso = forms.ModelChoiceField(queryset=Curso.objects.all(), label='Curso')
    dias = forms.IntegerField(label='Días desde el primer ingreso', initial=30, min_value=1, max_value=3650)
    listado = forms.CharField(label='Listado CSV', widget=forms.Textarea(attrs={'rows': 10}),
        help_text='Columnas: usuario,nombre,apellido,email,rol. Rol: cursante, formador o consulta. Máximo 25 personas. Las cuentas existentes conservan contraseña y permisos.')
    confirmar = forms.BooleanField(label='Confirmo el listado y los permisos: los formadores podrán responder en el foro, ver seguimiento y corregir; no emitir certificados.')

    def clean_listado(self):
        texto = self.cleaned_data['listado']
        if len(texto) > 120000:
            raise ValidationError('El listado es demasiado extenso.')
        reader = csv.DictReader(io.StringIO(texto.lstrip('\ufeff')))
        if reader.fieldnames != ['usuario', 'nombre', 'apellido', 'email', 'rol']:
            raise ValidationError('Usá las cinco columnas indicadas y separalas con comas.')
        filas = list(reader)
        if not 1 <= len(filas) <= 25:
            raise ValidationError('Ingresá entre 1 y 25 personas.')
        vistos, correos = set(), set()
        for n, r in enumerate(filas, 2):
            if None in r or any(v is None for v in r.values()):
                raise ValidationError(f'Fila {n}: revisá la cantidad de columnas.')
            for k in r: r[k] = r[k].strip()
            if not r['nombre'] or r['rol'] not in ('cursante', 'formador', 'consulta'):
                raise ValidationError(f'Fila {n}: completá nombre, apellido y un rol válido.')
            try:
                for campo, valor in [('username', r['usuario']), ('first_name', r['nombre']), ('last_name', r['apellido']), ('email', r['email'])]:
                    User._meta.get_field(campo).clean(valor, None)
            except ValidationError:
                raise ValidationError(f'Fila {n}: usuario, nombre o correo inválido.')
            clave, email = r['usuario'].casefold(), r['email'].casefold()
            if clave in vistos or (email and email in correos):
                raise ValidationError(f'Fila {n}: usuario o correo repetido en el listado.')
            vistos.add(clave)
            if email: correos.add(email)
            existentes = User.objects.filter(Q(username__iexact=r['usuario']) | (Q(email__iexact=r['email']) if email else Q(pk=-1)))
            if existentes.count() > 1:
                raise ValidationError(f'Fila {n}: el usuario y el correo corresponden a cuentas diferentes.')
            existente = existentes.first()
            if existente and not existente.is_active:
                raise ValidationError(f'Fila {n}: la cuenta existente está desactivada. Revisala antes de importar.')
            if not existente and User.objects.filter(first_name__iexact=r['nombre'], last_name__iexact=r['apellido']).exists():
                raise ValidationError(f'Fila {n}: ya existe una persona con este nombre. Usá su usuario actual.')
        return filas


@direccion
@never_cache
def listado(request):
    buscar = request.GET.get('buscar', '')[:150]
    personas = User.objects.filter(Q(username__icontains=buscar) | Q(first_name__icontains=buscar) | Q(last_name__icontains=buscar)).order_by('first_name', 'last_name', 'username')
    if request.GET.get('estado') in ('activos', 'inactivos'):
        personas = personas.filter(is_active=request.GET['estado'] == 'activos')
    return render(request, 'aula/usuarios/lista.html', {**pagina(request, personas, 20), 'buscar': buscar, 'estado': request.GET.get('estado', '')})


@direccion
@never_cache
@require_http_methods(['GET', 'POST'])
def detalle(request, pk):
    persona = get_object_or_404(User, pk=pk)
    protegida = persona.is_superuser or persona.pk == request.user.pk
    if request.method == 'POST':
        if protegida:
            raise PermissionDenied
        accion = request.POST.get('accion')
        with transaction.atomic():
            persona = User.objects.select_for_update().get(pk=pk)
            if accion in ('activar', 'desactivar'):
                persona.is_active = accion == 'activar'
                persona.save(update_fields=['is_active'])
                registrar(request, persona, CHANGE, 'Cuenta ' + accion + ' desde Usuarios.')
                messages.success(request, 'Estado de la cuenta actualizado. El historial se conserva.')
            elif accion == 'eliminar':
                if request.POST.get('confirmacion') != persona.username:
                    messages.error(request, 'Escribí el usuario exacto para confirmar la eliminación.')
                elif persona.last_login or persona.inscripciones_aula.exists() or persona.cursos_asignados.exists():
                    messages.error(request, 'Esta cuenta tiene acceso o historial de formación. Desactivala para conservar sus registros.')
                else:
                    from django.contrib.admin.utils import NestedObjects
                    collector = NestedObjects(using='default')
                    collector.collect([persona])
                    permitidos = {User, Perfil, AccesoCurso}
                    if collector.protected or any(m not in permitidos and not m._meta.auto_created for m in collector.model_objs):
                        messages.error(request, 'Hay registros vinculados. Desactivá la cuenta para conservarlos.')
                    else:
                        registrar(request, persona, DELETION, 'Cuenta sin actividad eliminada desde Usuarios.')
                        persona.delete()
                        messages.success(request, 'Cuenta sin actividad eliminada.')
                        return redirect('aula:usuarios')
            else:
                raise PermissionDenied
        return redirect('aula:usuario', pk=pk)
    cursos = Curso.objects.filter(Q(formadores=persona) | Q(inscripciones__cursante=persona)).distinct()
    accesos = {a.curso_id: a for a in AccesoCurso.objects.filter(usuario=persona)}
    return render(request, 'aula/usuarios/detalle.html', {'persona': persona, 'protegida': protegida,
        'cursos': [(c, accesos.get(c.pk)) for c in cursos]})


@direccion
@never_cache
@require_http_methods(['GET', 'POST'])
def acceso(request, pk, curso_pk):
    persona = get_object_or_404(User, pk=pk)
    curso = get_object_or_404(Curso.objects.filter(Q(formadores=persona) | Q(inscripciones__cursante=persona)).distinct(), pk=curso_pk)
    if persona.is_superuser:
        raise PermissionDenied
    instancia = AccesoCurso.objects.filter(usuario=persona, curso=curso).first() or AccesoCurso(usuario=persona, curso=curso)
    form = AccesoForm(request.POST if request.method == 'POST' else None, instance=instancia)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            obj = form.save()
            registrar(request, obj, CHANGE, 'Plazo y estado de acceso actualizados.')
        messages.success(request, 'Acceso actualizado.')
        return redirect('aula:usuario', pk=pk)
    return formulario(request, form, 'Configurar acceso de ' + (persona.get_full_name() or persona.username), curso.titulo,
        reverse('aula:usuario', args=[pk]))


@direccion
@never_cache
@require_http_methods(['GET', 'POST'])
def importar(request):
    form = ImportarForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        resultados = []
        with transaction.atomic():
            # Serialize all batch imports for this course and recheck identity inside the lock.
            curso = Curso.objects.select_for_update().get(pk=form.cleaned_data['curso'].pk)
            for fila in form.cleaned_data['listado']:
                email = fila['email']
                persona = User.objects.filter(Q(username__iexact=fila['usuario']) | (Q(email__iexact=email) if email else Q(pk=-1))).first()
                nueva = persona is None
                clave = ''
                if nueva:
                    clave = secrets.token_urlsafe(15)
                    persona = User.objects.create_user(username=fila['usuario'], first_name=fila['nombre'],
                        last_name=fila['apellido'], email=email, password=clave)
                    Perfil.objects.create(usuario=persona, cambiar_clave=True)
                    registrar(request, persona, ADDITION, 'Cuenta creada mediante importación de participantes.')
                if not persona.is_superuser:
                    if fila['rol'] == 'cursante':
                        Inscripcion.objects.get_or_create(curso=curso, cursante=persona)
                    elif nueva:
                        curso.formadores.add(persona)
                        PermisoFormador.objects.create(curso=curso, formador=persona, responder_foro=True,
                            moderar_foro=False, ver_seguimiento=fila['rol']=='formador', corregir=fila['rol']=='formador',
                            validar=False, emitir=False, disenar=False)
                    AccesoCurso.objects.get_or_create(curso=curso, usuario=persona, defaults={'dias': form.cleaned_data['dias']})
                resultados.append({'nombre': persona.get_full_name(), 'usuario': persona.username, 'email': persona.email,
                    'rol': fila['rol'], 'clave': clave, 'nueva': nueva})
            registrar(request, curso, CHANGE, f'Importación de {len(resultados)} participantes; contraseñas existentes conservadas.')
        # Plaintext exists only in this response, never in a model, session or log.
        return render(request, 'aula/usuarios/credenciales.html', {'resultados': resultados, 'curso': curso, 'dias': form.cleaned_data['dias']})
    return formulario(request, form, 'Crear cuentas e inscribir en lote', 'Revisá nombres y correos. Las contraseñas temporales nuevas se muestran una sola vez al terminar.', reverse('aula:usuarios'), 'Crear cuentas y mostrar credenciales')
