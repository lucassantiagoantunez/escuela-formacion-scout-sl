# Eliminar y recuperar clases

Dirección puede elegir **Eliminar clase** desde el módulo o desde la edición de la clase. Una pantalla muestra cuál se quitará y explica el alcance. **Mover a la papelera** la retira del índice, sus materiales y los requisitos pendientes del curso. No borra físicamente archivos, lecturas, pruebas ni resultados.

La papelera está en la gestión del curso. **Recuperar como borrador** devuelve la clase al módulo original, conservando los registros; hay que revisarla y publicarla de nuevo. Las rutas requieren Dirección, validan el curso y protegen los cambios con POST y CSRF. No se ofrece borrado irreversible.

La migración 0005 agrega un indicador con valor falso para todas las clases existentes. Las emisiones previas de certificados se conservan.
