from django.contrib import admin
from .models import Curso, Inscripcion, Modulo, Leccion, Progreso, PermisoFormador, Perfil


class DireccionAdmin(admin.ModelAdmin):
    # Hasta disponer de edición por curso, solo Dirección administra el Aula.
    def has_module_permission(self, request):
        return request.user.is_active and request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return self.has_module_permission(request)

    has_add_permission = has_view_permission
    has_change_permission = has_view_permission
    has_delete_permission = has_view_permission


@admin.register(Curso)
class CursoAdmin(DireccionAdmin):
    list_display = ['titulo', 'publicado']
    filter_horizontal = ['formadores']


@admin.register(Inscripcion)
class InscripcionAdmin(DireccionAdmin):
    list_display = ['cursante', 'curso', 'tutor', 'activa', 'fecha']
    list_filter = ['curso', 'activa']
    readonly_fields = ['fecha']


@admin.register(Modulo)
class ModuloAdmin(DireccionAdmin):
    list_display = ['titulo', 'curso', 'orden']
    list_filter = ['curso']


@admin.register(Leccion)
class LeccionAdmin(DireccionAdmin):
    list_display = ['titulo', 'modulo', 'publicada', 'obligatoria', 'orden']
    list_filter = ['modulo__curso', 'publicada']


@admin.register(Progreso)
class ProgresoAdmin(DireccionAdmin):
    list_display = ['cursante', 'leccion', 'completada_en']
    readonly_fields = ['cursante', 'leccion', 'completada_en']

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PermisoFormador)
class PermisoFormadorAdmin(DireccionAdmin):
    list_display=['formador','curso','responder_foro','moderar_foro','corregir','validar','emitir','disenar']
    list_filter=['curso','emitir','validar']
    fields=['curso','formador','responder_foro','moderar_foro','ver_seguimiento','corregir','validar','emitir','disenar']


@admin.register(Perfil)
class PerfilAdmin(DireccionAdmin):
    list_display = ['usuario', 'grupo', 'actualizado']
    search_fields = ['usuario__first_name', 'usuario__last_name', 'usuario__username', 'grupo']
    readonly_fields = [f.name for f in Perfil._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
