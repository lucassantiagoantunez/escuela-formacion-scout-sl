import io
import os
from pathlib import Path
import shutil
import subprocess
import signal
import tempfile
import zipfile
from contextlib import contextmanager

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from PIL import Image, UnidentifiedImageError
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from .models import RecursoLeccion

MIMES = {'.pdf': 'application/pdf', '.doc': 'application/msword',
    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    '.ppt': 'application/vnd.ms-powerpoint',
    '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    '.mp4': 'video/mp4', '.webm': 'video/webm', '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg'}


def validar_archivo(upload):
    ext = Path(upload.name).suffix.lower()
    if ext not in MIMES:
        raise ValidationError('Usá PDF, Word (.doc o .docx), PowerPoint (.ppt o .pptx), MP4, WebM, JPG o PNG.')
    limite = settings.AULA_VIDEO_MAX_BYTES if ext in {'.mp4', '.webm'} else settings.AULA_DOCUMENT_MAX_BYTES
    if not upload.size or upload.size > limite:
        raise ValidationError(f'El archivo debe tener contenido y pesar menos de {limite // (1024*1024)} MB.')
    upload.seek(0)
    cabecera = upload.read(16)
    upload.seek(0)
    try:
        if ext == '.pdf':
            if not cabecera.startswith(b'%PDF-'):
                raise ValueError
            pdf = PdfReader(upload)
            if pdf.is_encrypted or not 1 <= len(pdf.pages) <= 500:
                raise ValueError
        elif ext in {'.docx', '.pptx'}:
            with zipfile.ZipFile(upload) as z:
                nombres = z.namelist()
                necesario = 'word/document.xml' if ext == '.docx' else 'ppt/presentation.xml'
                if necesario not in nombres or '[Content_Types].xml' not in nombres:
                    raise ValueError
                if len(nombres) > 5000 or sum(x.file_size for x in z.infolist()) > 150 * 1024 * 1024:
                    raise ValueError
                if any('vbaproject' in n.lower() or '/embeddings/' in n.lower() for n in nombres):
                    raise ValueError
        elif ext in {'.doc', '.ppt'}:
            if not cabecera.startswith(bytes.fromhex('d0cf11e0a1b11ae1')):
                raise ValueError
        elif ext == '.mp4':
            if cabecera[4:8] != b'ftyp':
                raise ValueError
        elif ext == '.webm':
            if not cabecera.startswith(bytes.fromhex('1a45dfa3')):
                raise ValueError
        else:
            with Image.open(upload) as img:
                if img.format not in {'JPEG', 'PNG'} or img.width * img.height > 30_000_000:
                    raise ValueError
                img.verify()
    except (ValueError, OSError, zipfile.BadZipFile, UnidentifiedImageError, PdfReadError, Image.DecompressionBombError) as exc:
        raise ValidationError('No pudimos leer el archivo. Verificá su formato, que no tenga contraseña ni macros y que no esté dañado.') from exc
    finally:
        upload.seek(0)
    return ext


@contextmanager
def turno_conversion():
    # Un único proceso en este servidor de memoria limitada, sin hacer esperar
    # una solicitud detrás de otra ni bloquear las clases de los cursantes.
    with open(Path(tempfile.gettempdir()) / 'edifos-office.lock', 'a') as lock:
        if os.name != 'nt':
            import fcntl
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise ValidationError('Hay otro documento convirtiéndose. Esperá unos segundos y volvé a guardar.') from exc
        try:
            yield
        finally:
            if os.name != 'nt':
                fcntl.flock(lock, fcntl.LOCK_UN)


def convertir_office(upload):
    with turno_conversion():
        return _convertir_office(upload)


def _convertir_office(upload):
    executable = settings.AULA_OFFICE_EXECUTABLE
    if not Path(executable).is_file():
        raise ValidationError('La vista de Word y PowerPoint no está disponible en este momento. Probá nuevamente o cargá una versión PDF.')
    with tempfile.TemporaryDirectory(prefix='edifos-office-') as temporal:
        carpeta = Path(temporal)
        entrada = carpeta / ('documento' + Path(upload.name).suffix.lower())
        with entrada.open('wb') as salida:
            for chunk in upload.chunks():
                salida.write(chunk)
        perfil = carpeta / 'perfil'
        (perfil / 'user').mkdir(parents=True)
        # Impedir macros y actualizaciones automáticas de vínculos al abrir.
        (perfil / 'user/registrymodifications.xcu').write_text('''<?xml version="1.0"?><oor:items xmlns:oor="http://openoffice.org/2001/registry"><item oor:path="/org.openoffice.Office.Common/Security/Scripting"><prop oor:name="MacroSecurityLevel" oor:op="fuse"><value>3</value></prop></item><item oor:path="/org.openoffice.Office.Common/Misc"><prop oor:name="AllowDocumentMacroExecution" oor:op="fuse"><value>false</value></prop></item><item oor:path="/org.openoffice.Office.Writer/Content/Update"><prop oor:name="Link" oor:op="fuse"><value>2</value></prop></item></oor:items>''', encoding='utf-8')
        env = os.environ.copy()
        base = settings.BASE_DIR / '.office'
        env['LD_LIBRARY_PATH'] = ':'.join(str(base / p) for p in ['usr/lib/libreoffice/program', 'usr/lib/x86_64-linux-gnu', 'lib/x86_64-linux-gnu'])
        env['SAL_USE_VCLPLUGIN'] = 'svp'
        try:
            process = subprocess.Popen([str(executable), f'-env:UserInstallation={perfil.as_uri()}',
                '--headless', '--nologo', '--nodefault', '--nolockcheck', '--norestore',
                '--convert-to', 'pdf', '--outdir', str(carpeta), str(entrada)],
                env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=os.name != 'nt')
            try:
                process.communicate(timeout=22)
            except subprocess.TimeoutExpired:
                if os.name != 'nt':
                    os.killpg(process.pid, signal.SIGKILL)
                else:
                    process.kill()
                process.communicate()
                raise
            pdf = carpeta / 'documento.pdf'
            if process.returncode or not pdf.is_file() or pdf.stat().st_size > settings.AULA_DOCUMENT_MAX_BYTES:
                raise ValueError
            data = pdf.read_bytes()
            if not 1 <= len(PdfReader(io.BytesIO(data)).pages) <= 500:
                raise ValueError
            return data
        except (subprocess.TimeoutExpired, OSError, ValueError, PdfReadError) as exc:
            raise ValidationError('No pudimos preparar la vista del documento. Puede ser demasiado complejo, estar protegido o necesitar fuentes especiales. Probá exportarlo a PDF.') from exc
        finally:
            upload.seek(0)


def preparar_recursos(uploads):
    preparados = []
    if len(uploads) > 5 or sum(u.size for u in uploads) > 180 * 1024 * 1024:
        raise ValidationError('Cargá hasta 5 archivos por vez y un máximo total de 180 MB.')
    if sum(Path(u.name).suffix.lower() in {'.doc', '.docx', '.ppt', '.pptx'} for u in uploads) > 1:
        raise ValidationError('Agregá un Word o PowerPoint por vez. Guardá la clase y luego podés agregar el siguiente.')
    settings.AULA_PRIVATE_ROOT.mkdir(parents=True, exist_ok=True)
    if uploads and shutil.disk_usage(settings.AULA_PRIVATE_ROOT).free < sum(u.size for u in uploads) * 3 + 200 * 1024 * 1024:
        raise ValidationError('No queda espacio suficiente para estos archivos. Avisá a Dirección antes de volver a intentar.')
    for upload in uploads:
        ext = validar_archivo(upload)
        vista = convertir_office(upload) if ext in {'.doc', '.docx', '.ppt', '.pptx'} else None
        tipo = 'video' if ext in {'.mp4', '.webm'} else ('imagen' if ext in {'.png', '.jpg', '.jpeg'} else 'documento')
        preparados.append((upload, tipo, MIMES[ext], vista))
    return preparados


def guardar_recursos(leccion, preparados, guardados):
    orden = leccion.recursos.count()
    for index, (upload, tipo, mime, vista) in enumerate(preparados, start=1):
        recurso = RecursoLeccion(leccion=leccion, nombre=Path(upload.name).name[:255], tipo=tipo, mime=mime, orden=orden + index)
        recurso.archivo.save(upload.name, upload, save=False)
        guardados.append(recurso.archivo)
        if vista:
            recurso.vista_pdf.save('vista.pdf', ContentFile(vista), save=False)
            guardados.append(recurso.vista_pdf)
        recurso.save()
