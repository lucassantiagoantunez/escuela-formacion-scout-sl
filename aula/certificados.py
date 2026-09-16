import csv
import io
from xml.sax.saxutils import escape
from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.admin.models import ADDITION,CHANGE
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied,ValidationError
from django.db import transaction
from django.db.models import Q
from django.forms.models import model_to_dict
from django.http import HttpResponse
from django.shortcuts import get_object_or_404,redirect,render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST,require_http_methods
from .gestion import direccion,registrar,formulario
from .permisos import exigir,permisos,puede_seguimiento
from .models import Curso,Inscripcion,Leccion,Progreso,Prueba,IntentoPrueba,CierreCurso,MovimientoAcademico,Certificado


class CertificacionForm(forms.ModelForm):
    class Meta:
        model=Curso
        fields=['requiere_acta','referencia_formacion','fecha_inicio','fecha_fin','horas','responsable_certificados']
        labels={'requiere_acta':'Este curso requiere asiento en el libro de actas para acreditar la formación',
            'referencia_formacion':'Nivel o referencia de formación (por ejemplo: Nivel I)',
            'fecha_inicio':'Fecha de inicio','fecha_fin':'Fecha de finalización','horas':'Carga horaria (opcional)',
            'responsable_certificados':'Nombre y función de la autoridad que valida los certificados'}
        widgets={'fecha_inicio':forms.DateInput(attrs={'type':'date'},format='%Y-%m-%d'),
                 'fecha_fin':forms.DateInput(attrs={'type':'date'},format='%Y-%m-%d')}
        help_texts={'requiere_acta':'Marcalo para los cursos que deban incorporarse al registro institucional. La web lleva el seguimiento; Dirección realiza y verifica el asiento en el libro.',
            'responsable_certificados':'Se imprime como autoridad responsable. No se agrega una firma manuscrita ni se atribuye validación externa automática.'}

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        for field in ['fecha_inicio','fecha_fin','responsable_certificados']:
            self.fields[field].required=True

    def clean(self):
        d=super().clean()
        if d.get('fecha_inicio') and d.get('fecha_fin') and d['fecha_fin']<d['fecha_inicio']:
            self.add_error('fecha_fin','La fecha debe ser igual o posterior al inicio.')
        if d.get('requiere_acta') and not d.get('referencia_formacion'):
            self.add_error('referencia_formacion','Indicá a qué nivel o formación corresponde el registro.')
        return d


class CierreForm(forms.ModelForm):
    class Meta:
        model=CierreCurso
        fields=['nombre_certificado','participacion_validada','requisitos_validados','aprobado','observaciones','libro','acta','folio','fecha_acta']
        labels={'nombre_certificado':'Nombre completo que figurará en el certificado',
            'participacion_validada':'Verifiqué la participación y la asistencia del cursante',
            'requisitos_validados':'Verifiqué tutoría, trabajos, autorizaciones y demás requisitos aplicables',
            'aprobado':'Dirección confirma la aprobación del curso','observaciones':'Fundamento y referencias de la validación (uso interno)',
            'libro':'Libro','acta':'Número de acta','folio':'Folio o página','fecha_acta':'Fecha del asiento en el libro'}
        widgets={'observaciones':forms.Textarea(attrs={'rows':4}),'fecha_acta':forms.DateInput(attrs={'type':'date'},format='%Y-%m-%d')}
        help_texts={'aprobado':'Las lecturas y pruebas obligatorias deben estar completadas. Si retirás una aprobación, se revocan sus certificados de aprobación.',
            'fecha_acta':'Completá estos datos únicamente después de verificar el asiento real en el libro institucional.'}

    def clean(self):
        d=super().clean()
        if (d.get('aprobado') or d.get('participacion_validada')) and not d.get('observaciones','').strip():
            self.add_error('observaciones','Dejá la referencia o fundamento de la validación.')
        datos=[d.get(k) for k in ['libro','acta','folio','fecha_acta']]
        if any(datos) and (not all(datos) or not d.get('aprobado')):
            self.add_error(None,'Para registrar el asiento, completá libro, acta, folio y fecha, con el curso aprobado.')
        if d.get('fecha_acta') and d['fecha_acta']>timezone.localdate():
            self.add_error('fecha_acta','No se puede confirmar un asiento con fecha futura.')
        if d.get('aprobado') and not (d.get('participacion_validada') and d.get('requisitos_validados')):
            self.add_error('aprobado','Primero validá la participación y los demás requisitos.')
        return d


