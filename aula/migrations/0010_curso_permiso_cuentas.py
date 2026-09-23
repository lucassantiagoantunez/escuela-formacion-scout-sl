from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [('aula', '0009_itemprueba_explicacion')]
    operations = [migrations.AlterModelOptions(
        name='curso',
        options={'permissions': [('gestionar_cuentas', 'Crear, activar y desactivar cuentas del aula')]},
    )]
