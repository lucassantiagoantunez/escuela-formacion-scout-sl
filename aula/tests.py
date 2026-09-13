from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse
from .models import Curso, Inscripcion, Modulo, Leccion, Progreso


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
