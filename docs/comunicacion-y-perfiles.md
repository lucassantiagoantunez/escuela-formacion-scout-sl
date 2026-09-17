# Comunicación y perfiles privados

## Acceso de Comunicación

Grupo `Comunicación · Noticias y biblioteca`: nueve permisos, únicamente ver, agregar y cambiar Noticias, Materiales y Categorías de biblioteca. Requiere cuenta activa y staff; nunca superusuario. Acceso desde `/aula/comunicacion/` o el administrador. Puede publicar, destacar y retirar de publicación; no tiene borrado definitivo. Relaciones de materiales con programas y áreas quedan de solo lectura.

El grupo no habilita usuarios, grupos, código de componentes, páginas, inicio institucional, juegos, resultados, propuestas con datos de contacto, cursos, aprobaciones, certificados, actas ni perfiles privados. Los permisos académicos ya existentes son independientes y deben revisarse al incorporar a alguien al equipo de Comunicación. La migración crea el grupo sin asignarlo a ninguna persona.

## Revisión aplicada

- Se corrigió `has_delete_permission` de resultados, que devolvía `True` sin comprobar permisos.
- El administrador de componentes con HTML/CSS/JavaScript queda reservado a superusuarios, también ante pedidos directos.
- Los textos enriquecidos públicos se filtran al mostrar; las noticias se filtran también al guardar desde el administrador. Los componentes programables, restringidos a Dirección, mantienen su funcionalidad.
- Biblioteca restringe nuevas cargas por extensión y tamaño (20 MB). El contenido público subido tiene `nosniff`, CSP sandbox y descarga forzada excepto imágenes, para que no ejecute código en el origen de la web.
- La carga de imágenes del editor verifica cuenta activa, staff y permiso de noticias, extensión, tamaño y validación de imagen del editor.
- Cookies de sesión y CSRF solo por HTTPS en producción; sesión HttpOnly.
- Django actualizado de 6.0.3 a 6.0.8, con las [correcciones oficiales de seguridad](https://www.djangoproject.com/weblog/2026/aug/04/security-releases/).

Es una revisión del acceso editorial, perfiles y rutas relacionadas, no una auditoría de penetración integral. No se ha auditado el acceso externo a GitHub, Render o las cuentas personales; una cuenta editorial no concede esos accesos. Las cargas documentales no incluyen análisis antivirus. Ver [recomendaciones de Django sobre contenido subido](https://docs.djangoproject.com/en/6.0/topics/security/).

## Mi perfil

Ruta `/aula/mi-perfil/`, visible desde el panel y el curso. Nombre y apellido requeridos; correo y todos los campos adicionales opcionales. Campos basados en `Ficha de Inscripción - NI2026Rev.1.docx.pdf`: DNI, fecha de nacimiento (edad calculada), dirección, localidad, código postal, teléfono, estado civil, cantidad de hijos, profesión/trabajo, asociación, grupo, fechas de ingreso al grupo y al movimiento, sacramentos, fecha de promesa y cargo.

Datos declarados por la persona, sin validación automática de identidad. No se digitalizan firmas o autorizaciones de autoridades mediante campos autocompletables. No se alteran actas ni certificados existentes al cambiar el perfil. Fecha de actualización automática, sin presentarla como fecha oficial de inscripción.

Solo el titular puede editar su perfil; no se recibe un identificador de usuario elegible. Formularios con campos explícitos, CSRF, validación de fechas y DNI. Las vistas privadas no se almacenan en caché. Los registros de cambios contienen nombres de campos, no DNI, sacramentos ni valores anteriores. Dirección puede consultar los perfiles desde el administrador y la ficha del cursante. Formadores y Comunicación no acceden a esos datos privados, ni aunque alguien les asigne por error el permiso de ver perfiles. Nombre y apellido continúan visibles para identificar las participaciones del usuario.

## Comprobaciones

Pruebas de publicación editorial, denegación de borrado y acceso directo, aislamiento de perfiles, intento de cambiar permisos por POST, CSRF, validación, filtrado HTML, descarga de archivos, preservación de certificados y actas. El grupo se prueba con usuarios ficticios; las pruebas no alteran cuentas ni documentos reales.
