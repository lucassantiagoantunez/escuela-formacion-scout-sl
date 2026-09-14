from django.test import TestCase,Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from .models import Curso,Modulo,Leccion,Inscripcion,Progreso,Prueba,RecursoLeccion
from .certificados import pendientes,validar_aprobacion

class PapeleraTests(TestCase):
 def setUp(self):
  u=get_user_model();self.admin=u.objects.create_superuser('dir');self.alumno=u.objects.create_user('alumno')
  self.curso=Curso.objects.create(titulo='Curso',publicado=True);self.modulo=Modulo.objects.create(curso=self.curso,titulo='Módulo')
  self.clase=Leccion.objects.create(modulo=self.modulo,titulo='Charla',publicada=True)
  self.inscripcion=Inscripcion.objects.create(curso=self.curso,cursante=self.alumno)
  self.url=reverse('aula:gestion_leccion_eliminar',args=[self.curso.pk,self.clase.pk])
 def test_eliminar_y_restaurar_conserva_lecturas_y_archivos(self):
  Progreso.objects.create(cursante=self.alumno,leccion=self.clase)
  r=RecursoLeccion.objects.create(leccion=self.clase,nombre='charla.pdf',tipo='documento',archivo='charla.pdf',mime='application/pdf')
  self.client.force_login(self.admin)
  self.assertContains(self.client.get(self.url),'Mover a la papelera');self.assertTrue(Leccion.objects.exists())
  self.assertEqual(self.client.post(self.url).status_code,302)
  self.assertFalse(Leccion.objects.exists());self.assertEqual(self.modulo.lecciones.count(),0)
  self.assertEqual(Progreso.objects.count(),1);self.assertEqual(RecursoLeccion.objects.count(),1)
  self.assertEqual(self.client.get(reverse('aula:recurso_visor',args=[r.pk])).status_code,404)
  self.assertContains(self.client.get(reverse('aula:gestion_curso',args=[self.curso.pk])),'Papelera')
  url=reverse('aula:gestion_leccion_restaurar',args=[self.curso.pk,self.clase.pk])
  self.assertEqual(self.client.get(url).status_code,405);self.client.post(url)
  self.assertTrue(Leccion.objects.exists());self.clase.refresh_from_db();self.assertFalse(self.clase.publicada)
 def test_no_elimina_otro_curso_ni_cursante_ni_sin_csrf(self):
  self.client.force_login(self.alumno);self.assertEqual(self.client.post(self.url).status_code,403)
  self.client.force_login(self.admin)
  self.assertEqual(self.client.post(reverse('aula:gestion_leccion_eliminar',args=[999,self.clase.pk])).status_code,404)
  c=Client(enforce_csrf_checks=True);c.force_login(self.admin);self.assertEqual(c.post(self.url).status_code,403)
 def test_eliminada_no_es_pendiente_ni_borrador_bloqueante(self):
  otra=Leccion.objects.create(modulo=self.modulo,titulo='Vigente',publicada=True)
  Progreso.objects.create(cursante=self.alumno,leccion=otra)
  self.client.force_login(self.admin);self.client.post(self.url)
  self.assertEqual(pendientes(self.inscripcion),(0,[]));validar_aprobacion(self.inscripcion)
  self.client.force_login(self.alumno)
  self.assertEqual(self.client.post(reverse('aula:completar',args=[self.clase.pk])).status_code,404)
  self.assertEqual(self.client.get(reverse('aula:curso',args=[self.curso.pk])+f'?clase={self.clase.pk}').status_code,404)
 def test_prueba_eliminada_conservada_no_puede_publicarse(self):
  prueba=Prueba.objects.create(leccion=self.clase,tipo='trivia')
  self.client.force_login(self.admin);self.client.post(self.url)
  self.assertEqual(Prueba.objects.count(),1)
  self.assertEqual(self.client.post(reverse('aula:prueba_editar',args=[prueba.pk]),{'accion':'publicar'}).status_code,404)
