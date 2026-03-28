import random

from django.db.models import Case, IntegerField, Prefetch, Q, Value, When
from django.shortcuts import get_object_or_404, render
from django.views.decorators.clickjacking import xframe_options_sameorigin

from .models import (
    BloquePagina,
    ComponenteInteractivo,
    ContenidoInicio,
    EligeCamino,
    EscenaCamino,
    InteresCurso,
    Material,
    Noticia,
    OpcionEscenaCamino,
    OrdenaPasos,
    Pagina,
    Programa,
    ResultadoOrdenaPasos,
    ResultadoTrivia,
    RuletaDesafio,
    SectorRuleta,
    Trivia,
)


# ==================================================
# BLOQUE 1 - VISTA DE INICIO
# ==================================================
def inicio(request):
    noticias = Noticia.objects.filter(publicada=True).order_by("-destacada", "-fecha_creacion")[:3]
    contenido_inicio = ContenidoInicio.objects.filter(activo=True).first()

    return render(
        request,
        "core/inicio.html",
        {
            "noticias": noticias,
            "contenido_inicio": contenido_inicio,
        },
    )


# ==================================================
# BLOQUE 2 - VISTAS DE NOTICIAS
# ==================================================
def detalle_noticia(request, noticia_id):
    noticia = get_object_or_404(Noticia, id=noticia_id, publicada=True)

    return render(
        request,
        "core/detalle_noticia.html",
        {
            "noticia": noticia,
        },
    )


def noticias(request):
    noticias = Noticia.objects.filter(publicada=True).order_by("-destacada", "-fecha_creacion")

    return render(
        request,
        "core/noticias.html",
        {
            "noticias": noticias,
        },
    )


# ==================================================
# BLOQUE 3 - VISTA DE BIBLIOTECA
# ==================================================
def biblioteca(request):
    busqueda = request.GET.get("q", "").strip()
    materiales = Material.objects.all().order_by("titulo")

    if busqueda:
        materiales = materiales.filter(
            Q(titulo__icontains=busqueda) | Q(descripcion__icontains=busqueda)
        )

    return render(
        request,
        "core/biblioteca.html",
        {
            "materiales": materiales,
            "busqueda": busqueda,
            "hay_resultados": materiales.exists(),
        },
    )


# ==================================================
# BLOQUE 4 - VISTAS DE PROGRAMAS
# ==================================================
def programas(request):
    programas = Programa.objects.annotate(
        orden_seccion=Case(
            When(seccion="menor", then=Value(1)),
            When(seccion="media", then=Value(2)),
            When(seccion="intermedia", then=Value(3)),
            When(seccion="mayor", then=Value(4)),
            When(seccion="dirigentes", then=Value(5)),
            output_field=IntegerField(),
        )
    ).order_by("orden_seccion", "nombre")

    return render(
        request,
        "core/programas.html",
        {
            "programas": programas,
        },
    )


def detalle_programa(request, programa_id):
    programa = get_object_or_404(Programa, id=programa_id)
    areas = programa.areas.all()

    return render(
        request,
        "core/detalle_programa.html",
        {
            "programa": programa,
            "areas": areas,
        },
    )


# ==================================================
# BLOQUE 4A - VISTA DE PÁGINAS PERSONALIZADAS
# ==================================================
def detalle_pagina(request, slug):
    pagina_qs = Pagina.objects.filter(publicado=True).select_related("pagina_padre").prefetch_related(
        "materiales",
        Prefetch(
            "bloques",
            queryset=BloquePagina.objects.filter(activo=True)
            .select_related("componente_interactivo")
            .prefetch_related("materiales", "imagenes_galeria")
            .order_by("orden", "id"),
            to_attr="bloques_activos",
        ),
        Prefetch(
            "subpaginas",
            queryset=Pagina.objects.filter(publicado=True).order_by("orden", "titulo"),
            to_attr="subpaginas_publicadas",
        ),
    )

    pagina = get_object_or_404(pagina_qs, slug=slug)

    return render(
        request,
        "core/pagina_generica.html",
        {
            "pagina": pagina,
            "bloques": getattr(pagina, "bloques_activos", []),
            "subpaginas": getattr(pagina, "subpaginas_publicadas", []),
        },
    )


