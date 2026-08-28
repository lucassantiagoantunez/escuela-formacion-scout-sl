from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import (
    JuegoMemoria,
    JuegoPalabraSecreta,
    Noticia,
    PalabraJuego,
    ParejaMemoria,
    ResultadoMemoria,
    ResultadoPalabra,
)


class NavegacionInteractivaTests(TestCase):
    def test_selector_explica_los_seis_tipos_de_juego(self):
        respuesta = self.client.get(reverse("juegos_y_trivias"))

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Preguntas y respuestas")
        self.assertContains(respuesta, "Pasos y procedimientos")
        self.assertContains(respuesta, "Encontrá las parejas")
        self.assertContains(respuesta, "Pistas y letras")
        self.assertContains(respuesta, 'id="ordena" class="juegos-bloque bloque-ordena panel-juego" hidden')

    def test_noticias_aparecen_en_widget_superior(self):
        noticia = Noticia.objects.create(
            titulo="Novedad de prueba",
            resumen="Resumen",
            contenido="Contenido",
            publicada=True,
        )

        respuesta = self.client.get(reverse("inicio"))

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Últimas noticias")
        self.assertContains(respuesta, noticia.titulo)
        self.assertContains(respuesta, "6</strong><span>formas de aprender jugando")


class NuevosJuegosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.memoria = JuegoMemoria.objects.create(titulo="Memoria de prueba")
        ParejaMemoria.objects.create(
            juego=cls.memoria,
            concepto="Patrulla",
            relacion="Pequeño equipo",
        )
        cls.palabra = JuegoPalabraSecreta.objects.create(titulo="Palabras de prueba")
        PalabraJuego.objects.create(
            juego=cls.palabra,
            palabra="SERVICIO",
            pista="Acción útil",
        )

    def test_memoria_guarda_resultado_y_lo_muestra_en_ranking(self):
        respuesta = self.client.post(
            reverse("detalle_memoria", args=[self.memoria.id]),
            {"nombre_participante": "  Ana   Scout ", "movimientos": "8", "tiempo_total_segundos": "42"},
        )

        self.assertEqual(respuesta.status_code, 200)
        resultado = ResultadoMemoria.objects.get(juego=self.memoria)
        self.assertEqual(resultado.nombre, "Ana Scout")
        self.assertContains(respuesta, "8 movimientos")
        self.assertContains(respuesta, "Ana Scout")

    def test_palabra_secreta_valida_y_guarda_puntaje(self):
        respuesta = self.client.post(
            reverse("detalle_palabra", args=[self.palabra.id]),
            {"nombre_participante": "Lucas", "puntaje": "99", "tiempo_total_segundos": "31"},
        )

        self.assertEqual(respuesta.status_code, 200)
        resultado = ResultadoPalabra.objects.get(juego=self.palabra)
        self.assertEqual(resultado.puntaje, 1)
        self.assertEqual(resultado.total_palabras, 1)
        self.assertContains(respuesta, "Completaste 1 de 1 palabras")


class AdministradorEdifosTests(TestCase):
    def test_inicio_del_admin_esta_ordenado_por_tareas(self):
        usuario = get_user_model().objects.create_superuser(
            username="administrador",
            email="admin@example.com",
            password="clave-segura-de-prueba",
        )
        self.client.force_login(usuario)

        respuesta = self.client.get(reverse("admin:index"))

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "¿Qué querés actualizar?")
        self.assertContains(respuesta, "Publicar y organizar")
        self.assertContains(respuesta, "Juegos y actividades")
        self.assertContains(respuesta, "Participación y rankings")
