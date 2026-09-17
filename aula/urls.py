from django.contrib.auth import views as auth_views
from django.urls import path
from . import views
from . import gestion
from . import recursos
from . import pruebas, certificados
from . import foro,disenos,tableros
from . import perfil
from core.seguridad import comunicacion

app_name = 'aula'
urlpatterns = [
    path('mi-perfil/', perfil.editar, name='perfil'),
    path('comunicacion/', comunicacion, name='comunicacion'),
    path('gestion/inscripciones/<int:pk>/',tableros.ficha,name='ficha_cursante'),
    path('gestion/inscripciones/<int:pk>/datos/',gestion.inscripcion_editar,name='inscripcion_editar'),
    path('gestion/cursos/<int:curso_pk>/clases/<int:pk>/organizar/',gestion.organizar_clase,name='organizar_clase'),
    path('gestion/cursos/<int:curso_pk>/clases/<int:pk>/eliminar/',gestion.eliminar_leccion,name='gestion_leccion_eliminar'),
    path('gestion/cursos/<int:curso_pk>/clases/<int:pk>/restaurar/',gestion.restaurar_leccion,name='gestion_leccion_restaurar'),
    path('cursos/<int:pk>/foro/nuevo/',foro.nuevo,name='foro_nuevo'),
    path('foro/<int:pk>/responder/',foro.responder,name='foro_responder'),
    path('foro/<int:pk>/moderar/',foro.moderar,name='foro_moderar'),
    path('gestion/cursos/<int:pk>/diseno/<str:tipo>/',disenos.editar,name='diseno_certificado'),
    path('gestion/cursos/<int:pk>/diseno/<str:tipo>/fondo/',disenos.fondo,name='diseno_fondo'),
    path('gestion/cursos/<int:pk>/diseno/<str:tipo>/ejemplo.pdf',disenos.vista_previa,name='diseno_previa'),
    path('gestion/cursos/<int:curso_pk>/pruebas/nueva/',pruebas.nueva,name='prueba_nueva'),
    path('gestion/pruebas/<int:pk>/',pruebas.editar,name='prueba_editar'),
    path('gestion/pruebas/<int:pk>/actividades/nueva/',pruebas.item,name='prueba_item_nuevo'),
    path('gestion/pruebas/<int:pk>/actividades/<uuid:item_pk>/',pruebas.item,name='prueba_item_editar'),
    path('pruebas/<int:pk>/iniciar/',pruebas.iniciar,name='prueba_iniciar'),
    path('intentos/<uuid:pk>/',pruebas.resolver,name='prueba_resolver'),
    path('gestion/intentos/<uuid:pk>/',pruebas.revisar,name='prueba_revisar'),
    path('gestion/cursos/<int:pk>/registro/',certificados.registro,name='registro_curso'),
    path('gestion/cursos/<int:pk>/certificacion/',certificados.configurar,name='certificacion_configurar'),
    path('gestion/cursos/<int:pk>/actas.csv',certificados.exportar,name='registro_exportar'),
    path('gestion/inscripciones/<int:pk>/cierre/',certificados.cierre,name='cierre_editar'),
    path('gestion/inscripciones/<int:pk>/emitir/',certificados.emitir,name='certificado_emitir'),
    path('gestion/certificados/<uuid:pk>/revocar/',certificados.revocar,name='certificado_revocar'),
    path('certificados/<uuid:pk>.pdf',certificados.descargar,name='certificado_pdf'),
    path('constancias/<uuid:pk>/',certificados.verificar,name='certificado_verificar'),
    path('recursos/<uuid:pk>/archivo/', recursos.archivo, name='recurso_archivo'),
    path('recursos/<uuid:pk>/ver/', recursos.visor, name='recurso_visor'),
    path('gestion/recursos/<uuid:pk>/retirar/', gestion.retirar_recurso, name='recurso_retirar'),
    path('gestion/', gestion.inicio, name='gestion'),
    path('gestion/cursos/nuevo/', gestion.editar_curso, name='gestion_curso_nuevo'),
    path('gestion/cursos/<int:pk>/', gestion.detalle, name='gestion_curso'),
    path('gestion/cursos/<int:pk>/editar/', gestion.editar_curso, name='gestion_curso_editar'),
    path('gestion/cursos/<int:curso_pk>/modulos/nuevo/', gestion.editar_modulo, name='gestion_modulo_nuevo'),
    path('gestion/cursos/<int:curso_pk>/modulos/<int:pk>/', gestion.editar_modulo, name='gestion_modulo_editar'),
    path('gestion/cursos/<int:curso_pk>/clases/nueva/', gestion.editar_leccion, name='gestion_leccion_nueva'),
    path('gestion/cursos/<int:curso_pk>/modulos/<int:modulo_pk>/clases/nueva/', gestion.editar_leccion, name='gestion_modulo_leccion_nueva'),
    path('gestion/cursos/<int:curso_pk>/clases/<int:pk>/', gestion.editar_leccion, name='gestion_leccion_editar'),
    path('gestion/cursos/<int:curso_pk>/personas/nueva/', gestion.agregar_persona, name='gestion_persona_nueva'),
    path('gestion/cursos/<int:curso_pk>/personas/existente/', gestion.agregar_persona, {'existente': True}, name='gestion_persona_existente'),
    path('', views.panel, name='panel'),
    path('ingresar/', auth_views.LoginView.as_view(template_name='aula/login.html'), name='login'),
    path('salir/', auth_views.LogoutView.as_view(next_page='inicio'), name='logout'),
    path('cursos/<int:pk>/', views.curso, name='curso'),
    path('lecciones/<int:pk>/completar/', views.completar, name='completar'),
]
