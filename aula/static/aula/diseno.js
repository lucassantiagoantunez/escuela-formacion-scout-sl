import * as pdfjs from './pdfjs/pdf.mjs';
pdfjs.GlobalWorkerOptions.workerSrc=new URL('./pdfjs/pdf.worker.mjs',import.meta.url).href;
const form=document.querySelector('#form-diseno'),lienzo=document.querySelector('#diseno-lienzo'),canvas=document.querySelector('#diseno-fondo'),estado=document.querySelector('#diseno-estado');
const controles=(key,prop)=>form.elements.namedItem(`${key}_${prop}`),lista=document.querySelector('#textos-propios');
let extras=[];try{extras=JSON.parse(form.elements.extras.value||'[]');if(!Array.isArray(extras))extras=[];}catch{}
const historial=[],numericos=['x','y','ancho','alto','tamano'];
const extra=key=>key.startsWith('extra')?extras[Number(key.slice(5))]:null;
function valor(key,prop){const item=extra(key);if(item)return item[prop];const input=controles(key,prop);return input.type==='checkbox'?input.checked:input.value;}
function poner(key,prop,v){const item=extra(key);if(item)item[prop]=v;const input=controles(key,prop);if(input){if(input.type==='checkbox')input.checked=!!v;else input.value=v;}}
function recordar(){const valores={};for(const el of form.elements)if(el.name&&el.type!=='file'&&el.name!=='csrfmiddlewaretoken')valores[el.name]=el.type==='checkbox'?el.checked:el.value;
  const foto=JSON.stringify({valores,extras});if(historial.at(-1)!==foto){historial.push(foto);if(historial.length>30)historial.shift();}}
