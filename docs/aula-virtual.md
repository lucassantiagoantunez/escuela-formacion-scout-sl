# Aula Virtual EDiFoS: diagnóstico e integración

Revisión del 13 de septiembre de 2026. Repositorio: https://github.com/lucassantiagoantunez/escuela-formacion-scout-sl. Base revisada: `9e6cf21`; se consultó el remoto y coincidía con la copia local.

## Qué existe

| Área | Situación comprobada en el código |
|---|---|
| Stack | Python, Django 6.0.3, plantillas HTML, CSS y JavaScript propios; CKEditor 5 para edición institucional. |
| Estructura | `config` configura el proyecto; `core` contiene páginas, biblioteca, programas, noticias y seis tipos de juegos. Hay 33 migraciones previas. |
| Navegación | Plantilla `core/base.html` compartida y páginas adicionales administrables. Se agrega Aula antes de la ruta genérica por slug. |
| Backend | Django ya resuelve vistas, formularios, administración y persistencia. No hace falta otro frontend ni una API separada para esta etapa. |
| Base | SQLite por defecto, PostgreSQL mediante `DATABASE_URL`. No se inspeccionaron credenciales ni datos de producción. |
| Usuarios | Autenticación y sesiones Django existentes; el uso visible era principalmente administrativo. Se reutiliza el modelo de usuario sin migrarlo. |
| Archivos | `FileSystemStorage`, `media/` y servicio público de esos archivos incluso en producción. No es apropiado para entregas privadas. WhiteNoise sirve estáticos. |
| Despliegue | `build.sh` instala dependencias, recopila estáticos y ejecuta migraciones. Hay soporte del hostname de Render y dependencias Gunicorn/Uvicorn. El plan, comando de inicio, backups y variables reales de Render no están acreditados por el repositorio. |
| Limitaciones | Sin matrículas, autorización por curso ni historial académico previo. Las trivias públicas no son evaluaciones acreditables. DEBUG predeterminado verdadero; revisar configuración productiva. Los archivos locales requieren persistencia externa. |

## Arquitectura elegida

Monolito Django modular: nueva app `aula`, mismo dominio bajo `/aula/`, misma base y sesiones. Mantener `core` como web pública. Evita pagar y mantener otra aplicación, servicio de autenticación o frontend.

Dirección: inicialmente superusuarios activos, usando el administrador existente. Formadores: asignación por curso, sin convertirlos automáticamente en staff. Cursantes: matrícula activa y curso publicado. Ser staff por sí solo no concede acceso académico. Tutor: asignación interna en la matrícula; Dirección verifica acreditación y acuerdo institucional.

En producción, mantener el servicio web actual y usar PostgreSQL con copias verificadas. Para privados, incorporar un almacenamiento S3 compatible separado de la biblioteca pública: bucket privado, autorización de Django antes de cada descarga, URLs firmadas breves o respuesta autenticada, sin publicar `.url` directamente. No subir videos al disco del servidor.

| Alternativa | Uso y costo relativo |
|---|---|
| Django y autenticación existentes | Sin nuevo servicio ni costo de licencia. |
| Render actual + PostgreSQL persistente | Menos cambios operativos. Verificar plan y costo antes de contratar; no usar su Postgres gratuito para datos permanentes. |
| Cloudflare R2 privado | Capa gratuita Standard de 10 GB-mes, 1 millón de operaciones A y 10 millones B; egreso gratuito. Excedentes facturados. Requiere cuenta y configuración. |
| Disco persistente Render | Alternativa simple en un solo servidor; menos flexible para crecer a varias instancias. Solo servicios pagos. |
| Videos externos no listados | Reduce almacenamiento y transferencia del servidor. Un enlace no listado no garantiza confidencialidad; para contenidos sensibles, evaluar un proveedor con acceso restringido. |
| Correo SMTP institucional | Reutilizar si existe; después configurar recuperación de contraseña y notificaciones. No se ha confirmado proveedor. |

