from django.db import migrations


TRIVIAS = [
    {
        "titulo": "Escultismo para Muchachos: claves del método",
        "descripcion": "Ideas centrales presentadas por Baden-Powell y vigentes en el Método Scout: patrulla, servicio, observación y aprender haciendo.",
        "preguntas": [
            ("¿Cuál es el lema scout difundido por Baden-Powell?", "Siempre Listos", "Aprender de memoria", "Competir siempre"),
            ("¿Qué propone el sistema de patrullas?", "Aprender y actuar en un pequeño equipo", "Trabajar siempre en soledad", "Separar a quienes saben menos"),
            ("En el planteo original de Baden-Powell, ¿cuántos integrantes tenía aproximadamente una patrulla?", "Entre seis y ocho", "Más de cincuenta", "Solamente dos"),
            ("¿Qué lugar ocupa la acción en el Método Scout?", "Se aprende haciendo y reflexionando", "La práctica se evita", "Solo importa leer"),
            ("¿Para qué sirve la Ley Scout dentro del método?", "Orienta una forma de vivir y actuar", "Es un sistema de castigos", "Solo ordena competencias"),
            ("¿Qué actitud se vincula mejor con el servicio?", "Ayudar de manera útil y responsable", "Esperar siempre una recompensa", "Hacer lo que otros ya resolvieron"),
        ],
    },
    {
        "titulo": "Observación y rastreo scout",
        "descripcion": "Entrená la atención, la deducción y el cuidado del entorno a partir de las prácticas de observación de Escultismo para Muchachos.",
        "preguntas": [
            ("Observar bien significa…", "Notar detalles y relacionarlos antes de concluir", "Adivinar rápidamente", "Mirar solo lo más grande"),
            ("Una huella aislada permite afirmar con seguridad todo lo ocurrido?", "No; hay que reunir y comparar más indicios", "Sí; una señal alcanza", "Sí; si la vio el guía"),
            ("¿Qué ejercita el juego de Kim?", "La memoria y la observación de detalles", "La fuerza física", "La velocidad para correr"),
            ("Al seguir rastros en la naturaleza conviene…", "Evitar dañar el lugar y comprobar las señales", "Marcar árboles cortando su corteza", "Mover cada indicio encontrado"),
            ("¿Cuál es una buena práctica antes de salir a orientarse?", "Conocer la ruta, el clima y llevar lo necesario", "Depender únicamente del teléfono", "Salir sin avisar para ganar tiempo"),
            ("La deducción scout se construye principalmente con…", "Hechos observados y explicaciones comprobables", "Rumores", "La primera idea que aparece"),
        ],
    },
    {
        "titulo": "Campamento y vida al aire libre",
        "descripcion": "Decisiones responsables para organizar la vida de patrulla, cuidar el lugar y disfrutar una actividad segura.",
        "preguntas": [
            ("Antes de encender un fuego autorizado hay que…", "Revisar las reglas del lugar y preparar cómo apagarlo", "Buscar el sector con más hojas secas", "Encenderlo y luego avisar"),
            ("Al terminar un campamento, el lugar debería quedar…", "Limpio y con el menor impacto posible", "Con señales permanentes de la patrulla", "Con residuos juntos al lado del camino"),
            ("¿Por qué se distribuyen responsabilidades en la patrulla?", "Para que todos participen y el equipo funcione", "Para que una sola persona decida todo", "Para evitar aprender tareas nuevas"),
            ("¿Qué se hace con una herramienta que no se sabe usar?", "Pedir orientación y practicar de forma supervisada", "Improvisar lejos del grupo", "Probarla con más fuerza"),
            ("¿Qué ayuda a prevenir problemas con el agua para beber?", "Llevar agua segura y seguir indicaciones locales de potabilización", "Elegir cualquier curso transparente", "Esperar a tener sed"),
            ("Una evaluación previa del campamento debe incluir…", "Clima, terreno, comunicaciones y necesidades del grupo", "Solo el menú", "Únicamente la distancia"),
        ],
    },
]