# ==================================================
# BLOQUE 4B - VISTA DE COMPONENTES INTERACTIVOS
# ==================================================
@xframe_options_sameorigin
def render_componente_interactivo(request, slug):
    componente = get_object_or_404(
        ComponenteInteractivo,
        slug=slug,
        publicado=True,
    )

    return render(
        request,
        "core/render_componente_interactivo.html",
        {
            "componente": componente,
        },
    )


# ==================================================
# BLOQUE 5 - VISTAS DE TRIVIAS
# ==================================================
def detalle_trivia(request, trivia_id):
    trivia = get_object_or_404(Trivia, id=trivia_id)

    puntaje = None
    porcentaje = None
    mensaje_resultado = ""
    nombre_participante = ""
    tiempo_total_segundos = 0
    mostrar_recomendacion = False

    preguntas = trivia.preguntas.all().order_by("?")
    total_preguntas = preguntas.count()

    for pregunta in preguntas:
        pregunta.opciones_aleatorias = pregunta.opciones.all().order_by("?")
        pregunta.respuesta_usuario_id = None
        pregunta.opcion_correcta_id = None

    if request.method == "POST":
        puntaje = 0
        nombre_participante = request.POST.get("nombre_participante", "").strip()

        try:
            tiempo_total_segundos = int(request.POST.get("tiempo_total_segundos", 0) or 0)
        except ValueError:
            tiempo_total_segundos = 0

        for pregunta in preguntas:
            respuesta_id = request.POST.get(f"pregunta_{pregunta.id}")
            opcion_correcta = pregunta.opciones.filter(es_correcta=True).first()

            pregunta.respuesta_usuario_id = respuesta_id
            pregunta.opcion_correcta_id = str(opcion_correcta.id) if opcion_correcta else None

            if respuesta_id and opcion_correcta and str(opcion_correcta.id) == respuesta_id:
                puntaje += 1

        if total_preguntas > 0:
            porcentaje = round((puntaje / total_preguntas) * 100)

            if porcentaje == 100:
                mensaje_resultado = "¡Excelente! Respondiste todo correctamente."
            elif porcentaje >= 70:
                mensaje_resultado = "Muy bien. Tenés una buena base."
            elif porcentaje >= 50:
                mensaje_resultado = "Aprobado, pero hay temas para repasar."
            else:
                mensaje_resultado = "Necesitás repasar este tema."
        else:
            porcentaje = 0
            mensaje_resultado = "Esta trivia no tiene preguntas cargadas."

        if (
            porcentaje is not None
            and porcentaje < trivia.porcentaje_minimo_recomendacion
            and (trivia.material_recomendado or trivia.video_recomendado_url)
        ):
            mostrar_recomendacion = True

        if nombre_participante:
            ResultadoTrivia.objects.create(
                trivia=trivia,
                nombre=nombre_participante,
                puntaje=puntaje,
                total_preguntas=total_preguntas,
                porcentaje=porcentaje,
                tiempo_total_segundos=tiempo_total_segundos,
            )

    resultados = trivia.resultados.all().order_by("-porcentaje", "tiempo_total_segundos", "-fecha")
    ranking_unico = []
    nombres_vistos = set()

    for resultado in resultados:
        nombre_normalizado = resultado.nombre.strip().lower()

        if nombre_normalizado not in nombres_vistos:
            ranking_unico.append(resultado)
            nombres_vistos.add(nombre_normalizado)

    ranking = ranking_unico[:10]

    return render(
        request,
        "core/detalle_trivia.html",
        {
            "trivia": trivia,
            "preguntas": preguntas,
            "puntaje": puntaje,
            "total_preguntas": total_preguntas,
            "porcentaje": porcentaje,
            "mensaje_resultado": mensaje_resultado,
            "nombre_participante": nombre_participante,
            "tiempo_total_segundos": tiempo_total_segundos,
            "mostrar_recomendacion": mostrar_recomendacion,
            "ranking": ranking,
        },
    )


def juegos_y_trivias(request):
    trivias_destacadas = Trivia.objects.all().order_by("titulo")[:3]
    ordena_pasos_destacados = OrdenaPasos.objects.filter(activo=True).order_by("titulo")[:3]
    ruletas_destacadas = RuletaDesafio.objects.filter(activo=True).order_by("titulo")[:3]
    caminos_destacados = EligeCamino.objects.filter(activo=True).order_by("titulo")[:3]

    return render(
        request,
        "core/juegos_y_trivias.html",
        {
            "trivias_destacadas": trivias_destacadas,
            "ordena_pasos_destacados": ordena_pasos_destacados,
            "ruletas_destacadas": ruletas_destacadas,
            "caminos_destacados": caminos_destacados,
        },
    )


