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
  return t+'<button type="button" data-f="'+f.id+'"><img loading="lazy" src="'+uF(f,'mini')+'" alt="Foto del '+fdia(f.capturada_en)+'"><span>'+fh(f.capturada_en)+(f.altura_cm!=null?'<br>'+num(f.altura_cm)+' cm':'')+'</span></button>'}).join('')||'<p class="et">'+(papelera?'La papelera está vacía.':$('fD').value||$('fH').value?'No hay fotos en esas fechas.':'Aún no hay fotos de esta maceta.')+'</p>';
 $('fCuenta').textContent=fotos.length+(fotos.length==1?' foto':' fotos')+(papelera?' en la papelera':'');
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
$('album').onclick=e=>{const b=e.target.closest('[data-f]');if(!b)return;const f=fotoVer=fotos.find(x=>x.id==b.dataset.f),c=f.condiciones,m=macetas.find(x=>x.id==actual);
 $('vImg').src=uF(f,'grande');$('vImg').alt='Foto del '+fdia(f.capturada_en);$('vT').textContent=fh(f.capturada_en)+', '+new Date(f.capturada_en*1000).getFullYear();
 const L=['Origen de la fecha: '+FUENTE[f.fuente_fecha]];if(f.altura_cm!=null)L.push('Altura (a mano): '+num(f.altura_cm)+' cm');if(f.hojas!=null)L.push('Hojas (a mano): '+f.hojas);if(f.nota)L.push('Nota: '+f.nota);
 L.push(c?'Condiciones '+(m&&m.origen=='simulado'?'simuladas':'medidas')+' cerca de la foto: humedad del suelo '+c.hum_pct+' %, nivel de luz '+c.luz_pct+' %, índice '+c.indice+'/100':'Sin lecturas de sensores cerca de esa hora');
 $('vTxt').innerHTML=L.map(x=>esc(x)).join('<br>');$('vDel').textContent=papelera?'Restaurar':'Enviar a la papelera';$('vMsg').textContent='';$('visor').showModal()};
$('vNo').onclick=()=>$('visor').close();
$('vDel').onclick=async()=>{const u='/api/v1/macetas/'+actual+'/fotos/'+fotoVer.id;
 try{await pide(u+(papelera?'/restaurar':''),{m:papelera?'POST':'DELETE'});$('visor').close();$('fMsg').textContent=papelera?'Foto restaurada.':'Foto enviada a la papelera.';cargaFotos()}catch(e){$('vMsg').textContent=e.message}};
$('fPap').onclick=()=>{papelera=!papelera;$('fPap').textContent=papelera?'Volver a las fotos':'Ver papelera';$('fPap').setAttribute('aria-pressed',papelera);cargaFotos()};
$('fD').onchange=$('fH').onchange=cargaFotos;$('cA1').onchange=$('cB1').onchange=pintaComp;
$('cX').oninput=()=>$('comp').style.setProperty('--x',$('cX').value+'%');
function abreFotos(){fotos=[];papelera=false;$('fPap').textContent='Ver papelera';$('fPap').setAttribute('aria-pressed','false');$('fMsg').textContent=$('album').innerHTML='';$('compara').hidden=true;$('fD').value=$('fH').value=$('cA1').innerHTML=$('cB1').innerHTML='';
 for(const d of['visor','camara'])if($(d).open)$(d).close();cargaFotos()}
