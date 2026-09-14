import * as pdfjs from './pdfjs/pdf.mjs';
pdfjs.GlobalWorkerOptions.workerSrc=new URL('./pdfjs/pdf.worker.mjs',import.meta.url).href;
const form=document.querySelector('#form-diseno'),lienzo=document.querySelector('#diseno-lienzo'),canvas=document.querySelector('#diseno-fondo'),estado=document.querySelector('#diseno-estado');
const controles=(key,prop)=>form.elements.namedItem(`${key}_${prop}`);
function actualizar(){
  for(const caja of lienzo.querySelectorAll('[data-key]')){
    const key=caja.dataset.key;
    caja.style.left=controles(key,'x').value+'%';caja.style.top=controles(key,'y').value+'%';
    caja.style.width=controles(key,'ancho').value+'%';caja.style.height=controles(key,'alto').value+'%';
    caja.style.fontSize=(Number(controles(key,'tamano').value)/841.89*100)+'cqw';
    caja.style.color=form.elements.color.value;
    caja.style.fontFamily={'Helvetica':'Arial,sans-serif','Times-Roman':'Georgia,serif','Courier':'monospace'}[form.elements.fuente.value];
    if(key==='encabezado'||key==='libre')caja.textContent=form.elements.namedItem(key).value;
  }
}
form.addEventListener('input',actualizar);actualizar();
for(const caja of lienzo.querySelectorAll('[data-key]')){
  let inicio;
  caja.addEventListener('pointerdown',e=>{if(e.button!==0)return;const key=caja.dataset.key;
    inicio={x:e.clientX,y:e.clientY,ix:Number(controles(key,'x').value),iy:Number(controles(key,'y').value)};caja.setPointerCapture(e.pointerId);});
  caja.addEventListener('pointermove',e=>{if(!inicio)return;const key=caja.dataset.key,r=lienzo.getBoundingClientRect();
    controles(key,'x').value=Math.max(0,Math.min(100-Number(controles(key,'ancho').value),inicio.ix+(e.clientX-inicio.x)/r.width*100)).toFixed(1);
    controles(key,'y').value=Math.max(0,Math.min(86-Number(controles(key,'alto').value),inicio.iy+(e.clientY-inicio.y)/r.height*100)).toFixed(1);actualizar();});
  for(const nombre of ['pointerup','pointercancel'])caja.addEventListener(nombre,()=>{inicio=null;});
}
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
  if(file.size>10*1024*1024){estado.textContent='La plantilla admite hasta 10 MB.';return;}
  if(file.name.toLowerCase().endsWith('.pdf'))await fondo(new Uint8Array(await file.arrayBuffer()),true);
  else{const url=URL.createObjectURL(file);try{await fondo(url,false);}finally{URL.revokeObjectURL(url);}}
});
form.elements.quitar_fondo.addEventListener('change',()=>{if(form.elements.quitar_fondo.checked&&!form.elements.fondo.files.length)fondo(null,false);});
