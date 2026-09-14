import copy
import io
import json
import math
import re
from pathlib import Path
from xml.sax.saxutils import escape
from django import forms
from django.contrib import messages
from django.contrib.admin.models import CHANGE
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import HttpResponse,FileResponse,Http404
from django.shortcuts import get_object_or_404,render,redirect
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods,require_GET
from pypdf import PdfReader,PdfWriter,Transformation
from .almacenamiento import privado
from .models import Curso,DisenoCertificado,Certificado
from .permisos import exigir
from .gestion import registrar

CAMPOS=[('encabezado','Encabezado',8,8,24),('tipo','Tipo de certificado',18,9,21),
    ('libre','Texto libre',25,5,12),('nombre','Nombre del cursante',32,11,28),
    ('curso','Nombre del curso',46,11,22),('periodo','Fechas y carga horaria',59,6,12),
    ('autoridad','Autoridad responsable',68,7,13),('registro','Referencia de acta / aclaración',77,6,10)]

def inicial():
    return {'encabezado':'EDiFoS SAN LUIS','libre':'Se otorga la presente constancia a',
        'color':'#264c38','fuente':'Helvetica','campos':{k:{'x':10,'y':y,'ancho':80,'alto':h,'tamano':f} for k,_,y,h,f in CAMPOS}}

