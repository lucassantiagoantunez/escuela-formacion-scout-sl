from django.db import migrations


CAMINOS = [
    {
        "titulo": "La huella en el sendero",
        "descripcion": "Una salida por las sierras puntanas donde observar no alcanza: hay que comparar indicios, comunicarse y decidir sin apurarse.",
        "escenas": [
            ("inicio", "Una marca que no estaba", "En un sendero de las sierras, la patrulla encuentra una cinta enganchada y varias huellas frescas que salen del camino. El grupo que pasó antes todavía no volvió, pero nadie informó una emergencia. Hay señal de teléfono intermitente y quedan dos horas de luz.", True, False, ""),
            ("mirada", "Antes de seguir", "A simple vista parecen huellas de dos personas, aunque el suelo pedregoso corta el rastro. La cinta podría ser una señal o un pedazo de equipo perdido. Dos integrantes quieren avanzar ya; otra propone ubicar el lugar en el croquis.", False, False, ""),
            ("registro", "Los indicios empiezan a hablar", "Sin mover nada, anotan dirección, tamaño aproximado, estado del suelo y hora. Una marca de bastón aparece junto a una pisada más arrastrada. No prueba que alguien esté herido, pero cambia la lectura.", False, False, ""),
            ("puesto", "Información a medias", "Desde el puesto confirman que una patrulla debía volver por otro sendero. Llevan una persona con una molestia previa en el tobillo, pero también podrían haber cambiado la ruta con autorización. Piden una descripción precisa antes de activar ayuda.", False, False, ""),
            ("ladera", "El rastro se divide", "En una ladera, las pisadas claras siguen hacia arriba y un pedacito de tela aparece cerca de una senda baja. El viento puede haber movido la tela. Desde ahí no se ve el puesto y la señal desaparece.", False, False, ""),
            ("arroyo", "Un silbato del otro lado", "Cerca de un arroyo bajo se escucha un silbato corto, pero el eco de las piedras confunde la dirección. El cruce habitual está unos minutos más adelante; atravesar derecho parece más rápido.", False, False, ""),
            ("contacto", "Una respuesta concreta", "La patrulla responde con la señal acordada y recibe dos silbatos. Ahora pueden ubicar la dirección sin cruzar a ciegas. También entra un mensaje del puesto: el grupo demorado es de tres personas.", False, False, ""),
            ("encuentro", "El grupo demorado", "Encuentran a las tres personas juntas. Una está sentada, con dolor de tobillo, consciente y abrigada. Ya habían avisado el cambio de ruta, pero el mensaje no salió. No hay peligro inmediato en el lugar.", False, False, ""),
            ("coordinacion", "Ayudar sin improvisar", "El puesto recibe ubicación, estado general y cantidad de personas. Indica mantener al grupo unido, aplicar únicamente los primeros auxilios para los que estén capacitados y esperar el apoyo por la senda baja.", False, False, ""),
            ("final_solido", "Una búsqueda bien pensada", "Observaron, contrastaron los indicios y comunicaron datos útiles. Llegaron al grupo sin desarmar la patrulla ni convertir una sospecha en certeza. La ayuda se coordinó con tiempo y todos regresaron acompañados.", False, True, "bueno"),
            ("final_util", "Llegaron, pero con poco margen", "La intuición los acercó, aunque avanzaron con información incompleta y durante un rato nadie supo con precisión dónde estaban. El resultado fue bueno; el procedimiento dependió demasiado de que nada saliera mal.", False, True, "neutro"),
            ("final_dispersion", "Demasiadas pistas, ningún equipo", "Al separarse para cubrir más terreno perdieron comunicación entre ellos. Encontraron el rastro, pero tuvieron que dedicar tiempo a reagruparse y el puesto recibió versiones distintas. En una búsqueda real, esa dispersión puede agrandar el problema.", False, True, "malo"),
            ("final_apuro", "El atajo salió caro", "Cruzar fuera del paso y mover indicios hizo más lenta la tarea. Nadie sufrió una lesión seria, pero sumaron un riesgo que no ayudó a ubicar al grupo. La velocidad sin coordinación no fue una ventaja.", False, True, "malo"),
        ],
        "opciones": [
            ("inicio", "Parar unos minutos, contar al grupo y mirar el conjunto antes de tocar o seguir nada", "mirada"),
            ("inicio", "Seguir la huella más nítida mientras todavía hay luz y avisar cuando vuelva la señal", "ladera"),
            ("inicio", "Volver al puesto con la cinta y pedir información antes de meterse fuera del sendero", "puesto"),
            ("mirada", "Registrar lo que se ve y mandar ubicación, sin afirmar todavía qué pasó", "registro"),
            ("mirada", "Armar dos equipos: uno sigue las huellas y el otro busca hacia la senda baja", "final_dispersion"),
            ("mirada", "Avanzar todos juntos hasta el próximo punto donde el rastro pueda confirmarse", "ladera"),
            ("registro", "Enviar al puesto una descripción concreta y preguntar por el grupo que pasó antes", "puesto"),
            ("registro", "Seguir el arrastre de la pisada; es el indicio más consistente aunque todavía no haya confirmación", "ladera"),
            ("registro", "Esperar diez minutos en el lugar para ver si aparece un nuevo mensaje o sonido", "contacto"),
            ("puesto", "Comparar la descripción del grupo con las huellas y acordar cómo mantener informado al puesto", "registro"),
            ("puesto", "Salir por la senda baja que sugiere el encargado, manteniendo al grupo completo", "arroyo"),
            ("puesto", "Pedir que activen el plan y quedar disponibles en el punto conocido", "coordinacion"),
            ("ladera", "Volver al último punto seguro y comunicar las dos alternativas antes de elegir", "registro"),
            ("ladera", "Tomar la senda baja: la tela coincide con el color del equipo del grupo demorado", "arroyo"),
            ("ladera", "Subir rápido por la huella clara y llamar a los gritos para ganar tiempo", "final_util"),
            ("arroyo", "Responder con la señal de silbato y caminar hasta el cruce habitual mientras ubican el sonido", "contacto"),
            ("arroyo", "Cruzar derecho por la parte que parece menos profunda para llegar antes", "final_apuro"),
            ("arroyo", "Volver unos metros hasta recuperar señal y pasar ubicación aproximada", "coordinacion"),
            ("contacto", "Seguir juntos hacia la respuesta, dejando referencias claras para el regreso", "encuentro"),
            ("contacto", "Esperar donde están y pedir al puesto que envíe otro grupo desde la senda baja", "coordinacion"),
            ("contacto", "Mandar a dos integrantes livianos adelante y que el resto llegue después", "final_dispersion"),
            ("encuentro", "Evaluar la situación, abrigar, informar y esperar indicaciones sin forzar la marcha", "coordinacion"),
            ("encuentro", "Ayudar a la persona a caminar despacio para salir antes de que baje la luz", "final_util"),
            ("encuentro", "Improvisar un traslado inmediato con ramas y sogas disponibles", "final_apuro"),
            ("coordinacion", "Mantener el recuento, cuidar al grupo y seguir el plan que llega desde el puesto", "final_solido"),
            ("coordinacion", "Cambiar el plan y salir por el recorrido que parece más corto", "final_util"),
            ("coordinacion", "Publicar una foto y la ubicación en el grupo general para que cualquiera pueda ayudar", "final_dispersion"),
        ],
    },
    {
        "titulo": "Tormenta durante la salida",
        "descripcion": "Una tormenta eléctrica sorprende a la patrulla en las sierras. Cada minuto cuenta, pero el atajo más corto no siempre baja el riesgo.",
        "escenas": [
            ("inicio", "El primer trueno", "El cielo se cerró antes de lo previsto y se escucha un trueno. El refugio cerrado planificado está a unos quince minutos por una senda baja; los vehículos, a doce minutos por otro acceso. Una galería abierta queda a cinco minutos.", True, False, ""),
            ("reagrupar", "Todos juntos, dos opiniones", "La patrulla se cuenta y avisa el cambio. Una dirigente propone los vehículos; otro responsable recuerda que el edificio cerrado tiene lugar para todos. La señal va y viene y el trueno se escucha más cerca.", False, False, ""),
            ("senda_baja", "La ruta prevista cambió", "La senda baja cruza cerca de un cauce que empezó a crecer. Hay un desvío marcado que agrega seis minutos y se mantiene lejos del agua. La loma recorta el trayecto, pero deja al grupo expuesto.", False, False, ""),
            ("galeria", "Techo, pero sin paredes", "Llegan a la galería. El techo cubre de la lluvia, aunque los costados están abiertos y hay columnas metálicas. Desde allí se ven los vehículos, a campo abierto, y un monte de árboles altos hacia el otro lado.", False, False, ""),
            ("separados", "La velocidad desarmó al grupo", "Los primeros avanzaron hacia los vehículos y el resto quedó atrás. Nadie sabe si todos recibieron el mismo mensaje. Todavía pueden reagruparse usando la señal acordada.", False, False, ""),
            ("vehiculos", "No entran todos en un solo lugar", "Hay tres vehículos cerrados, pero uno tiene poco espacio. El edificio está a siete minutos desde acá. Hace falta distribuir adultos y chicos sin dejar a nadie afuera ni corriendo solo.", False, False, ""),
            ("edificio", "A resguardo", "Todo el grupo llega a una construcción cerrada. Afuera sigue tronando, aunque la lluvia empieza a aflojar. Algunos proponen salir apenas pare; otros recuerdan que el peligro eléctrico puede continuar.", False, False, ""),
            ("mensaje", "Una comunicación que ordena", "Entra la respuesta del responsable general: el edificio es el punto principal y los vehículos sirven como refugio seguro mientras se completa el traslado. Pide recuento y novedades breves, no mensajes cruzados.", False, False, ""),
            ("final_seguro", "La salida se frenó a tiempo", "Suspendieron la actividad con el primer trueno, llegaron a un refugio cerrado y esperaron al menos treinta minutos desde el último trueno antes de retomar. La decisión cuidó al grupo aunque obligó a cambiar el programa.", False, True, "bueno"),
            ("final_coordinado", "Dos refugios, un solo plan", "Distribuyeron el grupo entre vehículos cerrados y edificio, con responsables y recuento en cada lugar. No era la opción más cómoda, pero sí una respuesta coordinada y verificable.", False, True, "bueno"),
            ("final_incompleto", "Cubiertos de lluvia, no de los rayos", "La galería y la carpa frenan el agua, pero no son refugios seguros ante una tormenta eléctrica. La patrulla tuvo que cambiar otra vez de lugar cuando el riesgo ya estaba más cerca.", False, True, "neutro"),
            ("final_expuesto", "El atajo aumentó el riesgo", "La loma parecía ahorrar minutos, pero dejó al grupo en terreno alto y abierto. Llegaron sin lesiones, aunque eligieron una ruta que aumentaba la exposición justo cuando había que reducirla.", False, True, "malo"),
            ("final_agua", "El camino conocido dejó de ser seguro", "Intentar cruzar el cauce en crecimiento demoró al grupo y obligó a retroceder. Con tormenta, el plan también tiene que adaptarse al agua y al viento, no solamente a la distancia.", False, True, "malo"),
            ("final_reencuentro", "Se reagruparon a tiempo", "La separación inicial complicó el recuento, pero frenaron, usaron la señal acordada y retomaron el plan como un solo grupo. Quedó claro por qué la velocidad no reemplaza la comunicación.", False, True, "neutro"),
        ],
        "opciones": [
            ("inicio", "Frenar la actividad, reunir a todos y decidir entre el edificio y los vehículos con el plan a mano", "reagrupar"),
            ("inicio", "Ir primero a la galería: está cerca y permite revisar el radar bajo techo", "galeria"),
            ("inicio", "Mandar grupos chicos hacia los vehículos para que el traslado sea más rápido", "separados"),
            ("reagrupar", "Tomar la senda baja hacia el edificio y mantener un recuento durante el movimiento", "senda_baja"),
            ("reagrupar", "Ir a los vehículos, porque se llega un poco antes y después se completa el traslado", "vehiculos"),
            ("reagrupar", "Esperar bajo los árboles del monte hasta confirmar si la tormenta se acerca o se aleja", "final_incompleto"),
            ("senda_baja", "Usar el desvío marcado, aunque lleve unos minutos más, y mantenerse lejos del cauce", "edificio"),
            ("senda_baja", "Cruzar por el paso habitual antes de que el agua suba más", "final_agua"),
            ("senda_baja", "Subir por la loma: son menos metros y el edificio ya se ve", "final_expuesto"),
            ("galeria", "Salir juntos hacia los vehículos cerrados, sin quedarse pegados a las columnas", "vehiculos"),
            ("galeria", "Quedarse en el centro de la galería hasta que pase lo más fuerte", "final_incompleto"),
            ("galeria", "Moverse al monte de árboles altos porque corta mejor el viento", "final_incompleto"),
            ("separados", "Frenar a ambos grupos, usar la señal acordada y volver a reunirlos", "final_reencuentro"),
            ("separados", "Que cada grupo siga al refugio que tiene más cerca y confirme al llegar", "mensaje"),
            ("separados", "Mantener la marcha: volver para reagrupar haría perder demasiado tiempo", "final_expuesto"),
            ("vehiculos", "Distribuir chicos y adultos, hacer recuento y completar el traslado al edificio con un responsable", "mensaje"),
            ("vehiculos", "Subir a los que entren primero y dejar al resto bajo la galería hasta que haya lugar", "final_incompleto"),
            ("vehiculos", "Quedarse todos cerca de los autos para no perder contacto visual", "final_incompleto"),
            ("mensaje", "Seguir el plan informado y confirmar cantidad y ubicación en cada refugio", "final_coordinado"),
            ("mensaje", "Cambiar todos al edificio aunque algunos deban caminar sin un adulto de referencia", "final_reencuentro"),
            ("mensaje", "Mantener cada grupo donde está y mandar novedades permanentes desde varios teléfonos", "final_incompleto"),
            ("edificio", "Esperar treinta minutos desde el último trueno, hacer recuento y recién entonces evaluar la vuelta", "final_seguro"),
            ("edificio", "Salir cuando deje de llover; si no se ven rayos, el riesgo principal ya pasó", "final_incompleto"),
            ("edificio", "Aprovechar la espera para informar, revisar el plan de regreso y mantener al grupo adentro", "final_seguro"),
        ],
    },
    {
        "titulo": "Una patrulla prepara su campamento",
        "descripcion": "Armar campamento en un lugar habilitado exige leer el terreno, repartir tareas y cuidar el sitio. Las decisiones cómodas también tienen costos.",
        "escenas": [
            ("inicio", "Tres lugares posibles", "La patrulla llega a un campamento habilitado cerca de El Trapiche. Hay una zona plana y baja, otra con mucha sombra bajo árboles grandes y un sitio ya usado, apenas inclinado, cerca del sendero interno. El pronóstico anuncia viento y posible lluvia.", True, False, ""),
            ("reconocer", "Mirar antes de clavar", "Recorren los tres sectores. El bajo es cómodo pero junta marcas de agua; bajo los árboles hay una rama seca; el sitio usado drena mejor, aunque obliga a pensar bien la circulación.", False, False, ""),
            ("diseno", "Un campamento en el papel", "En un croquis rápido ubican carpas, cocina, circulación y punto de reunión según las reglas del lugar. El viento viene del oeste y otro grupo comparte el sendero.", False, False, ""),
            ("rama", "La mejor sombra tiene un problema", "La rama seca queda justo sobre el lugar pensado para dormir. No corresponde cortarla por cuenta propia y mover todo ahora cuesta menos que hacerlo con las carpas armadas.", False, False, ""),
            ("bajo", "El suelo avisa", "Las marcas muestran que el agua cruza la zona plana cuando llueve fuerte. Algunos proponen hacer pequeñas zanjas alrededor de las carpas; otros prefieren cambiar de lugar y no modificar el terreno.", False, False, ""),
            ("roles", "No todos saben hacer lo mismo", "Hay integrantes con experiencia y otros que acampan por primera vez. Si los más rápidos hacen todo, terminarán antes; si trabajan en parejas, el armado llevará más tiempo pero todos podrán aprender.", False, False, ""),
            ("agua", "La reserva todavía está lejos", "El punto de agua potable autorizado queda a unos minutos. Un arroyo cercano se ve limpio, y las botellas personales alcanzan por ahora. La cocina quiere empezar mientras el resto termina las carpas.", False, False, ""),
            ("cocina", "Comodidad y circulación", "La zona central es práctica para cocinar, pero concentra paso de personas. El sector designado por el lugar está más apartado de las carpas y tiene superficie estable, aunque obliga a llevar el equipo unos metros más.", False, False, ""),
            ("residuos", "Lo que entra también sale", "La primera comida termina y aparecen envoltorios, restos orgánicos y agua usada. El lugar pide retirar los residuos y usar únicamente los puntos habilitados para el descarte de líquidos.", False, False, ""),
            ("revision", "Antes de darlo por terminado", "El viento aumenta. La patrulla puede hacer una recorrida final: tensores, caminos despejados, materiales sueltos, agua disponible y responsabilidades para la noche.", False, False, ""),
            ("final_equipo", "Campamento listo y patrulla también", "Eligieron un sitio ya utilizado, organizaron zonas, mezclaron experiencia con aprendizaje y revisaron el conjunto. No fue el armado más rápido, pero todos entendieron cómo sostenerlo y dejar el lugar en buenas condiciones.", False, True, "bueno"),
            ("final_funciona", "Quedó armado, pero depende de pocos", "El campamento funciona y el sitio es razonable, aunque casi todas las decisiones y tareas quedaron en manos de quienes ya sabían. Se ganó tiempo, pero se perdió una parte importante del aprender haciendo.", False, True, "neutro"),
            ("final_impacto", "Resolver un problema creando otro", "Las zanjas, las ramas cortadas y los residuos quemados facilitaron cosas por un rato, pero dejaron impacto y no respetaron las reglas del lugar. Un buen campamento también se mide por cómo queda cuando la patrulla se va.", False, True, "malo"),
            ("final_riesgo", "La comodidad tapó las señales", "La rama, el agua acumulada y la circulación ya habían dado pistas. Ignorarlas obligó a mover parte del campamento con viento y lluvia, cuando todo era más difícil.", False, True, "malo"),
        ],
        "opciones": [
            ("inicio", "Recorrer los tres lugares, mirar suelo y ramas, y recién después elegir", "reconocer"),
            ("inicio", "Tomar la zona plana y baja: permite armar rápido y mantener todo junto", "bajo"),
            ("inicio", "Elegir la sombra; si una rama preocupa, se puede acomodar el diseño alrededor", "rama"),
            ("reconocer", "Usar el sitio ya marcado y hacer un croquis sencillo antes de repartir tareas", "diseno"),
            ("reconocer", "Armar en el bajo, pero dejando las mochilas y la cocina en el punto más alto", "bajo"),
            ("reconocer", "Aprovechar la sombra y consultar al encargado qué hacer con la rama antes de instalarse", "rama"),
            ("rama", "Mover el área de carpas al sitio usado y dejar esa zona libre", "diseno"),
            ("rama", "Pedir autorización y esperar una solución del encargado antes de usar el sector", "roles"),
            ("rama", "Sacar solamente la parte seca con las herramientas de la patrulla", "final_impacto"),
            ("bajo", "Cambiar al sitio que ya drena bien antes de descargar todo", "diseno"),
            ("bajo", "Hacer canales chicos para guiar el agua sin mover las carpas", "final_impacto"),
            ("bajo", "Armar ahí y dejar decidido un plan de traslado si empieza a llover", "final_riesgo"),
            ("diseno", "Armar parejas con distinta experiencia y poner revisiones breves por tarea", "roles"),
            ("diseno", "Mandar a los que saben con las carpas y que el resto prepare cocina y materiales", "final_funciona"),
            ("diseno", "Empezar por las carpas y decidir las demás zonas cuando se vea cuánto espacio queda", "cocina"),
            ("roles", "Trabajar en parejas: quien sabe muestra, quien aprende hace y después revisan juntos", "agua"),
            ("roles", "Dar las tareas difíciles a los más experimentados para ganarle al clima", "final_funciona"),
            ("roles", "Rotar tareas, aunque algunas queden a medio hacer cuando cambie el equipo", "revision"),
            ("agua", "Buscar agua en el punto autorizado, completar la reserva y recién después encender la cocina", "cocina"),
            ("agua", "Usar el arroyo para cocinar: se ve limpio y evita una caminata extra", "final_riesgo"),
            ("agua", "Empezar con las botellas disponibles y mandar después a dos personas por la reserva", "cocina"),
            ("cocina", "Usar el sector designado, mantener despejada la circulación y seguir las reglas de fuego", "residuos"),
            ("cocina", "Instalar la cocina en el centro para que todos puedan ayudar y vigilar", "final_riesgo"),
            ("cocina", "Dividir el equipo y hacer dos cocinas chicas cerca de cada grupo de carpas", "final_funciona"),
            ("residuos", "Separar, guardar y llevarse los residuos; usar solo los lugares habilitados", "revision"),
            ("residuos", "Guardar todo en una sola bolsa y clasificarlo al final del campamento", "revision"),
            ("residuos", "Quemar papeles y restos orgánicos para reducir lo que hay que llevar", "final_impacto"),
            ("revision", "Hacer la recorrida con toda la patrulla y corregir cada punto antes de descansar", "final_equipo"),
            ("revision", "Que revise quien coordinó: conoce el plan y termina más rápido", "final_funciona"),
            ("revision", "Ajustar solamente los tensores; lo demás puede esperar hasta la mañana", "final_riesgo"),
        ],
    },
]


