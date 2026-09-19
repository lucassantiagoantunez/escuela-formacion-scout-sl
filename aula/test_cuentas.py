from datetime import timedelta
from io import BytesIO
from tempfile import TemporaryDirectory
from unittest.mock import patch
from PIL import Image
from django.test import TestCase, Client, override_settings
from django.contrib.auth import get_user_model
from django.contrib.admin.models import LogEntry
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from .models import Curso, Inscripcion, Modulo, Leccion, Prueba, Perfil, AccesoCurso, PermisoFormador
from .permisos import permisos
from .usuarios import AccesoForm

User = get_user_model()


class CuentasTests(TestCase):
    def setUp(self):
        self.director = User.objects.create_superuser('direccion', password='Inicial-de-prueba-427!')
        self.alumno = User.objects.create_user('alumno', first_name='Ana', last_name='Prueba', password='Inicial-de-prueba-427!')
        self.curso = Curso.objects.create(titulo='Nivel I', publicado=True)
        self.inscripcion = Inscripcion.objects.create(curso=self.curso, cursante=self.alumno)
        self.modulo = Modulo.objects.create(curso=self.curso, titulo='Historia')
        self.clase = Leccion.objects.create(modulo=self.modulo, titulo='Clase', publicada=True)

    def test_foto_private_validation_removal_and_metadata(self):
        with TemporaryDirectory() as tmp, override_settings(AULA_PRIVATE_ROOT=tmp):
            self.client.force_login(self.alumno)
            raw = BytesIO()
            im = Image.new('RGB', (1000, 800), 'green')
            exif = Image.Exif(); exif[270] = 'dato privado de prueba'
            im.save(raw, 'JPEG', exif=exif)
            respuesta = self.client.post(reverse('aula:perfil'), {'first_name':'Ana', 'last_name':'Prueba',
                'foto':SimpleUploadedFile('foto.jpg', raw.getvalue(), content_type='image/jpeg')})
            self.assertEqual(respuesta.status_code, 302)
            p = Perfil.objects.get(usuario=self.alumno)
            with p.foto.open('rb') as f, Image.open(f) as imagen:
                self.assertLessEqual(imagen.width, 640)
                self.assertFalse(imagen.getexif())
            self.assertEqual(self.client.get(reverse('aula:perfil')).status_code, 200)
            self.assertEqual(self.client.get(reverse('aula:perfil_foto')).status_code, 200)
            otro = User.objects.create_user('otro')
            self.client.force_login(otro)
            self.assertEqual(self.client.get(reverse('aula:perfil_foto_persona', args=[self.alumno.pk])).status_code, 404)
            self.client.force_login(self.director)
            self.assertEqual(self.client.get(reverse('admin:aula_perfil_change', args=[p.pk])).status_code, 200)
            self.client.force_login(self.alumno)
            r = self.client.post(reverse('aula:perfil'), {'first_name':'Ana', 'last_name':'Prueba',
                'foto':SimpleUploadedFile('f.jpg', b'<script>bad</script>', content_type='image/jpeg')})
            self.assertEqual(r.status_code, 200)
            p.refresh_from_db(); self.assertTrue(p.foto)
            with self.captureOnCommitCallbacks(execute=True):
                self.client.post(reverse('aula:perfil'), {'first_name':'Ana', 'last_name':'Prueba','eliminar_foto':'on'})
            p.refresh_from_db(); self.assertFalse(p.foto)
            self.assertEqual(self.client.get(reverse('aula:perfil_foto')).status_code, 404)

    def test_temporary_password_requires_change_and_invalidates_other_sessions(self):
        Perfil.objects.create(usuario=self.alumno, cambiar_clave=True)
        self.client.force_login(self.alumno)
        otro = Client(); otro.force_login(self.alumno)
        r = self.client.get(reverse('aula:curso', args=[self.curso.pk]))
        self.assertRedirects(r, reverse('aula:password_change'))
        r = self.client.post(reverse('aula:password_change'), {'old_password':'incorrecta', 'new_password1':'Nueva-segura-748!', 'new_password2':'Nueva-segura-748!'})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(Perfil.objects.get(usuario=self.alumno).cambiar_clave)
        self.client.post(reverse('aula:password_change'), {'old_password':'Inicial-de-prueba-427!', 'new_password1':'Nueva-segura-748!', 'new_password2':'Nueva-segura-748!'})
        self.assertFalse(Perfil.objects.get(usuario=self.alumno).cambiar_clave)
        self.assertEqual(self.client.get(reverse('aula:perfil')).status_code, 200)
        self.assertEqual(otro.get(reverse('aula:perfil')).status_code, 302)
        self.assertNotIn('Nueva-segura', str(list(LogEntry.objects.values_list('change_message', flat=True))))
        csrf = Client(enforce_csrf_checks=True); csrf.force_login(self.alumno)
        self.assertEqual(csrf.post(reverse('aula:password_change'), {}).status_code, 403)

    def test_access_starts_once_and_expires_for_all_learning_paths(self):
        acceso = AccesoCurso.objects.create(usuario=self.alumno, curso=self.curso, dias=30)
        self.assertIsNone(acceso.inicio)
        self.client.force_login(self.alumno)
        ahora = timezone.now()
        with patch('django.utils.timezone.now', return_value=ahora):
            self.client.get(reverse('aula:panel'))
        acceso.refresh_from_db()
        self.assertEqual(acceso.inicio, ahora)
        self.assertEqual(acceso.fin, ahora+timedelta(days=30))
        p = Prueba.objects.create(leccion=Leccion.objects.create(modulo=self.modulo,titulo='Prueba',publicada=True), tipo='quiz')
        with patch('django.utils.timezone.now', return_value=acceso.fin):
            self.client.force_login(self.alumno)
            self.assertEqual(self.client.get(reverse('aula:curso',args=[self.curso.pk])).status_code, 404)
            self.assertEqual(self.client.post(reverse('aula:completar',args=[self.clase.pk])).status_code, 404)
            self.assertEqual(self.client.post(reverse('aula:prueba_iniciar',args=[p.pk])).status_code, 404)
            self.assertEqual(self.client.post(reverse('aula:foro_nuevo',args=[self.curso.pk]), {}).status_code, 404)
            self.assertEqual(self.client.get(reverse('aula:perfil')).status_code, 200)
        acceso.refresh_from_db(); self.assertEqual(acceso.inicio, ahora)
        self.assertTrue(Inscripcion.objects.filter(pk=self.inscripcion.pk).exists())
        self.curso.formadores.add(self.alumno)
        AccesoCurso.objects.filter(pk=acceso.pk).update(habilitado=False)
        self.assertFalse(any(permisos(self.alumno,self.curso).values()))
        form = AccesoForm({'habilitado':'on','dias':60,'inicio':ahora.isoformat(), 'recalcular':'on'}, instance=acceso)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.save().fin, ahora+timedelta(days=60))

    def test_import_no_resets_or_privilege_escalation_and_admin_only(self):
        url = reverse('aula:usuarios_importar')
        data = {'curso':self.curso.pk,'dias':30,'confirmar':'on','listado':'usuario,nombre,apellido,email,rol\nnueva,Maria,Nueva,maria@example.test,cursante\nprofe,Juan,Docente,,formador\nalumno,Ana,Prueba,,formador\n'}
        self.client.force_login(self.alumno)
        self.assertEqual(self.client.post(url,data).status_code,403)
        self.client.force_login(self.director)
        clave_previa = self.alumno.password
        r=self.client.post(url,data)
        self.assertEqual(r.status_code,200)
        self.assertContains(r, 'Cuentas preparadas')
        self.assertIn('no-store',r['Cache-Control'])
        nuevas = r.context['resultados']
        self.assertTrue(User.objects.get(username='nueva').check_password(nuevas[0]['clave']))
        profe=User.objects.get(username='profe')
        self.assertFalse(profe.is_staff or profe.is_superuser)
        permisos_profe=permisos(profe,self.curso)
        self.assertTrue(permisos_profe['corregir']); self.assertFalse(permisos_profe['emitir'])
        self.alumno.refresh_from_db(); self.assertEqual(self.alumno.password,clave_previa)
        self.assertFalse(self.curso.formadores.filter(pk=self.alumno.pk).exists())
        self.assertFalse(nuevas[2]['clave'])
        # Safe duplicate submission: no new users/password resets.
        r=self.client.post(url,data)
        self.assertTrue(all(not row['clave'] for row in r.context['resultados']))
        self.assertEqual(User.objects.count(),4)
        self.assertNotIn(nuevas[0]['clave'],str(list(LogEntry.objects.values_list('change_message',flat=True))))
        self.assertFalse(any('password' in k for k in self.client.session.keys()))

    def test_disable_protect_history_and_delete_only_unused(self):
        self.client.force_login(self.director)
        url=reverse('aula:usuario',args=[self.alumno.pk])
        self.client.post(url,{'accion':'eliminar','confirmacion':self.alumno.username})
        self.assertTrue(User.objects.filter(pk=self.alumno.pk).exists())
        self.client.post(url,{'accion':'desactivar'})
        self.alumno.refresh_from_db(); self.assertFalse(self.alumno.is_active)
        self.assertTrue(Inscripcion.objects.filter(pk=self.inscripcion.pk).exists())
        self.client.post(url,{'accion':'activar'})
        self.alumno.refresh_from_db(); self.assertTrue(self.alumno.is_active)
        self.assertEqual(self.client.post(reverse('aula:usuario',args=[self.director.pk]),{'accion':'desactivar'}).status_code,403)
        temporal=User.objects.create_user('sinactividad')
        self.client.post(reverse('aula:usuario',args=[temporal.pk]),{'accion':'eliminar','confirmacion':'sinactividad'})
        self.assertFalse(User.objects.filter(pk=temporal.pk).exists())
