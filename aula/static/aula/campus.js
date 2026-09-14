const campus = document.querySelector('.campus');
const toggle = document.querySelector('#alternar-indice');
function indice(visible) {
  campus.classList.toggle('campus-sin-indice', !visible);
  toggle.setAttribute('aria-expanded', String(visible));
}
indice(!window.matchMedia('(max-width:800px)').matches);
toggle.addEventListener('click', () => {
  const visible = toggle.getAttribute('aria-expanded') !== 'true';
  indice(visible);
  if (visible) document.querySelector('#buscar-clase').focus();
});
document.querySelector('#tamano-texto').addEventListener('click', event => {
  const grande = campus.classList.toggle('campus-texto-grande');
  event.currentTarget.setAttribute('aria-pressed', String(grande));
});
const normalizar = value => value.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().trim();
const modulos = [...document.querySelectorAll('[data-modulo]')];
const abiertos = modulos.map(modulo => modulo.open);
document.querySelector('#buscar-clase').addEventListener('input', event => {
  const busqueda = normalizar(event.target.value);
  let encontrados = 0;
  modulos.forEach((modulo, index) => {
    const coincideModulo = normalizar(modulo.dataset.nombre).includes(busqueda);
    const clases = [...modulo.querySelectorAll('[data-clase]')];
    clases.forEach(clase => { clase.hidden = !coincideModulo && !normalizar(clase.dataset.nombre).includes(busqueda); });
    modulo.hidden = !coincideModulo && !clases.some(clase => !clase.hidden);
    modulo.open = busqueda ? !modulo.hidden : abiertos[index];
    if (!modulo.hidden) encontrados++;
  });
  document.querySelector('.campus-sin-resultados').hidden = !busqueda || encontrados > 0;
});
