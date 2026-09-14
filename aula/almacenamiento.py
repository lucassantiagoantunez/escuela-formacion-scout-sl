from pathlib import Path
from uuid import uuid4
from django.conf import settings
from django.core.files.storage import FileSystemStorage


class AlmacenamientoPrivado(FileSystemStorage):
    @property
    def base_location(self):
        return str(settings.AULA_PRIVATE_ROOT)

    @property
    def location(self):
        return str(Path(settings.AULA_PRIVATE_ROOT).resolve())

    def url(self, name):
        raise ValueError('Los recursos del Aula requieren una descarga autorizada.')


def privado():
    return AlmacenamientoPrivado()


def ruta_archivo(instance, filename):
    return f'{instance.leccion_id}/{uuid4().hex}{Path(filename).suffix.lower()}'
