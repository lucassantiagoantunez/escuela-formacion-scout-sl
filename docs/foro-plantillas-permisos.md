# Foro, plantillas y permisos por curso

## Foro

Cada curso y taller del Aula tiene la opción **Foro** junto a Cursar y Mi avance. Los cursantes con inscripción activa y el equipo asignado pueden leer sus consultas. Los contenidos no se publican fuera del curso. No se envían correos ni avisos externos.

Se pueden abrir consultas, responder, buscar por asunto o texto y recorrer páginas de 20 temas o respuestas. El autor puede marcar su consulta resuelta o pendiente. Una nueva respuesta vuelve a dejarla pendiente. Los moderadores pueden cerrar respuestas, ocultar y restaurar consultas o respuestas. Se conserva lo ocultado y se registra quién moderó. Los mensajes se muestran como texto, sin ejecutar HTML.

## Diseñar certificados

En **Seguimiento y resultados**, elegir **Diseñar certificado de participación** o **Diseñar certificado de aprobación**. Se configura cada tipo por separado para cada curso.

- Subir un fondo PDF de una página o imagen JPG/PNG, hasta 10 MB. Las imágenes admiten hasta 25 megapíxeles. El PDF no puede tener contraseña. Se recomienda formato A4 apaisado; otros tamaños se ajustan conservando proporciones.
- Editar encabezado, texto libre, color y letra. Arrastrar los campos o ajustar izquierda, arriba, ancho, alto y tamaño de letra desde los controles. Los datos personales, curso, fechas, autoridad y acta se completan al emitir; sus valores provienen del cierre y la configuración del curso.
- Guardar y abrir **Ejemplo PDF del diseño guardado** para revisar el resultado exacto. La vista de trabajo es una ayuda de ubicación; el PDF ajusta textos largos al recuadro. El ejemplo lleva la leyenda SIN VALIDEZ y no crea una emisión.
- El 13% inferior queda reservado para identificación y verificación. Los campos configurables deben terminar antes del 86% de alto. Este espacio no se reemplaza con el fondo ni puede borrarse en el editor.
- Desmarcar **Usar este diseño** para que las próximas emisiones utilicen el diseño estándar. Las plantillas son fondos, no documentos Word editables; los textos ya dibujados en una imagen o PDF se modifican en su archivo original.

Cada emisión conserva su configuración y la referencia a un archivo de fondo único e inmutable. Al reemplazar/quitar un fondo no se borra el anterior: puede respaldar certificados ya emitidos. Los archivos se guardan en el disco privado existente y se sirven solo a usuarios autorizados para diseñar. Cambiar una plantilla no cambia certificados previos. Para corregir un certificado ya emitido, revocarlo con motivo y emitirlo nuevamente.

## Permisos de formadores

Dirección los configura en **Admin → Aula → Permisos de formadores por curso**. Primero asignar a la persona como formador del curso. Agregar un registro con curso y formador y marcar las tareas habilitadas. No necesita ser staff ni superusuario para realizar las tareas delegadas desde el Aula.

| Permiso | Alcance |
|---|---|
| Participar en el foro | Abrir consultas y responder |
| Moderar el foro | Cerrar, ocultar, restaurar y resolver consultas |
| Ver seguimiento | Consultar resultados y estado académico del curso |
| Corregir evaluaciones | Ver las entregas y registrar notas/devoluciones |
| Validar aprobación y registrar actas | Ver cursantes y validar requisitos y referencias institucionales |
| Emitir, descargar y revocar certificados | Ver cursantes y emitir solo después de las validaciones exigidas |
| Editar plantillas | Diseñar los dos tipos de certificado y abrir ejemplos |

Los permisos para corregir, validar y emitir incluyen la información necesaria para esas tareas. Tener solo permiso de diseño no da acceso a datos personales del seguimiento. Emitir **no** concede permiso para validar, editar plantillas ni cambiar reglas institucionales. Las comprobaciones se hacen en el servidor, además de ocultar controles en pantalla. La asignación a otro curso no hereda estas facultades.

Sin un registro específico se conserva el rol básico anterior: lectura del curso, participación en el foro, seguimiento y corrección. Emisión, validación, moderación y diseño permanecen deshabilitados. Para reducir también los permisos básicos, crear el registro y desmarcarlos. Al quitar la asignación como formador, los permisos dejan de aplicar incluso si el registro todavía existe. Solo Dirección puede modificar esta tabla de permisos; ningún formador puede concedérselos a sí mismo.

La edición de cursos/clases, las altas de usuarios y la configuración de reglas de certificación siguen a cargo de Dirección. El sistema no concede nuevos permisos a personas reales durante el despliegue.

## Verificación

La migración 0004 agrega tablas; no cambia inscripciones, certificados ni permisos existentes. Las pruebas cubren aislamiento entre cursos, matrícula pausada, CSRF, texto escapado, moderación sin borrado, paginación, permisos independientes, prohibición de autoasignación, fondos privados, validación de plantillas, ejemplos sin emisión y conservación del diseño de certificados anteriores. Se revisan el foro, el editor visual y PDFs generados exclusivamente con datos ficticios.