def trivias(request):
    trivias = Trivia.objects.all().order_by("titulo")

    return render(
        request,
        "core/trivias.html",
        {
            "trivias": trivias,
        },
    )


# ==================================================
# BLOQUE 6 - VISTAS DE ORDENA LOS PASOS
# ==================================================
def ordena_pasos(request):
    juegos = OrdenaPasos.objects.filter(activo=True).order_by("titulo")

    return render(
        request,
        "core/ordena_pasos.html",
        {
            "juegos": juegos,
        },
    )


def detalle_ordena_pasos(request, tema_id):
    tema = get_object_or_404(OrdenaPasos, id=tema_id, activo=True)
    etapas = list(tema.etapas.filter(activo=True).order_by("orden", "id"))

    puntaje = None
    porcentaje = None
    mensaje_resultado = ""
    nombre_participante = ""
    tiempo_total_segundos = 0
    total_pasos = 0
    mostrar_recomendacion = False

    if request.method == "POST":
        nombre_participante = request.POST.get("nombre_participante", "").strip()

        try:
            tiempo_total_segundos = int(request.POST.get("tiempo_total_segundos", 0) or 0)
        except ValueError:
            tiempo_total_segundos = 0

        puntaje = 0

        for etapa in etapas:
            pasos_orden_correcto = list(etapa.pasos.all().order_by("orden_correcto", "id"))
            orden_final = request.POST.get(f"orden_etapa_{etapa.id}", "").strip()

            try:
                ids_usuario = [int(valor) for valor in orden_final.split(",") if valor.strip()]
            except ValueError:
                ids_usuario = []

            pasos_por_id = {paso.id: paso for paso in pasos_orden_correcto}
            pasos_resultado = [
                pasos_por_id[paso_id]
                for paso_id in ids_usuario
                if paso_id in pasos_por_id
            ]

            ids_presentes = {paso.id for paso in pasos_resultado}
            for paso in pasos_orden_correcto:
                if paso.id not in ids_presentes:
                    pasos_resultado.append(paso)

            etapa.pasos_resultado = pasos_resultado
            etapa.total_pasos = len(pasos_orden_correcto)
            etapa.puntaje = 0

            for posicion, paso in enumerate(etapa.pasos_resultado, start=1):
                paso.posicion_usuario = posicion
                paso.esta_correcto = paso.orden_correcto == posicion

                if paso.esta_correcto:
                    etapa.puntaje += 1

            etapa.porcentaje = round((etapa.puntaje / etapa.total_pasos) * 100) if etapa.total_pasos > 0 else 0

            puntaje += etapa.puntaje
            total_pasos += etapa.total_pasos

        if total_pasos > 0:
            porcentaje = round((puntaje / total_pasos) * 100)

            if porcentaje == 100:
                mensaje_resultado = "¡Excelente! Ordenaste correctamente todas las etapas."
            elif porcentaje >= 70:
                mensaje_resultado = "Muy bien. Tenés una buena comprensión de la secuencia."
            elif porcentaje >= 50:
                mensaje_resultado = "Vas bien, pero todavía hay pasos para repasar."
            else:
                mensaje_resultado = "Necesitás revisar mejor la secuencia general del tema."
        else:
            porcentaje = 0
            mensaje_resultado = "Este tema todavía no tiene etapas con pasos cargados."

        if (
            porcentaje is not None
            and porcentaje < tema.porcentaje_minimo_recomendacion
            and (tema.material_recomendado or tema.video_recomendado_url)
        ):
            mostrar_recomendacion = True

        if nombre_participante:
            ResultadoOrdenaPasos.objects.create(
                tema=tema,
                nombre=nombre_participante,
                puntaje=puntaje,
                total_pasos=total_pasos,
                porcentaje=porcentaje,
                tiempo_total_segundos=tiempo_total_segundos,
            )

    else:
        for etapa in etapas:
            etapa.pasos_aleatorios = list(etapa.pasos.all().order_by("orden_correcto", "id"))
            random.shuffle(etapa.pasos_aleatorios)

    resultados = tema.resultados.all().order_by("-porcentaje", "-puntaje", "tiempo_total_segundos", "-fecha")
    ranking_unico = []
    nombres_vistos = set()

    for resultado in resultados:
        nombre_normalizado = resultado.nombre.strip().lower()

        if nombre_normalizado not in nombres_vistos:
            ranking_unico.append(resultado)
            nombres_vistos.add(nombre_normalizado)

    ranking = ranking_unico[:10]

    return render(
        request,
        "core/detalle_ordena_pasos.html",
        {
            "tema": tema,
            "etapas": etapas,
            "puntaje": puntaje,
            "total_pasos": total_pasos,
            "porcentaje": porcentaje,
            "mensaje_resultado": mensaje_resultado,
            "nombre_participante": nombre_participante,
            "tiempo_total_segundos": tiempo_total_segundos,
            "mostrar_recomendacion": mostrar_recomendacion,
            "ranking": ranking,
        },
    )


