'use strict';
/* Vista general: resumen con anillos y una tarjeta viva por maceta.
   Las tarjetas se actualizan en su sitio para que los cambios se animen. */
const quieto=matchMedia('(prefers-reduced-motion:reduce)');
const ICONO={hum:'<path d="M12 3q-6 8-6 12a6 6 0 0 0 12 0q0-4-6-12z"/>',luz:'<circle cx="12" cy="12" r="4.5"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M5 5l2 2M17 17l2 2M19 5l-2 2M7 17l-2 2"/>',
 ind:'<path d="M12 20S4 15 4 9a4 4 0 0 1 8-1 4 4 0 0 1 8 1c0 6-8 11-8 11z"/>'};
ICONO.temp='<path d="M10 4a2 2 0 0 1 4 0v9a4.5 4.5 0 1 1-4 0z"/><path d="M12 9v8"/>';
ICONO.riego='<circle cx="12" cy="12" r="8"/><path d="M12 7v5l3 2"/>';
const MACETA='<path d="M5 12h14l-2 9H7z"/><path d="M12 12V6M12 8Q7 8 6 4Q11 3 12 8Q13 3 18 4Q17 8 12 8"/>';
const aro=(r,cls)=>'<circle class="aro '+cls+'" r="'+r+'" cx="50" cy="50" pathLength="100"/>';
const anillo=k=>'<div class="med '+k+'"><svg viewBox="0 0 100 100" aria-hidden="true">'+aro(42,'fondo')+aro(42,'nivel')+'<g transform="translate(32 32) scale(1.5)" class="ico">'+ICONO[k]+'</g></svg><b></b><span class="et"></span><em></em></div>';
const tarjetas=new Map();let filtro='todas',molde=null;

function numero(el,texto){ // cuenta hasta el valor nuevo
 if(el._t===texto)return;el._t=texto;
 const m=/^([\d.]+(?:,\d+)?)(.*)$/.exec(texto),a=m&&+m[1].replace(/\./g,'').replace(',','.');
 cancelAnimationFrame(el._r);
 if(!m||quieto.matches||document.hidden){el._n=a;el.textContent=texto;return}
 const de=el._n??0,t0=performance.now(),dec=(m[1].split(',')[1]||'').length;el._n=a;
 const paso=t=>{const f=Math.min(1,(t-t0)/800),v=de+(a-de)*(1-(1-f)**3);
  if(el._t!==texto)return;
  if(f<1){el.textContent=v.toLocaleString('es-CO',{minimumFractionDigits:dec,maximumFractionDigits:dec})+m[2];el._r=requestAnimationFrame(paso)}else el.textContent=texto};
 el._r=requestAnimationFrame(paso);
}
function nivel(c,pct){c.style.strokeDashoffset=100-Math.max(0,Math.min(100,pct));c.style.opacity=pct>0?1:0}

function crear(m){
 const e=document.createElement('div');e.className='planta'+(m.origen=='simulado'?' virtual':'');e.setAttribute('role','listitem');
 e.innerHTML='<button class="basura" type="button"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13M10 11v5M14 11v5"/></svg></button><div class="escena"></div><h3><a href="#m/'+m.id+'"></a></h3><p class="et esp"></p><p class="tg2"></p><div class="meds">'+['hum','luz','ind'].map(anillo).join('')+'</div><p class="pie et"></p>';
 molde=molde||$('av').parentNode.cloneNode(true);
 const pc=molde.cloneNode(true),av=pc.querySelector('svg');av.removeAttribute('id');av.querySelector('defs').remove();
 e.querySelector('.escena').append(pc);e.querySelector('.basura').onclick=()=>pideBorrar(m.id);e._av=av;return e;
}
function actualizar(e,m){
 const v=m.vivo,ok=m.conectada&&v.listo,L=mediciones(m),q=s=>e.querySelector(s);
 e.classList.toggle('off',!m.conectada);
 setAvatar(ok?v.estados||[v.estado]:[],ok?v.pers:null,ok,e._av);
 if(m.conectada&&!ok)q('.bd').textContent='Leyendo…';
 q('h3 a').textContent=m.nombre;q('.basura').setAttribute('aria-label','Borrar '+m.nombre);q('.esp').textContent=m.especie;q('.esp').hidden=!m.especie;
 const t=tags(m);if(e._tags!==t){e._tags=t;q('.tg2').innerHTML=t}
 for(const k of['hum','luz','ind']){
  const x=L.find(y=>y.col==k),c=q('.med.'+k),b=c.querySelector('b');nivel(c.querySelector('.nivel'),x?x.bar:0);
  c.classList.toggle('mal',!!(x&&(x.mal||x.q)));
  if(x)numero(b,x.v+(x.u=='/100'?'':' ')+x.u);else{cancelAnimationFrame(b._r);b._t=b._n=null;b.textContent='—'}
  c.querySelector('span').textContent=x?x.n:k=='hum'?'Humedad del suelo':k=='luz'?'Luz':'Índice de salud';
  c.querySelector('em').textContent=x?(x.q?'⚠ Revisar sensor':x.e?(x.mal?'⚠ ':'✓ ')+x.e:'Estimado'):'';
 }
 const temp=L.find(x=>x.u=='°C');
 q('.pie').textContent=m.conectada?ok?(temp?'Temperatura ambiental: '+temp.v+' °C · ':'')+'Sin regar: '+v.horas_sin_regar+' h':'Leyendo sensores…':m.ultimo_contacto?'Último contacto: '+fh(m.ultimo_contacto):'Aún no ha respondido';
}

