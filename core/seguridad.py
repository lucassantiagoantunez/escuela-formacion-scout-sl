"""Editorial boundaries: content editing never implies account or code access."""
from pathlib import Path
from django import forms
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.views.decorators.http import require_POST
from django_ckeditor_5.views import upload_file
from aula.contenido import limpiar_html
from .models import Material, Noticia

GRUPO_COMUNICACION = 'Comunicación · Noticias y biblioteca'

class NoticiaEditorialForm(forms.ModelForm):
    class Meta:
        model = Noticia
        fields = '__all__'

    def clean_contenido(self):
        return limpiar_html(self.cleaned_data['contenido'])

class MaterialEditorialForm(forms.ModelForm):
    class Meta:
        model = Material
        fields = '__all__'

    def clean_archivo(self):
        archivo = self.cleaned_data.get('archivo')
        if not archivo or not hasattr(archivo, 'content_type'):
            return archivo
        if archivo.size > 20 * 1024 * 1024:
            raise forms.ValidationError('El archivo debe pesar hasta 20 MB.')
        if Path(archivo.name).suffix.lower() not in {'.pdf', '.doc', '.docx', '.ppt', '.pptx', '.xls', '.xlsx', '.odt', '.ods', '.odp', '.txt', '.csv', '.jpg', '.jpeg', '.png', '.webp'}:
            raise forms.ValidationError('Usá PDF, Word, PowerPoint, planillas, texto o imágenes JPG, PNG o WebP. No se permiten páginas HTML, SVG ni ejecutables.')
        return archivo

def puede_comunicar(user):
    return user.is_authenticated and user.is_active and user.is_staff and any(
        user.has_perm('core.' + accion + '_' + modelo)
        for modelo in ('noticia', 'material', 'categoriabiblioteca')
        for accion in ('add', 'change'))

@login_required
def comunicacion(request):
    if not puede_comunicar(request.user):
        raise PermissionDenied
    return render(request, 'aula/comunicacion.html')

@require_POST
def subir_imagen_editor(request):
    if not (request.user.is_authenticated and request.user.is_active and request.user.is_staff
            and (request.user.is_superuser or request.user.has_perm('core.add_noticia') or request.user.has_perm('core.change_noticia'))):
        raise PermissionDenied
    archivo = request.FILES.get('upload')
    if not archivo or archivo.size > 10 * 1024 * 1024 or Path(archivo.name).suffix.lower() not in {'.jpg', '.jpeg', '.png', '.webp'}:
        from django.http import JsonResponse
        return JsonResponse({'error': {'message': 'Usá JPG, PNG o WebP de hasta 10 MB.'}}, status=400)
    return upload_file(request)
