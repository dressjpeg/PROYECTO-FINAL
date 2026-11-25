'use strict';
/* Registro fotográfico de la maceta abierta */
let fotos=[],fotoVer=null,fotoN=0,camFlujo=null,papelera=false;
const uF=(f,t)=>'/api/v1/macetas/'+actual+'/fotos/'+f.id+'/'+t+'.jpg';
const fdia=t=>new Date(t*1000).toLocaleDateString('es-CO',{day:'numeric',month:'short',year:'numeric'});
const FUENTE={usuario:'fecha escrita a mano',camara:'hora de la cámara del dashboard',exif:'fecha guardada por la cámara',subida:'fecha de subida: la foto no traía fecha'};
const opc=v=>v===''?null:v;

async function cargaFotos(){
 const mio=++fotoN,id=actual;if(!id)return;
 const d=$('fD').value?new Date($('fD').value+'T00:00').getTime()/1000:0,h=$('fH').value?new Date($('fH').value+'T23:59:59').getTime()/1000:2**40;
 try{const L=await pide('/api/v1/macetas/'+id+'/fotos?desde='+d+'&hasta='+h+'&papelera='+papelera);if(mio!=fotoN||id!=actual)return;
  fotos=L;pintaFotos()}catch(e){if(mio==fotoN)$('fMsg').textContent='No se pudieron cargar: '+e.message}
}
function pintaFotos(){
 let mes='';
 $('album').innerHTML=fotos.slice().reverse().map(f=>{const m=new Date(f.capturada_en*1000).toLocaleDateString('es-CO',{month:'long',year:'numeric'}),t=m!=mes?'<h4>'+m+'</h4>':'';mes=m;
  return t+'<div class="foto"><button type="button" data-f="'+f.id+'"><img loading="lazy" src="'+uF(f,'mini')+'" alt="Foto del '+fdia(f.capturada_en)+'"><span>'+fh(f.capturada_en)+(f.altura_cm!=null?'<br>'+num(f.altura_cm)+' cm':'')+'</span></button><button type="button" class="fx'+(papelera?' sololocal':'')+'" data-q="'+f.id+'" title="'+(papelera?'Borrar para siempre':'Enviar a la papelera')+'" aria-label="'+(papelera?'Borrar para siempre':'Enviar a la papelera')+' la foto del '+fh(f.capturada_en)+'"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13M10 11v5M14 11v5"/></svg></button></div>'}).join('')||'<p class="et">'+(papelera?'La papelera está vacía.':$('fD').value||$('fH').value?'No hay fotos en esas fechas.':'Aún no hay fotos de esta maceta.')+'</p>';
 $('fCuenta').textContent=fotos.length+(fotos.length==1?' foto':' fotos')+(papelera?' en la papelera'+(document.body.classList.contains('remoto')?'. Para borrar definitivamente, usa el PC del servidor.':''):'');
 $('fVac').hidden=!papelera||!fotos.length&&!$('fD').value&&!$('fH').value;
 $('fTl').hidden=papelera||fotos.length<2;
 const cmp=!papelera&&fotos.length>1;$('compara').hidden=!cmp;
 if(cmp){const va=$('cA1').value,vb=$('cB1').value,o=fotos.map(f=>'<option value="'+f.id+'">'+fh(f.capturada_en)+'</option>').join('');
  $('cA1').innerHTML=$('cB1').innerHTML=o;$('cA1').value=fotos.some(f=>f.id==va)?va:fotos[0].id;$('cB1').value=fotos.some(f=>f.id==vb)?vb:fotos[fotos.length-1].id;pintaComp()}
}
function pintaComp(){
 const a=fotos.find(f=>f.id==$('cA1').value),b=fotos.find(f=>f.id==$('cB1').value);if(!a||!b)return;
 const s=(i,f)=>{const u=uF(f,'grande');if($(i).getAttribute('src')!=u)$(i).src=u;$(i).alt='Foto del '+fdia(f.capturada_en)};s('iA',a);s('iB',b);
 $('cmA').textContent=fdia(a.capturada_en);$('cmB').textContent=fdia(b.capturada_en);
 const d=Math.abs(b.capturada_en-a.capturada_en)/86400,x=[num(d)+(d==1?' día':' días')+' entre las dos fotos'];
 if(a.altura_cm!=null&&b.altura_cm!=null)x.push('altura: '+num(a.altura_cm)+' → '+num(b.altura_cm)+' cm');
 if(a.hojas!=null&&b.hojas!=null)x.push('hojas: '+a.hojas+' → '+b.hojas);
 $('cTxt').textContent=x.join(' · ')+'.';
}
async function enviaFoto(blob,camara){
 const q=new URLSearchParams({camara,nota:$('fNota').value.trim()});
 const a=opc($('fAlt').value.trim().replace(',','.')),h=opc($('fHoj').value);if(a!=null)q.set('altura',a);if(h!=null)q.set('hojas',h);
 if(!camara&&$('fCuando').value)q.set('cuando',Math.floor(new Date($('fCuando').value).getTime()/1000));
 const c=new AbortController(),t=setTimeout(()=>c.abort(),60000);
 try{const r=await fetch('/api/v1/macetas/'+actual+'/fotos?'+q,{method:'POST',body:blob,signal:c.signal,headers:{'X-Maceta':'1','Content-Type':'application/octet-stream'}}),j=await r.json();
  if(!r.ok)throw new Error(typeof j.detail=='string'?j.detail:'Revisa la altura, las hojas y la nota')}
 catch(e){throw e.name=='AbortError'||e instanceof TypeError?new Error('Sin conexión con el servidor central'):e}finally{clearTimeout(t)}
}
async function elige(e){
 const L=[...e.target.files];e.target.value='';if(!L.length)return;let ok=0,mal=[];
 for(const f of L){$('fMsg').textContent='Guardando '+(ok+mal.length+1)+' de '+L.length+'…';
  try{if(f.size>12e6)throw new Error('supera 12 MB');await enviaFoto(f,false);ok++}catch(x){mal.push(f.name+': '+x.message)}}
 $('fMsg').textContent=(ok?ok+(ok==1?' foto guardada. ':' fotos guardadas. '):'')+mal.join('. ');
 if(ok){$('fNota').value=$('fAlt').value=$('fHoj').value=$('fCuando').value=''}cargaFotos();
}
$('fArch').onchange=$('fCam').onchange=elige;
$('fSubir').onclick=()=>$('fArch').click();