function resumen(){
 const haySim=tipos.includes('simulado'),c=$('cuenta'),gr=[['real','Macetas reales',46],...(haySim?[['simulado','Macetas simuladas',34]]:[])];
 if(c._sim!==haySim){c._sim=haySim;
  c.innerHTML='<svg class="donas" viewBox="0 0 100 100" aria-hidden="true">'+gr.map(g=>aro(g[2],'fondo')+aro(g[2],'nivel '+g[0])).join('')+'<g transform="translate(32 33) scale(1.5)" class="mini">'+MACETA+'</g></svg><div class="filas">'+
   gr.map(g=>'<div class="fila '+g[0]+'"><div><b></b> <span class="et"></span></div><div class="macs" aria-hidden="true"></div></div>').join('')+'</div>'}
 gr.forEach(([k,n])=>{const a=macetas.filter(m=>m.origen==k),on=a.filter(m=>m.conectada).length;
  nivel(c.querySelector('.nivel.'+k),a.length?100*on/a.length:0);
  const f=c.querySelector('.fila.'+k),z=f.querySelector('.macs');f.querySelector('b').textContent=n+': '+on+(on==1?' conectada':' conectadas');
  f.querySelector('span').textContent=a.length?'de '+a.length+(a.length==1?' registrada':' registradas'):'Ninguna registrada aún';
  const p=a.slice(0,16).map(m=>'<i class="'+(m.conectada?'si':'')+'" title="'+esc(m.nombre)+'"><svg viewBox="0 0 24 24">'+MACETA+'</svg></i>').join('')+(a.length>16?' +'+(a.length-16):'');
  if(z._h!==p){z._h=p;z.innerHTML=p}});
}

function pintaLista(){
 $('verSim').hidden=!tipos.includes('simulado');$('aOrigen').hidden=tipos.length<2;resumen();
 const vistas=new Set(macetas.map(m=>m.id));
 for(const[id,e]of tarjetas)if(!vistas.has(id)){e.remove();tarjetas.delete(id)}
 let n=0;
 macetas.forEach((m,i)=>{let e=tarjetas.get(m.id);
  if(!e){e=crear(m);e.style.setProperty('--i',i);tarjetas.set(m.id,e);$('macetas').append(e)}
  e.hidden=filtro!='todas'&&m.origen!=filtro;if(!e.hidden)n++;actualizar(e,m)});
 $('vacio').hidden=n>0;
 $('vacio').textContent=filtro=='simulado'?'No hay macetas simuladas. Enciéndelas con: python -m simulador.demo':'No hay macetas registradas. Agrégalas en el menú ☰.';
}
$('verSim').onclick=e=>{const f=e.target.dataset.f;if(!f)return;filtro=f;$('verSim').querySelectorAll('button').forEach(b=>b.setAttribute('aria-pressed',b==e.target));pintaLista()};

/* Detalle: una tarjeta por medición, actualizada en su sitio */
function pintaMedidas(m){
 const z=$('dMed'),L=mediciones(m),claves=L.map(x=>x.col||(x.u=='°C'?'temp':'riego'));
 [...z.children].forEach(e=>{if(!claves.includes(e.dataset.k))e.remove()});
 L.forEach((x,i)=>{const k=claves[i];let e=z.querySelector('[data-k='+k+']');
  if(!e){e=document.createElement('div');e.dataset.k=k;e.className='medida med '+k;e.style.setProperty('--i',i);
   e.innerHTML='<h3></h3><svg viewBox="0 0 100 100" aria-hidden="true">'+(x.bar!=null?aro(42,'fondo')+aro(42,'nivel'):'<circle class="disco" cx="50" cy="50" r="44"/>')+'<g transform="translate(29 29) scale(1.75)" class="ico">'+ICONO[k]+'</g></svg><b></b><em></em><p class="alerta"></p><p class="et nota"></p><span class="tag"></span>'}
  if(z.children[i]!==e)z.insertBefore(e,z.children[i]||null);
  const q=s=>e.querySelector(s);
  e.classList.toggle('mal',!!(x.mal||x.q));q('h3').textContent=x.n;numero(q('b'),x.v+(x.u=='/100'?'':' ')+x.u);
  if(x.bar!=null)nivel(q('.nivel'),x.bar);
  q('em').textContent=x.e?(x.mal?'⚠ ':'✓ ')+x.e:'';q('.alerta').textContent=x.q?'⚠ '+x.q:'';q('.nota').textContent=x.nota||'';
  q('.tag').textContent=x.p;q('.tag').classList.toggle('sim',x.p=='Simulado')});
}