class DisenoForm(forms.Form):
    activo=forms.BooleanField(required=False,initial=True,label='Usar este diseño para los próximos certificados')
    fondo=forms.FileField(required=False,label='Subir plantilla de fondo (PDF, PNG o JPG)',help_text='Una página, hasta 10 MB. Usá una plantilla apaisada. Si incluye firmas abajo, elegí la verificación en una segunda página.')
    quitar_fondo=forms.BooleanField(required=False,label='Quitar el fondo actual')
    encabezado=forms.CharField(required=False,max_length=200,label='Texto del encabezado')
    libre=forms.CharField(required=False,max_length=300,label='Texto libre')
    color=forms.RegexField(regex=r'^#[0-9a-fA-F]{6}$',widget=forms.TextInput(attrs={'type':'color'}),label='Color del texto')
    fuente=forms.ChoiceField(choices=[('Helvetica','Moderna'),('Times-Roman','Clásica'),('Courier','Máquina de escribir')],label='Letra')
    pie=forms.ChoiceField(required=False,choices=[('franja','En la franja inferior (diseño anterior)'),('pagina','En una segunda página, sin tapar la plantilla')],label='Código y datos de verificación')
    extras=forms.CharField(required=False,widget=forms.HiddenInput(),max_length=40000)

    def __init__(self,*args,diseno,**kwargs):
        cfg=copy.deepcopy(diseno.configuracion or inicial())
        datos={k:cfg[k] for k in ['encabezado','libre','color','fuente']}
        datos['activo']=diseno.activo
        datos['pie']=cfg.get('pie','franja')
        datos['extras']=json.dumps(cfg.get('extras',[]))
        for key,_,_,_,_ in CAMPOS:
            for nombre,valor in cfg['campos'][key].items():datos[f'{key}_{nombre}']=valor
            datos.setdefault(f'{key}_visible',True)
            datos.setdefault(f'{key}_alineacion','centro')
            datos.setdefault(f'{key}_color',cfg['color'])
            datos.setdefault(f'{key}_negrita',False)
        super().__init__(*args,initial=datos,**kwargs)
        for key,_,_,_,_ in CAMPOS:
            self.fields[f'{key}_visible']=forms.BooleanField(required=False,label='Mostrar este campo')
            self.fields[f'{key}_alineacion']=forms.ChoiceField(required=False,choices=[('centro','Centrado'),('izquierda','Izquierda'),('derecha','Derecha')],label='Alineación')
            self.fields[f'{key}_color']=forms.RegexField(required=False,regex=r'^#[0-9a-fA-F]{6}$',widget=forms.TextInput(attrs={'type':'color'}),label='Color de este campo')
            self.fields[f'{key}_negrita']=forms.BooleanField(required=False,label='Negrita')
            for nombre,label,minimo,maximo in [('x','Desde la izquierda (%)',0,99),('y','Desde arriba (%)',0,99),
                    ('ancho','Ancho (%)',1,100),('alto','Alto (%)',1,100),('tamano','Tamaño de letra',6,96)]:
                self.fields[f'{key}_{nombre}']=forms.FloatField(min_value=minimo,max_value=maximo,label=label,
                    widget=forms.NumberInput(attrs={'step':'0.1','data-campo':key,'data-propiedad':nombre}))

    def clean_fondo(self):
        archivo=self.cleaned_data.get('fondo')
        if not archivo:return archivo
        if archivo.size>10*1024*1024:raise ValidationError('La plantilla admite hasta 10 MB.')
        ext=Path(archivo.name).suffix.lower()
        try:
            if ext=='.pdf':
                lector=PdfReader(archivo)
                if lector.is_encrypted or len(lector.pages)!=1:raise ValueError
                page=lector.pages[0]
                if not 100<=float(page.mediabox.width)<=3000 or not 100<=float(page.mediabox.height)<=3000:raise ValueError
            elif ext in {'.png','.jpg','.jpeg'}:
                from PIL import Image
                imagen=Image.open(archivo)
                if imagen.width*imagen.height>25_000_000 or imagen.format not in {'PNG','JPEG'}:raise ValueError
                imagen.verify()
            else:raise ValueError
        except Exception as exc:
            raise ValidationError('Usá un PDF de una página sin contraseña o una imagen JPG/PNG válida (hasta 25 megapíxeles).') from exc
        finally:archivo.seek(0)
        return archivo

    def clean(self):
        datos=super().clean()
        limite=100 if datos.get('pie')=='pagina' else 86
        for key,_,_,_,_ in CAMPOS:
            x,y,w,h=[datos.get(f'{key}_{n}') for n in ['x','y','ancho','alto']]
            if None not in [x,y,w,h] and (not all(math.isfinite(n) for n in [x,y,w,h]) or x+w>100.01 or y+h>limite+.01):
                self.add_error(f'{key}_y',f'El campo debe entrar en la hoja (hasta el {limite}% de alto).')
        return datos

    def clean_extras(self):
        try:
            datos=json.loads(self.cleaned_data.get('extras') or '[]')
            if not isinstance(datos,list) or len(datos)>20:raise ValueError
            resultado=[]
            for caja in datos:
                if not isinstance(caja,dict):raise ValueError
                item={}
                texto=caja.get('texto','')
                if not isinstance(texto,str) or len(texto)>1500:raise ValueError
                item['texto']=texto
                for k,low,high in [('x',0,99),('y',0,99),('ancho',1,100),('alto',1,100),('tamano',6,96)]:
                    v=float(caja[k])
                    if not math.isfinite(v) or not low<=v<=high:raise ValueError
                    item[k]=v
                limite=100 if self.cleaned_data.get('pie')=='pagina' else 86
                if item['x']+item['ancho']>100.01 or item['y']+item['alto']>limite+.01:raise ValueError
                item['color']=caja.get('color','#264c38')
                if not isinstance(item['color'],str) or not re.fullmatch(r'#[0-9a-fA-F]{6}',item['color']):raise ValueError
                item['alineacion']=caja.get('alineacion','centro')
                if item['alineacion'] not in {'izquierda','centro','derecha'}:raise ValueError
                item['negrita']=caja.get('negrita') is True
                item['visible']=caja.get('visible',True) is True
                resultado.append(item)
            return resultado
        except (ValueError,TypeError,KeyError,OverflowError):
            raise ValidationError('Revisá los textos propios: hasta 20, de 1500 caracteres, con posiciones dentro de la hoja.')

    def configuracion(self):
        d=self.cleaned_data
        return {**{k:d[k] for k in ['encabezado','libre','color','fuente']},'pie':d.get('pie') or 'franja','extras':d['extras'],
            'campos':{k:{n:d[f'{k}_{n}'] for n in ['x','y','ancho','alto','tamano','visible','alineacion','color','negrita']} for k,_,_,_,_ in CAMPOS}}

def valores(certificado,config):
    d=certificado.datos
    registro=(f"Libro {d['libro']} · Acta {d['acta']} · Folio {d['folio']} · {d['fecha_acta']}" if d.get('libro') else
        ('La participación no acredita la aprobación de un nivel.' if certificado.tipo=='participacion' else 'Aprobación validada por el equipo autorizado de EDiFoS.'))
    return {'encabezado':config['encabezado'],'libre':config['libre'],'nombre':d['nombre'],'curso':d['curso'],
        'tipo':'CERTIFICADO DE '+certificado.get_tipo_display().upper(),
        'periodo':f"Modalidad virtual · {d['inicio']} al {d['fin']}"+(f" · {d['horas']} horas" if d.get('horas') else ''),
        'autoridad':d['autoridad'],'registro':registro}

