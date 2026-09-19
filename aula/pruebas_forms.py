from django import forms
import json
from .models import Prueba, ItemPrueba, Modulo, RecursoLeccion, TIPOS_PRUEBA
from .pruebas_motor import FUENTES


class PruebaForm(forms.Form):
    modulo = forms.ModelChoiceField(queryset=Modulo.objects.none(), label='Módulo donde aparecerá')
    titulo = forms.CharField(max_length=200, label='Nombre de la prueba')
    fuente = forms.ChoiceField(required=False, label='Copiar un juego existente', help_text='Se crea una copia privada para este curso. El juego público y sus resultados no se modifican.')
    tipo = forms.ChoiceField(choices=TIPOS_PRUEBA, label='Tipo de prueba nueva', help_text='Si elegiste un juego, se usará su tipo.')
    instrucciones = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows':3}), label='Instrucciones para el cursante')
    minimo = forms.IntegerField(min_value=1,max_value=100,initial=70,label='Porcentaje para aprobar')
    max_intentos = forms.IntegerField(min_value=1,max_value=20,initial=3,label='Intentos permitidos')
    obligatoria = forms.BooleanField(required=False,initial=True,label='Es obligatoria para aprobar el curso')
    imagen_archivo = forms.ImageField(required=False,label='Cargar imagen para el rompecabezas',help_text='Elegí una imagen JPG o PNG. Se guarda de forma privada en esta prueba.')
    imagen = forms.ModelChoiceField(queryset=RecursoLeccion.objects.none(), required=False, label='O reutilizar una imagen del curso', help_text='Si cargás una imagen nueva, se usará esa. La imagen elegida se copia a la prueba.')

    def __init__(self,*args,curso,**kwargs):
        super().__init__(*args,**kwargs)
        self.fields['modulo'].queryset=curso.modulos.all()
        self.fields['fuente'].choices=[('', 'Crear una prueba nueva, solo de este curso')] + [
            (tipo, [(f'{tipo}:{j.pk}', j.titulo) for j in modelo.objects.all()]) for tipo,modelo in FUENTES.items()]
        self.fields['imagen'].queryset=RecursoLeccion.objects.filter(leccion__modulo__curso=curso,tipo='imagen',activo=True)

    def clean(self):
        d=super().clean()
        if not d.get('fuente') and d.get('tipo')=='rompecabezas' and not (d.get('imagen') or d.get('imagen_archivo')):
            self.add_error('imagen_archivo','Cargá o elegí la imagen del rompecabezas.')
        return d


class ItemForm(forms.ModelForm):
    opciones_texto=forms.CharField(required=False,label='Opciones',widget=forms.Textarea(attrs={'rows':5}),help_text='Una opción por renglón.')
    class Meta:
        model=ItemPrueba
        fields=['texto','opciones_texto','respuesta','explicacion','activo']
        labels={'texto':'Pregunta o consigna','respuesta':'Respuesta correcta','explicacion':'Explicación al terminar (opcional)','activo':'Incluir esta actividad en la prueba'}
        help_texts={'explicacion':'Se muestra después de entregar. Podés indicar qué clase repasar.'}
        widgets={'texto':forms.Textarea(attrs={'rows':3}), 'respuesta':forms.TextInput(), 'explicacion':forms.Textarea(attrs={'rows':3})}

    def __init__(self,*args,prueba,**kwargs):
        self.prueba=prueba
        super().__init__(*args,**kwargs)
        if prueba.tipo not in {'trivia', 'memoria', 'ordenar', 'palabra'}:
            self.fields.pop('explicacion')
        self.initial['opciones_texto']='\n'.join(self.instance.opciones or [])
        if prueba.tipo == 'trivia':
            self.fields['respuesta']=forms.TypedChoiceField(coerce=str,choices=[(str(i),f'Opción {i}') for i in range(1,9)],label='Opción correcta')
        elif prueba.tipo=='camino':
            self.fields['texto'].label='Situación de esta escena'
            self.fields['opciones_texto'].label='Decisiones disponibles'
            self.fields.pop('respuesta')
            choices=[('siguiente','Escena siguiente'),('final_bueno','Final favorable (100%)'),('final_neutro','Final intermedio (50%)'),('final_malo','Final desfavorable (0%)')]+[(str(i.pk),i.texto[:80]) for i in prueba.items.filter(activo=True)]
            try:
                destinos=json.loads(self.instance.respuesta)['destinos']
            except (ValueError,KeyError,TypeError):
                destinos=[]
            for n in range(1,9):
                self.fields[f'destino_{n}']=forms.ChoiceField(choices=choices,required=False,label=f'Destino de la decisión {n}',initial=destinos[n-1] if len(destinos)>=n else 'final_neutro')
        elif prueba.tipo=='ordenar':
            self.fields['opciones_texto'].label='Pasos en el orden correcto'
            self.fields['opciones_texto'].help_text='Escribí un paso por renglón. El cursante los verá mezclados.'
            self.fields.pop('respuesta')
        else:
            self.fields.pop('opciones_texto')
            if prueba.tipo=='memoria':
                self.fields['texto'].label='Concepto'
                self.fields['respuesta'].label='Concepto que forma la pareja'
            elif prueba.tipo=='palabra':
                self.fields['texto'].label='Pista'
                self.fields['respuesta'].label='Palabra que debe descubrir'
            elif prueba.tipo=='ruleta':
                self.fields['texto'].label='Reto que puede salir en la ruleta'
                self.fields.pop('respuesta')

    def clean(self):
        d=super().clean()
        opciones=[s.strip() for s in d.get('opciones_texto','').splitlines() if s.strip()]
        if self.prueba.tipo in {'trivia','camino','ordenar'}:
            limite=20 if self.prueba.tipo=='ordenar' else 8
            minimo=1 if self.prueba.tipo=='camino' else 2
            if not minimo<=len(opciones)<=limite or any(len(o)>1000 for o in opciones):
                self.add_error('opciones_texto',f'Escribí entre {minimo} y {limite} opciones, de hasta 1000 caracteres cada una.')
            if self.prueba.tipo == 'trivia' and d.get('respuesta') and int(d['respuesta'])>len(opciones):
                self.add_error('respuesta','La opción correcta debe existir en la lista.')
            if self.prueba.tipo=='camino':
                self.instance.respuesta=json.dumps({'destinos':[d.get(f'destino_{n+1}') or 'final_neutro' for n in range(len(opciones))]})
        if self.prueba.tipo in {'palabra','memoria'} and not d.get('respuesta','').strip():
            self.add_error('respuesta','Escribí la respuesta correcta.')
        self.instance.opciones=opciones
        return d


class CorreccionForm(forms.Form):
    puntaje=forms.IntegerField(min_value=0,max_value=100,label='Resultado (0 a 100)')
    devolucion=forms.CharField(max_length=6000,widget=forms.Textarea(attrs={'rows':4}),label='Devolución para el cursante')


class ReglasForm(forms.ModelForm):
    minimo=forms.IntegerField(min_value=1,max_value=100,label='Porcentaje para aprobar')
    max_intentos=forms.IntegerField(min_value=1,max_value=20,label='Intentos permitidos por versión')
    class Meta:
        model=Prueba
        fields=['instrucciones','minimo','max_intentos','obligatoria']
        labels={'instrucciones':'Instrucciones','obligatoria':'Obligatoria para aprobar el curso'}
        widgets={'instrucciones':forms.Textarea(attrs={'rows':3})}
