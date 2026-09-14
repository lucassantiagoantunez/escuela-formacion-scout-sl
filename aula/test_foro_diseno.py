import io
import json
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase,Client,override_settings
from django.urls import reverse
from pypdf import PdfReader,PdfWriter
from .models import (Curso,Modulo,Leccion,Inscripcion,Progreso,PermisoFormador,TemaForo,RespuestaForo,
    DisenoCertificado,CierreCurso,Certificado)
from .disenos import DisenoForm,inicial,ejemplo,dibujar
from .permisos import permisos
from .certificados import generar_pdf

class ForoDisenoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User=get_user_model()
        cls.admin=User.objects.create_superuser('direccion-foro')
        cls.alumno=User.objects.create_user('cursante-foro')
        cls.docente=User.objects.create_user('formador-foro',is_staff=True)
        cls.otro=User.objects.create_user('ajeno-foro')
        cls.curso=Curso.objects.create(titulo='Curso de prueba',publicado=True,certificacion_configurada=True,
            fecha_inicio=date(2025,1,1),fecha_fin=date(2025,2,1),responsable_certificados='Autoridad de prueba')
        cls.curso.formadores.add(cls.docente)
        cls.inscripcion=Inscripcion.objects.create(curso=cls.curso,cursante=cls.alumno)
        cls.tema=TemaForo.objects.create(curso=cls.curso,autor=cls.alumno,titulo='Consulta de prueba',texto='Una duda')
        cls.otrocurso=Curso.objects.create(titulo='Otro curso',publicado=True)

    def foro(self,tema=None):
        return reverse('aula:curso',args=[self.curso.pk])+'?vista=foro'+(f'&tema={tema.pk}' if tema else '')

    def diseno_url(self,tipo='participacion',curso=None):
        return reverse('aula:diseno_certificado',args=[(curso or self.curso).pk,tipo])

    def datos_diseno(self):
        f=DisenoForm(diseno=DisenoCertificado(curso=self.curso,tipo='participacion'))
        return {**f.initial,'activo':'on'}

    def test_foro_privado_y_matricula_pausada(self):
        self.assertEqual(self.client.get(self.foro()).status_code,302)
        self.client.force_login(self.otro);self.assertEqual(self.client.get(self.foro()).status_code,404)
        self.client.force_login(self.alumno);self.assertContains(self.client.get(self.foro()),'Consulta de prueba')
        self.inscripcion.activa=False;self.inscripcion.save()
        self.assertEqual(self.client.get(self.foro()).status_code,404)
        self.assertEqual(self.client.post(reverse('aula:foro_responder',args=[self.tema.pk]),{'texto':'Sin acceso'}).status_code,404)

    def test_tema_y_respuesta_escapados_con_redireccion(self):
        self.client.force_login(self.alumno)
        r=self.client.post(reverse('aula:foro_nuevo',args=[self.curso.pk]),{'titulo':'Mi duda','texto':'<script>test()</script>'})
        self.assertEqual(r.status_code,302);tema=TemaForo.objects.get(titulo='Mi duda')
        r=self.client.get(r.url);self.assertContains(r,'&lt;script&gt;');self.assertNotContains(r,'<script>test()')
        self.client.force_login(self.docente)
        r=self.client.post(reverse('aula:foro_responder',args=[tema.pk]),{'texto':'La explicación del formador'},follow=True)
        self.assertContains(r,'La explicación del formador');self.assertContains(r,'Equipo formador')
        self.assertEqual(tema.respuestas.count(),1)

    def test_formador_con_permiso_retirado_no_responde(self):
        PermisoFormador.objects.create(curso=self.curso,formador=self.docente,responder_foro=False)
        self.client.force_login(self.docente)
        self.assertNotContains(self.client.get(self.foro(self.tema)),'Publicar respuesta')
        self.assertEqual(self.client.post(reverse('aula:foro_responder',args=[self.tema.pk]),{'texto':'No autorizado'}).status_code,403)

    def test_moderacion_y_resolucion_no_borran_historial(self):
        self.client.force_login(self.alumno);url=reverse('aula:foro_moderar',args=[self.tema.pk])
        self.client.post(url,{'accion':'resolver'});self.tema.refresh_from_db();self.assertTrue(self.tema.resuelto)
        self.assertEqual(self.client.post(url,{'accion':'ocultar'}).status_code,403)
        PermisoFormador.objects.create(curso=self.curso,formador=self.docente,moderar_foro=True)
        self.client.force_login(self.docente);self.client.post(url,{'accion':'ocultar'})
        self.client.force_login(self.alumno);self.assertEqual(self.client.get(self.foro(self.tema)).status_code,404)
        self.assertEqual(TemaForo.objects.count(),1)
        self.client.force_login(self.docente);self.client.post(url,{'accion':'mostrar'});self.client.post(url,{'accion':'cerrar'})
        self.client.force_login(self.alumno)
        self.assertEqual(self.client.post(reverse('aula:foro_responder',args=[self.tema.pk]),{'texto':'cerrada'}).status_code,403)

    def test_tema_de_otro_curso_no_se_mezcla(self):
        t=TemaForo.objects.create(curso=self.otrocurso,autor=self.otro,titulo='Privado de otro',texto='Oculto')
        self.client.force_login(self.alumno)
        self.assertEqual(self.client.get(self.foro(t)).status_code,404)
        self.assertEqual(self.client.post(reverse('aula:foro_responder',args=[t.pk]),{'texto':'Ajeno'}).status_code,404)

    def test_foro_invalidos_y_csrf(self):
        self.client.force_login(self.alumno)
        r=self.client.post(reverse('aula:foro_nuevo',args=[self.curso.pk]),{'titulo':'Conservar este título','texto':''})
        self.assertContains(r,'Conservar este título');self.assertEqual(TemaForo.objects.count(),1)
        client=Client(enforce_csrf_checks=True);client.force_login(self.alumno)
        self.assertEqual(client.post(reverse('aula:foro_nuevo',args=[self.curso.pk]),{'titulo':'Test','texto':'Test'}).status_code,403)

    def test_permisos_no_se_extienden_a_otro_curso_ni_al_quitar_asignacion(self):
        PermisoFormador.objects.create(curso=self.curso,formador=self.docente,emitir=True,disenar=True)
        self.assertTrue(permisos(self.docente,self.curso)['emitir'])
        self.assertFalse(permisos(self.docente,self.otrocurso)['emitir'])
        self.curso.formadores.remove(self.docente)
        self.assertFalse(permisos(self.docente,self.curso)['emitir'])

    def test_formador_no_puede_concederse_permisos_en_admin(self):
        self.client.force_login(self.docente)
        self.assertEqual(self.client.get('/admin/aula/permisoformador/add/').status_code,403)
        self.assertEqual(self.client.post('/admin/aula/permisoformador/add/',{'curso':self.curso.pk,'formador':self.docente.pk,'emitir':'on'}).status_code,403)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get('/admin/aula/permisoformador/add/').status_code,200)

    def test_diseno_solo_autorizados(self):
        self.client.force_login(self.docente);self.assertEqual(self.client.get(self.diseno_url()).status_code,403)
        PermisoFormador.objects.create(curso=self.curso,formador=self.docente,disenar=True)
        self.assertContains(self.client.get(self.diseno_url()),'Vista de trabajo')
        self.assertEqual(self.client.get(self.diseno_url(curso=self.otrocurso)).status_code,403)
        self.assertEqual(self.client.post(reverse('aula:certificado_emitir',args=[self.inscripcion.pk]),{'tipo':'participacion'}).status_code,403)

    def test_guardar_y_vista_previa_no_emiten_certificados(self):
        self.client.force_login(self.admin)
        r=self.client.post(self.diseno_url(),self.datos_diseno());self.assertEqual(r.status_code,302)
        r=self.client.get(reverse('aula:diseno_previa',args=[self.curso.pk,'participacion']))
        self.assertEqual(r.status_code,200);pdf=PdfReader(io.BytesIO(r.content))
        self.assertEqual(len(pdf.pages),1);self.assertIn('EJEMPLO SIN VALIDEZ',pdf.pages[0].extract_text())
        self.assertEqual(Certificado.objects.count(),0)

    def test_posiciones_fuera_de_hoja_y_color_invalido(self):
        self.client.force_login(self.admin)
        d=self.datos_diseno();d['nombre_x']=90;d['color']='url(evil)'
        r=self.client.post(self.diseno_url(),d)
        self.assertEqual(r.status_code,200);self.assertFalse(DisenoCertificado.objects.exists())

    def test_pdf_de_dos_paginas_o_falso_rechazado(self):
        self.client.force_login(self.admin)
        writer=PdfWriter();writer.add_blank_page(842,595);writer.add_blank_page(842,595);out=io.BytesIO();writer.write(out)
        for data in [out.getvalue(),b'not a pdf']:
            d=self.datos_diseno();d['fondo']=SimpleUploadedFile('plantilla.pdf',data,content_type='application/pdf')
            self.assertEqual(self.client.post(self.diseno_url(),d).status_code,200)
            self.assertFalse(DisenoCertificado.objects.exists())

    def test_fondo_pdf_y_emision_conserva_version_anterior(self):
        self.client.force_login(self.admin)
        with TemporaryDirectory() as temporal,override_settings(AULA_PRIVATE_ROOT=Path(temporal)):
            writer=PdfWriter();writer.add_blank_page(842,595);out=io.BytesIO();writer.write(out)
            d=self.datos_diseno();d['fondo']=SimpleUploadedFile('plantilla.pdf',out.getvalue(),content_type='application/pdf')
            self.assertEqual(self.client.post(self.diseno_url(),d).status_code,302)
            diseno=DisenoCertificado.objects.get();viejo=diseno.fondo.name
            CierreCurso.objects.create(inscripcion=self.inscripcion,nombre_certificado='Nombre de prueba',participacion_validada=True,responsable=self.admin)
            self.client.post(reverse('aula:certificado_emitir',args=[self.inscripcion.pk]),{'tipo':'participacion'})
            cert=Certificado.objects.get();primero=cert.datos['diseno']
            d=self.datos_diseno();d.update(encabezado='Nuevo diseño',quitar_fondo='on')
            self.client.post(self.diseno_url(),d);cert.refresh_from_db()
            self.assertEqual(cert.datos['diseno'],primero);self.assertTrue((Path(temporal)/viejo).is_file())
            pdf=PdfReader(io.BytesIO(generar_pdf(cert)));self.assertEqual(len(pdf.pages),1)
            self.assertIn('Nombre de prueba',pdf.pages[0].extract_text())
            self.assertNotIn('Nuevo diseño',pdf.pages[0].extract_text())

    def test_permiso_emitir_no_permite_validar_y_se_puede_retirar(self):
        regla=PermisoFormador.objects.create(curso=self.curso,formador=self.docente,emitir=True)
        self.client.force_login(self.docente)
        self.assertEqual(self.client.get(reverse('aula:cierre_editar',args=[self.inscripcion.pk])).status_code,403)
        CierreCurso.objects.create(inscripcion=self.inscripcion,nombre_certificado='Prueba',participacion_validada=True,responsable=self.admin)
        self.client.post(reverse('aula:certificado_emitir',args=[self.inscripcion.pk]),{'tipo':'participacion'})
        self.assertEqual(Certificado.objects.count(),1)
        self.assertContains(self.client.get(reverse('aula:registro_curso',args=[self.curso.pk])),'Emitir participación')
        regla.emitir=False;regla.save()
        self.assertEqual(self.client.post(reverse('aula:certificado_emitir',args=[self.inscripcion.pk]),{'tipo':'participacion'}).status_code,403)

    def test_disenador_sin_seguimiento_no_ve_datos_de_cursantes(self):
        PermisoFormador.objects.create(curso=self.curso,formador=self.docente,disenar=True,ver_seguimiento=False,corregir=False)
        self.client.force_login(self.docente)
        r=self.client.get(reverse('aula:registro_curso',args=[self.curso.pk]))
        self.assertContains(r,'Diseñar certificado')
        self.assertNotContains(r,self.alumno.username);self.assertNotContains(r,'Validación de cursantes')

    def test_respuesta_final_y_orden_de_temas_paginados(self):
        RespuestaForo.objects.bulk_create([RespuestaForo(tema=self.tema,autor=self.alumno,texto=f'Respuesta {i}') for i in range(20)])
        self.client.force_login(self.alumno)
        r=self.client.post(reverse('aula:foro_responder',args=[self.tema.pk]),{'texto':'Última respuesta'},follow=True)
        self.assertContains(r,'Última respuesta');self.assertEqual(r.context['respuestas_foro'].number,2)
        self.assertEqual(self.client.get(self.foro()+'&tema='+'9'*100).status_code,404)

    def test_disenar_con_imagen_y_fondo_protegido(self):
        from PIL import Image
        out=io.BytesIO();Image.new('RGB',(840,595),'white').save(out,format='PNG')
        with TemporaryDirectory() as temporal,override_settings(AULA_PRIVATE_ROOT=Path(temporal)):
            self.client.force_login(self.admin);d=self.datos_diseno()
            d['fondo']=SimpleUploadedFile('fondo.png',out.getvalue(),content_type='image/png')
            self.assertEqual(self.client.post(self.diseno_url(),d).status_code,302)
            url=reverse('aula:diseno_fondo',args=[self.curso.pk,'participacion'])
            self.client.force_login(self.alumno);self.assertEqual(self.client.get(url).status_code,403)
            self.client.force_login(self.admin);r=self.client.get(url)
            self.assertEqual(r['Content-Type'],'image/png');r.close()

    def test_editor_quita_campos_y_conserva_identidad_en_segunda_pagina(self):
        self.client.force_login(self.admin);d=self.datos_diseno()
        d.update(pie='pagina',encabezado='')
        for key in inicial()['campos']:d.pop(key+'_visible',None)
        d['extras']=json.dumps([dict(texto='Texto propio <sin HTML>\nSegunda línea',x=20,y=88,ancho=60,alto=10,tamano=14,color='#123456',alineacion='izquierda',negrita=True)])
        self.assertEqual(self.client.post(self.diseno_url(),d).status_code,302)
        diseno=DisenoCertificado.objects.get()
        self.assertFalse(diseno.configuracion['campos']['nombre']['visible'])
        pdf=PdfReader(io.BytesIO(dibujar(ejemplo(self.curso,'participacion',diseno),muestra=True)))
        self.assertEqual(len(pdf.pages),2)
        self.assertIn('Texto propio <sin HTML>',pdf.pages[0].extract_text())
        self.assertNotIn('Curso de prueba',pdf.pages[0].extract_text())
        self.assertIn('Curso de prueba',pdf.pages[1].extract_text())
        self.assertIn('EJEMPLO SIN VALIDEZ',pdf.pages[1].extract_text())
        self.assertEqual(Certificado.objects.count(),0)

    def test_textos_propios_invalidos_no_se_guardan(self):
        self.client.force_login(self.admin)
        base=dict(texto='Prueba',x=10,y=10,ancho=80,alto=10,tamano=15,color='#123456')
        for extra in [{'x':float('nan')},{'color':'url(x)'},{'texto':['no']},{'y':99},{'alineacion':'javascript'}]:
            d=self.datos_diseno();d['extras']=json.dumps([{**base,**extra}])
            self.assertEqual(self.client.post(self.diseno_url(),d).status_code,200)
            self.assertFalse(DisenoCertificado.objects.exists())
        d=self.datos_diseno();d['extras']=json.dumps([base]*21)
        self.assertEqual(self.client.post(self.diseno_url(),d).status_code,200)
        self.assertFalse(DisenoCertificado.objects.exists())

    def test_diseno_antiguo_sigue_generando_una_pagina(self):
        diseno=DisenoCertificado(curso=self.curso,tipo='participacion',configuracion=inicial())
        pdf=PdfReader(io.BytesIO(dibujar(ejemplo(self.curso,'participacion',diseno))))
        self.assertEqual(len(pdf.pages),1)
        self.assertIn('EDiFoS SAN LUIS',pdf.pages[0].extract_text())
        self.assertIn('Curso de prueba',pdf.pages[0].extract_text())

    def test_fondo_pdf_con_segunda_pagina_no_pierde_verificacion(self):
        self.client.force_login(self.admin)
        with TemporaryDirectory() as temporal,override_settings(AULA_PRIVATE_ROOT=Path(temporal)):
            writer=PdfWriter();writer.add_blank_page(842,595);out=io.BytesIO();writer.write(out)
            d=self.datos_diseno();d.update(pie='pagina',nombre_y=90,nombre_alto=8)
            d['fondo']=SimpleUploadedFile('plantilla.pdf',out.getvalue(),content_type='application/pdf')
            self.assertEqual(self.client.post(self.diseno_url(),d).status_code,302)
            pdf=PdfReader(io.BytesIO(dibujar(ejemplo(self.curso,'participacion',DisenoCertificado.objects.get()),muestra=True)))
            self.assertEqual(len(pdf.pages),2)
            self.assertIn('Datos de verificación',pdf.pages[1].extract_text())