def ejemplo(curso,tipo,diseno):
    cert=Certificado(tipo=tipo,datos={'nombre':'NOMBRE DE EJEMPLO — SIN VALIDEZ','curso':curso.titulo,
        'inicio':str(curso.fecha_inicio or 'Fecha inicial'),'fin':str(curso.fecha_fin or 'Fecha final'),
        'horas':curso.horas,'autoridad':curso.responsable_certificados or 'Autoridad responsable',
        'libro':'Libro de ejemplo' if curso.requiere_acta else '', 'acta':'00','folio':'00','fecha_acta':'Fecha de asiento',
        'diseno':{'fondo':diseno.fondo.name or '', 'configuracion':diseno.configuracion or inicial()}},emitido=timezone.now())
    return cert

@login_required
@require_http_methods(['GET','POST'])
def editar(request,pk,tipo):
    curso=get_object_or_404(Curso,pk=pk);exigir(request.user,curso,'disenar')
    if tipo not in {'participacion','aprobacion'}:raise Http404
    diseno=DisenoCertificado.objects.filter(curso=curso,tipo=tipo).first() or DisenoCertificado(curso=curso,tipo=tipo)
    form=DisenoForm(request.POST if request.method=='POST' else None,request.FILES or None,diseno=diseno)
    if request.method=='POST' and form.is_valid():
        nuevo=None
        try:
            with transaction.atomic():
                Curso.objects.select_for_update().get(pk=pk);exigir(request.user,curso,'disenar')
                actual=DisenoCertificado.objects.filter(curso=curso,tipo=tipo).first()
                if actual:diseno=actual
                if form.cleaned_data['quitar_fondo']:diseno.fondo=''
                if form.cleaned_data['fondo']:
                    diseno.fondo.save(form.cleaned_data['fondo'].name,form.cleaned_data['fondo'],save=False)
                    nuevo=diseno.fondo.name
                diseno.activo=form.cleaned_data['activo'];diseno.configuracion=form.configuracion()
                # Validar el PDF antes de aceptar una plantilla que no pueda emitirse.
                dibujar(ejemplo(curso,tipo,diseno),muestra=True)
                diseno.save();registrar(request,diseno,CHANGE,'Diseño de certificado actualizado; diseños emitidos conservados.')
        except Exception as exc:
            if nuevo:privado().delete(nuevo)
            if not isinstance(exc,(ValueError,OSError,ValidationError)):raise
            form.add_error(None,'No pudimos preparar esa plantilla. Revisá el archivo y volvé a intentar.')
        else:
            messages.success(request,'Diseño guardado. Los certificados ya emitidos conservan su plantilla anterior.')
            return redirect('aula:diseno_certificado',pk=pk,tipo=tipo)
    config=diseno.configuracion or inicial();cert=ejemplo(curso,tipo,diseno)
    campos=[{'key':k,'label':label,'visible':form[f'{k}_visible'],'fields':[form[f'{k}_{n}'] for n in ['x','y','ancho','alto','tamano','alineacion','color','negrita']],
        'texto':valores(cert,config)[k]} for k,label,_,_,_ in CAMPOS]
    return render(request,'aula/gestion/diseno.html',{'curso':curso,'tipo':tipo,'form':form,'diseno':diseno,'campos':campos,
        'pdf_fondo':Path(diseno.fondo.name or '').suffix.lower()=='.pdf','config':config})

@login_required
@require_GET
def fondo(request,pk,tipo):
    curso=get_object_or_404(Curso,pk=pk);exigir(request.user,curso,'disenar')
    diseno=get_object_or_404(DisenoCertificado,curso=curso,tipo=tipo)
    if not diseno.fondo:raise Http404
    ext=Path(diseno.fondo.name).suffix.lower()
    response=FileResponse(diseno.fondo.open('rb'),content_type={'.pdf':'application/pdf','.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg'}[ext])
    response['Cache-Control']='private, no-store';response['X-Content-Type-Options']='nosniff'
    return response

@login_required
@require_GET
def vista_previa(request,pk,tipo):
    curso=get_object_or_404(Curso,pk=pk);exigir(request.user,curso,'disenar')
    diseno=get_object_or_404(DisenoCertificado,curso=curso,tipo=tipo)
    response=HttpResponse(dibujar(ejemplo(curso,tipo,diseno),muestra=True),content_type='application/pdf')
    response['Cache-Control']='private, no-store';response['Content-Disposition']='inline; filename="ejemplo-sin-validez.pdf"'
    return response

