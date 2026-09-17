from datetime import date
from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse
from .models import (Curso, Modulo, Leccion, Inscripcion, Progreso, Prueba, IntentoPrueba,
                     PermisoFormador, TemaForo, RespuestaForo, CierreCurso, Certificado, RecursoLeccion)


class TablerosTests(TestCase):
    def test_gestion_catalogo_busqueda_paginada_y_acceso(self):
        url = reverse('aula:gestion')
        self.client.force_login(self.alumno)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.force_login(self.director)
        Curso.objects.bulk_create([Curso(titulo=f'Taller {n}') for n in range(12)])
        r = self.client.get(url)
        self.assertEqual(len(r.context['pagina']), 6)
        self.assertEqual(r.context['pagina'].paginator.count, 13)
        self.assertContains(r, self.url)
        r = self.client.get(url, {'buscar': 'Taller', 'pagina': '2'})
        self.assertEqual(len(r.context['pagina']), 6)
        self.assertNotContains(r, self.curso.titulo)
        self.assertContains(r, 'buscar=Taller')

    def test_parrafo_vacio_no_desplaza_materiales_ni_borra_contenido(self):
        self.leccion.texto_enriquecido = True
        for vacio in ('<p>&nbsp;</p>', '<p><br></p>', '<p>\u00a0</p>', '<p> </p>\n'):
            self.leccion.texto = vacio
            self.assertEqual(self.leccion.contenido_html, '')
            self.assertEqual(self.leccion.texto, vacio)
        for contenido in ('<p>Texto de la clase</p>', '<table><tr><td></td></tr></table>', '<hr>'):
            self.leccion.texto = contenido
            self.assertTrue(self.leccion.contenido_html)

    @classmethod
    def setUpTestData(cls):
        U = get_user_model()
        cls.director = U.objects.create_superuser('director-panel')
        cls.formador = U.objects.create_user('formador-panel')
        cls.alumno = U.objects.create_user('alumno-panel', first_name='Ana')
        cls.otro = U.objects.create_user('otro-panel')
        cls.curso = Curso.objects.create(titulo='Nivel de prueba', publicado=True)
        cls.curso.formadores.add(cls.formador)
        cls.modulo = Modulo.objects.create(curso=cls.curso, titulo='Módulo principal')
        cls.leccion = Leccion.objects.create(modulo=cls.modulo, titulo='Lectura visible', publicada=True)
        cls.i = Inscripcion.objects.create(curso=cls.curso, cursante=cls.alumno)
        cls.url = reverse('aula:gestion_curso', args=[cls.curso.pk])

    def test_panel_separa_roles_y_no_leakea_cursos(self):
        Curso.objects.create(titulo='Curso ajeno', publicado=True)
        self.client.force_login(self.alumno)
        r=self.client.get('/aula/')
        self.assertContains(r,'Avance de lectura');self.assertNotContains(r,'Curso ajeno')
        self.assertNotContains(r,'entregas por corregir')
        Progreso.objects.create(cursante=self.alumno,leccion=self.leccion)
        Leccion.objects.create(modulo=self.modulo,titulo='Borrador secreto',publicada=False)
        r=self.client.get('/aula/');self.assertContains(r,'100%');self.assertContains(r,'aprobación pendiente')
        self.assertNotContains(r,'Borrador secreto')
        self.client.force_login(self.formador);self.assertContains(self.client.get('/aula/'),'Mi trabajo')
        self.assertNotContains(self.client.get('/aula/?vista=formacion'),self.curso.titulo)

    def test_modulos_paginados_clases_solo_al_abrir_y_busqueda_global(self):
        Modulo.objects.bulk_create([Modulo(curso=self.curso,titulo=f'Módulo {n}',orden=n+1) for n in range(20)])
        self.client.force_login(self.director)
        r=self.client.get(self.url);self.assertNotContains(r,self.leccion.titulo)
        r=self.client.get(self.url+'?seccion=contenido');self.assertEqual(len(r.context['pagina']),10)
        self.assertNotContains(r,self.leccion.titulo)
        r=self.client.get(self.url+f'?modulo={self.modulo.pk}');self.assertContains(r,self.leccion.titulo)
        self.assertContains(r,reverse('aula:gestion_modulo_leccion_nueva',args=[self.curso.pk,self.modulo.pk]))
        self.assertContains(r,'Agregar prueba')
        r=self.client.get(self.url+'?seccion=contenido&buscar=visible');self.assertEqual(r.context['pagina'].paginator.count,1)
        curso2=Curso.objects.create(titulo='Ajeno');mod2=Modulo.objects.create(curso=curso2,titulo='Ajeno')
        self.assertEqual(self.client.get(self.url+f'?modulo={mod2.pk}').status_code,404)

    def test_filtros_requisitos_pruebas_y_paginacion(self):
        self.client.force_login(self.director)
        url=reverse('aula:registro_curso',args=[self.curso.pk])
        self.assertEqual(self.client.get(url+'?estado=pendientes').context['pagina'].paginator.count,1)
        Progreso.objects.create(cursante=self.alumno,leccion=self.leccion)
        self.assertEqual(self.client.get(url+'?estado=revisar').context['pagina'].paginator.count,1)
        lp=Leccion.objects.create(modulo=self.modulo,titulo='Evaluación',publicada=True,obligatoria=False)
        p=Prueba.objects.create(leccion=lp,tipo='trivia')
        self.assertEqual(self.client.get(url+'?estado=revisar').context['pagina'].paginator.count,0)
        IntentoPrueba.objects.create(prueba=p,cursante=self.alumno,numero=1,revision=p.revision,
                                    estructura={},estado='corregido',puntaje=100,minimo=70,aprobado=True)
        self.assertEqual(self.client.get(url+'?estado=revisar').context['pagina'].paginator.count,1)
        self.assertEqual(self.client.get(url+'?vista=entregas&estado=corregido').context['pagina'].paginator.count,1)
        p.revision=2;p.save()
        self.assertEqual(self.client.get(url+'?estado=revisar').context['pagina'].paginator.count,0)

    def test_ficha_y_certificados_con_permisos_separados(self):
        url=reverse('aula:ficha_cursante',args=[self.i.pk])
        self.client.force_login(self.otro);self.assertEqual(self.client.get(url).status_code,403)
        self.client.force_login(self.alumno);self.assertEqual(self.client.get(url).status_code,403)
        PermisoFormador.objects.create(curso=self.curso,formador=self.formador,ver_seguimiento=False,corregir=False,disenar=True)
        self.client.force_login(self.formador);self.assertEqual(self.client.get(url).status_code,403)
        self.assertEqual(self.client.get(reverse('aula:registro_curso',args=[self.curso.pk])+'?vista=cierres').status_code,403)
        r=self.client.get('/aula/');self.assertNotContains(r,'1 cursantes')

    def test_duplicar_y_reordenar_preserva_archivos_y_no_copia_progreso(self):
        self.client.force_login(self.director)
        Progreso.objects.create(cursante=self.alumno,leccion=self.leccion)
        RecursoLeccion.objects.create(leccion=self.leccion,nombre='Archivo',archivo='privado.pdf',tipo='documento',mime='application/pdf')
        url=reverse('aula:organizar_clase',args=[self.curso.pk,self.leccion.pk])
        self.assertEqual(self.client.get(url).status_code,405)
        self.client.post(url,{'accion':'duplicar'})
        copia=Leccion.objects.exclude(pk=self.leccion.pk).get()
        self.assertFalse(copia.publicada);self.assertEqual(copia.recursos.get().archivo.name,'privado.pdf')
        self.assertFalse(Progreso.objects.filter(leccion=copia).exists())
        self.client.post(reverse('aula:organizar_clase',args=[self.curso.pk,copia.pk]),{'accion':'subir'})
        self.assertEqual(self.modulo.lecciones.first(),copia)
        c=Client(enforce_csrf_checks=True);c.force_login(self.director)
        self.assertEqual(c.post(url,{'accion':'duplicar'}).status_code,403)
        self.client.force_login(self.formador);self.assertEqual(self.client.post(url,{'accion':'duplicar'}).status_code,403)

    def test_consultas_pendientes_no_cuenta_respuesta_de_otro_cursante_como_equipo(self):
        tema=TemaForo.objects.create(curso=self.curso,autor=self.alumno,titulo='Consulta',texto='Duda')
        RespuestaForo.objects.create(tema=tema,autor=self.otro,texto='Opinión')
        self.client.force_login(self.formador)
        r=self.client.get('/aula/');self.assertEqual(r.context['pagina'][0].consultas,1)
        RespuestaForo.objects.create(tema=tema,autor=self.formador,texto='Respuesta')
        self.assertEqual(self.client.get('/aula/').context['pagina'][0].consultas,0)

    def test_guardar_y_seguir_editando_y_retorno_sin_redireccion_externa(self):
        self.client.force_login(self.director)
        url=reverse('aula:gestion_leccion_editar',args=[self.curso.pk,self.leccion.pk])
        data={'titulo':'Modificada','modulo':self.modulo.pk,'continuar':'1'}
        self.assertRedirects(self.client.post(url,data),url)
        data.pop('continuar');data['volver']=self.url+'?seccion=contenido&buscar=Modificada'
        self.assertEqual(self.client.post(url,data).url,data['volver'])
        data['volver']='https://example.com'
        self.assertTrue(self.client.post(url,data).url.startswith(self.url))

    def test_cierre_preflight_y_siguiente_no_aprueba_a_otra_persona(self):
        self.client.force_login(self.director)
        url=reverse('aula:cierre_editar',args=[self.i.pk])
        self.assertContains(self.client.get(url),'Quedan 1 lecturas')
        otra=Inscripcion.objects.create(curso=self.curso,cursante=self.otro)
        data={'nombre_certificado':'Ana','participacion_validada':'on','observaciones':'Referencia comprobada','continuar':'1'}
        r=self.client.post(url,data)
        self.assertRedirects(r,reverse('aula:cierre_editar',args=[otra.pk]))
        self.assertFalse(CierreCurso.objects.filter(inscripcion=otra).exists())
        self.assertFalse(Certificado.objects.exists())

    def test_cierre_historico_no_es_retirado_por_consultar_nuevos_pendientes(self):
        CierreCurso.objects.create(inscripcion=self.i,nombre_certificado='Ana',participacion_validada=True,
            requisitos_validados=True,aprobado=True,responsable=self.director)
        self.client.force_login(self.director)
        r=self.client.get(reverse('aula:ficha_cursante',args=[self.i.pk]))
        self.assertContains(r,'Aprobación registrada.');self.assertContains(r,'programa puede haber cambiado')
        self.assertTrue(CierreCurso.objects.get(inscripcion=self.i).aprobado)

    def test_editar_inscripcion_tutor_no_otorga_rol_de_formador(self):
        url=reverse('aula:inscripcion_editar',args=[self.i.pk])
        self.client.force_login(self.formador);self.assertEqual(self.client.post(url,{}).status_code,403)
        self.client.force_login(self.director);self.client.post(url,{'activa':'on','tutor':self.otro.pk})
        self.i.refresh_from_db();self.assertEqual(self.i.tutor,self.otro)
        self.assertFalse(self.curso.formadores.filter(pk=self.otro.pk).exists())
