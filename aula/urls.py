from django.contrib.auth import views as auth_views
from django.urls import path
from . import views
from . import gestion
from . import recursos

app_name = 'aula'
urlpatterns = [
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
