document.querySelectorAll('.panel-menu').forEach(nav => {
  const label = document.createElement('label');
  label.className = 'panel-selector';
  label.append('Sección del curso');
  const select = document.createElement('select');
  const initial = document.createElement('option');
  initial.value = ''; initial.textContent = 'Elegir sección…';
  select.append(initial);
  nav.querySelectorAll('a').forEach(link => {
    const option = document.createElement('option');
    option.value = link.href; option.textContent = link.textContent;
    option.selected = link.getAttribute('aria-current') === 'page';
    select.append(option);
  });
  select.addEventListener('change', () => { if (select.value) window.location.assign(select.value); });
  label.append(select); nav.prepend(label); nav.classList.add('con-selector');
});