ORDENA = [
    {
        "titulo": "Primeros auxilios: verificar, llamar y atender",
        "descripcion": "Práctica educativa basada en la Cruz Roja: seguridad de la escena, evaluación inicial, pedido de ayuda y atención dentro de la propia formación. No reemplaza un curso de primeros auxilios.",
        "etapa": "Respuesta inicial",
        "pasos": [
            "Comprobar que la escena sea segura y usar protección personal disponible.",
            "Verificar respuesta, respiración y hemorragias que amenacen la vida, sin demorar más de unos segundos.",
            "Llamar al servicio local de emergencias y pedir el equipo necesario cuando corresponda.",
            "Brindar cuidados acordes a la situación y a la propia capacitación.",
            "Acompañar, observar cambios y continuar hasta que llegue ayuda profesional.",
        ],
    },
    {
        "titulo": "Quemadura térmica: respuesta inicial",
        "descripcion": "Secuencia educativa basada en recomendaciones actuales de la Cruz Roja. No usar hielo ni sustancias grasosas. Ante una quemadura grave, pedir ayuda de emergencias.",
        "etapa": "Enfriar y proteger",
        "pasos": [
            "Asegurar la escena y alejar a la persona de la fuente de calor sin exponerse.",
            "Evaluar el estado general y pedir ayuda de emergencias si la quemadura es grave o existen otros signos de alarma.",
            "Retirar ropa o joyas que no estén adheridas a la piel.",
            "Enfriar la zona con agua corriente limpia y fresca durante 5 a 20 minutos; nunca con hielo.",
            "Proteger la quemadura de forma floja y limpia, y vigilar a la persona hasta recibir ayuda.",
        ],
    },
    {
        "titulo": "Hemorragia externa grave",
        "descripcion": "Secuencia educativa basada en la Cruz Roja. Una hemorragia que amenaza la vida es una emergencia: activar el sistema local y actuar solo dentro de la capacitación recibida.",
        "etapa": "Control inicial del sangrado",
        "pasos": [
            "Comprobar la seguridad de la escena y colocarse protección personal si está disponible.",
            "Reconocer el sangrado que amenaza la vida y llamar de inmediato al servicio de emergencias.",
            "Aplicar presión directa, firme y continua sobre la herida.",
            "Si la presión no controla el sangrado, usar torniquete o empaquetado únicamente cuando corresponda y se tenga capacitación.",
            "Mantener la atención, vigilar la respiración y acompañar hasta que llegue ayuda profesional.",
        ],
    },
]


RULETAS = [
    (
        "Ruleta de observación",
        "Microdesafíos para entrenar los sentidos y comparar observaciones sin dañar el entorno.",
        [
            "Observá durante 30 segundos y nombrá cinco detalles que no habías notado.",
            "Escuchá en silencio un minuto y distinguí al menos tres sonidos.",
            "Elegí un objeto, ocultalo y describilo para que tu patrulla lo identifique.",
            "Encontrá tres tonos distintos del mismo color en el entorno.",
            "Memorizá diez objetos durante un minuto y recordalos sin mirar.",
            "Describí un recorrido corto usando referencias claras, sin revelar el destino.",
        ],
    ),
    (
        "Ruleta de patrulla",
        "Desafíos breves para escuchar, cooperar, servir y repartir responsabilidades.",
        [
            "Inventen un grito de patrulla de menos de diez segundos.",
            "Cada integrante diga una habilidad que puede enseñar al equipo.",
            "Resuelvan una tarea sencilla usando una sola mano por persona.",
            "Elijan una buena acción concreta que puedan realizar esta semana.",
            "Cambien los roles habituales para la próxima actividad.",
            "Construyan entre todos una historia: cada persona agrega una oración.",
        ],
    ),
    (
        "Ruleta de campamento responsable",
        "Situaciones para revisar hábitos de seguridad, orden y cuidado del lugar.",
        [
            "Detecten tres riesgos posibles del sector y propongan cómo reducirlos.",
            "Armen en equipo una lista de control para antes de salir.",
            "Expliquen dónde ubicarían el agua, los residuos y el botiquín.",
            "Propongan una comida simple considerando higiene y conservación.",
            "Ensayen cómo avisarían una emergencia indicando ubicación y situación.",
            "Revisen el lugar y encuentren una forma concreta de dejarlo mejor.",
        ],
    ),
]