def pendientes(inscripcion):
    clases=Leccion.objects.filter(modulo__curso=inscripcion.curso,publicada=True,obligatoria=True,prueba__isnull=True)
    faltan=clases.exclude(progreso__cursante=inscripcion.cursante).count()
    pruebas=Prueba.objects.filter(leccion__modulo__curso=inscripcion.curso,leccion__publicada=True,obligatoria=True)
    sin_aprobar=[p.leccion.titulo for p in pruebas.select_related('leccion') if not p.intentos.filter(cursante=inscripcion.cursante,revision=p.revision,aprobado=True).exists()]
    return faltan,sin_aprobar


def validar_aprobacion(inscripcion):
    faltan,pruebas=pendientes(inscripcion)
    if not inscripcion.activa:
        raise ValidationError('La inscripción está pausada. Revisala antes de validar la aprobación.')
    if not Leccion.objects.filter(modulo__curso=inscripcion.curso,publicada=True).exists():
        raise ValidationError('El curso todavía no tiene clases o pruebas publicadas.')
    if Leccion.objects.filter(modulo__curso=inscripcion.curso,publicada=False).filter(
            Q(obligatoria=True,prueba__isnull=True)|Q(prueba__obligatoria=True)).exists():
        raise ValidationError('Todavía hay clases o pruebas obligatorias en borrador. Revisá el programa antes de cerrar el curso.')
    if faltan or pruebas:
        raise ValidationError(f'Quedan {faltan} lecturas obligatorias y {len(pruebas)} pruebas por aprobar.')


def retirar_aprobacion(inscripcion,responsable,motivo):
    cierre=CierreCurso.objects.filter(inscripcion=inscripcion,aprobado=True).first()
    if cierre:
        cierre.aprobado=False
        cierre.responsable=responsable
        cierre.save(update_fields=['aprobado','responsable','actualizado'])
        MovimientoAcademico.objects.create(cierre=cierre,responsable=responsable,datos={
            'aprobado':False,'motivo':motivo,'libro':cierre.libro,'acta':cierre.acta,'folio':cierre.folio})
    inscripcion.certificados.filter(tipo='aprobacion',revocado=False).update(
        revocado=True,motivo_revocacion=motivo,fecha_revocacion=timezone.now(),revocado_por=responsable)


def autorizado_equipo(request,curso):
    if not puede_seguimiento(request.user,curso):
        raise PermissionDenied


