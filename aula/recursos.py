from pathlib import Path
import re

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404, HttpResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils.http import content_disposition_header
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.http import require_safe
from django.views.static import serve

from .models import RecursoLeccion
from .views import cursos_permitidos


def permitido(request, pk):
    recurso = get_object_or_404(RecursoLeccion.objects.select_related('leccion__modulo__curso'), pk=pk, activo=True,leccion__eliminada=False,
                               leccion__modulo__curso__in=cursos_permitidos(request.user))
    curso = recurso.leccion.modulo.curso
    equipo = request.user.is_superuser or curso.formadores.filter(pk=request.user.pk).exists()
    if not equipo and not recurso.leccion.publicada:
        raise Http404
    return recurso


@login_required
@require_safe
@xframe_options_sameorigin
def visor(request, pk):
    recurso = permitido(request, pk)
    if recurso.tipo != 'documento':
        raise Http404
    respuesta = render(request, 'aula/visor.html', {'recurso': recurso})
    respuesta['Cache-Control'] = 'private, no-store'
    return respuesta


def segmento(archivo, inicio, longitud):
    try:
        archivo.seek(inicio)
        while longitud:
            bloque = archivo.read(min(65536, longitud))
            if not bloque:
                break
            longitud -= len(bloque)
            yield bloque
    finally:
        archivo.close()


@login_required
@require_safe
@xframe_options_sameorigin
def archivo(request, pk):
    recurso = permitido(request, pk)
    preview = request.GET.get('vista') == '1'
    campo = recurso.vista_pdf if preview and recurso.vista_pdf else recurso.archivo
    mime = 'application/pdf' if preview and recurso.vista_pdf else recurso.mime
    nombre = Path(recurso.nombre).stem + '.pdf' if preview and recurso.vista_pdf else recurso.nombre
    try:
        stream = campo.open('rb')
        size = campo.size
    except (OSError, ValueError):
        raise Http404('El archivo no está disponible.')
    rango = request.headers.get('Range')
    if rango:
        match = re.fullmatch(r'bytes=(\d*)-(\d*)', rango)
        try:
            if not match or not any(match.groups()):
                raise ValueError
            inicio = int(match[1]) if match[1] else max(0, size - int(match[2]))
            fin = min(int(match[2]), size - 1) if match[1] and match[2] else size - 1
            if inicio > fin or inicio >= size:
                raise ValueError
        except ValueError:
            stream.close()
            respuesta = HttpResponse(status=416)
            respuesta['Content-Range'] = f'bytes */{size}'
            respuesta['Cache-Control'] = 'private, no-store'
            return respuesta
        if request.method == 'HEAD':
            stream.close()
            respuesta = HttpResponse(status=206, content_type=mime)
        else:
            respuesta = StreamingHttpResponse(segmento(stream, inicio, fin - inicio + 1), status=206, content_type=mime)
        respuesta['Content-Length'] = str(fin - inicio + 1)
        respuesta['Content-Range'] = f'bytes {inicio}-{fin}/{size}'
    elif request.method == 'HEAD':
        stream.close()
        respuesta = HttpResponse(content_type=mime)
        respuesta['Content-Length'] = str(size)
    else:
        respuesta = FileResponse(stream, content_type=mime)
    respuesta['Content-Disposition'] = content_disposition_header(request.GET.get('descargar') == '1', nombre)
    respuesta['Accept-Ranges'] = 'bytes'
    respuesta['Cache-Control'] = 'private, no-store'
    respuesta['X-Content-Type-Options'] = 'nosniff'
    return respuesta


def media_publica(request, path):
    # También bloquea variantes con segmentos ../ y enlaces simbólicos.
    try:
        destino = (settings.MEDIA_ROOT / path).resolve()
        raiz = settings.AULA_PRIVATE_ROOT.resolve()
        if destino == raiz or raiz in destino.parents:
            raise Http404
    except (ValueError, OSError):
        raise Http404
    return serve(request, path, document_root=settings.MEDIA_ROOT)