# ==================================================
# BLOQUE 7 - VISTAS DE RULETAS
# ==================================================
def ruletas(request):
    ruletas = RuletaDesafio.objects.filter(activo=True).order_by("titulo")

    return render(
        request,
        "core/ruletas.html",
        {
            "ruletas": ruletas,
        },
    )


def detalle_ruleta(request, ruleta_id):
    ruleta_qs = RuletaDesafio.objects.filter(activo=True).prefetch_related(
        Prefetch(
            "sectores",
            queryset=SectorRuleta.objects.filter(activo=True).order_by("orden", "id"),
            to_attr="sectores_activos",
        )
    )

    ruleta = get_object_or_404(ruleta_qs, id=ruleta_id)
    sectores = getattr(ruleta, "sectores_activos", [])

    sectores_json = [
        {
            "id": sector.id,
            "texto": sector.texto,
            "tipo": sector.tipo,
            "orden": sector.orden,
        }
        for sector in sectores
    ]

    return render(
        request,
        "core/detalle_ruleta.html",
        {
            "ruleta": ruleta,
            "sectores": sectores,
            "sectores_json": sectores_json,
        },
    )


# ==================================================
# BLOQUE 8 - VISTAS DE ELIGE EL CAMINO
# ==================================================
def caminos(request):
    caminos = EligeCamino.objects.filter(activo=True).order_by("titulo")

    return render(
        request,
        "core/caminos.html",
        {
            "caminos": caminos,
        },
    )


def detalle_camino(request, camino_id):
    camino_qs = EligeCamino.objects.filter(activo=True).prefetch_related(
        Prefetch(
            "escenas",
            queryset=EscenaCamino.objects.filter(activo=True)
            .select_related("material_recomendado")
            .prefetch_related(
                Prefetch(
                    "opciones",
                    queryset=OpcionEscenaCamino.objects.filter(
                        activo=True,
                        escena_destino__activo=True,
                    )
                    .select_related("escena_destino")
                    .order_by("orden", "id"),
                    to_attr="opciones_activas",
                )
            )
            .order_by("orden", "id"),
            to_attr="escenas_activas",
        )
    )

    camino = get_object_or_404(camino_qs, id=camino_id)
    escenas = getattr(camino, "escenas_activas", [])

    escena_inicial = None
    for escena in escenas:
        escena.opciones_disponibles = getattr(escena, "opciones_activas", [])

        if escena_inicial is None and escena.es_inicio:
            escena_inicial = escena

    if escena_inicial is None and escenas:
        escena_inicial = escenas[0]

    return render(
        request,
        "core/detalle_camino.html",
        {
            "camino": camino,
            "escenas": escenas,
            "escena_inicial": escena_inicial,
        },
    )


# ==================================================
# BLOQUE 9 - VISTA DE QUIERO APRENDER
# ==================================================
def quiero_aprender(request):
    mensaje_exito = False
    contenido_inicio = ContenidoInicio.objects.filter(activo=True).first()

    if request.method == "POST":
        nombre = request.POST.get("nombre", "").strip()
        email = request.POST.get("email", "").strip()
        seccion = request.POST.get("seccion", "").strip()
        curso_interes = request.POST.get("curso_interes", "").strip()
        detalle = request.POST.get("detalle", "").strip()

        if nombre and curso_interes:
            InteresCurso.objects.create(
                nombre=nombre,
                email=email if email else None,
                seccion=seccion,
                curso_interes=curso_interes,
                detalle=detalle,
            )
            mensaje_exito = True

    return render(
        request,
        "core/quiero_aprender.html",
        {
            "mensaje_exito": mensaje_exito,
            "contenido_inicio": contenido_inicio,
        },
    )