from django import template
from django.urls import reverse
from aula.models import Perfil

register = template.Library()


@register.inclusion_tag('aula/identidad.html', takes_context=True)
def identidad(context, persona, grande=False):
    perfil = getattr(persona, 'perfil_aula', None)
    viewer = context.get('user')
    nombre = persona.get_full_name() or persona.username
    iniciales = ((persona.first_name[:1] + persona.last_name[:1]) or persona.username[:2]).upper()
    avatar = dict(Perfil.AVATARES).get(perfil.avatar, '') if perfil and perfil.avatar else ''
    foto = ''
    if perfil and perfil.foto and not avatar and (viewer == persona or getattr(viewer, 'is_superuser', False) or perfil.compartir_foto):
        foto = reverse('aula:perfil_foto_persona', args=[persona.pk])
    return {'foto_identidad': foto, 'simbolo_identidad': avatar.split(' ')[0] if avatar else iniciales,
            'nombre_identidad': nombre, 'grande_identidad': grande}
