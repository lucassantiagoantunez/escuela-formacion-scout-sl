from django import template
from django.utils.safestring import mark_safe
from aula.contenido import limpiar_html

register = template.Library()

@register.filter
def editorial_seguro(value):
    return mark_safe(limpiar_html(value))
