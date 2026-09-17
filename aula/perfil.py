import re
from django import forms
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from .models import Perfil
from .gestion import registrar
from django.contrib.admin.models import CHANGE


class DatosPersonalesForm(forms.ModelForm):
    first_name = forms.CharField(label='Nombre(s)', max_length=150)
    last_name = forms.CharField(label='Apellido(s)', max_length=150)
    email = forms.EmailField(label='Correo electrónico', required=False)

    class Meta:
        model = get_user_model()
        fields = ('first_name', 'last_name', 'email')


class PerfilForm(forms.ModelForm):
    class Meta:
        model = Perfil
        fields = ('dni', 'fecha_nacimiento', 'direccion', 'localidad', 'codigo_postal',
                  'telefono', 'estado_civil', 'cantidad_hijos', 'profesion', 'asociacion',
                  'grupo', 'fecha_ingreso_grupo', 'fecha_ingreso_movimiento', 'sacramentos',
                  'fecha_promesa', 'cargo')
        widgets = {campo: forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d')
                   for campo in ('fecha_nacimiento', 'fecha_ingreso_grupo', 'fecha_ingreso_movimiento', 'fecha_promesa')}
        help_texts = {'dni': 'Opcional. Ingresá de 7 a 8 números, sin puntos.',
                      'sacramentos': 'Opcional. Completalo solo si deseás informar este dato a Dirección.'}

    def clean_dni(self):
        dni = re.sub(r'[.\s]', '', self.cleaned_data.get('dni', ''))
        if dni and not re.fullmatch(r'[0-9]{7,8}', dni):
            raise forms.ValidationError('Ingresá un DNI de 7 u 8 números o dejá el campo vacío.')
        return dni

    def clean(self):
        datos = super().clean()
        nacimiento = datos.get('fecha_nacimiento')
        for campo in ('fecha_nacimiento', 'fecha_ingreso_grupo', 'fecha_ingreso_movimiento', 'fecha_promesa'):
            fecha = datos.get(campo)
            if fecha and fecha > timezone.localdate():
                self.add_error(campo, 'La fecha no puede ser futura.')
            elif fecha and nacimiento and campo != 'fecha_nacimiento' and fecha < nacimiento:
                self.add_error(campo, 'La fecha no puede ser anterior al nacimiento.')
        return datos


@login_required
@never_cache
@require_http_methods(['GET', 'POST'])
def editar(request):
    perfil = Perfil.objects.filter(usuario=request.user).first() or Perfil(usuario=request.user)
    datos_form = DatosPersonalesForm(request.POST if request.method == 'POST' else None, instance=request.user)
    perfil_form = PerfilForm(request.POST if request.method == 'POST' else None, instance=perfil)
    if request.method == 'POST':
        validos = datos_form.is_valid() & perfil_form.is_valid()
        if validos:
            with transaction.atomic():
                datos_form.save()
                perfil_form.save()
                campos = datos_form.changed_data + perfil_form.changed_data
                registrar(request, perfil, CHANGE, 'Perfil actualizado. Campos: ' + ', '.join(campos))
            messages.success(request, 'Tus datos se guardaron correctamente.')
            return redirect('aula:perfil')
    return render(request, 'aula/perfil.html', {'datos_form': datos_form, 'perfil_form': perfil_form, 'perfil': perfil,
        'secciones': [('Contacto y domicilio', ['dni', 'fecha_nacimiento', 'direccion', 'localidad', 'codigo_postal', 'telefono']),
                     ('Datos personales adicionales', ['estado_civil', 'cantidad_hijos', 'profesion']),
                     ('Trayectoria scout', ['asociacion', 'grupo', 'fecha_ingreso_grupo', 'fecha_ingreso_movimiento', 'fecha_promesa', 'cargo', 'sacramentos'])]})
