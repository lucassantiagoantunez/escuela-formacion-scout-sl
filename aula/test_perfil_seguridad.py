from datetime import date, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.admin.models import LogEntry
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from core.models import Noticia, Material, ResultadoMemoria, JuegoMemoria
from core.seguridad import GRUPO_COMUNICACION
from .models import Curso, Inscripcion, Perfil, Certificado, CierreCurso


class PerfilSeguridadTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        U = get_user_model()
        cls.alumno = U.objects.create_user('perfil-alumno', first_name='Nombre', last_name='Anterior')
        cls.otro = U.objects.create_user('perfil-otro')
        cls.director = U.objects.create_superuser('perfil-direccion')
        cls.editor = U.objects.create_user('perfil-editor', is_staff=True)
        cls.editor.groups.add(Group.objects.get(name=GRUPO_COMUNICACION))
        cls.curso = Curso.objects.create(titulo='Privado', publicado=True)
        cls.inscripcion = Inscripcion.objects.create(curso=cls.curso, cursante=cls.alumno)
        cls.certificado = Certificado.objects.create(inscripcion=cls.inscripcion, tipo='participacion',
            datos={'nombre': 'Nombre Anterior', 'curso': 'Privado'}, responsable=cls.director)
        cls.cierre = CierreCurso.objects.create(inscripcion=cls.inscripcion, responsable=cls.director,
            nombre_certificado='Nombre Anterior')
        cls.url = reverse('aula:perfil')

    def test_propietario_campos_opcionales_sin_escalar_ni_alterar_certificados(self):
        self.assertEqual(self.client.get(self.url).status_code, 302)
        self.client.force_login(self.alumno)
        self.assertEqual(self.client.get(self.url).status_code, 200)
        self.assertFalse(Perfil.objects.filter(usuario=self.alumno).exists())
        data = {'first_name': 'Nombre nuevo', 'last_name': 'Apellido', 'dni': '12.345.678',
                'sacramentos': 'Dato reservado', 'usuario': self.otro.pk, 'is_superuser': 'on',
                'is_staff': 'on', 'groups': Group.objects.get(name=GRUPO_COMUNICACION).pk}
        self.assertRedirects(self.client.post(self.url, data), self.url)
        self.alumno.refresh_from_db()
        self.assertFalse(self.alumno.is_staff or self.alumno.is_superuser)
        self.assertEqual(self.alumno.groups.count(), 0)
        perfil = Perfil.objects.get(usuario=self.alumno)
        self.assertEqual(perfil.dni, '12345678')
        self.assertFalse(Perfil.objects.filter(usuario=self.otro).exists())
        self.certificado.refresh_from_db(); self.cierre.refresh_from_db()
        self.assertEqual(self.certificado.datos['nombre'], 'Nombre Anterior')
        self.assertEqual(self.cierre.nombre_certificado, 'Nombre Anterior')
        self.assertNotIn('12345678', LogEntry.objects.latest('pk').change_message)
        self.assertNotIn('Dato reservado', LogEntry.objects.latest('pk').change_message)
        respuesta = self.client.get(self.url)
        self.assertIn('no-store', respuesta['Cache-Control'])
        self.assertRedirects(self.client.post(self.url, {'first_name': 'Nombre', 'last_name': 'Apellido'}), self.url)
        perfil.refresh_from_db(); self.assertEqual(perfil.dni, '')

    def test_validacion_y_csrf(self):
        self.client.force_login(self.alumno)
        data = {'first_name': '', 'last_name': 'A', 'dni': 'abc', 'cantidad_hijos': '-1',
                'fecha_nacimiento': (timezone.localdate() + timedelta(days=1)).isoformat()}
        r = self.client.post(self.url, data)
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Perfil.objects.filter(usuario=self.alumno).exists())
        self.alumno.refresh_from_db(); self.assertEqual(self.alumno.first_name, 'Nombre')
        csrf = Client(enforce_csrf_checks=True); csrf.force_login(self.alumno)
        self.assertEqual(csrf.post(self.url, {'first_name': 'Nombre', 'last_name': 'Otro'}).status_code, 403)
        perfil = Perfil(fecha_nacimiento=date(2000, 1, 1))
        self.assertEqual(perfil.edad, timezone.localdate().year - 2000)

    def test_perfiles_privados_incluso_formador_y_editor_con_permiso_directo(self):
        perfil = Perfil.objects.create(usuario=self.alumno, dni='12345678', sacramentos='Privado sacramentos')
        self.curso.formadores.add(self.editor)
        self.editor.user_permissions.add(Permission.objects.get(codename='view_perfil'))
        self.client.force_login(self.editor)
        for url in (reverse('admin:aula_perfil_changelist'), reverse('admin:aula_perfil_change', args=[perfil.pk])):
            self.assertEqual(self.client.get(url).status_code, 403)
        for url in (self.url, reverse('aula:curso', args=[self.curso.pk]), reverse('aula:panel')):
            r = self.client.get(url)
            self.assertNotContains(r, '12345678'); self.assertNotContains(r, 'Privado sacramentos')
        self.client.force_login(self.director)
        self.assertContains(self.client.get(reverse('admin:aula_perfil_change', args=[perfil.pk])), '12345678')

    def test_comunicacion_puede_publicar_pero_no_administrar(self):
        self.client.force_login(self.editor)
        self.assertContains(self.client.get(reverse('aula:comunicacion')), 'Publicar contenido')
        for modelo in ('noticia', 'material', 'categoriabiblioteca'):
            self.assertEqual(self.client.get(reverse(f'admin:core_{modelo}_changelist')).status_code, 200)
            self.assertEqual(self.client.get(reverse(f'admin:core_{modelo}_add')).status_code, 200)
        r = self.client.post(reverse('admin:core_noticia_add'), {'titulo': 'Novedad', 'resumen': 'Resumen',
            'contenido': '<p onclick="alert(1)">Texto</p><script>alert(1)</script>', 'publicada': 'on', '_save': 'Guardar'})
        self.assertEqual(r.status_code, 302)
        noticia = Noticia.objects.get(titulo='Novedad')
        self.assertTrue(noticia.publicada); self.assertNotIn('<script', noticia.contenido); self.assertNotIn('onclick', noticia.contenido)
        for url in ('/admin/auth/user/', '/admin/auth/group/', '/admin/core/componenteinteractivo/',
                    '/admin/core/pagina/', '/admin/core/contenidoinicio/', '/admin/core/interescurso/',
                    '/admin/aula/curso/', '/aula/gestion/', f'/aula/gestion/inscripciones/{self.inscripcion.pk}/cierre/'):
            self.assertEqual(self.client.get(url).status_code, 403, url)
        self.assertEqual(self.client.post(reverse('admin:core_noticia_delete', args=[noticia.pk]), {'post': 'yes'}).status_code, 403)
        self.assertTrue(Noticia.objects.filter(pk=noticia.pk).exists())

    def test_borrar_resultado_y_codigo_denegados_por_ser_staff(self):
        juego = JuegoMemoria.objects.create(titulo='Juego')
        resultado = ResultadoMemoria.objects.create(juego=juego,nombre='Participante',movimientos=1)
        self.client.force_login(self.editor)
        self.assertEqual(self.client.post(reverse('admin:core_resultadomemoria_delete',args=[resultado.pk]), {'post':'yes'}).status_code,403)
        self.assertTrue(ResultadoMemoria.objects.filter(pk=resultado.pk).exists())
        self.editor.user_permissions.add(Permission.objects.get(codename='change_componenteinteractivo'))
        self.assertEqual(self.client.get('/admin/core/componenteinteractivo/').status_code,403)

    def test_archivos_y_html_no_ejecutables(self):
        from core.seguridad import MaterialEditorialForm
        from core.templatetags.contenido_seguro import editorial_seguro
        f=MaterialEditorialForm({'titulo':'Archivo'}, {'archivo': SimpleUploadedFile('ataque.html',b'<script>alert(1)</script>',content_type='text/html')})
        self.assertFalse(f.is_valid()); self.assertIn('archivo',f.errors)
        self.assertNotIn('onerror',editorial_seguro('<img src=x onerror=alert(1)><p>Hola</p>'))
        self.assertNotIn('javascript:',editorial_seguro('<a href="javascript:alert(1)">Hola</a>'))
        with TemporaryDirectory() as d, override_settings(MEDIA_ROOT=Path(d),AULA_PRIVATE_ROOT=Path(d)/'.privado'):
            (Path(d)/'archivo.html').write_text('<script>alert(1)</script>')
            r=self.client.get('/media/archivo.html')
            self.assertEqual(r.status_code,200)
            self.assertIn('attachment',r['Content-Disposition']); self.assertEqual(r['Content-Type'],'application/octet-stream')
            self.assertIn('sandbox',r['Content-Security-Policy'])
            r.close()
        self.client.force_login(self.alumno)
        self.assertEqual(self.client.post('/ckeditor5/image_upload/').status_code,403)
        self.client.force_login(self.editor)
        self.assertEqual(self.client.post('/ckeditor5/image_upload/',{'upload':SimpleUploadedFile('p.svg',b'<svg/>')}).status_code,400)
