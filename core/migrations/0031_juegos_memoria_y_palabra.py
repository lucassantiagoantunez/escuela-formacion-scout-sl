from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0030_pregunta_imagen"),
    ]

    operations = [
        migrations.CreateModel(
            name="JuegoMemoria",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("titulo", models.CharField(max_length=200)),
                ("descripcion", models.TextField(blank=True)),
                ("activo", models.BooleanField(default=True)),
                ("fecha_creacion", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "Juego de memoria",
                "verbose_name_plural": "Juegos de memoria",
                "ordering": ["titulo"],
            },
        ),
        migrations.CreateModel(
            name="JuegoPalabraSecreta",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("titulo", models.CharField(max_length=200)),
                ("descripcion", models.TextField(blank=True)),
                ("activo", models.BooleanField(default=True)),
                ("fecha_creacion", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "Juego de palabra secreta",
                "verbose_name_plural": "Juegos de palabra secreta",
                "ordering": ["titulo"],
            },
        ),
        migrations.CreateModel(
            name="ParejaMemoria",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("concepto", models.CharField(max_length=120)),
                ("relacion", models.CharField(max_length=180)),
                ("explicacion", models.TextField(blank=True)),
                ("orden", models.PositiveIntegerField(default=1)),
                ("juego", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="parejas", to="core.juegomemoria")),
            ],
            options={
                "verbose_name": "Pareja de memoria",
                "verbose_name_plural": "Parejas de memoria",
                "ordering": ["orden", "id"],
            },
        ),
        migrations.CreateModel(
            name="PalabraJuego",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("palabra", models.CharField(max_length=40)),
                ("pista", models.CharField(max_length=240)),
                ("explicacion", models.TextField(blank=True)),
                ("orden", models.PositiveIntegerField(default=1)),
                ("juego", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="palabras", to="core.juegopalabrasecreta")),
            ],
            options={
                "verbose_name": "Palabra del juego",
                "verbose_name_plural": "Palabras del juego",
                "ordering": ["orden", "id"],
            },
        ),
        migrations.CreateModel(
            name="ResultadoMemoria",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nombre", models.CharField(max_length=100)),
                ("movimientos", models.PositiveIntegerField()),
                ("tiempo_total_segundos", models.PositiveIntegerField(default=0)),
                ("fecha", models.DateTimeField(auto_now_add=True)),
                ("juego", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="resultados", to="core.juegomemoria")),
            ],
            options={
                "verbose_name": "Resultado de memoria",
                "verbose_name_plural": "Resultados de memoria",
                "ordering": ["movimientos", "tiempo_total_segundos", "fecha"],
            },
        ),
        migrations.CreateModel(
            name="ResultadoPalabra",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nombre", models.CharField(max_length=100)),
                ("puntaje", models.PositiveIntegerField()),
                ("total_palabras", models.PositiveIntegerField()),
                ("tiempo_total_segundos", models.PositiveIntegerField(default=0)),
                ("fecha", models.DateTimeField(auto_now_add=True)),
                ("juego", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="resultados", to="core.juegopalabrasecreta")),
            ],
            options={
                "verbose_name": "Resultado de palabra secreta",
                "verbose_name_plural": "Resultados de palabra secreta",
                "ordering": ["-puntaje", "tiempo_total_segundos", "fecha"],
            },
        ),
    ]
