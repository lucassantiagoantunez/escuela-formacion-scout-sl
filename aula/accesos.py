from datetime import timedelta
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.shortcuts import redirect
from .models import AccesoCurso, Perfil


def bloqueados(user):
    ahora = timezone.now()
    return AccesoCurso.objects.filter(usuario=user).filter(
        Q(habilitado=False) | Q(inicio__gt=ahora) | Q(fin__lte=ahora)).values('curso_id')


def iniciar_plazos(user):
    # One atomic start for simultaneous requests. Never restart an elapsed period.
    with transaction.atomic():
        for acceso in AccesoCurso.objects.select_for_update().filter(
                usuario=user, habilitado=True, inicio=None, fin=None, dias__isnull=False):
            acceso.inicio = timezone.now()
            acceso.fin = acceso.inicio + timedelta(days=acceso.dias)
            acceso.save(update_fields=['inicio', 'fin'])


class CuentaMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # Also covers active sessions when a new courtesy period is assigned.
            if request.path.startswith('/aula/'):
                iniciar_plazos(request.user)
            excepciones = ('/aula/cambiar-contrasena/', '/aula/salir/', '/admin/logout/')
            if request.path not in excepciones and not request.path.startswith(('/static/', '/media/')):
                if Perfil.objects.filter(usuario=request.user, cambiar_clave=True).exists():
                    return redirect('aula:password_change')
        return self.get_response(request)