@login_required
def registro(request,pk):
    from .tableros import pagina, ficha_datos
    from django.db.models import Exists, OuterRef, F
    curso=get_object_or_404(Curso,pk=pk)
    autorizado_equipo(request,curso)
    acciones=permisos(request.user,curso)
    ve_cursantes=acciones['ver_seguimiento'] or acciones['validar'] or acciones['emitir']
    ve_entregas=acciones['ver_seguimiento'] or acciones['corregir']
    permitidas=[]
    if ve_cursantes: permitidas.append('cierres')
    if ve_entregas: permitidas.append('entregas')
    if ve_cursantes or acciones['disenar']: permitidas.append('certificados')
    vista=request.GET.get('vista',permitidas[0])
    if vista not in permitidas: raise PermissionDenied
    buscar=request.GET.get('buscar','')[:160]
    estado=request.GET.get('estado','pendiente' if vista=='entregas' else '')
    datos={'curso':curso,'acciones':acciones,'ve_cursantes':ve_cursantes,'ve_entregas':ve_entregas,
           'seccion':vista,'buscar':buscar,'estado':estado,'inscripciones':[],'intentos':[]}
    if vista=='entregas':
        intentos=IntentoPrueba.objects.filter(prueba__leccion__modulo__curso=curso).exclude(estado='abierto').select_related('cursante','prueba__leccion').order_by('-entregado','-pk')
        if estado in ('pendiente','corregido'): intentos=intentos.filter(estado=estado)
        intentos=intentos.filter(Q(cursante__first_name__icontains=buscar)|Q(cursante__last_name__icontains=buscar)|Q(cursante__username__icontains=buscar)|Q(prueba__leccion__titulo__icontains=buscar))
        datos.update(pagina(request,intentos,20));datos['intentos']=datos['pagina']
    elif ve_cursantes:
        inscritos=curso.inscripciones.select_related('cursante','tutor','cierre').filter(Q(cursante__first_name__icontains=buscar)|Q(cursante__last_name__icontains=buscar)|Q(cursante__username__icontains=buscar)).order_by('cursante__first_name','cursante__username')
        if estado=='aprobado': inscritos=inscritos.filter(cierre__aprobado=True)
        elif estado=='acta':
            inscritos=inscritos.filter(cierre__aprobado=True).filter(Q(cierre__libro='')|Q(cierre__acta='')|Q(cierre__folio='')|Q(cierre__fecha_acta=None)) if curso.requiere_acta else inscritos.none()
        elif estado=='emitido': inscritos=inscritos.filter(certificados__tipo='aprobacion',certificados__revocado=False).distinct()
        elif estado=='pausada': inscritos=inscritos.filter(activa=False)
        elif estado in ('revisar','pendientes'):
            lecturas=Leccion.objects.filter(modulo__curso=curso,publicada=True,obligatoria=True,prueba__isnull=True)
            aprobadas=IntentoPrueba.objects.filter(cursante_id=OuterRef('cursante_id'),prueba__leccion__modulo__curso=curso,prueba__leccion__eliminada=False,prueba__leccion__publicada=True,prueba__obligatoria=True,revision=F('prueba__revision'),aprobado=True).values('prueba_id').distinct()
            from django.db.models import Count,Subquery,IntegerField,Value
            from django.db.models.functions import Coalesce
            lecturas_hechas=Progreso.objects.filter(cursante_id=OuterRef('cursante_id'),leccion__in=lecturas).order_by().values('cursante_id').annotate(n=Count('pk')).values('n')
            pruebas_hechas=aprobadas.order_by().values('cursante_id').annotate(n=Count('prueba_id',distinct=True)).values('n')
            total_pruebas=Prueba.objects.filter(leccion__modulo__curso=curso,leccion__eliminada=False,leccion__publicada=True,obligatoria=True).count()
            inscritos=inscritos.filter(activa=True).exclude(cierre__aprobado=True).annotate(lecturas_n=Coalesce(Subquery(lecturas_hechas,output_field=IntegerField()),Value(0)),pruebas_n=Coalesce(Subquery(pruebas_hechas,output_field=IntegerField()),Value(0)))
            completos=Q(lecturas_n=lecturas.count(),pruebas_n=total_pruebas)
            inscritos=inscritos.filter(completos) if estado=='revisar' else inscritos.exclude(completos)
        datos.update(pagina(request,inscritos,15))
        datos['pagina'].object_list=ficha_datos(curso,datos['pagina'])
        datos['inscripciones']=datos['pagina']
    return render(request,'aula/gestion/registro.html',datos)


@direccion
@require_http_methods(['GET','POST'])
def configurar(request,pk):
    curso=get_object_or_404(Curso,pk=pk)
    form=CertificacionForm(request.POST or None,instance=curso)
    if request.method=='POST' and form.is_valid():
        with transaction.atomic():
            form.instance.certificacion_configurada=True
            form.save()
            registrar(request,curso,CHANGE,'Configuración de certificados y registro institucional actualizada.')
        return redirect('aula:registro_curso',pk=pk)
    return formulario(request,form,'Certificados y libro de actas','Definí cómo se acredita este curso antes de emitir certificados.',reverse('aula:registro_curso',args=[pk]))