/* Cámara: en este PC se abre aquí; en un celular por HTTP se usa la cámara del sistema */
$('fTomar').onclick=async()=>{
 if(!navigator.mediaDevices||!navigator.mediaDevices.getUserMedia)return $('fCam').click();
 try{camFlujo=await navigator.mediaDevices.getUserMedia({video:{facingMode:'environment',width:{ideal:1600}},audio:false})}
 catch(e){$('fMsg').textContent=e.name=='NotAllowedError'?'El navegador no dio permiso para usar la cámara. Puedes subir una foto.':'No hay una cámara disponible. Puedes subir una foto.';return}
 $('cVideo').srcObject=camFlujo;const u=papelera?null:fotos[fotos.length-1];$('cGuia').hidden=$('cGuiaC').hidden=!u;if(u)$('cGuia').src=uF(u,'grande');guia();$('cMsg').textContent='';$('camara').showModal();
};
const guia=()=>$('cGuia').style.opacity=$('cOp').value/100;$('cOp').oninput=guia;
const cierraCam=()=>{if(camFlujo)camFlujo.getTracks().forEach(t=>t.stop());camFlujo=null;$('cVideo').srcObject=null};
$('camara').onclose=cierraCam;$('cNo').onclick=()=>$('camara').close();
$('cSi').onclick=async()=>{
 const v=$('cVideo');if(!v.videoWidth)return;$('cSi').disabled=true;
 const k=document.createElement('canvas');k.width=v.videoWidth;k.height=v.videoHeight;k.getContext('2d').drawImage(v,0,0);
 try{const b=await new Promise(r=>k.toBlob(r,'image/jpeg',.92));if(!b)throw new Error('la cámara no entregó imagen');
  await enviaFoto(b,true);$('camara').close();$('fMsg').textContent='Foto guardada.';$('fNota').value=$('fAlt').value=$('fHoj').value='';cargaFotos()}
 catch(e){$('cMsg').textContent='No se guardó: '+e.message}$('cSi').disabled=false;
};

