from django import forms
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.admin.models import CHANGE
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count,Q
from django.shortcuts import get_object_or_404,redirect
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from .models import Curso,TemaForo,RespuestaForo
from .permisos import permisos
from .gestion import registrar

class TemaForm(forms.Form):
    titulo=forms.CharField(max_length=160,label='Asunto de la consulta')
    texto=forms.CharField(max_length=6000,widget=forms.Textarea(attrs={'rows':5}),label='Tu consulta')

class RespuestaForm(forms.Form):
    texto=forms.CharField(max_length=6000,widget=forms.Textarea(attrs={'rows':4}),label='Tu respuesta')

def acceso(request,pk):
    from .views import cursos_permitidos
    curso=get_object_or_404(cursos_permitidos(request.user),pk=pk)
    p=permisos(request.user,curso)
    equipo=request.user.is_superuser or curso.formadores.filter(pk=request.user.pk).exists()
    return curso,p,equipo

def escribir(request,curso,p,equipo):
    if equipo and not p['responder_foro']:
        raise PermissionDenied

def url(curso,tema=None):
    return reverse('aula:curso',args=[curso.pk])+'?vista=foro'+(f'&tema={tema.pk}' if tema else '')

def contexto(request,curso,extra=None):
    extra=extra or {}
    p=permisos(request.user,curso)
    equipo=request.user.is_superuser or curso.formadores.filter(pk=request.user.pk).exists()
    temas=TemaForo.objects.filter(curso=curso).select_related('autor')
    if not p['moderar_foro']:
        temas=temas.filter(oculto=False)
    tema_id=extra.get('tema_id') or request.GET.get('tema')
    tema=None;respuestas=[]
    if tema_id:
        tema=get_object_or_404(temas,pk=tema_id if str(tema_id).isdigit() and len(str(tema_id))<19 else 0)
        respuestas=tema.respuestas.select_related('autor')
        if not p['moderar_foro']:
            respuestas=respuestas.filter(oculto=False)
        respuestas=Paginator(respuestas,20).get_page(request.GET.get('pagina'))
    busqueda=request.GET.get('buscar','')[:160]
    if busqueda:
        temas=temas.filter(Q(titulo__icontains=busqueda)|Q(texto__icontains=busqueda))
    temas=temas.annotate(cantidad=Count('respuestas',filter=Q(respuestas__oculto=False))).order_by('-actualizado','-pk')
    datos={'tema_foro':tema,'temas_foro':Paginator(temas,20).get_page(request.GET.get('pagina')),
        'respuestas_foro':respuestas,'foro_permisos':p,'foro_escribir':not equipo or p['responder_foro'],
        'foro_gestionar':bool(tema and (p['moderar_foro'] or tema.autor_id==request.user.pk)),
        'form_tema':TemaForm(),'form_respuesta':RespuestaForm(),'foro_buscar':busqueda,
        'formadores_foro':set(curso.formadores.values_list('pk',flat=True))}
    datos.update(extra)
    return datos

@login_required
@require_POST
def nuevo(request,pk):
    curso,p,equipo=acceso(request,pk);escribir(request,curso,p,equipo)
    form=TemaForm(request.POST)
    if form.is_valid():
        with transaction.atomic():
            # Serializa con cambios del curso y revalida el acceso antes de escribir.
            Curso.objects.select_for_update().get(pk=pk)
            curso,p,equipo=acceso(request,pk);escribir(request,curso,p,equipo)
            tema=TemaForo.objects.create(curso=curso,autor=request.user,**form.cleaned_data)
        return redirect(url(curso,tema))
    from .views import curso as vista
    return vista(request,pk=pk,foro_extra={'form_tema':form})

@login_required
@require_POST
def responder(request,pk):
    tema=get_object_or_404(TemaForo,pk=pk)
    curso,p,equipo=acceso(request,tema.curso_id);escribir(request,curso,p,equipo)
    form=RespuestaForm(request.POST)
    if form.is_valid():
        with transaction.atomic():
            tema=TemaForo.objects.select_for_update().get(pk=pk)
            curso,p,equipo=acceso(request,tema.curso_id);escribir(request,curso,p,equipo)
            if tema.oculto or tema.cerrado:
                raise PermissionDenied
            RespuestaForo.objects.create(tema=tema,autor=request.user,**form.cleaned_data)
            tema.actualizado=timezone.now();tema.resuelto=False
            tema.save(update_fields=['actualizado','resuelto'])
        pagina=(tema.respuestas.filter(oculto=False).count()+19)//20
        return redirect(url(curso,tema)+f'&pagina={pagina}')
    if tema.oculto and not p['moderar_foro']:
        raise PermissionDenied
    from .views import curso as vista
    return vista(request,pk=curso.pk,foro_extra={'form_respuesta':form,'tema_id':tema.pk})

@login_required
@require_POST
def moderar(request,pk):
    with transaction.atomic():
        tema=get_object_or_404(TemaForo.objects.select_for_update(),pk=pk)
        curso,p,equipo=acceso(request,tema.curso_id)
        accion=request.POST.get('accion')
        if accion in {'resolver','pendiente'} and (p['moderar_foro'] or tema.autor_id==request.user.pk):
            if tema.oculto and not p['moderar_foro']:
                raise PermissionDenied
            tema.resuelto=accion=='resolver'
        elif p['moderar_foro'] and accion in {'cerrar','abrir','ocultar','mostrar'}:
            if accion in {'cerrar','abrir'}:tema.cerrado=accion=='cerrar'
            else:tema.oculto=accion=='ocultar'
        elif p['moderar_foro'] and accion in {'ocultar_respuesta','mostrar_respuesta'}:
            identificador=request.POST.get('respuesta','')
            respuesta=get_object_or_404(RespuestaForo,pk=identificador if identificador.isdigit() and len(identificador)<19 else 0,tema=tema)
            respuesta.oculto=accion=='ocultar_respuesta';respuesta.save(update_fields=['oculto'])
        else:
            raise PermissionDenied
        tema.save()
        registrar(request,tema,CHANGE,'Foro: '+accion)
    messages.success(request,'Consulta actualizada.')
    return redirect(url(curso,tema))
