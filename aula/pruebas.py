from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.admin.models import ADDITION, CHANGE
from django.core.exceptions import ValidationError, PermissionDenied
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Max
from django.http import Http404
from django.shortcuts import get_object_or_404,redirect,render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST,require_http_methods
from .models import Curso,Leccion,Inscripcion,Prueba,ItemPrueba,IntentoPrueba,CorreccionPrueba,RecursoLeccion
from .gestion import direccion,registrar,formulario
from .permisos import exigir
from .pruebas_forms import PruebaForm,ItemForm,CorreccionForm,ReglasForm
from .pruebas_motor import FUENTES,importar,preparar,corregir,escena_actual


@direccion
@require_http_methods(['GET','POST'])
def nueva(request,curso_pk):
    curso=get_object_or_404(Curso,pk=curso_pk)
    form=PruebaForm(request.POST or None,request.FILES or None,curso=curso,initial={'modulo':request.GET.get('modulo')})
    if request.method=='POST' and form.is_valid():
        guardados=[]
        try:
            with transaction.atomic():
                Curso.objects.select_for_update().get(pk=curso.pk)
                d=form.cleaned_data
                fuente=d['fuente'].split(':') if d['fuente'] else None
                tipo=fuente[0] if fuente else d['tipo']
                leccion=Leccion.objects.create(modulo=d['modulo'],titulo=d['titulo'],obligatoria=False,
                    orden=(d['modulo'].lecciones.aggregate(n=Max('orden'))['n'] or 0)+1)
                prueba=Prueba.objects.create(leccion=leccion,tipo=tipo,instrucciones=d['instrucciones'],
                    minimo=d['minimo'],max_intentos=d['max_intentos'],obligatoria=d['obligatoria'])
                if fuente:
                    juego=get_object_or_404(FUENTES[tipo],pk=fuente[1])
                    importar(prueba,juego)
                    prueba.origen=f'{juego.titulo} ({tipo}, {juego.pk})'
                    prueba.save(update_fields=['origen'])
                if tipo=='rompecabezas':
                    if d.get('imagen_archivo'):
                        from .archivos import preparar_recursos,guardar_recursos
                        preparados=preparar_recursos([d['imagen_archivo']])
                        guardar_recursos(leccion,preparados,guardados)
                        recurso=leccion.recursos.get()
                    else:
                        imagen=d['imagen']
                        recurso=RecursoLeccion(leccion=leccion,nombre=imagen.nombre,tipo='imagen',mime=imagen.mime)
                        with imagen.archivo.open('rb') as src:
                            recurso.archivo.save(imagen.nombre,ContentFile(src.read()),save=False)
                        guardados.append(recurso.archivo)
                        recurso.save()
                    prueba.contenido={'imagen':str(recurso.pk)}
                    prueba.save(update_fields=['contenido'])
                registrar(request,prueba,ADDITION,'Prueba privada creada en el curso.')
        except Exception as exc:
            for archivo in guardados:
                try:
                    archivo.delete(save=False)
                except OSError:
                    pass
            if not isinstance(exc,(ValidationError,OSError)):
                raise
            form.add_error(None,exc if isinstance(exc,ValidationError) else 'No se pudo copiar la imagen. Intentá de nuevo.')
        else:
            messages.success(request,'Prueba creada como borrador. Revisá sus actividades antes de publicarla.')
            return redirect('aula:prueba_editar',pk=prueba.pk)
    return formulario(request,form,'Agregar una prueba','Elegí un juego para copiar o creá una actividad privada del curso.',reverse('aula:gestion_curso',args=[curso.pk]),'Crear prueba')


@direccion
@require_http_methods(['GET','POST'])
def editar(request,pk):
    prueba=get_object_or_404(Prueba.objects.select_related('leccion__modulo__curso'),pk=pk,leccion__eliminada=False)
    reglas=ReglasForm(request.POST if request.POST.get('accion')=='reglas' else None,instance=prueba)
    if request.method=='POST' and request.POST.get('accion')=='reglas':
        if reglas.is_valid():
            with transaction.atomic():
                vigente=Prueba.objects.select_for_update().get(pk=pk)
                # Dar más intentos no invalida lo ya resuelto. Cambiar el criterio sí crea versión.
                cambia_criterio=vigente.minimo!=reglas.cleaned_data['minimo']
                for campo,valor in reglas.cleaned_data.items():
                    setattr(vigente,campo,valor)
                if cambia_criterio:
                    vigente.revision+=1
                    vigente.leccion.publicada=False
                    vigente.leccion.save(update_fields=['publicada'])
                vigente.save()
                registrar(request,vigente,CHANGE,'Reglas de la prueba actualizadas.')
            messages.success(request,'Reglas guardadas.'+(' Revisá y publicá la nueva versión.' if cambia_criterio else ''))
            return redirect('aula:prueba_editar',pk=pk)
        return render(request,'aula/gestion/prueba.html',{'prueba':prueba,'items':prueba.items.all(),'reglas':reglas})
    if request.method=='POST':
        try:
            with transaction.atomic():
                prueba=Prueba.objects.select_for_update().get(pk=pk)
                if request.POST.get('accion')=='publicar':
                    preparar(prueba)
                    prueba.leccion.publicada=True
                elif request.POST.get('accion')=='ocultar':
                    prueba.leccion.publicada=False
                else:
                    raise Http404
                prueba.leccion.save(update_fields=['publicada'])
                registrar(request,prueba,CHANGE,'Se cambió la publicación de la prueba.')
        except ValidationError as exc:
            messages.error(request,' '.join(exc.messages))
        return redirect('aula:prueba_editar',pk=pk)
    return render(request,'aula/gestion/prueba.html',{'prueba':prueba,'items':prueba.items.all(),'reglas':reglas})