@login_required
@require_http_methods(['GET','POST'])
def cierre(request,pk):
    inscripcion=get_object_or_404(Inscripcion.objects.select_related('curso','cursante'),pk=pk)
    exigir(request.user,inscripcion.curso,'validar')
    instancia=CierreCurso.objects.filter(inscripcion=inscripcion).first() or CierreCurso(inscripcion=inscripcion,responsable=request.user,nombre_certificado=inscripcion.cursante.get_full_name())
    form=CierreForm(request.POST or None,instance=instancia)
    if request.method=='POST' and form.is_valid():
        try:
            with transaction.atomic():
                inscripcion=Inscripcion.objects.select_for_update().get(pk=pk)
                if form.cleaned_data['aprobado']:
                    validar_aprobacion(inscripcion)
                form.instance.responsable=request.user
                objeto=form.save()
                datos=model_to_dict(objeto,exclude=['id','inscripcion','responsable'])
                datos['fecha_acta']=str(datos['fecha_acta']) if datos['fecha_acta'] else None
                MovimientoAcademico.objects.create(cierre=objeto,responsable=request.user,datos=datos)
                certificados=inscripcion.certificados.filter(revocado=False)
                if not objeto.participacion_validada:
                    certificados.update(revocado=True,motivo_revocacion='Dirección retiró la validación de participación.',fecha_revocacion=timezone.now(),revocado_por=request.user)
                elif not objeto.aprobado:
                    certificados.filter(tipo='aprobacion').update(revocado=True,motivo_revocacion='Dirección retiró la aprobación del curso.',fecha_revocacion=timezone.now(),revocado_por=request.user)
                registrar(request,objeto,CHANGE,'Validación académica y referencias de acta guardadas con historial.')
            messages.success(request,'Validación guardada.')
            if request.POST.get('continuar')=='1':
                siguiente=Inscripcion.objects.filter(curso_id=inscripcion.curso_id,activa=True,pk__gt=inscripcion.pk).exclude(cierre__aprobado=True).order_by('pk').first()
                if siguiente:
                    return redirect('aula:cierre_editar',pk=siguiente.pk)
                messages.info(request,'No hay más cursantes pendientes después de esta ficha.')
            return redirect('aula:ficha_cursante',pk=inscripcion.pk)
        except ValidationError as exc:
            form.add_error(None,exc)
    from .tableros import ficha_datos
    datos=ficha_datos(inscripcion.curso,[inscripcion])[0]
    bloqueos=[]
    try:
        validar_aprobacion(inscripcion)
    except ValidationError as exc:
        bloqueos=exc.messages
    return render(request,'aula/gestion/cierre.html',{'curso':inscripcion.curso,'inscripcion':datos,
        'form':form,'acciones':permisos(request.user,inscripcion.curso),'seccion':'cierres','bloqueos':bloqueos})


@login_required
@require_POST
def emitir(request,pk):
    inscripcion=get_object_or_404(Inscripcion.objects.select_related('curso','cursante'),pk=pk)
    exigir(request.user,inscripcion.curso,'emitir')
    tipo=request.POST.get('tipo')
    try:
        with transaction.atomic():
            inscripcion=Inscripcion.objects.select_for_update().get(pk=pk)
            curso=Curso.objects.select_for_update().get(pk=inscripcion.curso_id)
            cierre=CierreCurso.objects.filter(inscripcion=inscripcion).first()
            if tipo not in {'participacion','aprobacion'}:
                raise ValidationError('Elegí el tipo de certificado.')
            if not curso.certificacion_configurada or not curso.fecha_inicio or not curso.fecha_fin or not curso.responsable_certificados:
                raise ValidationError('Primero configurá los certificados del curso.')
            if curso.fecha_fin>timezone.localdate():
                raise ValidationError('La fecha de finalización del curso todavía no llegó.')
            if not cierre or not cierre.participacion_validada or not cierre.nombre_certificado.strip():
                raise ValidationError('Primero validá la participación del cursante.')
            if tipo=='aprobacion':
                validar_aprobacion(inscripcion)
                if not cierre.aprobado or not cierre.requisitos_validados:
                    raise ValidationError('Dirección debe confirmar la aprobación y sus requisitos.')
                if curso.requiere_acta and not all([cierre.libro,cierre.acta,cierre.folio,cierre.fecha_acta]):
                    raise ValidationError('Falta trasladar y verificar este resultado en el libro de actas.')
            anterior=inscripcion.certificados.filter(tipo=tipo,revocado=False).first()
            if anterior:
                messages.info(request,'Ese certificado ya fue emitido. Se conserva el mismo código.')
            else:
                datos={'nombre':cierre.nombre_certificado,'curso':curso.titulo,'referencia':curso.referencia_formacion,
                    'inicio':str(curso.fecha_inicio),'fin':str(curso.fecha_fin),'horas':curso.horas,
                    'autoridad':curso.responsable_certificados,'validado_por':request.user.get_full_name() or request.user.username,
                    'requiere_acta':curso.requiere_acta,'libro':cierre.libro if tipo=='aprobacion' else '',
                    'acta':cierre.acta if tipo=='aprobacion' else '', 'folio':cierre.folio if tipo=='aprobacion' else '',
                    'fecha_acta':str(cierre.fecha_acta) if cierre.fecha_acta and tipo=='aprobacion' else ''}
                from .models import DisenoCertificado
                diseno=DisenoCertificado.objects.filter(curso=curso,tipo=tipo,activo=True).first()
                if diseno:
                    datos['diseno']={'fondo':diseno.fondo.name or '', 'configuracion':diseno.configuracion}
                certificado=Certificado.objects.create(inscripcion=inscripcion,tipo=tipo,datos=datos,responsable=request.user)
                registrar(request,certificado,ADDITION,'Certificado emitido con datos y referencias inmutables.')
                messages.success(request,'Certificado emitido y disponible para el cursante.')
    except ValidationError as exc:
        messages.error(request,' '.join(exc.messages))
    return redirect('aula:ficha_cursante',pk=inscripcion.pk)


