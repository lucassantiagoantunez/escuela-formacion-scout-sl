# Clases con documentos, videos y texto

## Experiencia de cursado

El curso abre con un índice lateral de módulos desplegables y una clase por pantalla. El índice incluye búsqueda por nombre y marca las lecturas completadas. **Anterior** y **Siguiente** cambian de clase sin modificar el progreso; **Marcar como completada y continuar** registra la lectura y abre la siguiente clase publicada. Al terminar, muestra **Mi avance**. Volver al curso sin elegir una clase abre la primera lectura pendiente.

**Mi avance** muestra el progreso de lecturas obligatorias por módulo. No equivale a una calificación: la herramienta de evaluaciones y notas aún no está implementada. **Documentos y materiales** reúne los archivos visibles para cada participante. En celular, **Índice** abre la navegación; **Texto grande** amplía el texto de la clase.

## Preparar una clase

Desde **Gestionar EDiFoS → curso → módulo → Agregar clase**:

- Escribir y pegar texto; usar títulos, listas, colores, tamaños, citas y tablas.
- Pegar un enlace de YouTube para verlo dentro de la clase. El autor debe permitir la reproducción insertada.
- Elegir PDF, Word, PowerPoint, imágenes o videos propios en **Documentos, videos e imágenes**.
- Guardar como borrador para revisar desde **Ver la clase guardada** antes de mostrarla a cursantes.
- Al editar se pueden agregar más archivos. **Quitar de la clase** oculta el recurso y revoca su descarga, conservándolo en almacenamiento.

Documentos e imágenes: 20 MB cada uno; videos MP4/WebM: 150 MB; hasta 5 archivos y 180 MB por guardado. Incluir un solo Word o PowerPoint por guardado para no acumular conversiones. Para muchos videos, YouTube ahorra espacio; el almacenamiento actual del servicio es de 5 GB y también contiene otros materiales de la web. El codec del video debe ser compatible con el navegador; MP4 con H.264/AAC es una opción habitual.

El visor ofrece páginas/diapositivas, tamaño, pantalla completa, texto accesible y descarga del original. Word y PowerPoint se convierten a PDF en el propio servidor. La vista no conserva animaciones ni videos internos y puede variar si faltan fuentes. No se envían los documentos a visores de terceros.

## Operación técnica

- Django mantiene los originales y vistas en `MEDIA_ROOT/.aula_privada`, dentro del disco persistente de Render. `AULA_PRIVATE_ROOT` permite cambiar la ruta; debe permanecer en almacenamiento persistente.
- Todos los accesos pasan por rutas autenticadas que comprueban inscripción activa, publicación y rol. `/media/` bloquea esa carpeta. No configurar un servidor estático público sobre toda la carpeta media sin mantener la misma exclusión.
- `build.sh` prepara LibreOffice solo en Render, usando paquetes firmados de Debian extraídos en `.office`. El instalador adapta rutas y registro sin privilegios, y comprueba conversiones DOCX/PPTX antes de completar el build. No escribe en el disco de materiales.
- `AULA_OFFICE_EXECUTABLE` permite seleccionar otro ejecutable. El proceso se limita a 22 segundos y a una conversión concurrente por servidor; si está ocupado, el formulario informa que se debe reintentar. Un error no guarda parcialmente la clase.
- Se validan extensión, contenido básico, tamaño y límites de PDF/ZIP. Se rechazan macros OOXML y objetos incrustados. El perfil de conversión deshabilita macros y actualizaciones de vínculos. Esto no constituye un antivirus.
- PDF.js 6.3.289 se sirve localmente, con su licencia y recursos. El HTML del editor se limpia con nh3 al guardar y mostrar. El texto anterior se conserva escapado.
- Al migrar a varios servidores, reemplazar disco local por almacenamiento de objetos privado y pasar conversión a una cola de trabajos. Respaldar tanto PostgreSQL como el directorio privado; uno sin el otro no permite recuperar materiales completos.

Pruebas: `python manage.py test`, `python manage.py makemigrations --check --dry-run`, `python manage.py collectstatic --noinput`. Los documentos de `aula/fixtures_multimedia` son sintéticos y se usan en la comprobación del conversor durante build.