@direccion
@require_http_methods(['GET','POST'])
def item(request,pk,item_pk=None):
    prueba=get_object_or_404(Prueba,pk=pk)
    if prueba.tipo=='rompecabezas' or prueba.contenido.get('grafo'):
        raise Http404
    instancia=get_object_or_404(ItemPrueba,pk=item_pk,prueba=prueba) if item_pk else ItemPrueba(prueba=prueba)
    form=ItemForm(request.POST or None,instance=instancia,prueba=prueba)
    if request.method=='POST' and form.is_valid():
        with transaction.atomic():
            prueba=Prueba.objects.select_for_update().get(pk=pk)
            if not item_pk:
                if prueba.items.count()>=100:
                    form.add_error(None,'La prueba admite hasta 100 actividades.')
                else:
                    form.instance.orden=(prueba.items.aggregate(n=Max('orden'))['n'] or 0)+1
            if not form.errors:
                form.save()
                prueba.revision+=1
                prueba.save(update_fields=['revision'])
                prueba.leccion.publicada=False
                prueba.leccion.save(update_fields=['publicada'])
                registrar(request,prueba,CHANGE,'Contenido de prueba actualizado; nueva versión en borrador.')
                messages.success(request,'Actividad guardada. Revisá y publicá la prueba; los intentos anteriores quedan en el historial.')
                return redirect('aula:prueba_editar',pk=pk)
    return formulario(request,form,'Editar actividad' if item_pk else 'Agregar actividad',
        'Los cambios crean una nueva versión en borrador. Para aprobarla será necesario resolver la versión publicada.',reverse('aula:prueba_editar',args=[pk]))


def matricula(request,prueba):
    return get_object_or_404(Inscripcion,curso=prueba.leccion.modulo.curso,cursante=request.user,activa=True,
                            curso__publicado=True)


@login_required
@require_POST
def iniciar(request,pk):
    prueba=get_object_or_404(Prueba.objects.select_related('leccion__modulo__curso'),pk=pk,leccion__publicada=True,leccion__eliminada=False)
    inscripcion=matricula(request,prueba)
    try:
        with transaction.atomic():
            get_object_or_404(Inscripcion.objects.select_for_update(),pk=inscripcion.pk,activa=True,curso__publicado=True)
            prueba=get_object_or_404(Prueba.objects.select_for_update(),pk=pk,leccion__publicada=True,leccion__eliminada=False)
            intentos=prueba.intentos.filter(cursante=request.user,revision=prueba.revision)
            abierto=intentos.filter(estado='abierto').first()
            if abierto:
                return redirect('aula:prueba_resolver',pk=abierto.pk)
            if intentos.count()>=prueba.max_intentos:
                raise ValidationError('Ya usaste los intentos permitidos de esta versión. Consultá al equipo formador.')
            intento=IntentoPrueba.objects.create(prueba=prueba,cursante=request.user,
                numero=(prueba.intentos.filter(cursante=request.user).aggregate(n=Max('numero'))['n'] or 0)+1,
                revision=prueba.revision,estructura=preparar(prueba),minimo=prueba.minimo)
        return redirect('aula:prueba_resolver',pk=intento.pk)
    except ValidationError as exc:
        messages.error(request,' '.join(exc.messages))
        return redirect(reverse('aula:curso',args=[prueba.leccion.modulo.curso_id])+f'?clase={prueba.leccion_id}')