@login_required
@require_POST
def revocar(request,pk):
    certificado=get_object_or_404(Certificado,pk=pk)
    exigir(request.user,certificado.inscripcion.curso,'emitir')
    motivo=request.POST.get('motivo','').strip()
    if not motivo or len(motivo)>2000:
        messages.error(request,'Escribí un motivo de revocación de hasta 2000 caracteres.')
    else:
        with transaction.atomic():
            certificado=Certificado.objects.select_for_update().get(pk=pk)
            if not certificado.revocado:
                certificado.revocado=True;certificado.motivo_revocacion=motivo
                certificado.fecha_revocacion=timezone.now();certificado.revocado_por=request.user
                certificado.save()
                registrar(request,certificado,CHANGE,'Certificado revocado; código e historial conservados.')
        messages.success(request,'El certificado fue revocado.')
    return redirect('aula:ficha_cursante',pk=certificado.inscripcion_id)


def generar_pdf(certificado):
    if certificado.datos.get('diseno'):
        from .disenos import dibujar
        return dibujar(certificado)
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4,landscape
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import Paragraph
    from reportlab.lib.colors import HexColor
    buffer=io.BytesIO();w,h=landscape(A4);pdf=canvas.Canvas(buffer,pagesize=(w,h))
    pdf.setTitle('Certificado EDiFoS - '+str(certificado.pk))
    pdf.setFillColor(HexColor('#f7faf4'));pdf.rect(0,0,w,h,fill=1,stroke=0)
    pdf.setStrokeColor(HexColor('#365f46'));pdf.setLineWidth(2);pdf.rect(24,24,w-48,h-48)
    pdf.setFillColor(HexColor('#264c38'));pdf.rect(24,h-112,w-48,88,fill=1,stroke=0)
    pdf.setFillColor(HexColor('#ffffff'));pdf.setFont('Helvetica-Bold',25);pdf.drawString(52,h-67,'EDiFoS SAN LUIS')
    pdf.setFont('Helvetica',11);pdf.drawString(52,h-88,'Escuela Diocesana de Formación Scout - Aula Virtual')
    datos=certificado.datos
    filas=[('CERTIFICADO DE '+certificado.get_tipo_display().upper(),20,True),
        ('EDiFoS San Luis deja constancia de que',12,False),(datos['nombre'],23,True)]
    frase='ha participado y aprobado el curso' if certificado.tipo=='aprobacion' else 'ha participado en el curso'
    filas.extend([(frase,12,False),(datos['curso'],18,True),
        (f"Modalidad virtual · Del {datos['inicio']} al {datos['fin']}"+(f" · {datos['horas']} horas" if datos.get('horas') else ''),11,False)])
    if datos.get('libro'):
        filas.append((f"Registro institucional: libro {datos['libro']} · acta {datos['acta']} · folio {datos['folio']} · {datos['fecha_acta']}",10,False))
    elif certificado.tipo=='participacion':
        filas.append(('Esta constancia de participación no acredita la aprobación de un nivel de formación.',10,False))
    filas.append(('Autoridad responsable: '+datos['autoridad'],11,False))
    # Ajustar todo el cuerpo como una unidad conserva el pie aun con nombres largos.
    from reportlab.platypus import KeepInFrame
    from reportlab.platypus import Spacer
    cuerpo=[]
    for texto,size,bold in filas:
        estilo=ParagraphStyle('cert',fontName='Helvetica-Bold' if bold else 'Helvetica',fontSize=size,
            leading=size*1.35,textColor=HexColor('#264c38'),alignment=1)
        cuerpo.extend([Paragraph(escape(texto),estilo),Spacer(1,9)])
    bloque=KeepInFrame(w-130,h-224,cuerpo,mode='shrink',hAlign='CENTER',vAlign='TOP')
    _,alto=bloque.wrapOn(pdf,w-130,h-224)
    bloque.drawOn(pdf,65,h-132-alto)
    pdf.setFillColor(HexColor('#526958'));pdf.setFont('Helvetica',9)
    pdf.drawString(52,72,'Emitido el '+timezone.localtime(certificado.emitido).strftime('%d/%m/%Y')+' · Registro digital de EDiFoS')
    pdf.drawString(52,56,'Código: '+str(certificado.pk))
    pdf.setFont('Helvetica',8);pdf.drawString(52,41,'Verificación de vigencia: https://edifos.com/aula/constancias/'+str(certificado.pk)+'/')
    pdf.showPage();pdf.save();return buffer.getvalue()


