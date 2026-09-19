(() => {
  const form = document.getElementById('simplificar-accesos');
  if (!form) return;
  const estado = document.getElementById('estado-accesos');
  const resultado = document.getElementById('resultado-accesos');
  const titulo = document.getElementById('titulo-resultados');
  const cuerpo = document.querySelector('#credenciales tbody');
  const boton = form.querySelector('button');
  let lote = 0, procesando = false, solicitud = null, cantidad = 0;
  window.addEventListener('beforeunload', event => {
    if (solicitud) { event.preventDefault(); event.returnValue = ''; }
  });
  form.addEventListener('submit', async event => {
    event.preventDefault();
    if (procesando || !form.reportValidity()) return;
    if (!solicitud) solicitud = new FormData(form);
    procesando = true;
    boton.disabled = true;
    form.querySelectorAll('input').forEach(input => input.disabled = true);
    estado.textContent = `Procesando… ${cantidad} cuentas confirmadas. No cierres esta pestaña.`;
    try {
      let terminado = false;
      while (!terminado) {
        solicitud.set('lote', String(lote));
        const respuesta = await fetch(form.action, {
          method: 'POST', body: solicitud, credentials: 'same-origin',
          headers: {'X-Requested-With': 'XMLHttpRequest'},
        });
        if (respuesta.redirected || !respuesta.headers.get('Content-Type')?.includes('application/json')) {
          throw new Error('El servidor no confirmó el último grupo. Podés reintentar con el botón de abajo.');
        }
        const datos = await respuesta.json();
        if (!respuesta.ok) {
          const mensajes = Object.values(datos.errores || {}).flat().map(error => error.message).join(' ');
          throw new Error(mensajes || 'No se pudo confirmar el último grupo.');
        }
        for (const persona of datos.resultados) {
          const fila = document.createElement('tr');
          for (const campo of ['nombre', 'usuario', 'email', 'rol', 'clave']) {
            const celda = document.createElement('td');
            celda.textContent = persona[campo];
            fila.append(celda);
          }
          cuerpo.append(fila);
        }
        cantidad = datos.completadas;
        resultado.hidden = false;
        titulo.textContent = `Accesos actualizados · ${cantidad} de ${datos.total} cuentas`;
        estado.textContent = `${cantidad} de ${datos.total} cuentas confirmadas. No cierres esta pestaña.`;
        lote += 1;
        terminado = datos.terminado;
      }
      solicitud = null;
      form.reset();
      form.hidden = true;
      estado.textContent = `Listo: se actualizaron las ${cantidad} cuentas. Se conservaron sus permisos e inscripciones.`;
      resultado.scrollIntoView({behavior: 'smooth', block: 'start'});
    } catch (error) {
      estado.textContent = `Se detuvo el proceso; ${cantidad} cuentas confirmadas. ${error.message || 'Revisá tu conexión y reintentá.'}`;
      boton.disabled = false;
      boton.textContent = 'Reintentar el grupo pendiente';
      if (cantidad === 0) {
        solicitud = null;
        form.querySelectorAll('input').forEach(input => input.disabled = false);
      }
    } finally {
      procesando = false;
    }
  });
})();
