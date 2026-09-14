document.querySelectorAll('[data-puzzle]').forEach(tablero=>{
  let seleccion=null;
  const actualizar=()=>{document.querySelector('#orden-piezas').value=[...tablero.children].map(p=>p.dataset.pieza).join(',');[...tablero.children].forEach((p,i)=>p.setAttribute('aria-label',`Pieza en posición ${i+1}`));};
  tablero.addEventListener('click',event=>{
    const pieza=event.target.closest('[data-pieza]');if(!pieza)return;
    if(seleccion&&seleccion!==pieza){const marcador=document.createElement('span');seleccion.replaceWith(marcador);pieza.replaceWith(seleccion);marcador.replaceWith(pieza);seleccion.setAttribute('aria-pressed','false');seleccion=null;actualizar();}
    else{if(seleccion)seleccion.setAttribute('aria-pressed','false');seleccion=seleccion===pieza?null:pieza;if(seleccion)seleccion.setAttribute('aria-pressed','true');}
  });actualizar();
});