def dibujar(certificado,muestra=False):
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4,landscape
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.colors import HexColor
    from reportlab.platypus import Paragraph,KeepInFrame
    from reportlab.lib.utils import ImageReader
    diseno=certificado.datos['diseno'];cfg=diseno['configuracion'];w,h=landscape(A4)
    salida=io.BytesIO();pdf=canvas.Canvas(salida,pagesize=(w,h));pdf.setTitle('Certificado EDiFoS')
    nombre=diseno.get('fondo','');base=None
    if nombre:
        with privado().open(nombre,'rb') as src:
            data=src.read()
        if nombre.lower().endswith('.pdf'):
            base=PdfReader(io.BytesIO(data)).pages[0]
            base.transfer_rotation_to_content()
        else:
            pdf.drawImage(ImageReader(io.BytesIO(data)),0,0,w,h,preserveAspectRatio=True,anchor='c')
    cajas=[(texto,cfg['campos'][campo]) for campo,texto in valores(certificado,cfg).items()]
    cajas.extend((caja['texto'],caja) for caja in cfg.get('extras',[]))
    for texto,caja in cajas:
        if not caja.get('visible',True) or not texto:continue
        ancho=w*caja['ancho']/100;alto=h*caja['alto']/100
        fuente=cfg['fuente']
        if caja.get('negrita'):fuente={'Helvetica':'Helvetica-Bold','Times-Roman':'Times-Bold','Courier':'Courier-Bold'}[fuente]
        estilo=ParagraphStyle('campo',fontName=fuente,fontSize=caja['tamano'],leading=caja['tamano']*1.2,
            alignment={'izquierda':0,'centro':1,'derecha':2}.get(caja.get('alineacion'),1),textColor=HexColor(caja.get('color') or cfg['color']))
        bloque=KeepInFrame(ancho,alto,[Paragraph(escape(texto).replace('\n','<br/>'),estilo)],mode='shrink',hAlign='CENTER',vAlign='TOP')
        _,usado=bloque.wrapOn(pdf,ancho,alto)
        bloque.drawOn(pdf,w*caja['x']/100,h*(1-caja['y']/100)-usado)
    # La segunda página conserva trazabilidad sin pintar sobre firmas o bordes del diploma.
    if cfg.get('pie')=='pagina':
        pdf.showPage()
        pdf.setFillColor(HexColor('#264c38'));pdf.setFont('Helvetica-Bold',20)
        pdf.drawString(40,h-55,'Datos de verificación · EDiFoS')
        info=valores(certificado,cfg)
        estilo=ParagraphStyle('verificacion',fontName='Helvetica',fontSize=12,leading=18)
        contenido=[Paragraph(escape(info[k]),estilo) for k in ['tipo','nombre','curso','periodo','autoridad','registro']]
        bloque=KeepInFrame(w-80,h-180,contenido,mode='shrink');_,usado=bloque.wrapOn(pdf,w-80,h-180)
        bloque.drawOn(pdf,40,h-95-usado)
    pdf.setFillColor(HexColor('#ffffff'));pdf.rect(0,0,w,h*.13,fill=1,stroke=0)
    pdf.setFillColor(HexColor('#264c38'));pdf.setFont('Helvetica',9)
    pdf.drawString(35,52,'EJEMPLO SIN VALIDEZ' if muestra else 'Emitido el '+timezone.localtime(certificado.emitido).strftime('%d/%m/%Y'))
    pdf.drawString(35,36,'Código: '+str(certificado.pk))
    pdf.setFont('Helvetica',8)
    pdf.drawString(35,22,('Vista previa; no se emitió ningún certificado.' if muestra else 'Verificación de vigencia: https://edifos.com/aula/constancias/'+str(certificado.pk)+'/'))
    pdf.showPage();pdf.save()
    if base:
        writer=PdfWriter();page=writer.add_blank_page(w,h)
        ancho=float(base.mediabox.width);alto=float(base.mediabox.height);escala=min(w/ancho,h/alto)
        for key in ['/Annots','/AA']:base.pop(key,None)
        trans=Transformation().translate(-float(base.mediabox.left),-float(base.mediabox.bottom)).scale(escala).translate((w-ancho*escala)/2,(h-alto*escala)/2)
        page.merge_transformed_page(base,trans)
        rendered=PdfReader(io.BytesIO(salida.getvalue()))
        page.merge_page(rendered.pages[0])
        for extra in rendered.pages[1:]:writer.add_page(extra)
        out=io.BytesIO();writer.write(out);return out.getvalue()
    return salida.getvalue()
