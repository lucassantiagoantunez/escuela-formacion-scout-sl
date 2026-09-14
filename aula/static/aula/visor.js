import * as pdfjs from './pdfjs/pdf.mjs';
pdfjs.GlobalWorkerOptions.workerSrc = new URL('./pdfjs/pdf.worker.mjs', import.meta.url).href;
const root = document.querySelector('[data-pdf-url]');
const estado = document.querySelector('#estado');
const canvas = document.querySelector('canvas');
const anterior = document.querySelector('#anterior');
const siguiente = document.querySelector('#siguiente');
let documento, numero = 1, trabajando = false;
async function mostrar() {
  if (trabajando || !documento) return;
  trabajando = true;
  anterior.disabled = siguiente.disabled = true;
  estado.textContent = 'Cargando página…';
  try {
    const pagina = await documento.getPage(numero);
    const original = pagina.getViewport({scale:1});
    const scale = Math.min(1400, Math.max(220, root.clientWidth-32)) / original.width * Number(document.querySelector('#zoom').value);
    const viewport = pagina.getViewport({scale});
    const dpi = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.floor(viewport.width*dpi); canvas.height = Math.floor(viewport.height*dpi);
    canvas.style.width = `${viewport.width}px`; canvas.style.height = `${viewport.height}px`;
    await pagina.render({canvasContext:canvas.getContext('2d'),viewport,transform:[dpi,0,0,dpi,0,0]}).promise;
    document.querySelector('#pagina').textContent = `Página ${numero} de ${documento.numPages}`;
    const text = await pagina.getTextContent();
    document.querySelector('#texto').textContent = text.items.map(item => item.str + (item.hasEOL ? '\n' : ' ')).join('');
    estado.textContent = '';
  } catch { estado.textContent = 'No se pudo mostrar esta página. Podés descargar el original o volver a intentar.'; }
  finally { trabajando = false; anterior.disabled = numero <= 1; siguiente.disabled = numero >= documento.numPages; }
}
anterior.addEventListener('click', () => { if (!trabajando && numero > 1) {numero--; mostrar();} });
siguiente.addEventListener('click', () => { if (!trabajando && numero < documento.numPages) {numero++; mostrar();} });
document.querySelector('#zoom').addEventListener('change', mostrar);
document.querySelector('#pantalla').addEventListener('click', async () => {
  try { if (document.fullscreenElement) await document.exitFullscreen(); else await root.requestFullscreen(); mostrar(); }
  catch { estado.textContent = 'Este navegador no permite pantalla completa. Podés ampliar el documento con Tamaño.'; }
});
let resize; window.addEventListener('resize', () => {clearTimeout(resize); resize=setTimeout(mostrar,200);});
try {
  documento = await pdfjs.getDocument({url:root.dataset.pdfUrl, isEvalSupported:false,
    cMapUrl:new URL('./pdfjs/cmaps/',import.meta.url).href, cMapPacked:true,
    standardFontDataUrl:new URL('./pdfjs/standard_fonts/',import.meta.url).href,
    wasmUrl:new URL('./pdfjs/wasm/',import.meta.url).href}).promise;
  await mostrar();
} catch { estado.textContent = 'No pudimos abrir el documento. Comprobá tu sesión o descargá el archivo original.'; }
