from django.core.exceptions import PermissionDenied
from .models import PermisoFormador

ACCIONES=('responder_foro','moderar_foro','ver_seguimiento','corregir','validar','emitir','disenar')
BASE={'responder_foro','ver_seguimiento','corregir'}

def permisos(user,curso):
    if not user.is_authenticated or not user.is_active:
        return dict.fromkeys(ACCIONES,False)
    if user.is_superuser:
        return dict.fromkeys(ACCIONES,True)
    from .accesos import bloqueados
    if bloqueados(user).filter(curso=curso).exists():
        return dict.fromkeys(ACCIONES,False)
    if not curso.formadores.filter(pk=user.pk).exists():
        return dict.fromkeys(ACCIONES,False)
    regla=PermisoFormador.objects.filter(curso=curso,formador=user).first()
    return {a:getattr(regla,a) if regla else a in BASE for a in ACCIONES}

def exigir(user,curso,accion):
    if not permisos(user,curso).get(accion,False):
        raise PermissionDenied

def puede_seguimiento(user,curso):
    p=permisos(user,curso)
    return any(p[a] for a in ('ver_seguimiento','corregir','validar','emitir','disenar'))