CAMINOS = [
    {
        "titulo": "La huella en el sendero",
        "descripcion": "Una historia de observación responsable: reunir indicios, evitar conclusiones apresuradas y cuidar el entorno.",
        "escenas": [
            ("inicio", "Una marca junto al sendero", "La patrulla encuentra huellas y una cinta junto al camino. ¿Qué hace primero?", True, False, ""),
            ("observar", "Observar antes de concluir", "Registran dirección, cantidad de huellas y estado de la cinta sin mover nada.", False, False, ""),
            ("preguntar", "Reunir información", "Un responsable del lugar confirma que otro grupo pasó hace poco y dejó una señal temporal.", False, False, ""),
            ("final_bueno", "Deducción comprobada", "La patrulla contrasta los indicios, informa la cinta abandonada y continúa sin alterar el sendero.", False, True, "bueno"),
            ("final_malo", "Una pista perdida", "Al mover y marcar todo, la patrulla borra información y deja un impacto innecesario.", False, True, "malo"),
        ],
        "opciones": [
            ("inicio", "Observar y registrar los indicios sin tocarlos", "observar"),
            ("inicio", "Mover todo y dejar nuevas marcas", "final_malo"),
            ("observar", "Consultar al responsable del lugar", "preguntar"),
            ("observar", "Afirmar de inmediato que alguien se perdió", "final_malo"),
            ("preguntar", "Comparar la información y comunicar el residuo encontrado", "final_bueno"),
        ],
    },
    {
        "titulo": "Tormenta durante la salida",
        "descripcion": "Decisiones de prevención y comunicación ante un cambio de clima durante una actividad al aire libre.",
        "escenas": [
            ("inicio", "El cielo cambia", "El pronóstico empeora y se oyen truenos a la distancia. La patrulla debe decidir.", True, False, ""),
            ("reagrupar", "Reagrupar y comunicar", "El grupo se reúne, cuenta a sus integrantes y avisa al responsable de la actividad.", False, False, ""),
            ("plan", "Aplicar el plan acordado", "Revisan la ruta de regreso y el refugio seguro previsto antes de la salida.", False, False, ""),
            ("final_bueno", "Todos a resguardo", "La patrulla sigue el plan, se mantiene unida y llega al lugar seguro.", False, True, "bueno"),
            ("final_malo", "El grupo se dispersa", "Continuar sin comunicar y separarse vuelve más difícil controlar la situación.", False, True, "malo"),
        ],
        "opciones": [
            ("inicio", "Reunir al grupo y comunicar el cambio", "reagrupar"),
            ("inicio", "Acelerar y dejar que cada uno elija su camino", "final_malo"),
            ("reagrupar", "Consultar y seguir el plan de seguridad", "plan"),
            ("reagrupar", "Esperar separados para ver qué sucede", "final_malo"),
            ("plan", "Ir juntos al resguardo previsto", "final_bueno"),
        ],
    },
    {
        "titulo": "Una patrulla prepara su campamento",
        "descripcion": "Organización, participación y cuidado antes de instalar una zona de campamento.",
        "escenas": [
            ("inicio", "Elegir el lugar", "La patrulla llega al sector autorizado y debe organizarse antes de armar.", True, False, ""),
            ("evaluar", "Revisar el terreno", "Observan drenaje, ramas, circulación, normas del lugar y zonas definidas.", False, False, ""),
            ("roles", "Distribuir responsabilidades", "Cada integrante asume una tarea y sabe a quién pedir ayuda.", False, False, ""),
            ("final_bueno", "Campamento listo", "El equipo arma con orden, mantiene vías despejadas y acuerda una revisión final.", False, True, "bueno"),
            ("final_malo", "Improvisación y riesgos", "Instalarse sin mirar el terreno ni coordinar genera desorden y riesgos evitables.", False, True, "malo"),
        ],
        "opciones": [
            ("inicio", "Evaluar el lugar antes de armar", "evaluar"),
            ("inicio", "Armar de inmediato donde haya espacio", "final_malo"),
            ("evaluar", "Repartir tareas y acordar prioridades", "roles"),
            ("evaluar", "Dejar todo a cargo de una sola persona", "final_malo"),
            ("roles", "Trabajar, revisar y corregir en equipo", "final_bueno"),
        ],
    },
]


MEMORIAS = [
    (
        "Símbolos y conceptos scouts",
        "Encontrá las relaciones entre ideas centrales del Método Scout.",
        [
            ("Siempre Listos", "Preparación para actuar responsablemente"),
            ("Patrulla", "Pequeño equipo de aprendizaje y acción"),
            ("Promesa", "Compromiso personal y voluntario"),
            ("Ley Scout", "Valores que orientan la vida cotidiana"),
            ("Servicio", "Acción útil en favor de otras personas"),
            ("Aprender haciendo", "Experiencia, reflexión y nueva práctica"),
        ],
    ),
    (
        "Rastreo y observación",
        "Uní cada práctica de observación con su propósito.",
        [
            ("Juego de Kim", "Memoria de detalles observados"),
            ("Huella", "Indicio que debe compararse con otros"),
            ("Croquis", "Representación simple de un lugar o recorrido"),
            ("Punto cardinal", "Referencia para expresar una dirección"),
            ("Deducción", "Explicación apoyada en indicios"),
            ("Silencio", "Recurso para distinguir sonidos del entorno"),
        ],
    ),
    (
        "Campamento seguro",
        "Relacioná cada aspecto de la vida al aire libre con una decisión preventiva.",
        [
            ("Pronóstico", "Revisarlo antes y durante la actividad"),
            ("Botiquín", "Ubicarlo y asignar responsables capacitados"),
            ("Agua", "Asegurar una fuente apta para consumo"),
            ("Residuos", "Reducirlos y retirarlos según las normas"),
            ("Herramientas", "Usarlas con técnica y supervisión"),
            ("Plan de emergencia", "Acordar comunicación, roles y puntos seguros"),
        ],
    ),
]