/* Visor y papelera */
$('album').onclick=e=>{const q=e.target.closest('[data-q]');if(q)return quita(q);const b=e.target.closest('[data-f]');if(!b)return;const f=fotoVer=fotos.find(x=>x.id==b.dataset.f),c=f.condiciones,m=macetas.find(x=>x.id==actual);
 $('vImg').src=uF(f,'grande');$('vImg').alt='Foto del '+fdia(f.capturada_en);$('vT').textContent=fh(f.capturada_en)+', '+new Date(f.capturada_en*1000).getFullYear();
 const L=['Origen de la fecha: '+FUENTE[f.fuente_fecha]];if(f.altura_cm!=null)L.push('Altura (a mano): '+num(f.altura_cm)+' cm');if(f.hojas!=null)L.push('Hojas (a mano): '+f.hojas);if(f.nota)L.push('Nota: '+f.nota);
 L.push(c?'Condiciones '+(m&&m.origen=='simulado'?'simuladas':'medidas')+' cerca de la foto: humedad del suelo '+c.hum_pct+' %, nivel de luz '+c.luz_pct+' %, índice '+c.indice+'/100':'Sin lecturas de sensores cerca de esa hora');
 $('vTxt').innerHTML=L.map(x=>esc(x)).join('<br>');$('vElim').hidden=!papelera;$('vDel').textContent=papelera?'Restaurar':'Enviar a la papelera';$('vMsg').textContent='';$('visor').showModal()};
$('vNo').onclick=()=>$('visor').close();
$('vDel').onclick=async()=>{const u='/api/v1/macetas/'+actual+'/fotos/'+fotoVer.id;
 try{await pide(u+(papelera?'/restaurar':''),{m:papelera?'POST':'DELETE'});$('visor').close();$('fMsg').textContent=papelera?'Foto restaurada.':'Foto enviada a la papelera.';cargaFotos()}catch(e){$('vMsg').textContent=e.message}};
$('fPap').onclick=()=>{papelera=!papelera;$('fPap').textContent=papelera?'Volver a las fotos':'Ver papelera';$('fPap').setAttribute('aria-pressed',papelera);cargaFotos()};
/* Borrado definitivo: una foto, una maceta o todas. Cuenta toda la papelera, aunque haya un filtro de fechas */
let elimU='',elimMsg='fMsg';
const nF=n=>n==1?'1 foto':n+' fotos',nomM=id=>{const m=macetas.find(x=>x.id==id);return m?m.nombre:'maceta'};
function pideElim(t,txt,u,msg){elimU=u;elimMsg=msg;$('xT').textContent=t;$('xTxt').textContent=txt+' No se podrán recuperar.';$('xMsg').textContent='';$('xSi').disabled=false;$('vaciar').showModal()}
async function vaciaUna(id,msg){
 try{const n=(await pide('/api/v1/papelera'))[id]||0;
  if(!n){$(msg).textContent='La papelera está vacía.';return}
  pideElim('¿Vaciar la papelera?','Se borrarán para siempre '+nF(n)+' de «'+nomM(id)+'»'+(msg=='fMsg'&&($('fD').value||$('fH').value)?', también las que oculta el filtro de fechas':'')+'.','/api/v1/macetas/'+id+'/papelera?esperadas='+n,msg)}
 catch(e){$(msg).textContent=e.message}
}
$('fVac').onclick=()=>vaciaUna(actual,'fMsg');
function elimUna(f){pideElim('¿Borrar esta foto?','Se borrará para siempre la foto del '+fh(f.capturada_en)+'.','/api/v1/macetas/'+actual+'/papelera/'+f.id,'fMsg');$('xTxt').textContent=$('xTxt').textContent.replace('podrán','podrá')}
$('vElim').onclick=()=>{$('visor').close();elimUna(fotoVer)};
$('pTodo').onclick=async()=>{try{const p=Object.values(await pide('/api/v1/papelera')),n=p.reduce((a,b)=>a+b,0);
 if(!n)return cargaPap();pideElim('¿Vaciar todas las papeleras?','Se borrarán para siempre '+nF(n)+' de '+(p.length==1?'1 maceta':p.length+' macetas')+', reales y simuladas.','/api/v1/papelera?esperadas='+n,'pMsg')}catch(e){$('pMsg').textContent=e.message}};
