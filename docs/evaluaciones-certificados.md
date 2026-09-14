# Evaluaciones, certificados y libro de actas

## Uso cotidiano

En **Gestionar EDiFoS → curso → módulo → Agregar prueba** se puede copiar un juego existente o crear una prueba privada. Aparece en el índice del curso como una clase. Primero se guarda como borrador; Dirección revisa las actividades y pulsa **Publicar prueba**.

Tipos disponibles: trivia/quiz, ordenar pasos, relacionar parejas, palabra secreta, elegir un camino, ruleta de retos y rompecabezas de nueve piezas. Se copian consignas y respuestas de los seis tipos de juegos existentes. Las imágenes y recomendaciones externas de esos juegos no se importan. El rompecabezas admite cargar directamente una imagen JPG/PNG o reutilizar una imagen del curso. La copia no modifica los juegos públicos ni sus resultados.

La nota se calcula en el servidor. La ruleta sortea un reto por intento y requiere una respuesta escrita y corrección del equipo. En los caminos, Dirección define decisiones que llevan a otras escenas o finales (favorable 100%, intermedio 50%, desfavorable 0%). Se validan las salidas; un recorrido de 100 decisiones sin final termina con 0%. Ordenar y rompecabezas puntúan por posiciones correctas; las palabras ignoran mayúsculas, tildes y espacios repetidos. No son exámenes supervisados ni un mecanismo de control de identidad.

Cada intento conserva una copia de las preguntas y sus reglas. Abrirlo reserva un intento y volver a abrirlo permite continuar. Entregar dos veces no duplica ni cambia la entrega. Cambiar contenido o porcentaje de aprobación crea una nueva versión en borrador; los resultados anteriores siguen en el historial, pero la versión nueva debe aprobarse. En **Instrucciones, aprobación e intentos** se puede ampliar el máximo sin perder notas. Las correcciones manuales requieren devolución y conservan responsable y fecha.

**Seguimiento, certificados y actas** reúne los resultados, correcciones y validaciones. Los formadores asignados pueden revisar entregas; solo Dirección valida requisitos, emite certificados y registra actas. El cursante encuentra sus resultados y certificados en **Mi avance**; los certificados también quedan en **Mis cursos** aunque el curso deje de estar publicado.

## Certificación institucional

1. Configurar fechas, autoridad responsable, carga horaria opcional y si el curso requiere traslado al libro de actas. Esta decisión es explícita por curso; no se deduce del nombre.
2. Validar al cursante con su nombre completo, participación/asistencia, demás requisitos y fundamento documental.
3. Para confirmar aprobación, deben estar completadas las lecturas obligatorias publicadas y aprobadas las versiones actuales de las pruebas obligatorias publicadas. Se bloquea el cierre si quedan clases o pruebas obligatorias en borrador. Dirección verifica separadamente tutoría, trabajos y requisitos externos al aula, y revisa que el programa esté completo.
4. Cuando corresponde libro, realizar el asiento real y registrar libro, acta, folio y fecha. Los cuatro datos son necesarios para emitir el certificado de aprobación de ese curso. El listado CSV permite preparar el trabajo institucional; descargarlo no confirma un asiento.
5. Emitir participación o participación y aprobación. El primero no acredita un nivel aprobado. No se emiten constancias antes de la fecha de finalización configurada.

Los certificados son PDF con código único, datos conservados al emitir y enlace público de vigencia. El enlace no expone nombre ni datos de matrícula; el PDF completo exige sesión del titular o Dirección. No se dibuja una firma ni se atribuye una aprobación externa automática. Dirección conserva la responsabilidad de reunir las firmas y formalidades institucionales aplicables. La aprobación de un juego, la emisión del PDF o el registro digital **no homologan por sí mismos una formación**.

Cambiar posteriormente el curso o nombre del usuario no modifica un certificado emitido. Para corregir sus datos, revocar con motivo y emitir de nuevo. Quitar una validación revoca sus certificados correspondientes. Una corrección que deja sin ningún intento aprobado la versión vigente de una prueba obligatoria retira la aprobación y revoca sus certificados de aprobación; queda historial y Dirección debe revisar cualquier asiento previo en el libro.

## Documentación de referencia

Se revisaron las copias del proyecto de **Reglamento Formación CADiSCA.pdf** y **Anexo para la virtualidad.pdf**. El reglamento atribuye funciones de certificación y listas de aprobados a las autoridades del curso; los artículos 52 y 53 distinguen la acreditación del Nivel I y el requisito para acceder al Nivel II. El anexo contempla tutoría, asistencia y recuperación. Esas obligaciones no se sustituyen con el porcentaje de lectura o la nota de un juego.

El seguimiento del traslado a libros responde al requerimiento institucional del proyecto. No se presenta como una regla nacional según la cual cualquier curso pasa a estar homologado con solo completar campos en una web. La selección de cursos homologables y su reconocimiento corresponde a las autoridades competentes.

## Operación y verificación

No requiere servicios nuevos: Django/PostgreSQL, disco privado existente y ReportLab para PDF. La migración 0003 agrega tablas y campos; no altera cursos, inscripciones ni resultados existentes. Los campos de configuración empiezan sin validaciones ni certificados emitidos.

Pruebas automatizadas cubren permisos, matrícula, CSRF, copias privadas, versiones, intentos, corrección en servidor, tipos de actividad, actas, emisión, revocación, privacidad, CSV y descarga PDF. La revisión visual usa exclusivamente personas y cursos ficticios. No se crean aprobaciones, certificados ni actas reales durante el despliegue.

Los cursos se abren en una pestaña nueva desde Mis cursos. Dentro de ellos la navegación continúa en la misma pestaña. La presentación en pantalla completa se ajusta al ancho y alto disponibles con un margen adicional del 10%, sin cambiar el zoom del navegador.