Fuentes de costos consultadas: [Render gratuito](https://render.com/docs/free), [precios Render](https://render.com/pricing), [precios R2](https://developers.cloudflare.com/r2/pricing/). Render gratuito no conserva archivos locales y su PostgreSQL gratuito expira a los 30 días. No se contrataron servicios.

## Fuentes institucionales y reglas

Se revisaron `sources/Reglamento Formación CADiSCA.pdf`, `sources/Anexo para la virtualidad.pdf` y el adjunto `Texto pegado.txt` de la conversación «Prompt aula virtual». La planificación del Nivel I 2026 no estaba disponible; no se inventan fechas, docentes ni cronograma.

- Reglamento, páginas 13–18: condiciones generales, trabajos y Nivel I presencial en su disposición general; artículo 49 exige 100% de participación para ese esquema.
- Anexo virtual, página 1: permite Nivel I virtual, exige disponibilidad para el 90% de encuentros, tutor Scouter/Maestro Scout con acuerdo del Jefe de Grupo, justificaciones y trabajos de recuperación evaluados por el formador responsable, con comunicación a Dirección. También pide pertenencia institucional, autorizaciones, edad correspondiente y cuenta Gmail. Estos requisitos no equivalen a autorizar automáticamente un curso exclusivamente asincrónico.
- Reglamento, página 28: cuatro bloques de Nivel I: generalidades, pastoral, organismos, CADISCA/ADISCA y reglamentación. Psicología Evolutiva pertenece al Nivel II (página 29), no se agrega como lección independiente del I.
- Decisión EDiFoS: asignar tutor internamente, organizar contenidos en módulos editables y mantener coherencia visual. La organización de ramas y secciones debe cruzarse también con los ejes del artículo 47 y la planificación cuando esté disponible.
- Funcionalidad adicional: progreso autodeclarado de lectura. Nunca equivale a asistencia, nota ni aprobación oficial. Las certificaciones futuras requerirán validación de Dirección y registro de los requisitos aplicables.

## Primera entrega implementada

Ingreso y salida con sesiones Django y CSRF; panel de cursos autorizados; cursos, matrículas con tutor, módulos y lecciones ordenables; texto escapado y enlace a video; publicación explícita; progreso persistente mediante POST y sin duplicados. Consultar una página no completa una lección. Administración de estructura e inscripciones y consulta de progreso desde Django Admin. Los borradores solo son visibles para Dirección y formadores asignados.

Esta es la primera etapa funcional, todavía no la primera versión utilizable completa del prompt. No incluye archivos privados, entregas, correcciones, consultas, cuestionarios, certificados, recuperación de contraseña ni panel de seguimiento del formador. El formador tiene en esta etapa acceso de lectura a sus cursos asignados.

## Siguientes bloques compatibles

### Gestión sencilla implementada

El acceso «Gestionar EDiFoS» abre `/aula/gestion/` para Dirección. Aparece en el menú de la web para superusuarios y también como acceso destacado en `/admin/`. No cambia las cuentas, cursos ni matrículas existentes.

Desde allí se puede crear o editar un curso; agregar o renombrar módulos; agregar o editar clases con texto y enlace HTTPS a video; elegir qué está publicado; crear una persona e inscribirla o asignarla como formador en una sola operación; agregar cuentas existentes sin duplicar matrículas; y consultar participantes y avance de lecturas. Las clases nuevas se añaden al final del módulo. Todavía no hay reordenamiento visual, gestión de tutores ni baja de participantes en este panel.

La creación de cuentas conserva los validadores y el cifrado de contraseñas de Django. Cuenta e inscripción se guardan juntas o se revierten juntas si falla una operación. No se conceden permisos administrativos desde estos formularios. Se registra quién realizó cada modificación en el historial de Django Admin sin guardar contraseñas en ese registro. Las invitaciones por correo aún no están implementadas; Dirección comparte el acceso de forma privada.

Noticias, biblioteca, páginas, programas y juegos tienen accesos organizados a sus editores existentes; sus formularios aún no han sido rediseñados. La simplificación completa de esos editores es una etapa posterior.

Validación de esta etapa: 30 pruebas automatizadas del conjunto del proyecto, incluidos permisos, CSRF, publicación, aislamiento de módulos por curso, duplicados y reversión de creación de cuentas. Revisión visual de vistas renderizadas con datos ficticios, incluida la pantalla de alta a 390 píxeles de ancho. No se requiere una nueva migración de base de datos.

### Desarrollo pendiente

1. Almacenamiento privado y recursos: validar formatos/tamaños, nombres aleatorios, descarga autorizada y conservación de archivos. Actividades con fechas y entregas versionadas; devoluciones y registro de cada cambio sin sobrescribir historial.
2. Consultas de tema y privadas; tablero del formador con autorización por curso. Roles editoriales explícitos antes de permitirle modificar contenido.
3. Evaluaciones separadas de las trivias públicas: intentos y respuestas en servidor, ventanas, límites, corrección automática y manual, resultados e historial.
4. Encuentros, asistencias, justificación, recuperación y tutorías; aprobación institucional independiente del progreso; certificados identificables y revocables.
5. Correo, recuperación, protección contra intentos de ingreso repetidos, monitoreo, backups y prueba de restauración. Activar HTTPS, cookies seguras y DEBUG=false en despliegue controlado.

## Operación y publicación

Usar Python 3.12 o superior compatible con Django 6 (validación realizada con Python 3.13). Instalar `requirements.txt`, ejecutar `python manage.py migrate` y `python manage.py createsuperuser` para una instalación nueva. Dirección crea usuarios en Usuarios, crea curso y módulos/lecciones en Aula, asigna formadores y matrículas y publica cuando corresponde. No se crean contraseñas predeterminadas ni datos de alumnos de ejemplo.

Antes de publicar: respaldar base actual, verificar PostgreSQL y configuración de producción, ejecutar pruebas, aplicar migraciones, recopilar estáticos y comprobar `/`, `/biblioteca/`, `/juegos/`, `/admin/` y `/aula/`. No se cambió la configuración del servicio Render ni se desplegó en esta etapa.
