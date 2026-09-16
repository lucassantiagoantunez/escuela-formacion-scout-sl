document.querySelectorAll('[data-editor-clase]').forEach(form => {
  let enviando = false;
  let cambiado = false;
  form.addEventListener('input', () => { cambiado = true; });
  form.addEventListener('change', () => { cambiado = true; });
  window.addEventListener('beforeunload', event => {
    if (cambiado && !enviando) { event.preventDefault(); event.returnValue = ''; }
  });
  form.addEventListener('submit', event => {
    if (enviando) { event.preventDefault(); return; }
    enviando = true;
    form.querySelector('[data-estado-guardado]').textContent = 'Guardando la clase y preparando los archivos. Esperá sin cerrar esta página.';
  });
  window.addEventListener('pageshow', () => { enviando = false; });
});
