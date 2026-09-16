# Paneles y navegación del Aula

La entrada `/aula/` muestra el trabajo del equipo para Dirección y formadores, y los cursos propios para cursantes. Quien integra el equipo puede consultar sus inscripciones en `?vista=formacion`. Los accesos desde la web institucional abren el Aula en otra pestaña; el encabezado del Aula permite regresar a la web.

Gestión del curso usa secciones independientes: resumen, contenido, personas, configuración y papelera. Contenido pagina los módulos y abre solo las clases del módulo elegido. Cada módulo ofrece Agregar clase y Agregar prueba. La búsqueda encuentra clases por título o módulo; las clases tienen filtros de publicación y prueba. Personas separa cursantes y formadores y pagina los resultados.

Evaluaciones, cierre y certificados son vistas independientes del registro, con búsqueda y paginación. La ficha del cursante reúne requisitos, certificados e historial. El cierre explica impedimentos antes de guardar, agrupa requisitos y acta, y permite guardar y revisar el siguiente cursante. La corrección permite avanzar a la siguiente entrega pendiente. Las validaciones de aprobación y emisión siguen ejecutándose en el servidor; ningún contador o porcentaje aprueba automáticamente un curso.

El porcentaje del panel es avance de lecturas obligatorias publicadas y no eliminadas. Las pruebas se cuentan por aprobación en su revisión vigente. El estado histórico del cierre se muestra separado de los pendientes del programa actual. Este cambio no congela versiones de programa ni reinterpreta cierres anteriores.

Los indicadores del equipo respetan los permisos por curso. El contador del foro cuenta consultas abiertas, no resueltas ni ocultas, que aún no tienen respuesta visible del equipo. No equivale a mensajes no leídos.

Dirección puede reordenar clases, duplicar una clase de contenido como borrador y editar inscripción/tutor desde la ficha. La copia reutiliza archivos privados inmutables y no copia progreso, intentos ni resultados. Las pruebas conservan su editor independiente. Dar tutoría no otorga permisos de formador.

Las pantallas se adaptan a celular con selector de sección y listas acotadas. El selector es una mejora progresiva: sin JavaScript permanecen los enlaces. Los guardados del editor ofrecen continuar editando y aviso al salir con cambios sin guardar.

Comprobación: suite completa de 111 pruebas; revisión visual local con datos ficticios en computadora y celular. Se mantiene el alojamiento existente y no se requieren migraciones de datos. Versionado de cohortes y operaciones académicas por lote quedan fuera de esta entrega de navegación.