def cargar_caminos(apps, schema_editor):
    EligeCamino = apps.get_model("core", "EligeCamino")
    EscenaCamino = apps.get_model("core", "EscenaCamino")
    OpcionEscenaCamino = apps.get_model("core", "OpcionEscenaCamino")

    for datos in CAMINOS:
        camino, _ = EligeCamino.objects.get_or_create(titulo=datos["titulo"])
        camino.descripcion = datos["descripcion"]
        camino.activo = True
        camino.save(update_fields=["descripcion", "activo"])
        camino.escenas.all().delete()

        escenas = {}
        for orden, (clave, titulo, texto, es_inicio, es_final, tipo_final) in enumerate(datos["escenas"], 1):
            escenas[clave] = EscenaCamino.objects.create(
                camino=camino,
                titulo=titulo,
                texto=texto,
                orden=orden,
                es_inicio=es_inicio,
                es_final=es_final,
                tipo_final=tipo_final,
                activo=True,
            )

        ordenes_por_origen = {}
        for origen, texto, destino in datos["opciones"]:
            ordenes_por_origen[origen] = ordenes_por_origen.get(origen, 0) + 1
            OpcionEscenaCamino.objects.create(
                escena_origen=escenas[origen],
                texto_opcion=texto,
                escena_destino=escenas[destino],
                orden=ordenes_por_origen[origen],
                activo=True,
            )


class Migration(migrations.Migration):
    dependencies = [("core", "0032_contenido_interactivo_inicial")]

    operations = [migrations.RunPython(cargar_caminos, migrations.RunPython.noop)]