$('pL').onclick=e=>{const b=e.target.closest('[data-p]');if(b)vaciaUna(b.dataset.p,'pMsg')};
async function cargaPap(){
 try{const p=Object.entries(await pide('/api/v1/papelera')),n=p.reduce((a,x)=>a+x[1],0);
  $('pN').textContent='('+n+')';$('pTodo').hidden=!n;
  $('pL').innerHTML=p.map(([id,k])=>'<div class="acc" style="align-items:center"><span>'+esc(nomM(id))+': '+nF(k)+'</span><button type="button" data-p="'+id+'">Vaciar</button></div>').join('')||'<p class="et">No hay fotos descartadas.</p>'}
 catch(e){$('pN').textContent=''}
}
$('pap').ontoggle=()=>{if($('pap').open){$('pMsg').textContent='';cargaPap()}};addEventListener('hashchange',cargaPap);addEventListener('load',()=>setTimeout(cargaPap,500));
$('xNo').onclick=()=>$('vaciar').close();
$('xSi').onclick=async()=>{$('xSi').disabled=true;
 try{const r=await pide(elimU,{m:'DELETE'});$('vaciar').close();
  $(elimMsg).textContent=(r.borradas==1?'1 foto borrada.':r.borradas+' fotos borradas.')+(r.fallidas?' '+nF(r.fallidas)+' en la papelera: no se pudo borrar el archivo.':'');if(actual)cargaFotos();cargaPap()}
 catch(e){$('xMsg').textContent=e.message;$('xSi').disabled=false}};
$('fD').onchange=$('fH').onchange=cargaFotos;$('cA1').onchange=$('cB1').onchange=pintaComp;
$('cX').oninput=()=>$('comp').style.setProperty('--x',$('cX').value+'%');
function abreFotos(){fotos=[];papelera=false;$('fPap').textContent='Ver papelera';$('fPap').setAttribute('aria-pressed','false');$('fMsg').textContent=$('album').innerHTML='';$('compara').hidden=$('fVac').hidden=$('fTl').hidden=true;$('fD').value=$('fH').value=$('cA1').innerHTML=$('cB1').innerHTML='';
 for(const d of['visor','camara','vaciar','tl'])if($(d).open)$(d).close();cargaFotos()}

/* Timelapse: las fotos que deja ver el filtro, en orden. Cada paso espera a que la foto esté cargada */
let tlL=[],tlN=0,tlOn=false,tlT=0,tlGiro=0,tlMid='';const tlC=new Map();
function tlFoto(f){let p=tlC.get(f.id);
 if(!p){const i=new Image();i.src='/api/v1/macetas/'+tlMid+'/fotos/'+f.id+'/grande.jpg';p=i.decode().then(()=>i);p.catch(()=>tlC.delete(f.id));tlC.set(f.id,p);
  if(tlC.size>30)tlC.delete(tlC.keys().next().value)}
 return p}