/* Menú lateral: se cierra con ✕, Escape, al tocar fuera o al cambiar de sección */
$('menuB').onclick=()=>{$('menu').showModal();cargaAcceso();cargaPap()};
$('menuX').onclick=()=>$('menu').close();
$('menu').addEventListener('click',e=>{if(e.target==$('menu')&&e.clientX>$('menu').getBoundingClientRect().right)$('menu').close()});
$('menu').addEventListener('close',()=>{for(const d of $('menu').querySelectorAll(':scope>details'))d.open=false});
addEventListener('hashchange',()=>{if($('menu').open)$('menu').close()});

/* Modo presentación: una maceta a pantalla completa, con los mismos datos y avatar de las tarjetas */
let prId=null,prE=null,prT=0;
function prPinta(){
 if(!$('pres').open)return;
 $('prH').textContent=new Date().toLocaleTimeString('es-CO',{hour:'numeric',minute:'2-digit'});$('prC').textContent=$('con').textContent;
 let i=macetas.findIndex(m=>m.id==prId);if(i<0){i=0;prId=macetas.length?macetas[0].id:null}
 const m=macetas[i];$('prA').disabled=$('prS').disabled=$('prR').disabled=macetas.length<2;
 if(!m){$('prZ').textContent='No hay macetas registradas.';prE=null;$('prN').textContent='';return}
 if(!prE||prE._id!=m.id){prE=crear(m);prE._id=m.id;prE.removeAttribute('role');prE.querySelector('.basura').hidden=true;const a=prE.querySelector('h3 a');a.removeAttribute('href');
  const f=document.createElement('p');f.className='frase';prE.querySelector('.meds').before(f);$('prZ').replaceChildren(prE)}
 actualizar(prE,m);prE.querySelector('.frase').textContent=m.conectada&&m.vivo.listo?'«'+m.vivo.frase+'»':'';$('prN').textContent=(i+1)+' de '+macetas.length;
}
function prVa(d){const n=macetas.length;if(!n)return;prId=macetas[(macetas.findIndex(m=>m.id==prId)+d+n)%n].id;prPinta();prReloj()}
function prReloj(){clearInterval(prT);if($('prR').getAttribute('aria-pressed')=='true')prT=setInterval(()=>prVa(1),10000)}
$('presB').onclick=async()=>{
 $('menu').close();prId=actual||(macetas.find(m=>m.origen=='real'&&m.conectada)||macetas[0]||{}).id;prE=null;
 try{await Promise.race([document.documentElement.requestFullscreen(),new Promise(r=>setTimeout(r,1500))])}catch(e){}
 if(!$('pres').open)$('pres').showModal();prPinta();prReloj()};
$('prA').onclick=()=>prVa(-1);$('prS').onclick=()=>prVa(1);$('prX').onclick=()=>$('pres').close();
$('prR').onclick=()=>{$('prR').setAttribute('aria-pressed',$('prR').getAttribute('aria-pressed')!='true');prReloj()};
$('pres').addEventListener('keydown',e=>{const d={ArrowLeft:-1,ArrowRight:1}[e.key];if(d){e.preventDefault();prVa(d)}});
$('pres').addEventListener('close',()=>{clearInterval(prT);prE=null;$('prZ').replaceChildren();if(document.fullscreenElement)document.exitFullscreen().catch(()=>{})});
setInterval(prPinta,1000);

$('nueva').onclick=()=>{$('menuB').onclick();$('mAlta').open=true;$('aN').focus()};

/* Deslizar con el dedo: hacia la izquierda avanza, hacia la derecha retrocede */
function desliza(zona,mueve,ir){
 let x=0,y=0,id=null,dx=0,fijo=false;
 const suelta=()=>{const e=mueve();id=null;if(e){e.classList.add('vuelve');e.style.transform=e.style.opacity=''}};
 zona.classList.add('desliza');
 zona.addEventListener('touchstart',e=>{
  if(e.touches.length>1||(window.visualViewport&&visualViewport.scale>1.05)){if(id!=null)suelta();return}
  const t=e.touches[0];id=t.identifier;x=t.clientX;y=t.clientY;dx=0;fijo=false;const m=mueve();if(m)m.classList.remove('vuelve')},{passive:true});
 zona.addEventListener('touchmove',e=>{
  if(id==null)return;const t=[...e.touches].find(k=>k.identifier==id);if(!t)return;dx=t.clientX-x;
  const dy=t.clientY-y;if(!fijo){if(Math.abs(dx)<10&&Math.abs(dy)<10)return;if(Math.abs(dx)<Math.abs(dy)*1.3){suelta();return}fijo=true}
  const m=mueve();if(m&&!quieto.matches){m.style.transform='translateX('+dx*.6+'px)';m.style.opacity=1-Math.min(.5,Math.abs(dx)/500)}},{passive:true});
 zona.addEventListener('touchend',()=>{if(id==null)return;const d=fijo&&Math.abs(dx)>50?(dx<0?1:-1):0;suelta();if(d)ir(d)});
 zona.addEventListener('touchcancel',()=>{if(id!=null)suelta()});
}
desliza($('prZ'),()=>$('prZ').firstElementChild,prVa);
