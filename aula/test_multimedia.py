import io
from pathlib import Path
import tempfile
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from pypdf import PdfWriter

from .archivos import validar_archivo, preparar_recursos
from .contenido import limpiar_html, youtube_embed
from .models import Curso, Inscripcion, Leccion, Modulo, RecursoLeccion


def pdf_upload(name='material.pdf'):
    buffer = io.BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=400, height=300)
    writer.write(buffer)
    return SimpleUploadedFile(name, buffer.getvalue(), 'application/pdf')


class MultimediaTests(TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.media = Path(self.temp.name)
        self.override = override_settings(MEDIA_ROOT=self.media, AULA_PRIVATE_ROOT=self.media / '.aula_privada')
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.director = get_user_model().objects.create_superuser('director')
        self.alumno = get_user_model().objects.create_user('alumno')
        self.otro = get_user_model().objects.create_user('otro')
        self.curso = Curso.objects.create(titulo='Nivel I', publicado=True)
        self.modulo = Modulo.objects.create(curso=self.curso, titulo='Historia')
        self.inscripcion = Inscripcion.objects.create(curso=self.curso, cursante=self.alumno)
        self.client.force_login(self.director)

    def subir(self, archivos=None):
        response = self.client.post(reverse('aula:gestion_modulo_leccion_nueva', args=[self.curso.pk, self.modulo.pk]),
            {'titulo': 'Mi clase', 'texto': '<h2>Objetivos</h2><p><strong>Aprender</strong></p><table><tbody><tr><td>A</td></tr></tbody></table>',
             'archivos': archivos or [pdf_upload()], 'publicada': 'on'})
        self.assertEqual(response.status_code, 302)
        return Leccion.objects.get(titulo='Mi clase')

    def test_texto_y_pdf_se_guardan_y_muestran_dentro_de_clase(self):
        leccion = self.subir()
        self.assertTrue(leccion.texto_enriquecido)
        recurso = leccion.recursos.get()
        self.assertTrue(recurso.archivo.storage.exists(recurso.archivo.name))
        self.assertTrue(Path(recurso.archivo.path).is_relative_to(self.media.resolve()))
        self.client.force_login(self.alumno)
        response = self.client.get(reverse('aula:curso', args=[self.curso.pk]))
        self.assertContains(response, '<strong>Aprender</strong>')
        self.assertContains(response, '<table>')
        self.assertContains(response, reverse('aula:recurso_visor', args=[recurso.pk]))
        response = self.client.get(reverse('aula:recurso_archivo', args=[recurso.pk]))
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertEqual(response['Cache-Control'], 'private, no-store')
        self.assertTrue(b''.join(response.streaming_content).startswith(b'%PDF-'))

    def test_permisos_de_visor_archivo_y_publicacion(self):
        recurso = self.subir().recursos.get()
        urls = [reverse('aula:recurso_visor', args=[recurso.pk]), reverse('aula:recurso_archivo', args=[recurso.pk])]
        self.client.logout()
        for url in urls:
            self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(self.otro)
        for url in urls:
            self.assertEqual(self.client.get(url).status_code, 404)
        self.client.force_login(self.alumno)
        recurso.leccion.publicada = False
        recurso.leccion.save()
        for url in urls:
            self.assertEqual(self.client.get(url).status_code, 404)
        self.curso.formadores.add(self.otro)
        self.client.force_login(self.otro)
        self.assertEqual(self.client.get(urls[0]).status_code, 200)

    def test_revocar_matricula_revoca_descarga(self):
        recurso = self.subir().recursos.get()
        self.inscripcion.activa = False
        self.inscripcion.save()
        self.client.force_login(self.alumno)
        self.assertEqual(self.client.get(reverse('aula:recurso_archivo', args=[recurso.pk])).status_code, 404)

    def test_no_hay_acceso_por_media_publica(self):
        recurso = self.subir().recursos.get()
        self.client.logout()
        for path in [f'/media/.aula_privada/{recurso.archivo.name}', f'/media/x/../.aula_privada/{recurso.archivo.name}']:
            self.assertEqual(self.client.get(path).status_code, 404)
        with self.assertRaises(ValueError):
            recurso.archivo.url
        (self.media / 'publico.txt').write_text('Material público')
        response = self.client.get('/media/publico.txt')
        self.assertEqual(response.status_code, 200)
        response.close()

    def test_range_y_head_para_reproduccion(self):
        recurso = self.subir([SimpleUploadedFile('video.mp4', b'\x00\x00\x00\x18ftypisom' + b'v' * 100)]).recursos.get()
        url = reverse('aula:recurso_archivo', args=[recurso.pk])
        self.client.force_login(self.alumno)
        response = self.client.get(url, HTTP_RANGE='bytes=4-7')
        self.assertEqual(response.status_code, 206)
        self.assertEqual(b''.join(response.streaming_content), b'ftyp')
        self.assertEqual(response['Content-Length'], '4')
        response = self.client.get(url, HTTP_RANGE='bytes=-4')
        self.assertEqual(b''.join(response.streaming_content), b'vvvv')
        self.assertEqual(self.client.get(url, HTTP_RANGE='bytes=999-1000').status_code, 416)
        self.assertEqual(self.client.get(url, HTTP_RANGE='bytes=0-1,4-5').status_code, 416)
        self.assertEqual(self.client.head(url)['Content-Length'], '112')

    def test_retirar_recurso_conserva_archivo_y_revoca_acceso(self):
        recurso = self.subir().recursos.get()
        url = reverse('aula:recurso_retirar', args=[recurso.pk])
        self.assertEqual(self.client.get(url).status_code, 405)
        self.client.force_login(self.alumno)
        self.assertEqual(self.client.post(url).status_code, 403)
        self.client.force_login(self.director)
        self.assertEqual(self.client.post(url).status_code, 302)
        recurso.refresh_from_db()
        self.assertFalse(recurso.activo)
        self.assertTrue(Path(recurso.archivo.path).is_file())
        self.assertEqual(self.client.get(reverse('aula:recurso_archivo', args=[recurso.pk])).status_code, 404)

    def test_formato_falso_y_limites(self):
        for upload in [SimpleUploadedFile('virus.pdf', b'<html>falso</html>'), SimpleUploadedFile('video.mp4', b'basura'), SimpleUploadedFile('x.exe', b'MZ')]:
            with self.assertRaises(ValidationError):
                validar_archivo(upload)
        with override_settings(AULA_DOCUMENT_MAX_BYTES=10):
            with self.assertRaises(ValidationError):
                validar_archivo(pdf_upload())

    def test_error_en_archivo_no_modifica_clase(self):
        self.subir()
        leccion = Leccion.objects.get()
        response = self.client.post(reverse('aula:gestion_leccion_editar', args=[self.curso.pk, leccion.pk]),
            {'modulo': self.modulo.pk, 'titulo': 'No guardar', 'archivos': SimpleUploadedFile('x.pdf', b'no es PDF')})
        self.assertContains(response, 'No se guardaron los cambios')
        leccion.refresh_from_db()
        self.assertEqual(leccion.titulo, 'Mi clase')
        self.assertEqual(leccion.recursos.count(), 1)

    def test_fallo_conversion_no_crea_clase(self):
        with patch('aula.gestion.preparar_recursos', side_effect=ValidationError('Conversión fallida')):
            response = self.client.post(reverse('aula:gestion_modulo_leccion_nueva', args=[self.curso.pk, self.modulo.pk]), {'titulo': 'No guardar'})
        self.assertContains(response, 'Conversión fallida')
        self.assertFalse(Leccion.objects.exists())

    def test_office_conserva_original_y_sirve_pdf_privado(self):
        original = Path(__file__).with_name('fixtures_multimedia').joinpath('ejemplo.docx').read_bytes()
        vista = pdf_upload().read()
        with patch('aula.archivos.convertir_office', return_value=vista):
            recurso = self.subir([SimpleUploadedFile('Guía.docx', original)]).recursos.get()
        self.client.force_login(self.alumno)
        url = reverse('aula:recurso_archivo', args=[recurso.pk])
        response = self.client.get(url + '?vista=1')
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertEqual(b''.join(response.streaming_content), vista)
        response = self.client.get(url + '?descargar=1')
        self.assertIn('attachment', response['Content-Disposition'])
        self.assertEqual(b''.join(response.streaming_content), original)

    def test_no_acumula_conversiones_en_una_solicitud(self):
        with patch('aula.archivos.convertir_office') as convertir:
            with self.assertRaisesMessage(ValidationError, 'un Word o PowerPoint por vez'):
                preparar_recursos([SimpleUploadedFile('a.docx', b'a'), SimpleUploadedFile('b.pptx', b'b')])
            convertir.assert_not_called()

    def test_sanitizacion_y_preservacion_de_texto_anterior(self):
        sucio = '<p style="color:red;position:fixed;background-image:url(https://evil.test/a)">Hola<script>alert(1)</script><a href="javascript:alert(1)">enlace</a></p><iframe src="https://evil.test"></iframe>'
        limpio = limpiar_html(sucio)
        for malo in ['<script', '<iframe', 'javascript:', 'position:', 'background-image']:
            self.assertNotIn(malo, limpio)
        self.assertIn('color:red', limpio.replace(' ', ''))
        leccion = Leccion.objects.create(modulo=self.modulo, titulo='Anterior', texto='<script>texto literal</script>\nOtro párrafo')
        self.assertIn('&lt;script&gt;', leccion.contenido_html)

    def test_youtube_se_inserta_y_rechaza_hosts_falsos(self):
        for url in ['https://youtu.be/abcdefghijk', 'https://www.youtube.com/watch?v=abcdefghijk', 'https://youtube.com/shorts/abcdefghijk']:
            self.assertIn('/embed/abcdefghijk', youtube_embed(url))
        for url in ['https://youtube.com.evil.test/watch?v=abcdefghijk', 'https://youtube.com@evil.test/watch?v=abcdefghijk', 'javascript:alert(1)']:
            self.assertEqual(youtube_embed(url), '')
        leccion = Leccion.objects.create(modulo=self.modulo, titulo='Video', video_url='https://youtu.be/abcdefghijk', publicada=True)
        response = self.client.get(reverse('aula:curso', args=[self.curso.pk]))
        self.assertContains(response, 'src="https://www.youtube-nocookie.com/embed/abcdefghijk?rel=0"')
