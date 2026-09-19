from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('aula', '0008_perfil_avatar_perfil_compartir_foto')]
    operations = [migrations.AddField(model_name='itemprueba', name='explicacion',
                                     field=models.TextField(blank=True))]
