from django.db import migrations


def preparar_grupo(apps, schema_editor):
    alias = schema_editor.connection.alias
    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')
    ContentType = apps.get_model('contenttypes', 'ContentType')
    grupo, _ = Group.objects.using(alias).get_or_create(name='Comunicación · Noticias y biblioteca')
    permisos = []
    for modelo in ('noticia', 'material', 'categoriabiblioteca'):
        ct, _ = ContentType.objects.using(alias).get_or_create(app_label='core', model=modelo)
        for accion in ('view', 'add', 'change'):
            p, _ = Permission.objects.using(alias).get_or_create(content_type=ct, codename=f'{accion}_{modelo}', defaults={'name': f'Can {accion} {modelo}'})
            permisos.append(p)
    grupo.permissions.set(permisos)
    # No accounts are assigned or promoted by deployment.


class Migration(migrations.Migration):
    dependencies = [('core', '0033_caminos_mas_completos'), ('auth', '0012_alter_user_first_name_max_length')]
    operations = [migrations.RunPython(preparar_grupo, migrations.RunPython.noop)]