PALABRAS = [
    (
        "Vocabulario scout",
        "Descubrí conceptos presentes en la propuesta educativa scout.",
        [
            ("PATRULLA", "Pequeño equipo donde cada integrante participa", "El sistema de patrullas promueve responsabilidad compartida."),
            ("PROMESA", "Compromiso personal asumido voluntariamente", "La Promesa expresa una decisión personal dentro del marco scout."),
            ("SERVICIO", "Acción útil orientada al bien de otras personas", "El servicio conecta los valores con necesidades reales."),
            ("PROGRESION", "Camino personal de crecimiento", "La progresión acompaña objetivos adecuados a cada persona."),
            ("AVENTURA", "Experiencia desafiante, segura y con propósito", "La aventura crea oportunidades para aprender haciendo."),
            ("EQUIPO", "Personas que cooperan hacia un objetivo", "El trabajo en equipo distribuye tareas y aprendizajes."),
        ],
    ),
    (
        "Naturaleza y orientación",
        "Palabras para leer el entorno y planificar un recorrido responsable.",
        [
            ("BRUJULA", "Instrumento que ayuda a reconocer direcciones", "La brújula se usa junto con el mapa y otras referencias."),
            ("SENDERO", "Camino pensado para transitar un ambiente", "Usar senderos habilitados ayuda a reducir el impacto."),
            ("RASTRO", "Señal que aporta información sobre un paso o suceso", "Un rastro se interpreta comparando varios indicios."),
            ("CROQUIS", "Dibujo simple de un lugar o recorrido", "Un croquis prioriza referencias útiles y claras."),
            ("NORTE", "Punto cardinal usado como referencia", "Orientar el mapa facilita relacionarlo con el terreno."),
            ("ENTORNO", "Conjunto de elementos que nos rodean", "Conocerlo ayuda a cuidarlo y anticipar riesgos."),
        ],
    ),
    (
        "Vida de patrulla",
        "Descubrí palabras vinculadas con organización, cooperación y participación.",
        [
            ("CONSEJO", "Espacio para dialogar y tomar decisiones", "Escuchar distintas voces mejora las decisiones del equipo."),
            ("RESPETO", "Reconocimiento y cuidado de cada persona", "El respeto sostiene un ambiente seguro e inclusivo."),
            ("ESCUCHA", "Atención genuina a lo que otra persona expresa", "Escuchar permite comprender antes de responder."),
            ("MISION", "Objetivo concreto que moviliza al equipo", "Una misión clara ayuda a organizar roles y tiempos."),
            ("AYUDA", "Apoyo oportuno frente a una necesidad", "Ayudar responsablemente también implica reconocer los propios límites."),
            ("ACUERDO", "Decisión construida y aceptada por el grupo", "Los acuerdos claros permiten revisar cómo trabaja la patrulla."),
        ],
    ),
]