@login_required
def descargar(request,pk):
    certificado=get_object_or_404(Certificado.objects.select_related('inscripcion__curso'),pk=pk,revocado=False)
    if certificado.inscripcion.cursante_id!=request.user.pk and not permisos(request.user,certificado.inscripcion.curso)['emitir']:
        raise PermissionDenied
    respuesta=HttpResponse(generar_pdf(certificado),content_type='application/pdf')
    respuesta['Content-Disposition']=f'inline; filename="certificado-edifos-{certificado.pk}.pdf"'
    respuesta['Cache-Control']='private, no-store'
    return respuesta


def verificar(request,pk):
    certificado=get_object_or_404(Certificado,pk=pk)
    # El enlace impreso confirma vigencia sin publicar identidad ni datos de matrícula.
    respuesta=render(request,'aula/certificado_verificar.html',{'codigo':certificado.pk,'vigente':not certificado.revocado,'tipo':certificado.get_tipo_display(),'fecha':certificado.emitido})
    respuesta['Cache-Control']='no-store';respuesta['X-Robots-Tag']='noindex, nofollow'
    return respuesta


@direccion
def exportar(request,pk):
    curso=get_object_or_404(Curso,pk=pk)
    respuesta=HttpResponse(content_type='text/csv; charset=utf-8')
    respuesta['Content-Disposition']=f'attachment; filename="registro-curso-{pk}.csv"';respuesta['Cache-Control']='private, no-store'
    respuesta.write('\ufeff');writer=csv.writer(respuesta)
    writer.writerow(['Curso','Cursante','Usuario','Participación validada','Aprobación validada','Requiere acta','Estado de asiento','Libro','Acta','Folio','Fecha acta'])
    def seguro(v):
        s=str(v or '')
        return "'"+s if s.lstrip().startswith(('=','+','-','@')) or s.startswith(('\t','\r','\n')) else s
    for inscripcion in curso.inscripciones.select_related('cursante'):
        c=CierreCurso.objects.filter(inscripcion=inscripcion).first()
        estado='No aplica' if not curso.requiere_acta else ('Asentado' if c and c.aprobado and c.fecha_acta else 'Pendiente')
        writer.writerow([seguro(v) for v in [curso.titulo,c.nombre_certificado if c else inscripcion.cursante.get_full_name(),inscripcion.cursante.username,
            'Sí' if c and c.participacion_validada else 'No','Sí' if c and c.aprobado else 'No','Sí' if curso.requiere_acta else 'No',estado,
            c.libro if c else '',c.acta if c else '',c.folio if c else '',c.fecha_acta if c else '']])
    return respuesta