@login_required
@require_http_methods(['GET','POST'])
def resolver(request,pk):
    intento=get_object_or_404(IntentoPrueba.objects.select_related('prueba__leccion__modulo__curso'),pk=pk,cursante=request.user)
    inscripcion=matricula(request,intento.prueba)
    if not intento.prueba.leccion.publicada or intento.revision!=intento.prueba.revision:
        if intento.estado=='abierto':
            messages.info(request,'Esta versión dejó de estar disponible. Volvé a la clase para abrir la versión actual.')
            return redirect('aula:curso',pk=intento.prueba.leccion.modulo.curso_id)
    if request.method=='POST' and intento.estado=='abierto':
        try:
            with transaction.atomic():
                get_object_or_404(Inscripcion.objects.select_for_update(),pk=inscripcion.pk,activa=True,curso__publicado=True)
                vigente=Prueba.objects.select_for_update().get(pk=intento.prueba_id)
                intento=IntentoPrueba.objects.select_for_update().get(pk=pk,cursante=request.user)
                if intento.estado!='abierto':
                    return redirect('aula:prueba_resolver',pk=pk)
                if not vigente.leccion.publicada or vigente.revision!=intento.revision:
                    raise ValidationError('La prueba cambió. Volvé al curso para abrir la versión publicada.')
                if intento.estructura.get('grafo'):
                    nodo,escena=escena_actual(intento)
                    if str(request.POST.get('paso'))!=str(len(intento.respuestas.get('ruta',[]))):
                        raise ValidationError('El recorrido cambió. Revisá la escena actual.')
                    elegida=request.POST.get('decision')
                    if escena['final'] or elegida not in {o['id'] for o in escena['opciones']}:
                        raise ValidationError('Elegí una opción de esta escena.')
                    ruta=intento.respuestas.get('ruta',[])
                    intento.respuestas={'ruta':ruta+[elegida]}
                    _,escena=escena_actual(intento)
                    if escena['final']:
                        intento.puntaje={'bueno':100,'neutro':50,'malo':0}.get(escena['resultado'],0)
                        intento.estado='corregido'
                    elif len(intento.respuestas['ruta'])>=100:
                        intento.puntaje=0
                        intento.estado='corregido'
                        messages.info(request,'El recorrido terminó al alcanzar 100 decisiones sin llegar a un final. Consultá al equipo antes de volver a intentar.')
                else:
                    intento.respuestas,intento.puntaje=corregir(intento.estructura,request.POST)
                    intento.estado='pendiente' if intento.puntaje is None else 'corregido'
                if intento.estado!='abierto':
                    intento.entregado=timezone.now()
                    intento.aprobado=intento.puntaje is not None and intento.puntaje>=intento.minimo
                intento.save()
            return redirect('aula:prueba_resolver',pk=pk)
        except ValidationError as exc:
            messages.error(request,' '.join(exc.messages))
    from .views import curso as vista_curso
    return vista_curso(request,pk=intento.prueba.leccion.modulo.curso_id,intento=intento)


@login_required
@require_http_methods(['GET','POST'])
def revisar(request,pk):
    intento=get_object_or_404(IntentoPrueba.objects.select_related('prueba__leccion__modulo__curso','cursante'),pk=pk)
    curso=intento.prueba.leccion.modulo.curso
    exigir(request.user,curso,'corregir')
    form=CorreccionForm(request.POST or None)
    if intento.estado=='abierto':
        raise Http404
    if request.method=='POST' and form.is_valid():
        with transaction.atomic():
            inscripcion=Inscripcion.objects.select_for_update().get(curso=curso,cursante=intento.cursante)
            intento=IntentoPrueba.objects.select_for_update().get(pk=pk)
            CorreccionPrueba.objects.create(intento=intento,responsable=request.user,**form.cleaned_data)
            intento.puntaje=form.cleaned_data['puntaje']
            intento.aprobado=intento.puntaje>=intento.minimo
            intento.estado='corregido'
            intento.save(update_fields=['puntaje','aprobado','estado'])
            if not intento.aprobado and intento.revision==intento.prueba.revision and intento.prueba.obligatoria:
                if not intento.prueba.intentos.filter(cursante=intento.cursante,revision=intento.revision,aprobado=True).exists():
                    from .certificados import retirar_aprobacion
                    retirar_aprobacion(inscripcion,request.user,'Se corrigió una prueba obligatoria y dejó de estar aprobada.')
            registrar(request,intento,CHANGE,'Corrección registrada con devolución e historial.')
        messages.success(request,'Corrección guardada y disponible para el cursante.')
        if request.POST.get('continuar') == '1':
            siguiente = IntentoPrueba.objects.filter(prueba__leccion__modulo__curso=curso, estado='pendiente').exclude(pk=pk).order_by('entregado', 'pk').first()
            if siguiente:
                return redirect('aula:prueba_revisar', pk=siguiente.pk)
            return redirect(reverse('aula:registro_curso', args=[curso.pk]) + '?vista=entregas&estado=pendiente')
        return redirect('aula:prueba_revisar',pk=pk)
    preguntas=[]
    if intento.estructura.get('grafo'):
        nodo=intento.estructura['inicio']
        for decision in intento.respuestas.get('ruta',[]):
            escena=intento.estructura['grafo'][nodo]
            opcion=next(o for o in escena['opciones'] if o['id']==decision)
            preguntas.append({'texto':escena['texto'],'respuesta':opcion['texto']})
            nodo=opcion['destino']
    for p in intento.estructura.get('preguntas',[]):
        respuesta=intento.respuestas.get(p['id'],'')
        opciones={o['id']:o['texto'] for o in p.get('opciones',[])}
        respuesta=' → '.join(opciones.get(v,v) for v in respuesta) if isinstance(respuesta,list) else opciones.get(respuesta,respuesta)
        preguntas.append({'texto':p['texto'],'respuesta':respuesta})
    return render(request,'aula/gestion/revisar.html',{'intento':intento,'form':form,'preguntas':preguntas,'curso':curso})
