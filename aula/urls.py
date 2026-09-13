from django.contrib.auth import views as auth_views
from django.urls import path
from . import views

app_name = 'aula'
urlpatterns = [
    path('', views.panel, name='panel'),
    path('ingresar/', auth_views.LoginView.as_view(template_name='aula/login.html'), name='login'),
    path('salir/', auth_views.LogoutView.as_view(next_page='inicio'), name='logout'),
    path('cursos/<int:pk>/', views.curso, name='curso'),
    path('lecciones/<int:pk>/completar/', views.completar, name='completar'),
]