def cargar_contenido(apps, schema_editor):
    Trivia = apps.get_model("core", "Trivia")
    Pregunta = apps.get_model("core", "Pregunta")
    OpcionRespuesta = apps.get_model("core", "OpcionRespuesta")
    OrdenaPasos = apps.get_model("core", "OrdenaPasos")
    EtapaOrdenaPasos = apps.get_model("core", "EtapaOrdenaPasos")
    PasoOrdenaPasos = apps.get_model("core", "PasoOrdenaPasos")
    RuletaDesafio = apps.get_model("core", "RuletaDesafio")
    SectorRuleta = apps.get_model("core", "SectorRuleta")
    EligeCamino = apps.get_model("core", "EligeCamino")
    EscenaCamino = apps.get_model("core", "EscenaCamino")
    OpcionEscenaCamino = apps.get_model("core", "OpcionEscenaCamino")
    JuegoMemoria = apps.get_model("core", "JuegoMemoria")
    ParejaMemoria = apps.get_model("core", "ParejaMemoria")
    JuegoPalabraSecreta = apps.get_model("core", "JuegoPalabraSecreta")
    PalabraJuego = apps.get_model("core", "PalabraJuego")

    for datos in TRIVIAS:
        trivia, _ = Trivia.objects.get_or_create(
            titulo=datos["titulo"], defaults={"descripcion": datos["descripcion"]}
        )
        for orden, (texto, correcta, incorrecta_1, incorrecta_2) in enumerate(datos["preguntas"], 1):
            pregunta, _ = Pregunta.objects.get_or_create(
                trivia=trivia, texto=texto, defaults={"orden": orden}
            )
            for opcion, es_correcta in ((correcta, True), (incorrecta_1, False), (incorrecta_2, False)):
                OpcionRespuesta.objects.get_or_create(
                    pregunta=pregunta, texto=opcion, defaults={"es_correcta": es_correcta}
                )

    for datos in ORDENA:
        tema, _ = OrdenaPasos.objects.get_or_create(
            titulo=datos["titulo"],
            defaults={"descripcion": datos["descripcion"], "activo": True},
        )
        etapa, _ = EtapaOrdenaPasos.objects.get_or_create(
            tema=tema,
            titulo=datos["etapa"],
            defaults={"descripcion": datos["descripcion"], "orden": 1, "tiempo_limite_segundos": 120, "activo": True},
        )
        for orden, texto in enumerate(datos["pasos"], 1):
            PasoOrdenaPasos.objects.get_or_create(
                etapa=etapa, texto=texto, defaults={"orden_correcto": orden}
            )

    for titulo, descripcion, sectores in RULETAS:
        ruleta, _ = RuletaDesafio.objects.get_or_create(
            titulo=titulo, defaults={"descripcion": descripcion, "activo": True}
        )
        for orden, texto in enumerate(sectores, 1):
            SectorRuleta.objects.get_or_create(
                ruleta=ruleta,
                texto=texto,
                defaults={"tipo": "buena_accion" if orden % 2 == 0 else "prenda_castigo", "orden": orden, "activo": True},
            )

    for datos in CAMINOS:
        camino, _ = EligeCamino.objects.get_or_create(
            titulo=datos["titulo"], defaults={"descripcion": datos["descripcion"], "activo": True}
        )
        escenas = {}
        for orden, (clave, titulo, texto, es_inicio, es_final, tipo_final) in enumerate(datos["escenas"], 1):
            escena, _ = EscenaCamino.objects.get_or_create(
                camino=camino,
                titulo=titulo,
                defaults={
                    "texto": texto, "orden": orden, "es_inicio": es_inicio,
                    "es_final": es_final, "tipo_final": tipo_final, "activo": True,
                },
            )
            escenas[clave] = escena
        for orden, (origen, texto, destino) in enumerate(datos["opciones"], 1):
            OpcionEscenaCamino.objects.get_or_create(
                escena_origen=escenas[origen],
                texto_opcion=texto,
                escena_destino=escenas[destino],
                defaults={"orden": orden, "activo": True},
            )

    for titulo, descripcion, parejas in MEMORIAS:
        juego, _ = JuegoMemoria.objects.get_or_create(
            titulo=titulo, defaults={"descripcion": descripcion, "activo": True}
        )
        for orden, (concepto, relacion) in enumerate(parejas, 1):
            ParejaMemoria.objects.get_or_create(
                juego=juego,
                concepto=concepto,
                defaults={"relacion": relacion, "explicacion": f"{concepto}: {relacion}.", "orden": orden},
            )

    for titulo, descripcion, palabras in PALABRAS:
        juego, _ = JuegoPalabraSecreta.objects.get_or_create(
            titulo=titulo, defaults={"descripcion": descripcion, "activo": True}
        )
        for orden, (palabra, pista, explicacion) in enumerate(palabras, 1):
            PalabraJuego.objects.get_or_create(
                juego=juego,
                palabra=palabra,
                defaults={"pista": pista, "explicacion": explicacion, "orden": orden},
            )


def quitar_contenido(apps, schema_editor):
    titulos_por_modelo = {
        "Trivia": [item["titulo"] for item in TRIVIAS],
        "OrdenaPasos": [item["titulo"] for item in ORDENA],
        "RuletaDesafio": [item[0] for item in RULETAS],
        "EligeCamino": [item["titulo"] for item in CAMINOS],
        "JuegoMemoria": [item[0] for item in MEMORIAS],
        "JuegoPalabraSecreta": [item[0] for item in PALABRAS],
    }
    for nombre_modelo, titulos in titulos_por_modelo.items():
        apps.get_model("core", nombre_modelo).objects.filter(titulo__in=titulos).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0031_juegos_memoria_y_palabra"),
    ]

    operations = [
        migrations.RunPython(cargar_contenido, quitar_contenido),
    ]
