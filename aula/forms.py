from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from .models import Curso, Leccion, Modulo
from django_ckeditor_5.widgets import CKEditor5Widget
from django.utils.html import linebreaks
from .contenido import limpiar_html, youtube_embed
from .archivos import validar_archivo


class VariosArchivosInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class VariosArchivosField(forms.FileField):
    widget = VariosArchivosInput

    def clean(self, data, initial=None):
        archivos = data if isinstance(data, (list, tuple)) else ([data] if data else [])
        if len(archivos) > 5:
            raise forms.ValidationError('Elegí hasta 5 archivos por vez.')
        resultado = []
        for archivo in archivos:
            archivo = super().clean(archivo, initial)
            validar_archivo(archivo)
            resultado.append(archivo)
        return resultado


class CursoForm(forms.ModelForm):
    class Meta:
        model = Curso
        fields = ['titulo', 'descripcion', 'publicado']
        labels = {'titulo': 'Nombre del curso', 'descripcion': 'Presentación', 'publicado': 'Habilitar el acceso a los cursantes inscriptos'}
        help_texts = {'publicado': 'Podés dejarlo sin marcar mientras preparás el contenido.'}
        widgets = {'descripcion': forms.Textarea(attrs={'rows': 4})}


class ModuloForm(forms.ModelForm):
    class Meta:
        model = Modulo
        fields = ['titulo']
        labels = {'titulo': 'Nombre del módulo'}


class LeccionForm(forms.ModelForm):
    archivos = VariosArchivosField(label='Documentos, videos e imágenes', required=False,
        help_text='PDF, Word, PowerPoint, JPG y PNG: hasta 20 MB por archivo. Videos MP4 o WebM: hasta 150 MB. Hasta 5 archivos por guardado, incluyendo un Word o PowerPoint por vez. Los documentos se muestran dentro de la clase; PowerPoint se convierte en diapositivas sin animaciones.',
        widget=VariosArchivosInput(attrs={'accept': '.pdf,.doc,.docx,.ppt,.pptx,.mp4,.webm,.png,.jpg,.jpeg'}))
    class Meta:
        model = Leccion
        fields = ['modulo', 'titulo', 'texto', 'video_url', 'obligatoria', 'publicada']
        labels = {'modulo': 'Módulo', 'titulo': 'Título de la clase', 'texto': 'Contenido de la clase',
                  'video_url': 'Enlace al video (opcional)', 'obligatoria': 'Contar esta clase en el avance de lectura',
                  'publicada': 'Mostrar esta clase a los cursantes'}
        help_texts = {'publicada': 'Sin marcar: se guarda como borrador, visible solo para el equipo.'}
        widgets = {'texto': CKEditor5Widget(config_name='aula')}

    def __init__(self, *args, curso, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['modulo'].queryset = curso.modulos.all()
        if self.instance.pk and not self.instance.texto_enriquecido:
            self.initial['texto'] = linebreaks(self.instance.texto, autoescape=True)
        self.fields['video_url'].label = 'Video de YouTube (opcional)'
        self.fields['video_url'].help_text = 'Pegá el enlace de YouTube. Se reproducirá dentro de la clase; el autor del video debe permitir insertarlo.'
        self.order_fields(['modulo', 'titulo', 'texto', 'video_url', 'archivos', 'obligatoria', 'publicada'])

    def clean_texto(self):
        return limpiar_html(self.cleaned_data['texto'])

    def clean_video_url(self):
        url = self.cleaned_data['video_url']
        if url and not url.startswith('https://'):
            raise forms.ValidationError('Pegá un enlace que comience con https://.')
        if url and not youtube_embed(url) and url != self.instance.video_url:
            raise forms.ValidationError('Pegá el enlace de un video de YouTube. Para un video propio, usá el campo de archivos.')
        return url


ROLES = [('cursante', 'Cursante — participa del curso'), ('formador', 'Formador — consulta el contenido del curso')]


class PersonaForm(UserCreationForm):
    dias_cortesia = forms.IntegerField(label='Días de acceso desde el primer ingreso', initial=30, required=False, min_value=1, max_value=3650, help_text='Dejá vacío para no fijar vencimiento. Podés cambiarlo después en Usuarios y accesos.')
    first_name = forms.CharField(label='Nombre', max_length=150)
    last_name = forms.CharField(label='Apellido', max_length=150)
    email = forms.EmailField(label='Correo electrónico (opcional)', required=False)
    rol = forms.ChoiceField(label='Participa como', choices=ROLES, widget=forms.RadioSelect)

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ['first_name', 'last_name', 'email', 'username']
        labels = {'username': 'Nombre de usuario para ingresar'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].label = 'Contraseña de acceso'
        self.fields['password2'].label = 'Repetir contraseña'
        self.fields['password1'].help_text = 'Usá al menos 8 caracteres. Evitá contraseñas comunes, solo números o datos parecidos al nombre de la persona.'
        self.fields['password2'].help_text = 'Escribí otra vez la misma contraseña.'
        self.fields['username'].widget.attrs.pop('autofocus', None)
        self.fields['username'].help_text = 'Por ejemplo: maria.perez. La persona usará este nombre para entrar al Aula.'
        self.order_fields(['first_name', 'last_name', 'email', 'username', 'password1', 'password2', 'rol', 'dias_cortesia'])


class PersonaChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f'{obj.get_full_name() or obj.username} ({obj.username})'


class InscribirForm(forms.Form):
    persona = PersonaChoiceField(queryset=get_user_model().objects.none(), label='Persona con cuenta existente', empty_label='Elegí una persona')
    rol = forms.ChoiceField(label='Participa como', choices=ROLES, widget=forms.RadioSelect)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['persona'].queryset = get_user_model().objects.filter(is_active=True).order_by('first_name', 'last_name', 'username')
