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
from django.contrib.auth.views import PasswordChangeView
from django.urls import reverse_lazy
from django.http import FileResponse, Http404
from django.core.files.base import ContentFile
from io import BytesIO
from PIL import Image, ImageOps, UnidentifiedImageError


class CambiarClave(PasswordChangeView):
    template_name = 'aula/clave.html'
    success_url = reverse_lazy('aula:perfil')

    def form_valid(self, form):
        response = super().form_valid(form)
        Perfil.objects.filter(usuario=self.request.user).update(cambiar_clave=False)
        registrar(self.request, self.request.user, CHANGE, 'Contraseña cambiada por su titular.')
        messages.success(self.request, 'Tu contraseña se cambió correctamente.')
        return response


@login_required
@never_cache
def foto(request, pk=None):
    if pk is not None and pk != request.user.pk and not request.user.is_superuser:
        from .views import cursos_permitidos
        titular = get_user_model().objects.filter(pk=pk, is_active=True).first()
        if not titular or not Perfil.objects.filter(usuario=titular, compartir_foto=True, avatar='').exists():
            raise Http404
        compartidos = cursos_permitidos(request.user).filter(pk__in=cursos_permitidos(titular).values('pk'))
        if not compartidos.exists():
            raise Http404
    perfil = Perfil.objects.filter(usuario_id=pk or request.user.pk).first()
    if not perfil or not perfil.foto:
        raise Http404
    try:
        response = FileResponse(perfil.foto.open('rb'), content_type='image/jpeg')
    except OSError:
        raise Http404
    response['X-Content-Type-Options'] = 'nosniff'
    return response


class DatosPersonalesForm(forms.ModelForm):
    first_name = forms.CharField(label='Nombre(s)', max_length=150)
    last_name = forms.CharField(label='Apellido(s)', max_length=150)
    email = forms.EmailField(label='Correo electrónico', required=False)

    class Meta:
        model = get_user_model()
        fields = ('first_name', 'last_name', 'email')


class PerfilForm(forms.ModelForm):
    eliminar_foto = forms.BooleanField(label='Quitar mi foto actual', required=False)
    foto = forms.FileField(label='Subir foto', required=False, widget=forms.FileInput(
        attrs={'accept': 'image/jpeg,image/png,image/webp'}), help_text='Opcional. JPG, PNG o WebP, hasta 5 MB. Podés elegir si la compartís en tus cursos.')

    class Meta:
        model = Perfil
        fields = ('foto', 'avatar', 'compartir_foto', 'dni', 'fecha_nacimiento', 'direccion', 'localidad', 'codigo_postal',
                  'telefono', 'estado_civil', 'cantidad_hijos', 'profesion', 'asociacion',
                  'grupo', 'fecha_ingreso_grupo', 'fecha_ingreso_movimiento', 'sacramentos',
                  'fecha_promesa', 'cargo')
        widgets = {**{campo: forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d')
                   for campo in ('fecha_nacimiento', 'fecha_ingreso_grupo', 'fecha_ingreso_movimiento', 'fecha_promesa')},
                   'avatar': forms.RadioSelect}
        help_texts = {'dni': 'Opcional. Ingresá de 7 a 8 números, sin puntos.',
                      'sacramentos': 'Opcional. Completalo solo si deseás informar este dato a Dirección.'}

    def clean_foto(self):
        archivo = self.cleaned_data.get('foto')
        if not archivo or not hasattr(archivo, 'content_type'):
            return archivo
        if archivo.size > 5 * 1024 * 1024:
            raise forms.ValidationError('La foto debe pesar hasta 5 MB.')
        try:
            with Image.open(archivo) as im:
                if im.format not in ('JPEG', 'PNG', 'WEBP') or im.width * im.height > 20000000:
                    raise ValueError
                im = ImageOps.exif_transpose(im).convert('RGB')
                im.thumbnail((640, 640))
                salida = BytesIO()
                im.save(salida, format='JPEG', quality=88)
            # Re-encode pixels only: no EXIF, GPS, animation or uploaded metadata.
            return ContentFile(salida.getvalue(), name='perfil.jpg')
        except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
            raise forms.ValidationError('Elegí una imagen JPG, PNG o WebP válida y de hasta 20 megapíxeles.')

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
    anterior = perfil.foto.name
    perfil_form = PerfilForm(request.POST if request.method == 'POST' else None, request.FILES or None, instance=perfil)
    if request.method == 'POST':
        validos = datos_form.is_valid() & perfil_form.is_valid()
        if validos:
            with transaction.atomic():
                datos_form.save()
                if perfil_form.cleaned_data.get('eliminar_foto') and not request.FILES.get('foto'):
                    perfil.foto = ''
                perfil_form.save()
                if anterior and anterior != perfil.foto.name:
                    transaction.on_commit(lambda: perfil.foto.storage.delete(anterior))
                campos = datos_form.changed_data + perfil_form.changed_data
                registrar(request, perfil, CHANGE, 'Perfil actualizado. Campos: ' + ', '.join(campos))
            messages.success(request, 'Tus datos se guardaron correctamente.')
            return redirect('aula:perfil')
    return render(request, 'aula/perfil.html', {'datos_form': datos_form, 'perfil_form': perfil_form, 'perfil': perfil,
        'secciones': [('Contacto y domicilio', ['dni', 'fecha_nacimiento', 'direccion', 'localidad', 'codigo_postal', 'telefono']),
                     ('Datos personales adicionales', ['estado_civil', 'cantidad_hijos', 'profesion']),
                     ('Trayectoria scout', ['asociacion', 'grupo', 'fecha_ingreso_grupo', 'fecha_ingreso_movimiento', 'fecha_promesa', 'cargo', 'sacramentos'])]})