function actualizar(){
  form.elements.extras.value=JSON.stringify(extras);
  lienzo.querySelector('.diseno-pie').hidden=form.elements.pie.value==='pagina';
  for(const caja of lienzo.querySelectorAll('[data-key]')){
    const key=caja.dataset.key;caja.hidden=!valor(key,'visible');
    caja.style.left=valor(key,'x')+'%';caja.style.top=valor(key,'y')+'%';
    caja.style.width=valor(key,'ancho')+'%';caja.style.height=valor(key,'alto')+'%';
    caja.style.fontSize=(Number(valor(key,'tamano'))/841.89*100)+'cqw';
    caja.style.color=valor(key,'color')||form.elements.color.value;
    caja.style.fontWeight=valor(key,'negrita')?'bold':'normal';
    caja.style.textAlign={centro:'center',izquierda:'left',derecha:'right'}[valor(key,'alineacion')]||'center';
    caja.style.fontFamily={'Helvetica':'Arial,sans-serif','Times-Roman':'Times New Roman,serif','Courier':'Courier New,monospace'}[form.elements.fuente.value];
    const texto=caja.querySelector('.diseno-texto');
    if(extra(key))texto.textContent=extra(key).texto;
    else if(key==='encabezado'||key==='libre')texto.textContent=form.elements.namedItem(key).value;
    if(!caja.hidden){let size=Number(valor(key,'tamano'));for(let i=0;i<30&&texto.scrollHeight>caja.clientHeight;i++){size*=.95;caja.style.fontSize=(size/841.89*100)+'cqw';}}
  }
}
function seleccionar(caja){lienzo.querySelectorAll('.seleccionado').forEach(el=>el.classList.remove('seleccionado'));caja.classList.add('seleccionado');const panel=form.querySelector(`[data-control="${caja.dataset.key}"]`);if(panel)panel.open=true;}
function conectar(caja){
  let inicio;const key=caja.dataset.key;
  caja.querySelector('.quitar-campo').addEventListener('click',()=>{recordar();poner(key,'visible',false);actualizar();});
  caja.addEventListener('pointerdown',e=>{if(e.button!==0||e.target.closest('button'))return;recordar();seleccionar(caja);
    inicio={x:e.clientX,y:e.clientY,ix:Number(valor(key,'x')),iy:Number(valor(key,'y')),w:Number(valor(key,'ancho')),h:Number(valor(key,'alto')),resize:e.target.classList.contains('redimensionar')};caja.setPointerCapture(e.pointerId);});
  caja.addEventListener('pointermove',e=>{if(!inicio)return;const r=lienzo.getBoundingClientRect(),dx=(e.clientX-inicio.x)/r.width*100,dy=(e.clientY-inicio.y)/r.height*100,limite=form.elements.pie.value==='pagina'?100:86;
    if(inicio.resize){poner(key,'ancho',Math.max(1,Math.min(100-inicio.ix,inicio.w+dx)).toFixed(1));poner(key,'alto',Math.max(1,Math.min(limite-inicio.iy,inicio.h+dy)).toFixed(1));}
    else{poner(key,'x',Math.max(0,Math.min(100-inicio.w,inicio.ix+dx)).toFixed(1));poner(key,'y',Math.max(0,Math.min(limite-inicio.h,inicio.iy+dy)).toFixed(1));}actualizar();});
  for(const nombre of ['pointerup','pointercancel'])caja.addEventListener(nombre,()=>{inicio=null;});
  caja.addEventListener('keydown',e=>{if(e.target!==caja)return;if(['Delete','Backspace'].includes(e.key)){e.preventDefault();recordar();poner(key,'visible',false);actualizar();}
    if(['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(e.key)){e.preventDefault();recordar();const p=e.key.includes('Left')||e.key.includes('Right')?'x':'y',sign=e.key==='ArrowLeft'||e.key==='ArrowUp'?-1:1,limite=p==='x'?100:form.elements.pie.value==='pagina'?100:86;
      poner(key,p,Math.max(0,Math.min(limite-Number(valor(key,p==='x'?'ancho':'alto')),Number(valor(key,p))+sign*(e.shiftKey?1:.1))).toFixed(1));actualizar();}});
}
function construirExtras(){
  lista.replaceChildren();lienzo.querySelectorAll('[data-extra]').forEach(el=>el.remove());
  extras.forEach((item,i)=>{const key='extra'+i,details=document.createElement('details');details.dataset.control=key;const summary=document.createElement('summary');summary.textContent='Texto propio '+(i+1);details.append(summary);
    for(const [prop,label,tipo] of [['texto','Contenido','textarea'],['visible','Mostrar este texto','checkbox'],['x','Desde la izquierda (%)','number'],['y','Desde arriba (%)','number'],['ancho','Ancho (%)','number'],['alto','Alto (%)','number'],['tamano','Tamaño de letra','number'],['color','Color','color'],['alineacion','Alineación','select'],['negrita','Negrita','checkbox']]){
      const p=document.createElement('p'),etiqueta=document.createElement('label'),input=document.createElement(tipo==='textarea'?'textarea':tipo==='select'?'select':'input');input.name=key+'_'+prop;input.id=input.name;etiqueta.htmlFor=input.id;etiqueta.textContent=label;
      if(tipo==='select')for(const [v,t] of [['centro','Centrado'],['izquierda','Izquierda'],['derecha','Derecha']]){const opt=document.createElement('option');opt.value=v;opt.textContent=t;input.append(opt);}
      else if(tipo!=='textarea')input.type=tipo;
      if(tipo==='number'){input.step='0.1';input.min=prop==='tamano'?6:['ancho','alto'].includes(prop)?1:0;input.max=prop==='tamano'?96:100;}
      if(tipo==='textarea'){input.maxLength=1500;input.rows=3;}
      if(tipo==='checkbox')input.checked=item[prop]!==false;else input.value=item[prop];
      input.addEventListener('input',()=>{item[prop]=tipo==='checkbox'?input.checked:numericos.includes(prop)?Number(input.value):input.value;});p.append(etiqueta,input);details.append(p);
    }
    lista.append(details);const caja=document.createElement('div');caja.className='diseno-campo';caja.dataset.key=key;caja.dataset.extra='1';caja.tabIndex=0;caja.setAttribute('aria-label','Mover texto propio '+(i+1));const texto=document.createElement('span');texto.className='diseno-texto';const quitar=document.createElement('button');quitar.type='button';quitar.className='quitar-campo';quitar.textContent='×';quitar.setAttribute('aria-label','Quitar texto propio '+(i+1));const resize=document.createElement('span');resize.className='redimensionar';resize.title='Cambiar tamaño del recuadro';caja.append(texto,quitar,resize);lienzo.append(caja);conectar(caja);
  });
}
form.addEventListener('focusin',recordar);form.addEventListener('input',actualizar);
form.addEventListener('submit',()=>{form.elements.extras.value=JSON.stringify(extras);});
document.querySelector('#agregar-texto').addEventListener('click',()=>{if(extras.length>=20){estado.textContent='Podés agregar hasta 20 textos propios. Recuperá o editá uno de los existentes.';return;}recordar();extras.push({texto:'Escribí tu texto',visible:true,x:15,y:52,ancho:70,alto:8,tamano:16,color:form.elements.color.value,alineacion:'centro',negrita:false});construirExtras();actualizar();seleccionar(lienzo.querySelector(`[data-key="extra${extras.length-1}"]`));});
document.querySelector('#diseno-deshacer').addEventListener('click',()=>{if(!historial.length)return;const foto=JSON.parse(historial.pop());extras=foto.extras;for(const [name,v] of Object.entries(foto.valores)){const el=form.elements.namedItem(name);if(el){if(el.type==='checkbox')el.checked=v;else el.value=v;}}construirExtras();actualizar();});
document.querySelector('#diseno-limpiar').addEventListener('click',()=>{recordar();form.elements.pie.value='pagina';form.elements.fuente.value='Times-Roman';
  const posiciones={tipo:[28,6,20],libre:[34,4,14],nombre:[38,5,25],curso:[49,7,22],periodo:[60,6,12]};
  for(const caja of lienzo.querySelectorAll('[data-key]:not([data-extra])')){const key=caja.dataset.key;poner(key,'visible',!!posiciones[key]);if(posiciones[key]){const [y,alto,tamano]=posiciones[key];for(const [p,v] of Object.entries({x:22,y,ancho:56,alto,tamano,color:'#143c2b',alineacion:'centro'}))poner(key,p,v);}}
  actualizar();estado.textContent='Se quitaron encabezado, autoridad y acta del diploma. Las firmas del fondo quedan libres. Podés ajustar o deshacer esta distribución.';});
document.querySelector('#color-todos').addEventListener('click',()=>{recordar();for(const caja of lienzo.querySelectorAll('[data-key]'))poner(caja.dataset.key,'color',form.elements.color.value);actualizar();});
document.querySelector('#diseno-guias').addEventListener('change',e=>lienzo.classList.toggle('sin-guias',!e.target.checked));
document.querySelector('#diseno-ampliar').addEventListener('click',e=>{const activa=document.body.classList.toggle('editor-ampliado');e.target.textContent=activa?'Salir del editor ampliado':'Ampliar editor';actualizar();});
document.addEventListener('keydown',e=>{if(e.key==='Escape'){document.body.classList.remove('editor-ampliado');document.querySelector('#diseno-ampliar').textContent='Ampliar editor';actualizar();}});
for(const caja of lienzo.querySelectorAll('[data-key]'))conectar(caja);construirExtras();actualizar();
new ResizeObserver(actualizar).observe(lienzo);
async function fondo(origen,pdf){
  canvas.width=1200;canvas.height=Math.round(1200*595.28/841.89);const ctx=canvas.getContext('2d');ctx.clearRect(0,0,canvas.width,canvas.height);
  if(!origen)return;
  try{
    if(pdf){const doc=await pdfjs.getDocument(typeof origen==='string'?{url:origen,isEvalSupported:false}:{data:origen,isEvalSupported:false}).promise;
      try{const page=await doc.getPage(1),base=page.getViewport({scale:1}),scale=Math.min(canvas.width/base.width,canvas.height/base.height),viewport=page.getViewport({scale});
        await page.render({canvasContext:ctx,viewport,transform:[1,0,0,1,(canvas.width-viewport.width)/2,(canvas.height-viewport.height)/2]}).promise;
      }finally{await doc.destroy();}
    }else{const img=new Image();img.src=origen;await img.decode();const scale=Math.min(canvas.width/img.width,canvas.height/img.height);ctx.drawImage(img,(canvas.width-img.width*scale)/2,(canvas.height-img.height*scale)/2,img.width*scale,img.height*scale);}
    estado.textContent='';
  }catch{estado.textContent='No se pudo dibujar el fondo aquí. Revisá el archivo o abrí el ejemplo PDF después de guardar.';}
}
if(lienzo.dataset.fondo)fondo(lienzo.dataset.fondo,lienzo.dataset.pdf==='1');
form.elements.fondo.addEventListener('change',async()=>{const file=form.elements.fondo.files[0];if(!file)return;
  form.elements.quitar_fondo.checked=false;
  if(file.size>10*1024*1024){estado.textContent='La plantilla admite hasta 10 MB.';return;}
  if(file.name.toLowerCase().endsWith('.pdf'))await fondo(new Uint8Array(await file.arrayBuffer()),true);
  else{const url=URL.createObjectURL(file);try{await fondo(url,false);}finally{URL.revokeObjectURL(url);}}
});
form.elements.quitar_fondo.addEventListener('change',()=>{if(!form.elements.fondo.files.length)fondo(form.elements.quitar_fondo.checked?null:lienzo.dataset.fondo,lienzo.dataset.pdf==='1');});
