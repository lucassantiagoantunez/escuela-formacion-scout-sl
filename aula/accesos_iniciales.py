"""Review and update only accounts that have never been used, by Direction."""
import unicodedata
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.admin.models import CHANGE
from django.core import signing
from django.core.exceptions import ValidationError
from django.db import transaction, IntegrityError
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters, sensitive_variables
from django.views.decorators.http import require_http_methods
from .gestion import direccion, registrar
from .models import Curso, Perfil

User = get_user_model()
SALT = 'aula.accesos-iniciales.v1'
TAMANO_LOTE = 4


def pendientes(curso):
    return User.objects.filter(Q(cursos_asignados=curso) | Q(inscripciones_aula__curso=curso),
        is_active=True, is_staff=False, is_superuser=False, last_login__isnull=True,
        perfil_aula__cambiar_clave=True).distinct().order_by('pk')


def simple(texto):
    return ''.join(c for c in unicodedata.normalize('NFKD', texto).lower() if c.isascii() and c.isalnum())


def propuestas(curso):
    ocupados = set(User.objects.values_list('username', flat=True))
    ocupados = {n.casefold() for n in ocupados}
    filas = []
    for persona in pendientes(curso):
        nombres = persona.first_name.split()
        apellido = simple(persona.last_name.split()[0]) if persona.last_name.strip() else ''
        base = simple(persona.first_name[:1]) + apellido if apellido else simple(persona.first_name)
        base = base or 'usuario'
        nuevo = base
        if nuevo in ocupados and nuevo != persona.username.casefold():
            if len(nombres) > 1:
                nuevo = simple(nombres[0][:1] + nombres[1][:1]) + apellido
            n = 2
            while nuevo in ocupados and nuevo != persona.username.casefold():
                nuevo = base + str(n); n += 1
        ocupados.add(nuevo)
        filas.append({'id': persona.pk, 'anterior': persona.username, 'nuevo': nuevo,
                      'nombre': persona.get_full_name()})
    return filas


class PrepararForm(forms.Form):
    curso = forms.ModelChoiceField(queryset=Curso.objects.all(), label='Curso')


class AplicarForm(forms.Form):
    propuesta = forms.CharField(widget=forms.HiddenInput)
    clave = forms.CharField(label='Contraseña temporal', min_length=8, max_length=128,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}))
    repetir = forms.CharField(label='Repetir contraseña temporal', widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}))
    confirmar = forms.BooleanField(label='Confirmo estos usuarios y el cambio obligatorio de contraseña al ingresar')

    def clean(self):
        datos = super().clean()
        if datos.get('clave') != datos.get('repetir'):
            self.add_error('repetir', 'Las contraseñas deben coincidir.')
        return datos


@direccion
@never_cache
@sensitive_post_parameters('clave', 'repetir')
@require_http_methods(['GET', 'POST'])
@sensitive_variables()
def editar(request):
    preparar = PrepararForm(request.GET or None)
    form = None; filas = []; curso = None
    if request.method == 'POST':
        por_lotes = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        form = AplicarForm(request.POST)
        try:
            datos = signing.loads(request.POST.get('propuesta', ''), salt=SALT, max_age=3600)
            if datos['director'] != request.user.pk:
                raise signing.BadSignature
            curso = get_object_or_404(Curso, pk=datos['curso'])
            filas = datos['filas']
            numero = request.POST.get('lote', '0')
            if not numero.isdigit() or len(numero) > 4:
                raise signing.BadSignature
            inicio = int(numero) * TAMANO_LOTE
            lote = filas[inicio:inicio + TAMANO_LOTE]
            if not lote:
                raise signing.BadSignature
        except (signing.BadSignature, KeyError, TypeError):
            form.is_valid()
            form.add_error(None, 'La propuesta venció o no es válida. Volvé a elegir el curso.')
        else:
            if not por_lotes and len(filas) > TAMANO_LOTE:
                form.is_valid()
                form.add_error(None, 'Actualizá la página y habilitá JavaScript para procesar la lista en grupos pequeños.')
            if form.is_valid():
                try:
                    with transaction.atomic():
                        Curso.objects.select_for_update().get(pk=curso.pk)
                        ids = [f['id'] for f in lote]
                        personas = {p.pk: p for p in User.objects.select_for_update().filter(pk__in=ids)}
                        elegibles = set(pendientes(curso).values_list('pk', flat=True))
                        if not filas or not set(ids).issubset(elegibles):
                            raise ValidationError('Una cuenta ya ingresó o cambió de estado. Revisá una nueva propuesta.')
                        resultados = []
                        for fila in lote:
                            persona = personas[fila['id']]
                            # A lost response can safely be retried, without rotating the
                            # password again or duplicating audit entries.
                            repetida = por_lotes and persona.username == fila['nuevo'] and persona.check_password(form.cleaned_data['clave'])
                            if (not repetida and persona.username != fila['anterior']) or User.objects.filter(username__iexact=fila['nuevo']).exclude(pk=persona.pk).exists():
                                raise ValidationError('Un nombre de usuario cambió o ya está ocupado. Revisá una nueva propuesta.')
                            if not repetida:
                                persona.username = fila['nuevo']
                                persona.set_password(form.cleaned_data['clave'])
                                persona.save(update_fields=['username', 'password'])
                                Perfil.objects.filter(usuario=persona).update(cambiar_clave=True)
                                registrar(request, persona, CHANGE, 'Acceso inicial simplificado; usuario anterior: ' + fila['anterior'])
                            resultados.append({'nombre': persona.get_full_name(), 'usuario': persona.username,
                                'email': persona.email, 'rol': 'Formador / apoyo' if curso.formadores.filter(pk=persona.pk).exists() else 'Cursante',
                                'clave': form.cleaned_data['clave'], 'nueva': True})
                    if por_lotes:
                        return JsonResponse({'resultados': resultados, 'completadas': inicio + len(lote),
                            'total': len(filas), 'terminado': inicio + len(lote) == len(filas)})
                    return render(request, 'aula/usuarios/accesos_actualizados.html', {'resultados': resultados})
                except (ValidationError, IntegrityError) as error:
                    form.add_error(None, error if isinstance(error, ValidationError) else 'Un usuario ya está ocupado. Revisá una nueva propuesta.')
        if por_lotes:
            return JsonResponse({'errores': form.errors.get_json_data()}, status=400)
    elif preparar.is_valid():
        curso = preparar.cleaned_data['curso']
        filas = propuestas(curso)
        if filas:
            form = AplicarForm(initial={'propuesta': signing.dumps({'director': request.user.pk, 'curso': curso.pk, 'filas': filas}, salt=SALT)})
    return render(request, 'aula/usuarios/accesos_iniciales.html', {'preparar': preparar, 'form': form, 'filas': filas, 'curso': curso})
