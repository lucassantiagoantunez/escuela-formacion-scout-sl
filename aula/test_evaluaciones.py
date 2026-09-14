import io
import json
from datetime import date
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.http import QueryDict
from django.test import TestCase, Client, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from tempfile import TemporaryDirectory
from pathlib import Path
from django.urls import reverse
from pypdf import PdfReader
from .models import (Curso,Modulo,Leccion,Inscripcion,Progreso,Prueba,ItemPrueba,
    IntentoPrueba,CierreCurso,Certificado,MovimientoAcademico,RecursoLeccion)
from .pruebas_motor import preparar,corregir,importar
from .pruebas_forms import ItemForm
from .certificados import generar_pdf
from core.models import Trivia,Pregunta,OpcionRespuesta as Opcion


class EvaluacionesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User=get_user_model()
        cls.director=User.objects.create_superuser('direccion-evaluaciones')
        cls.alumna=User.objects.create_user('alumna-evaluaciones',first_name='Persona',last_name='Ficticia')
        cls.otra=User.objects.create_user('otra-evaluaciones')
        cls.formador=User.objects.create_user('docente-evaluaciones')
        cls.curso=Curso.objects.create(titulo='Curso ficticio',publicado=True,certificacion_configurada=True,
            fecha_inicio=date(2025,1,1),fecha_fin=date(2025,2,1),responsable_certificados='Autoridad de prueba')
        cls.curso.formadores.add(cls.formador)
        cls.modulo=Modulo.objects.create(curso=cls.curso,titulo='Módulo ficticio')
        cls.inscripcion=Inscripcion.objects.create(curso=cls.curso,cursante=cls.alumna)
        cls.lectura=Leccion.objects.create(modulo=cls.modulo,titulo='Lectura',publicada=True)
        cls.leccion=Leccion.objects.create(modulo=cls.modulo,titulo='Evaluación',publicada=True,obligatoria=False,orden=2)
        cls.prueba=Prueba.objects.create(leccion=cls.leccion,tipo='trivia',max_intentos=1)
        cls.item=ItemPrueba.objects.create(prueba=cls.prueba,texto='Elegí la correcta',opciones=['Correcta','Incorrecta'],respuesta='1')

    def iniciar(self):
        self.client.force_login(self.alumna)
        r=self.client.post(reverse('aula:prueba_iniciar',args=[self.prueba.pk]))
        self.assertEqual(r.status_code,302)
        return IntentoPrueba.objects.latest('iniciado')

    def entregar(self,intento,correcta=True):
        p=intento.estructura['preguntas'][0]
        token=p['correcta'] if correcta else next(o['id'] for o in p['opciones'] if o['id']!=p['correcta'])
        self.client.post(reverse('aula:prueba_resolver',args=[intento.pk]),{'q_'+p['id']:token,'puntaje':100,'aprobado':True})
        intento.refresh_from_db()

    def cierre(self,**extra):
        datos=dict(inscripcion=self.inscripcion,nombre_certificado='Persona Ficticia',participacion_validada=True,
            requisitos_validados=True,aprobado=True,observaciones='Documentación de prueba verificada',responsable=self.director)
        datos.update(extra)
        return CierreCurso.objects.create(**datos)

    def aprobar(self):
        i=self.iniciar();self.entregar(i)
        Progreso.objects.create(cursante=self.alumna,leccion=self.lectura)
        return i

    def emitir(self,tipo='aprobacion'):
        self.client.force_login(self.director)
        return self.client.post(reverse('aula:certificado_emitir',args=[self.inscripcion.pk]),{'tipo':tipo},follow=True)

    def test_intento_reanuda_y_entrega_es_inmutable(self):
        i=self.iniciar();self.assertEqual(self.iniciar().pk,i.pk)
        self.entregar(i,False)
        self.assertEqual(i.puntaje,0);self.assertFalse(i.aprobado)
        self.entregar(i,True);self.assertEqual(i.puntaje,0)
        self.iniciar();self.assertEqual(IntentoPrueba.objects.count(),1)

    def test_permiso_matricula_borrador_y_csrf(self):
        i=self.iniciar();url=reverse('aula:prueba_resolver',args=[i.pk])
        self.client.force_login(self.otra)
        self.assertEqual(self.client.get(url).status_code,404)
        self.assertEqual(self.client.post(reverse('aula:prueba_iniciar',args=[self.prueba.pk])).status_code,404)
        self.client.force_login(self.alumna)
        self.inscripcion.activa=False;self.inscripcion.save()
        self.assertEqual(self.client.post(url).status_code,404)
        csrf=Client(enforce_csrf_checks=True);csrf.force_login(self.alumna)
        self.assertEqual(csrf.post(reverse('aula:prueba_iniciar',args=[self.prueba.pk])).status_code,403)
        self.inscripcion.activa=True;self.inscripcion.save()
        self.leccion.publicada=False;self.leccion.save()
        self.assertEqual(self.client.post(reverse('aula:prueba_iniciar',args=[self.prueba.pk])).status_code,404)

    def test_campus_navegable_desde_intento_sin_clave_respuesta(self):
        i=self.iniciar();r=self.client.get(reverse('aula:prueba_resolver',args=[i.pk]))
        self.assertContains(r,reverse('aula:curso',args=[self.curso.pk])+'?vista=avance')
        self.assertNotContains(r,'"correcta"');self.assertNotContains(r,'"respuesta"')
        self.assertEqual(self.client.post(reverse('aula:completar',args=[self.leccion.pk])).status_code,404)
        self.entregar(i);r=self.client.get(reverse('aula:curso',args=[self.curso.pk]))
        self.assertIn(self.leccion.pk,r.context['completadas'])
        self.assertEqual(r.context['total'],1)

    def test_nueva_version_conserva_intento_y_bloquea_entrega_vieja(self):
        i=self.iniciar();estructura=i.estructura.copy()
        self.client.force_login(self.director)
        r=self.client.post(reverse('aula:prueba_item_editar',args=[self.prueba.pk,self.item.pk]),
            {'texto':'Nueva pregunta','opciones_texto':'A\nB','respuesta':'2','activo':'on'})
        self.assertEqual(r.status_code,302)
        self.prueba.refresh_from_db();self.leccion.refresh_from_db()
        self.assertEqual(self.prueba.revision,2);self.assertFalse(self.leccion.publicada)
        self.client.post(reverse('aula:prueba_editar',args=[self.prueba.pk]),{'accion':'publicar'})
        self.client.force_login(self.alumna);self.entregar(i)
        self.assertEqual(i.estado,'abierto');self.assertEqual(i.estructura,estructura)
        nuevo=self.iniciar();self.assertNotEqual(i.pk,nuevo.pk)

    def test_ampliar_intentos_sin_perder_notas(self):
        i=self.iniciar();self.entregar(i,False)
        self.client.force_login(self.director)
        r=self.client.post(reverse('aula:prueba_editar',args=[self.prueba.pk]),
            {'accion':'reglas','minimo':70,'max_intentos':2,'obligatoria':'on'})
        self.assertEqual(r.status_code,302);self.prueba.refresh_from_db();self.assertEqual(self.prueba.revision,1)
        self.assertNotEqual(self.iniciar().pk,i.pk)

    def test_copia_de_trivia_no_modifica_juego_publico(self):
        cantidad=Trivia.objects.count()
        juego=Trivia.objects.create(titulo='Juego público')
        p=Pregunta.objects.create(trivia=juego,texto='Original')
        Opcion.objects.create(pregunta=p,texto='A',es_correcta=True)
        Opcion.objects.create(pregunta=p,texto='B',es_correcta=False)
        self.client.force_login(self.director)
        r=self.client.post(reverse('aula:prueba_nueva',args=[self.curso.pk]),{'modulo':self.modulo.pk,
            'titulo':'Copia privada','fuente':f'trivia:{juego.pk}','tipo':'trivia','minimo':70,'max_intentos':3,'obligatoria':'on'})
        self.assertEqual(r.status_code,302)
        copia=Prueba.objects.get(leccion__titulo='Copia privada');self.assertFalse(copia.leccion.publicada)
        copia.items.update(texto='Editada');p.refresh_from_db();self.assertEqual(p.texto,'Original')
        self.assertEqual(Trivia.objects.count(),cantidad+1)

    def test_juego_incompleto_no_deja_clase_huerfana(self):
        juego=Trivia.objects.create(titulo='Incompleto')
        self.client.force_login(self.director)
        r=self.client.post(reverse('aula:prueba_nueva',args=[self.curso.pk]),{'modulo':self.modulo.pk,
            'titulo':'No guardar','fuente':f'trivia:{juego.pk}','tipo':'trivia','minimo':70,'max_intentos':3})
        self.assertContains(r,'no tiene actividades')
        self.assertFalse(Leccion.objects.filter(titulo='No guardar').exists())

    def test_docente_corrige_pero_no_emite_y_guarda_historial(self):
        i=self.iniciar();self.entregar(i,False);url=reverse('aula:prueba_revisar',args=[i.pk])
        self.client.force_login(self.otra);self.assertEqual(self.client.get(url).status_code,403)
        self.client.force_login(self.formador)
        self.assertEqual(self.client.get(reverse('aula:registro_curso',args=[self.curso.pk])).status_code,200)
        self.client.post(url,{'puntaje':85,'devolucion':'Revisión con fundamento'})
        i.refresh_from_db();self.assertTrue(i.aprobado);self.assertEqual(i.correcciones.count(),1)
        self.assertEqual(self.client.post(reverse('aula:certificado_emitir',args=[self.inscripcion.pk])).status_code,403)

    def test_correccion_que_retira_aprobacion_revoca_certificado(self):
        i=self.aprobar();c=self.cierre();self.emitir();cert=Certificado.objects.get()
        self.client.post(reverse('aula:prueba_revisar',args=[i.pk]),{'puntaje':20,'devolucion':'Corrección de un error de calificación'})
        c.refresh_from_db();cert.refresh_from_db()
        self.assertFalse(c.aprobado);self.assertTrue(cert.revocado)
        self.assertTrue(MovimientoAcademico.objects.filter(cierre=c).exists())

    def test_participacion_no_requiere_aprobar_y_no_autocertifica(self):
        self.emitir('participacion');self.assertFalse(Certificado.objects.exists())
        self.cierre(aprobado=False,requisitos_validados=False)
        self.emitir('participacion');self.assertEqual(Certificado.objects.get().tipo,'participacion')
        self.emitir();self.assertEqual(Certificado.objects.count(),1)

    def test_aprobacion_exige_lecturas_pruebas_requisitos_y_acta(self):
        c=self.cierre();self.emitir();self.assertFalse(Certificado.objects.exists())
        self.aprobar();self.curso.requiere_acta=True;self.curso.save()
        self.emitir();self.assertFalse(Certificado.objects.exists())
        c.libro='I';c.acta='25';c.folio='7';c.fecha_acta=date(2025,2,2);c.save()
        self.emitir();self.assertEqual(Certificado.objects.count(),1)
        self.emitir();self.assertEqual(Certificado.objects.count(),1)

    def test_validacion_requiere_fundamento_y_asiento_completo(self):
        self.aprobar();self.client.force_login(self.director)
        url=reverse('aula:cierre_editar',args=[self.inscripcion.pk])
        data={'nombre_certificado':'Persona Ficticia','participacion_validada':'on','aprobado':'on','libro':'I'}
        r=self.client.post(url,data);self.assertContains(r,'completá libro')
        self.assertFalse(CierreCurso.objects.exists())
        data.update(requisitos_validados='on',observaciones='Tutor y asistencia verificados',acta='1',folio='2',fecha_acta='2025-02-02')
        self.assertEqual(self.client.post(url,data).status_code,302)
        self.assertEqual(MovimientoAcademico.objects.count(),1)

    def test_no_emite_aprobacion_con_programa_obligatorio_en_borrador(self):
        self.aprobar();self.cierre()
        Leccion.objects.create(modulo=self.modulo,titulo='Pendiente de publicar',obligatoria=True)
        self.emitir();self.assertFalse(Certificado.objects.exists())

    def test_pdf_privado_verificacion_publica_sin_identidad_y_revocacion(self):
        self.aprobar();self.cierre();self.emitir();cert=Certificado.objects.get()
        url=reverse('aula:certificado_pdf',args=[cert.pk])
        self.client.force_login(self.otra);self.assertEqual(self.client.get(url).status_code,403)
        self.client.force_login(self.alumna);r=self.client.get(url)
        self.assertEqual(r['Content-Type'],'application/pdf');self.assertEqual(r['Cache-Control'],'private, no-store')
        pdf=PdfReader(io.BytesIO(r.content));self.assertEqual(len(pdf.pages),1)
        self.assertIn('Persona Ficticia',pdf.pages[0].extract_text())
        self.client.logout();r=self.client.get(reverse('aula:certificado_verificar',args=[cert.pk]))
        self.assertEqual(r.status_code,200);self.assertNotContains(r,'Persona Ficticia');self.assertNotContains(r,self.curso.titulo)
        self.client.force_login(self.director);self.client.post(reverse('aula:certificado_revocar',args=[cert.pk]),{'motivo':'Error de datos'})
        self.assertEqual(self.client.get(url).status_code,404)
        cert.refresh_from_db();self.assertTrue(cert.revocado);self.assertIsNotNone(cert.fecha_revocacion)

    def test_datos_certificado_inmutables_y_disponibles_al_archivar_curso(self):
        self.aprobar();self.cierre();self.emitir();cert=Certificado.objects.get()
        self.curso.titulo='Otro título';self.curso.publicado=False;self.curso.save()
        self.alumna.first_name='Otro nombre';self.alumna.save()
        cert.refresh_from_db();self.assertEqual(cert.datos['nombre'],'Persona Ficticia');self.assertEqual(cert.datos['curso'],'Curso ficticio')
        self.client.force_login(self.alumna)
        self.assertContains(self.client.get('/aula/'),reverse('aula:certificado_pdf',args=[cert.pk]))

    def test_csv_neutraliza_formulas(self):
        self.cierre(nombre_certificado='=HYPERLINK("bad")')
        self.client.force_login(self.director)
        r=self.client.get(reverse('aula:registro_exportar',args=[self.curso.pk]))
        self.assertIn("'=HYPERLINK",r.content.decode('utf-8'))

    def test_tipos_ordenar_parejas_palabra_y_ruleta(self):
        for tipo,opciones,respuesta in [('ordenar',['Uno','Dos','Tres'],''),('memoria',[],'Pareja'),('palabra',[],'Árbol'),('ruleta',[],'')]:
            with self.subTest(tipo=tipo):
                self.prueba.tipo=tipo;self.prueba.save();self.item.opciones=opciones;self.item.respuesta=respuesta;self.item.save()
                estructura=preparar(self.prueba);p=estructura['preguntas'][0];post=QueryDict('',mutable=True)
                if tipo=='ordenar':post.setlist('q_'+p['id'],p['secuencia'])
                else:post['q_'+p['id']]=p['correcta'] if tipo=='memoria' else ('arbol' if tipo=='palabra' else 'Mi respuesta escrita')
                _,nota=corregir(estructura,post);self.assertEqual(nota,None if tipo=='ruleta' else 100)
                post=QueryDict('',mutable=True)
                with self.assertRaises(ValidationError):corregir(estructura,post)

    def test_rompecabezas_calificacion_servidor(self):
        self.prueba.tipo='rompecabezas'
        imagen=RecursoLeccion.objects.create(leccion=self.leccion,nombre='Puzzle',tipo='imagen',archivo='prueba.jpg',mime='image/jpeg')
        self.prueba.contenido={'imagen':str(imagen.pk)};self.prueba.save()
        datos=preparar(self.prueba);self.assertEqual(len(datos['piezas']),9)
        self.assertEqual(corregir(datos,{'piezas':','.join(datos['solucion'])})[1],100)
        with self.assertRaises(ValidationError):corregir(datos,{'piezas':'fake'})

    def test_cargar_rompecabezas_privado_directamente(self):
        from PIL import Image
        buffer=io.BytesIO();Image.new('RGB',(90,90),'green').save(buffer,format='PNG')
        self.client.force_login(self.director)
        with TemporaryDirectory() as temporal,override_settings(AULA_PRIVATE_ROOT=Path(temporal)):
            r=self.client.post(reverse('aula:prueba_nueva',args=[self.curso.pk]),{'modulo':self.modulo.pk,
                'titulo':'Puzzle privado','tipo':'rompecabezas','minimo':70,'max_intentos':3,
                'imagen_archivo':SimpleUploadedFile('puzzle.png',buffer.getvalue(),content_type='image/png')})
            self.assertEqual(r.status_code,302)
            prueba=Prueba.objects.get(leccion__titulo='Puzzle privado')
            recurso=prueba.leccion.recursos.get();self.assertTrue(Path(recurso.archivo.path).is_file())
            self.client.force_login(self.otra)
            self.assertEqual(self.client.get(reverse('aula:recurso_archivo',args=[recurso.pk])).status_code,404)

    def test_camino_publico_copia_todas_las_decisiones_editables(self):
        from core.models import EligeCamino,EscenaCamino,OpcionEscenaCamino
        juego=EligeCamino.objects.create(titulo='Recorrido público')
        inicio=EscenaCamino.objects.create(camino=juego,titulo='Inicio',texto='Decidí',es_inicio=True)
        final=EscenaCamino.objects.create(camino=juego,titulo='Fin',texto='Fin',es_final=True,tipo_final='bueno')
        OpcionEscenaCamino.objects.create(escena_origen=inicio,texto_opcion='Seguir',escena_destino=final)
        self.prueba.tipo='camino';self.prueba.save();self.prueba.items.all().delete()
        importar(self.prueba,juego);datos=preparar(self.prueba)
        self.assertEqual(self.prueba.items.count(),1)
        self.assertEqual(datos['grafo'][datos['inicio']]['opciones'][0]['destino'],'final_bueno')

    def test_camino_editable_sin_saltos_y_final_corregido(self):
        self.prueba.tipo='camino';self.prueba.save()
        form=ItemForm({'texto':'Decisión','opciones_texto':'Ayudar\nIgnorar','destino_1':'final_bueno',
            'destino_2':'final_malo','activo':'on'},instance=self.item,prueba=self.prueba)
        self.assertTrue(form.is_valid(),form.errors);form.save()
        i=self.iniciar();url=reverse('aula:prueba_resolver',args=[i.pk])
        self.client.post(url,{'paso':0,'decision':'final_bueno','puntaje':100});i.refresh_from_db()
        self.assertEqual(i.estado,'abierto')
        opcion=i.estructura['grafo'][i.estructura['inicio']]['opciones'][0]
        self.client.post(url,{'paso':0,'decision':opcion['id']});i.refresh_from_db()
        self.assertTrue(i.aprobado);self.assertEqual(i.puntaje,100)

    def test_camino_sin_salida_no_publica(self):
        self.prueba.tipo='camino';self.prueba.save()
        self.item.opciones=['Volver','Seguir'];self.item.respuesta=json.dumps({'destinos':[str(self.item.pk)]*2});self.item.save()
        with self.assertRaises(ValidationError):preparar(self.prueba)

    def test_pantallas_de_gestion_y_curso_abre_nueva_pestana(self):
        self.client.force_login(self.director)
        for nombre,args in [('prueba_nueva',[self.curso.pk]),('prueba_editar',[self.prueba.pk]),
            ('prueba_item_nuevo',[self.prueba.pk]),('registro_curso',[self.curso.pk]),('certificacion_configurar',[self.curso.pk]),('cierre_editar',[self.inscripcion.pk])]:
            with self.subTest(pantalla=nombre):self.assertEqual(self.client.get(reverse('aula:'+nombre,args=args)).status_code,200)
        self.client.force_login(self.alumna);self.assertContains(self.client.get('/aula/'),'target="_blank" rel="noopener"')
