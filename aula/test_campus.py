from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from .models import Curso, Modulo, Leccion, Inscripcion, Progreso


class CampusTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('cursante')
        self.curso = Curso.objects.create(titulo='Nivel I', publicado=True)
        Inscripcion.objects.create(curso=self.curso, cursante=self.user)
        self.m1 = Modulo.objects.create(curso=self.curso, titulo='Historia', orden=1)
        self.m2 = Modulo.objects.create(curso=self.curso, titulo='Método', orden=2)
        self.primera = Leccion.objects.create(modulo=self.m1, titulo='Inicio', texto='Contenido de la primera', publicada=True, orden=1)
        self.borrador = Leccion.objects.create(modulo=self.m1, titulo='Reservada', texto='Contenido reservado', orden=2)
        self.segunda = Leccion.objects.create(modulo=self.m2, titulo='Siguiente', texto='Contenido de la segunda', publicada=True)
        self.url = reverse('aula:curso', args=[self.curso.pk])
        self.client.force_login(self.user)

    def test_una_clase_a_la_vez_y_enlaces_al_indice(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'Contenido de la primera')
        self.assertNotContains(response, 'Contenido de la segunda')
        self.assertNotContains(response, 'Reservada')
        self.assertContains(response, f'?clase={self.segunda.pk}')
        response = self.client.get(self.url, {'clase': self.segunda.pk})
        self.assertContains(response, 'Contenido de la segunda')
        self.assertNotContains(response, 'Contenido de la primera')
        self.assertFalse(Progreso.objects.exists())

    def test_no_abre_clases_ocultas_ajenas_o_selector_invalido(self):
        otro = Curso.objects.create(titulo='Ajeno', publicado=True)
        modulo = Modulo.objects.create(curso=otro, titulo='Ajeno')
        ajena = Leccion.objects.create(modulo=modulo, titulo='Ajena', publicada=True)
        for pk in [self.borrador.pk, ajena.pk, 'invalido']:
            self.assertEqual(self.client.get(self.url, {'clase': pk}).status_code, 404)

    def test_completar_continua_en_otro_modulo_y_al_final_muestra_avance(self):
        response = self.client.post(reverse('aula:completar', args=[self.primera.pk]), {'seguir': '1'})
        self.assertRedirects(response, self.url + f'?clase={self.segunda.pk}')
        self.assertContains(self.client.get(self.url), 'Contenido de la segunda')
        response = self.client.post(reverse('aula:completar', args=[self.segunda.pk]), {'seguir': '1'})
        self.assertRedirects(response, self.url + '?vista=avance')
        self.assertContains(self.client.get(self.url + '?vista=avance'), '100%')
        self.assertEqual(Progreso.objects.filter(cursante=self.user).count(), 2)

    def test_progreso_no_cuenta_borradores_y_materiales_vacios(self):
        self.assertContains(self.client.get(self.url + '?vista=avance'), '0 de 2 lecciones obligatorias')
        self.assertContains(self.client.get(self.url + '?vista=materiales'), 'Todavía no hay archivos publicados')

    def test_curso_sin_clases_muestra_bienvenida(self):
        self.primera.publicada = self.segunda.publicada = False
        self.primera.save()
        self.segunda.save()
        self.assertContains(self.client.get(self.url), 'BIENVENIDA AL CURSO')