async function tlMuestra(n){
 const g=++tlGiro,f=tlL[n];tlN=n;clearTimeout(tlT);$('tlP').value=n;
 try{const i=await tlFoto(f);if(g!=tlGiro)return;$('tlI').src=i.src;$('tlM').textContent=''}
 catch(e){if(g!=tlGiro)return;$('tlI').removeAttribute('src');$('tlM').textContent='No se pudo cargar esta foto.'}
 $('tlI').alt='Foto del '+fdia(f.capturada_en);$('tlF').textContent=fdia(f.capturada_en);
 const d=Math.floor((f.capturada_en-tlL[0].capturada_en)/86400),x=['Foto '+(n+1)+' de '+tlL.length,'día '+d];
 if(f.altura_cm!=null)x.push('altura: '+num(f.altura_cm)+' cm');if(f.hojas!=null)x.push('hojas: '+f.hojas);$('tlD').textContent=x.join(' · ');
 $('tlP').setAttribute('aria-valuetext',fdia(f.capturada_en));
 const s=n+1<tlL.length?n+1:$('tlR').getAttribute('aria-pressed')=='true'?0:-1;
 if(s>=0)tlFoto(tlL[s]).catch(()=>{});
 if(tlOn){if(s<0)tlPara();else tlT=setTimeout(()=>tlMuestra(s),+$('tlV').value)}
}
function tlPara(){tlOn=false;clearTimeout(tlT);$('tlB').textContent=tlN==tlL.length-1?'↻ Ver de nuevo':'▶ Reproducir'}
function tlSigue(){tlOn=true;$('tlB').textContent='❚❚ Pausar';tlMuestra(tlN==tlL.length-1?0:tlN)}
$('fTl').onclick=()=>{tlMid=actual;tlL=fotos.slice();tlC.clear();tlN=0;$('tlP').max=tlL.length-1;$('tlT').textContent='Timelapse de «'+nomM(actual)+'»';$('tl').showModal();
 if(matchMedia('(prefers-reduced-motion:reduce)').matches){tlPara();tlMuestra(0)}else tlSigue()};
$('tlB').onclick=()=>tlOn?tlPara():tlSigue();
$('tlP').oninput=()=>{const n=+$('tlP').value;tlN=n;tlPara();tlMuestra(n)};
$('tlR').onclick=()=>{$('tlR').setAttribute('aria-pressed',$('tlR').getAttribute('aria-pressed')!='true')};
$('tlX').onclick=()=>$('tl').close();
$('tl').addEventListener('close',()=>{tlOn=false;tlGiro++;clearTimeout(tlT);tlC.clear();$('tlI').removeAttribute('src')});

/* Borrar desde la miniatura: a la papelera, con Deshacer; si ya está en la papelera, pide confirmar */
async function quita(q){
 const f=fotos.find(x=>x.id==q.dataset.q),id=actual,u='/api/v1/macetas/'+id+'/fotos/'+f.id;if(papelera)return elimUna(f);
 q.disabled=true;
 try{await pide(u,{m:'DELETE'});if(id!=actual)return;
  const b=document.createElement('button');b.type='button';b.textContent='Deshacer';
  b.onclick=async()=>{b.disabled=true;try{await pide(u+'/restaurar',{m:'POST'});if(id==actual){$('fMsg').textContent='Foto restaurada.';cargaFotos()}cargaPap()}catch(e){$('fMsg').textContent=e.message}};
  $('fMsg').textContent='Foto enviada a la papelera. ';$('fMsg').append(b);cargaFotos();cargaPap()}
 catch(e){q.disabled=false;$('fMsg').textContent=e.message}
}

