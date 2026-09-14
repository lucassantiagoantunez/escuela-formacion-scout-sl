document.querySelectorAll('[data-editor-clase]').forEach(form => {
  let enviando = false;
  form.addEventListener('submit', event => {
    if (enviando) { event.preventDefault(); return; }
    enviando = true;
    form.querySelector('[data-estado-guardado]').textContent = 'Guardando la clase y preparando los archivos. Esperá sin cerrar esta página.';
  });
  window.addEventListener('pageshow', () => { enviando = false; });
});
