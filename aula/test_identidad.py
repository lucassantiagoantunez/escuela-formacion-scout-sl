from io import BytesIO
from tempfile import TemporaryDirectory
from PIL import Image
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.test import TestCase, override_settings, Client
from django.urls import reverse
from django.utils import timezone
from unittest.mock import patch
from .models import Perfil, Curso, Inscripcion, AccesoCurso, TemaForo

User = get_user_model()


class IdentidadTests(TestCase):
    def test_large_batch_is_bounded_retryable_and_atomic_per_group(self):
        director = User.objects.create_superuser('director-lotes')
        curso = Curso.objects.create(titulo='Lote de 46')
        personas = []
        for n in range(46):
            persona = User.objects.create_user(f'persona.apellido{n}', first_name='Persona', last_name=f'Apellido{n}')
            Perfil.objects.create(usuario=persona, cambiar_clave=True)
            Inscripcion.objects.create(curso=curso, cursante=persona)
            AccesoCurso.objects.create(usuario=persona, curso=curso, dias=30)
            personas.append(persona)
        self.client.force_login(director)
        url = reverse('aula:accesos_iniciales')
        r = self.client.get(url, {'curso':curso.pk})
        token = r.context['form'].initial['propuesta']
        post = {'propuesta':token, 'clave':'Temporal-2026', 'repetir':'Temporal-2026', 'confirmar':'on'}
        self.assertContains(self.client.post(url, post), 'habilitá JavaScript')
        self.assertEqual(User.objects.filter(username__startswith='persona.apellido').count(), 46)
        headers = {'HTTP_X_REQUESTED_WITH':'XMLHttpRequest'}
        original = User.set_password
        llamadas = []
        def cortar(persona, clave):
            llamadas.append(persona.pk)
            if len(llamadas) == 3:
                raise SystemExit(1)  # Same interruption as a timed-out worker.
            return original(persona, clave)
        with patch.object(User, 'set_password', cortar), self.assertRaises(SystemExit):
            self.client.post(url, post, **headers)
        self.assertEqual(User.objects.filter(username__startswith='persona.apellido').count(), 46)
        for numero in range(12):
            r = self.client.post(url, {**post, 'lote':numero}, **headers)
            self.assertEqual(r.status_code, 200)
            self.assertLessEqual(len(r.json()['resultados']), 4)
            self.assertEqual(r.json()['completadas'], min(46, (numero+1)*4))
            self.assertEqual(r.json()['terminado'], numero == 11)
            if numero == 0:
                guardados = list(User.objects.filter(pk__in=[p.pk for p in personas[:4]]).values_list('password',flat=True))
                repetida = self.client.post(url, post, **headers)
                self.assertEqual(repetida.status_code, 200)
                self.assertEqual(guardados, list(User.objects.filter(pk__in=[p.pk for p in personas[:4]]).values_list('password',flat=True)))
        self.assertEqual(User.objects.filter(username__startswith='papellido').count(), 46)
        self.assertEqual(AccesoCurso.objects.filter(inicio__isnull=True, dias=30).count(), 46)
        self.assertEqual(Inscripcion.objects.filter(curso=curso).count(), 46)
        self.assertEqual(len(set(User.objects.filter(pk__in=[p.pk for p in personas]).values_list('password', flat=True))), 46)
        self.assertEqual(self.client.post(url, {**post,'lote':12}, **headers).status_code, 400)

    def test_avatar_navigation_and_forum_keep_private_data_private(self):
        usuario = User.objects.create_user('ana', first_name='Ana', last_name='Pérez')
        Perfil.objects.create(usuario=usuario, avatar='brujula', dni='12345678')
        curso = Curso.objects.create(titulo='Curso', publicado=True)
        Inscripcion.objects.create(curso=curso, cursante=usuario)
        TemaForo.objects.create(curso=curso, autor=usuario, titulo='Hola', texto='Consulta')
        self.client.force_login(usuario)
        for url in [reverse('aula:panel'), reverse('aula:perfil'), reverse('aula:curso', args=[curso.pk])+'?vista=foro']:
            respuesta = self.client.get(url)
            self.assertContains(respuesta, '🧭')
            if url != reverse('aula:perfil'):
                self.assertNotContains(respuesta, '12345678')
        self.client.post(reverse('aula:perfil'), {'first_name':'Ana','last_name':'Pérez','avatar':'carpa'})
        self.assertEqual(Perfil.objects.get(usuario=usuario).avatar, 'carpa')
        self.client.post(reverse('aula:perfil'), {'first_name':'Ana','last_name':'Pérez','avatar':'invalido'})
        self.assertEqual(Perfil.objects.get(usuario=usuario).avatar, 'carpa')

    def test_photo_requires_opt_in_and_current_shared_course(self):
        with TemporaryDirectory() as tmp, override_settings(AULA_PRIVATE_ROOT=tmp):
            autora = User.objects.create_user('autora')
            otro = User.objects.create_user('otro')
            curso = Curso.objects.create(titulo='Curso', publicado=True)
            Inscripcion.objects.create(curso=curso, cursante=autora)
            Inscripcion.objects.create(curso=curso, cursante=otro)
            imagen = BytesIO(); Image.new('RGB', (20,20)).save(imagen, 'JPEG')
            perfil = Perfil.objects.create(usuario=autora, foto=ContentFile(imagen.getvalue(), name='foto.jpg'))
            url = reverse('aula:perfil_foto_persona', args=[autora.pk])
            self.assertEqual(self.client.get(url).status_code, 302)
            self.client.force_login(otro)
            self.assertEqual(self.client.get(url).status_code, 404)
            perfil.compartir_foto=True; perfil.save()
            respuesta = self.client.get(url)
            self.assertEqual(respuesta.status_code, 200)
            self.assertIn('no-store', respuesta['Cache-Control'])
            respuesta.close()
            perfil.avatar='arbol'; perfil.save()
            self.assertEqual(self.client.get(url).status_code, 404)
            perfil.avatar=''; perfil.save()
            AccesoCurso.objects.create(usuario=otro, curso=curso, habilitado=False)
            self.assertEqual(self.client.get(url).status_code, 404)
            self.client.force_login(User.objects.create_user('ajeno'))
            self.assertEqual(self.client.get(url).status_code, 404)

    def test_simplify_preserves_identity_and_rejects_used_accounts(self):
        director = User.objects.create_superuser('director', password='Directivo-123!')
        a = User.objects.create_user('sacha.zamora', first_name='Sacha Ivan', last_name='Zamora', password='Original-123!')
        User.objects.create_user('szamora')
        Perfil.objects.create(usuario=a, cambiar_clave=True)
        curso = Curso.objects.create(titulo='Nivel I')
        inscripcion = Inscripcion.objects.create(curso=curso, cursante=a)
        acceso = AccesoCurso.objects.create(usuario=a, curso=curso, dias=30)
        url = reverse('aula:accesos_iniciales')
        self.client.force_login(director)
        r = self.client.get(url, {'curso':curso.pk})
        self.assertEqual(r.context['filas'][0]['nuevo'], 'sizamora')
        token = r.context['form'].initial['propuesta']
        post = {'propuesta':token, 'clave':'Temporal-2026', 'repetir':'Temporal-2026', 'confirmar':'on'}
        csrf = Client(enforce_csrf_checks=True); csrf.force_login(director)
        self.assertEqual(csrf.post(url, post).status_code, 403)
        self.client.force_login(User.objects.create_user('editor', is_staff=True))
        self.assertEqual(self.client.post(url, post).status_code, 403)
        self.client.force_login(director)
        User.objects.filter(pk=a.pk).update(last_login=timezone.now())
        self.assertContains(self.client.post(url, post), 'Una cuenta ya ingresó')
        a.refresh_from_db(); self.assertEqual(a.username, 'sacha.zamora')
        User.objects.filter(pk=a.pk).update(last_login=None)
        self.assertContains(self.client.post(url, post), 'Accesos actualizados')
        a.refresh_from_db(); self.assertEqual(a.username, 'sizamora')
        self.assertTrue(a.check_password('Temporal-2026'))
        self.assertFalse(a.is_staff)
        self.assertTrue(a.perfil_aula.cambiar_clave)
        acceso.refresh_from_db(); self.assertIsNone(acceso.inicio)
        self.assertTrue(Inscripcion.objects.filter(pk=inscripcion.pk,cursante=a).exists())
        self.assertContains(self.client.post(url, post), 'Un nombre de usuario cambió')
