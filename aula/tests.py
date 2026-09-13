from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse
from .models import Curso, Inscripcion, Modulo, Leccion, Progreso
from django.contrib.admin.models import LogEntry
from unittest.mock import patch


class AulaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alumno = get_user_model().objects.create_user('alumno', password='Clave-de-prueba-927')
        cls.otro = get_user_model().objects.create_user('otro')
        cls.formador = get_user_model().objects.create_user('formador')
        cls.curso = Curso.objects.create(titulo='Nivel I', publicado=True)
        cls.curso.formadores.add(cls.formador)
        cls.inscripcion = Inscripcion.objects.create(curso=cls.curso, cursante=cls.alumno)
        cls.modulo = Modulo.objects.create(curso=cls.curso, titulo='Historia')
        cls.leccion = Leccion.objects.create(modulo=cls.modulo, titulo='Origen', publicada=True)
        cls.oculta = Leccion.objects.create(modulo=cls.modulo, titulo='Texto reservado')

    def test_anonimo_debe_ingresar(self):
        self.assertRedirects(self.client.get('/aula/'), '/aula/ingresar/?next=/aula/')

    def test_login_y_logout(self):
        r = self.client.post('/aula/ingresar/', {'username': 'alumno', 'password': 'Clave-de-prueba-927'})
        self.assertRedirects(r, '/aula/')
        self.assertEqual(self.client.get('/aula/salir/').status_code, 405)
        self.assertRedirects(self.client.post('/aula/salir/'), '/')

    def test_no_inscripto_no_ve_curso_ni_puede_completar(self):
        self.client.force_login(self.otro)
        self.assertNotContains(self.client.get('/aula/'), 'Nivel I')
        self.assertEqual(self.client.get(reverse('aula:curso', args=[self.curso.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse('aula:completar', args=[self.leccion.pk])).status_code, 404)

    def test_lectura_no_completa_y_post_es_idempotente(self):
        self.client.force_login(self.alumno)
        url = reverse('aula:curso', args=[self.curso.pk])
        r = self.client.get(url)
        self.assertContains(r, 'Origen')
        self.assertNotContains(r, 'Texto reservado')
        self.assertFalse(Progreso.objects.exists())
        completar = reverse('aula:completar', args=[self.leccion.pk])
        self.assertEqual(self.client.get(completar).status_code, 405)
        self.client.post(completar)
        self.client.post(completar)
        self.assertEqual(Progreso.objects.count(), 1)
        self.assertContains(self.client.get(url), '100%')

    def test_ocultos_e_inscripcion_revocada(self):
        self.client.force_login(self.alumno)
        self.assertEqual(self.client.post(reverse('aula:completar', args=[self.oculta.pk])).status_code, 404)
        self.inscripcion.activa = False
        self.inscripcion.save()
        self.assertEqual(self.client.get(reverse('aula:curso', args=[self.curso.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse('aula:completar', args=[self.leccion.pk])).status_code, 404)

    def test_curso_borrador_y_formador_asignado(self):
        self.curso.publicado = False
        self.curso.save()
        self.client.force_login(self.alumno)
        self.assertEqual(self.client.get(reverse('aula:curso', args=[self.curso.pk])).status_code, 404)
        self.client.force_login(self.formador)
        self.assertContains(self.client.get(reverse('aula:curso', args=[self.curso.pk])), 'Texto reservado')
        self.assertEqual(self.client.post(reverse('aula:completar', args=[self.leccion.pk])).status_code, 404)

    def test_csrf_obligatorio(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.alumno)
        self.assertEqual(client.post(reverse('aula:completar', args=[self.leccion.pk])).status_code, 403)

    def test_staff_no_equivale_a_direccion(self):
        self.otro.is_staff = True
        self.otro.save()
        self.client.force_login(self.otro)
        self.assertEqual(self.client.get('/admin/aula/curso/').status_code, 403)

    def test_texto_se_muestra_sin_ejecutar_html(self):
        self.leccion.texto = '<script>alert(1)</script>'
        self.leccion.save()
        self.client.force_login(self.alumno)
        self.assertContains(self.client.get(reverse('aula:curso', args=[self.curso.pk])), '&lt;script&gt;')


class GestionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.director = get_user_model().objects.create_superuser('direccion', password='Test-gestion-8725')
        cls.curso = Curso.objects.create(titulo='Nivel I')
        cls.modulo = Modulo.objects.create(curso=cls.curso, titulo='Historia')
        cls.persona = get_user_model().objects.create_user('existente', first_name='María')
        cls.otro_curso = Curso.objects.create(titulo='Nivel II')
        cls.otro_modulo = Modulo.objects.create(curso=cls.otro_curso, titulo='Otro')

    def setUp(self):
        self.client.force_login(self.director)

    def nueva_persona(self):
        return {'first_name': 'Ana', 'last_name': 'Pérez', 'email': 'ana@example.com',
                'username': 'ana.perez', 'password1': 'Seguro-8725-zeta', 'password2': 'Seguro-8725-zeta', 'rol': 'cursante'}

    def test_cuenta_e_inscripcion_en_un_paso_sin_permisos_admin(self):
        data = self.nueva_persona()
        data.update({'is_superuser': 'on', 'is_staff': 'on'})
        r = self.client.post(reverse('aula:gestion_persona_nueva', args=[self.curso.pk]), data)
        self.assertRedirects(r, reverse('aula:gestion_curso', args=[self.curso.pk]))
        user = get_user_model().objects.get(username='ana.perez')
        self.assertTrue(user.check_password(data['password1']))
        self.assertFalse(user.is_staff or user.is_superuser)
        self.assertTrue(Inscripcion.objects.get(curso=self.curso, cursante=user).activa)
        self.assertEqual(LogEntry.objects.count(), 2)
        self.assertNotIn(data['password1'], str(list(LogEntry.objects.values())))

    def test_error_no_crea_cuenta_ni_inscripcion_y_no_repite_password(self):
        data = self.nueva_persona()
        data['password2'] = 'diferente'
        r = self.client.post(reverse('aula:gestion_persona_nueva', args=[self.curso.pk]), data)
        self.assertContains(r, 'No se guardaron los cambios')
        self.assertNotContains(r, data['password1'])
        self.assertFalse(get_user_model().objects.filter(username='ana.perez').exists())
        self.assertFalse(Inscripcion.objects.exists())

    def test_fallo_de_inscripcion_revierte_cuenta(self):
        with patch('aula.gestion.asignar', side_effect=RuntimeError('Fallo simulado')):
            with self.assertRaises(RuntimeError):
                self.client.post(reverse('aula:gestion_persona_nueva', args=[self.curso.pk]), self.nueva_persona())
        self.assertFalse(get_user_model().objects.filter(username='ana.perez').exists())
        self.assertFalse(LogEntry.objects.exists())

    def test_usuario_duplicado_no_modifica_cuenta(self):
        data = self.nueva_persona()
        url = reverse('aula:gestion_persona_nueva', args=[self.curso.pk])
        self.client.post(url, data)
        data['first_name'] = 'Distinto'
        self.assertContains(self.client.post(url, data), 'No se guardaron los cambios')
        self.assertEqual(get_user_model().objects.get(username='ana.perez').first_name, 'Ana')
        self.assertEqual(Inscripcion.objects.count(), 1)

    def test_existente_reactiva_sin_duplicar_y_asigna_formador(self):
        inscripcion = Inscripcion.objects.create(curso=self.curso, cursante=self.persona, activa=False)
        url = reverse('aula:gestion_persona_existente', args=[self.curso.pk])
        self.client.post(url, {'persona': self.persona.pk, 'rol': 'cursante'})
        self.client.post(url, {'persona': self.persona.pk, 'rol': 'cursante'})
        inscripcion.refresh_from_db()
        self.assertTrue(inscripcion.activa)
        self.assertEqual(Inscripcion.objects.count(), 1)
        self.client.post(url, {'persona': self.persona.pk, 'rol': 'formador'})
        self.assertTrue(self.curso.formadores.filter(pk=self.persona.pk).exists())
        self.persona.refresh_from_db()
        self.assertFalse(self.persona.is_staff)

    def test_persona_inactiva_no_se_puede_asignar(self):
        self.persona.is_active = False
        self.persona.save()
        r = self.client.post(reverse('aula:gestion_persona_existente', args=[self.curso.pk]), {'persona': self.persona.pk, 'rol': 'cursante'})
        self.assertContains(r, 'No se guardaron los cambios')
        self.assertFalse(Inscripcion.objects.exists())

    def test_gestion_solo_direccion_en_todas_las_rutas(self):
        urls = [reverse('aula:gestion'), reverse('aula:gestion_curso_nuevo'),
                reverse('aula:gestion_curso', args=[self.curso.pk]),
                reverse('aula:gestion_curso_editar', args=[self.curso.pk]),
                reverse('aula:gestion_modulo_nuevo', args=[self.curso.pk]),
                reverse('aula:gestion_modulo_editar', args=[self.curso.pk, self.modulo.pk]),
                reverse('aula:gestion_leccion_nueva', args=[self.curso.pk]),
                reverse('aula:gestion_persona_nueva', args=[self.curso.pk]),
                reverse('aula:gestion_persona_existente', args=[self.curso.pk])]
        self.persona.is_staff = True
        self.persona.save()
        self.curso.formadores.add(self.persona)
        self.client.force_login(self.persona)
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 403)
                self.assertEqual(self.client.post(url, {}).status_code, 403)
        self.client.logout()
        self.assertEqual(self.client.get(reverse('aula:gestion')).status_code, 302)

    def test_recorrido_curso_modulo_clase_y_publicacion(self):
        self.client.post(reverse('aula:gestion_curso_nuevo'), {'titulo': 'Taller', 'descripcion': 'Presentación'})
        curso = Curso.objects.get(titulo='Taller')
        self.assertFalse(curso.publicado)
        self.client.post(reverse('aula:gestion_modulo_nuevo', args=[curso.pk]), {'titulo': 'Primer tema'})
        modulo = curso.modulos.get()
        self.client.post(reverse('aula:gestion_leccion_nueva', args=[curso.pk]), {'modulo': modulo.pk, 'titulo': 'Primera clase', 'texto': 'Contenido'})
        clase = modulo.lecciones.get()
        self.assertFalse(clase.publicada)
        self.assertContains(self.client.get(reverse('aula:gestion_curso', args=[curso.pk])), 'Primera clase')
        self.client.post(reverse('aula:gestion_leccion_editar', args=[curso.pk, clase.pk]), {'modulo': modulo.pk, 'titulo': 'Clase publicada', 'publicada': 'on'})
        clase.refresh_from_db()
        self.assertTrue(clase.publicada)

    def test_no_cruza_modulos_entre_cursos(self):
        r = self.client.post(reverse('aula:gestion_leccion_nueva', args=[self.curso.pk]), {'modulo': self.otro_modulo.pk, 'titulo': 'Intrusa'})
        self.assertContains(r, 'No se guardaron los cambios')
        self.assertFalse(Leccion.objects.exists())
        self.assertEqual(self.client.get(reverse('aula:gestion_modulo_editar', args=[self.curso.pk, self.otro_modulo.pk])).status_code, 404)

    def test_progreso_y_tutor_pendiente(self):
        Inscripcion.objects.create(curso=self.curso, cursante=self.persona)
        leccion = Leccion.objects.create(modulo=self.modulo, titulo='Publicada', publicada=True)
        oculta = Leccion.objects.create(modulo=self.modulo, titulo='Oculta')
        Progreso.objects.create(leccion=leccion, cursante=self.persona)
        Progreso.objects.create(leccion=oculta, cursante=self.persona)
        r = self.client.get(reverse('aula:gestion_curso', args=[self.curso.pk]))
        self.assertContains(r, '1 / 1 lecturas completadas')
        self.assertContains(r, 'Pendiente de asignación por Dirección')

    def test_csrf_y_get_sin_mutacion(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.director)
        url = reverse('aula:gestion_persona_nueva', args=[self.curso.pk])
        self.assertEqual(client.post(url, self.nueva_persona()).status_code, 403)
        self.assertEqual(client.get(url).status_code, 200)
        self.assertFalse(Inscripcion.objects.exists())