/* Biblioteca: todas las fotos agrupadas por planta, sin sensores ni avatar. Las más recientes primero */
let bbG=[],bbSel='',bbK=0,bbP=null,bbI=0;
const bbU=(g,f,t)=>'/api/v1/macetas/'+g.m.id+'/fotos/'+f.id+'/'+t+'.jpg';
async function cargaBib(){
 const n=++bbK;$('bbM').textContent='Cargando…';
 const L=await Promise.all(macetas.filter(m=>m.fotos).map(m=>pide('/api/v1/macetas/'+m.id+'/fotos').then(f=>({m,f:f.reverse()}),()=>({m,f:null}))));
 if(n!=bbK||vista!='bib')return;
 const mal=L.filter(g=>!g.f).length;bbG=L.filter(g=>g.f&&g.f.length);if(!bbG.some(g=>g.m.id==bbSel))bbSel='';
 const t=bbG.reduce((a,g)=>a+g.f.length,0);
 $('bbM').textContent=(t?nF(t)+' de '+(bbG.length==1?'1 planta':bbG.length+' plantas')+'.':mal?'':'Aún no hay fotos. Tómalas desde cada maceta.')+(mal?' No se pudieron cargar las fotos de '+(mal==1?'1 planta.':mal+' plantas.'):'');
 pintaBib();
}
function pintaBib(){
 $('bbF').hidden=bbG.length<2;
 $('bbF').innerHTML='<button type="button" data-b="" aria-pressed="'+!bbSel+'">Todas</button>'+bbG.map(g=>'<button type="button" data-b="'+g.m.id+'" aria-pressed="'+(bbSel==g.m.id)+'">'+esc(g.m.nombre)+'</button>').join('');
 $('bbL').innerHTML=bbG.map((g,i)=>bbSel&&bbSel!=g.m.id?'':'<div class="bbP"><h3><svg class="mi" viewBox="0 0 24 24" aria-hidden="true">'+MACETA+'</svg><a href="#m/'+g.m.id+'">'+esc(g.m.nombre)+'</a><span class="et">'+(g.m.especie?esc(g.m.especie)+' · ':'')+(g.m.origen=='simulado'?'Simulada · ':'')+nF(g.f.length)+'</span></h3><div class="bbG">'+
  g.f.map((f,j)=>'<button type="button" data-g="'+i+'" data-j="'+j+'"><img loading="lazy" src="'+bbU(g,f,'mini')+'" alt="'+esc(g.m.nombre)+', '+fdia(f.capturada_en)+'"></button>').join('')+'</div></div>').join('');
}
/* Foto vecina, siempre de la misma maceta */
const bbDest=d=>{const k=bbI+d;return k>=0&&k<bbP.f.length?k:-1};
function bbMuestra(){
 const f=bbP.f[bbI];$('bbT').textContent=bbP.m.nombre;$('bbI').src=bbU(bbP,f,'grande');$('bbI').alt='Foto del '+fdia(f.capturada_en);
 $('bbD').textContent=[fdia(f.capturada_en),(bbI+1)+' de '+bbP.f.length,f.altura_cm!=null?'altura: '+num(f.altura_cm)+' cm':'',f.hojas!=null?'hojas: '+f.hojas:'',f.nota].filter(Boolean).join(' · ');
 $('bbA').disabled=bbDest(-1)<0;$('bbS').disabled=bbDest(1)<0;$('bbH').hidden=bbP.f.length<2;$('bbE').href='#m/'+bbP.m.id;
}
const bbVa=d=>{const k=bbDest(d);if(k>=0){bbI=k;bbMuestra()}};
$('bbF').onclick=e=>{const b=e.target.closest('[data-b]');if(b){bbSel=b.dataset.b;pintaBib()}};
$('bbL').onclick=e=>{const b=e.target.closest('[data-j]');if(b){bbP=bbG[b.dataset.g];bbI=+b.dataset.j;bbMuestra();$('bbV').showModal()}};
$('bbA').onclick=()=>bbVa(-1);$('bbS').onclick=()=>bbVa(1);$('bbX').onclick=()=>$('bbV').close();
$('bbV').addEventListener('keydown',e=>{const d={ArrowLeft:-1,ArrowRight:1}[e.key];if(d){e.preventDefault();bbVa(d)}});
$('bbV').addEventListener('close',()=>$('bbI').removeAttribute('src'));
addEventListener('hashchange',()=>{if($('bbV').open)$('bbV').close()});
$('bibB').onclick=()=>$('menu').close();
desliza($('bbI'),()=>$('bbI'),bbVa);
