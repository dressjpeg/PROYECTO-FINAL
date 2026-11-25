'use strict';
const esc=s=>String(s).replace(/[&<>"']/g,c=>'&#'+c.charCodeAt(0)+';');
const poner=(id,h)=>{const e=$(id);if(e._h!==h){e._h=h;e.innerHTML=h}};
const fh=t=>new Date(t*1000).toLocaleString('es-CO',{day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit'});
const dur=s=>{s=Math.floor(s);const d=Math.floor(s/86400),h=Math.floor(s%86400/3600),m=Math.floor(s%3600/60);return d?d+' d '+h+' h':h?h+' h '+m+' min':m?m+' min':s+' s'};
let macetas=[],tipos=[],actual=null,vista='lista',det=null,rango=86400,nHist=0,nCiclo=0;

async function pide(u,o={}){
 const c=new AbortController(),t=setTimeout(()=>c.abort(),15000);
 try{
  const r=await fetch(u,{method:o.m||'GET',signal:c.signal,headers:o.m?{'X-Maceta':'1','Content-Type':'application/json',...o.h}:{'X-Maceta':'1'},body:o.b&&JSON.stringify(o.b)}),j=await r.json();
  if(r.status==401)location.href='/entrar';
  if(!r.ok)throw new Error(typeof j.detail=='string'?j.detail:Array.isArray(j.detail)?j.detail.map(d=>d.msg.replace('Value error, ','')).join('. '):'Error '+r.status);
  return j;
 }catch(e){throw e.name=='AbortError'||e instanceof TypeError?new Error('Sin conexión con el servidor central'):e}finally{clearTimeout(t)}
}

/* ----- Nombre, valor con unidad, estado y procedencia de cada medición ----- */
function mediciones(m){
 const v=m.vivo;if(!v||!v.listo)return[];
 const sim=m.origen=='simulado',med=sim?'Simulado':'Medido por sensor',es=v.estados||[v.estado],q=m.calidad;
 const L=[{n:'Humedad del suelo',v:v.hum_pct,u:'%',bar:v.hum_pct,col:'hum',p:med,nota:'Relativa a la calibración del sensor',
  e:es.includes(0)?'Seca':es.includes(1)?'Encharcada':'Adecuada',mal:es.includes(0)||es.includes(1),
  q:q.includes('hum_saturada')?'Sensor en su tope: tierra muy seca o sonda desconectada':q.includes('hum_sin_senal')?'Sensor sin señal válida':''}];
 const luz={e:es.includes(2)?'Poca luz':es.includes(3)?'Mucha luz':'Adecuada',mal:es.includes(2)||es.includes(3),q:q.includes('luz_fuera_de_rango')?'Fuera del rango fiable del sensor':''};
 if(v.luz_lx!=null)L.push({n:'Luminosidad',v:num(v.luz_lx,0),u:'lx',p:med,nota:'Nivel de luz: '+v.luz_pct+' %',bar:v.luz_pct,col:'luz',...luz});
 else L.push({n:'Nivel de luz',v:v.luz_pct,u:'%',p:med,nota:'Escala logarítmica. Sin calibración en lux',bar:v.luz_pct,col:'luz',...luz});
 if(v.temp_c!=null)L.push({n:'Temperatura ambiental',v:num(v.temp_c),u:'°C',p:med});
 L.push({n:'Índice de salud',v:v.indice,u:'/100',bar:v.indice,col:'ind',p:'Estimado por reglas',est:1,nota:'No es una medición de la salud'},
  {n:'Tiempo sin regar',v:v.horas_sin_regar,u:'h',p:sim?'Simulado':'Calculado por el firmware',nota:sim?'':'Al reiniciar, la maceta se asume recién regada'});
 return L;
}
const tags=m=>(m.origen=='simulado'?'<span class="tag sim">Simulada</span> ':'<span class="tag">Real</span> ')+
 '<span class="pto '+(m.conectada?'si">● Conectada':'no">○ Sin conexión')+'</span>';

function pintaDetalle(){
 const m=macetas.find(x=>x.id==actual);
 if(!m){$('dN').textContent='No existe esa maceta';return}
 poner('elige',macetas.map(x=>'<option value="'+x.id+'">'+esc(x.nombre)+(x.origen=='simulado'?' (simulada)':'')+'</option>').join(''));$('elige').value=actual;
 $('dN').textContent=m.nombre+(m.especie?' · '+m.especie:'');poner('dTags',tags(m));
 document.querySelectorAll('.procH').forEach(e=>{e.textContent=m.origen=='simulado'?'Simulado':'Medido';e.classList.toggle('sim',m.origen=='simulado')});
 const v=m.vivo,ok=m.conectada&&v.listo;
 $('dAviso').hidden=ok;$('dAviso').textContent=m.conectada?'Leyendo sensores…':'Sin conexión con esta maceta. '+(m.ultimo_contacto?'Último contacto: '+fh(m.ultimo_contacto)+'. ':'')+'El historial guardado sigue disponible.';
 setAvatar(ok?v.estados||[v.estado]:[],ok?v.pers:null,ok);$('dFrase').textContent=ok?'«'+v.frase+'»':'';
 pintaMedidas(m);$('detalle').classList.toggle('virtual',m.origen=='simulado');
 const c=det&&det.id==actual&&det.config,F=[['Lecturas guardadas en el servidor',num(m.lecturas,0)]];
 if(ok&&v.uptime_s!=null)F.push(['Humedad, lectura cruda',v.hum_raw+' cuentas ADC (0–4095)'],['Luz, lectura cruda',v.luz_raw+' cuentas ADC (0–4095)'],['Señal WiFi',v.wifi_rssi+' dBm'],['Encendida hace',dur(v.uptime_s)],['Hora de internet en la maceta',v.hora_real?'Sí':'No'],['RAM libre',num(v.heap_libre/1024)+' KB'],['Almacenamiento usado',num(v.fs_usado/1024,0)+' de '+num(v.fs_total/1024,0)+' KB']);
 if(c&&c.calibracion){const u=c.umbrales,k=c.calibracion;F.push(['Seca por debajo de',u.sed+' %'],['Encharcada por encima de',u.encharcada+' %'],['Poca luz por debajo de',u.poca_luz+' %'],['Mucha luz por encima de',u.mucha_luz+' %'],['Estresada por debajo de',u.estres+'/100'],['Calibración de humedad (seco / húmedo)',k.hum_seco+' / '+k.hum_humedo+' cuentas ADC'],['Calibración de luz (oscuro / claro)',k.luz_oscuro_log+' / '+k.luz_claro_log+' cuentas ADC'])}
 poner('dTec',F.map(([a,b])=>'<tr><td>'+esc(a)+'</td><td>'+esc(b)+'</td></tr>').join(''));
 poner('dProp',m.origen=='real'?'<a href="'+esc(m.url)+'" target="_blank" rel="noopener">Abrir el dashboard propio de esta maceta</a>':'Las macetas simuladas no tienen dashboard propio.');
}

function limpiaGraficas(){['ch','cl','ci'].forEach(id=>{const c=$(id);c._o=null;c._px=null;c.getContext('2d').clearRect(0,0,1e5,1e5)})}
async function cargaHist(){
 const mio=++nHist,id=actual,s=rango,x1=Math.floor(Date.now()/1000);if(!id)return;
 try{
  const [d,L]=await Promise.all([pide('/api/v1/macetas/'+id),pide('/api/v1/macetas/'+id+'/lecturas?limite=20000&desde='+(x1-s))]);
  if(mio!=nHist||id!=actual)return;
  det=d;pintaDetalle();
  const u=d.config&&d.config.umbrales,c={};L.forEach(x=>c[x.fuente_hora]=(c[x.fuente_hora]||0)+1);
  $('hMsg').textContent=num(L.length,0)+' lecturas.'+(c.servidor?' '+c.servidor+' ubicadas con la hora del PC.':'')+(c.corregida?' '+c.corregida+' con hora corregida.':'');
  const fx=t=>new Date(t*1000).toLocaleString('es-CO',s>86400?{day:'numeric',month:'short'}:{hour:'2-digit',minute:'2-digit'});
  const g=(cv,k,col,um,dash,un)=>grafica(cv,{x0:x1-s,x1,y0:0,y1:100,pts:L.map(x=>[x.t,x[k]]),col,um,dash,gap:960,fx,ft:q=>fh(q[0])+' · '+q[1]+un});
  g('ch','hum_pct','--hum',u&&[[u.sed,'Seca'],[u.encharcada,'Encharcada']],false,' %');
  g('cl','luz_pct','--luz',u&&[[u.poca_luz,'Poca luz'],[u.mucha_luz,'Mucha luz']],false,' %');
  g('ci','indice','--ind',u&&[[u.estres,'Estresada']],true,'/100');
 }catch(e){if(mio==nHist&&id==actual){$('hMsg').textContent='No se pudo cargar: '+e.message;limpiaGraficas()}}
}

function ruta(){
 const m=/^#m\/([\w-]+)$/.exec(location.hash);actual=m?m[1]:null;vista=actual?'det':location.hash=='#cap'?'cap':location.hash=='#biblioteca'?'bib':'lista';det=null;nHist++;capCfg=false;
 $('lista').hidden=vista!='lista';$('capacidad').hidden=vista!='cap';$('biblioteca').hidden=vista!='bib';[['navM','lista'],['navC','cap']].forEach(([i,v])=>v==vista?$(i).setAttribute('aria-current','page'):$(i).removeAttribute('aria-current'));$('detalle').hidden=!actual;scrollTo(0,0);
 if(actual){limpiaGraficas();$('hMsg').textContent='Cargando…';$('dirMsg').textContent='';const x=macetas.find(q=>q.id==actual);$('dU').value=x?x.url:'';pintaDetalle();cargaHist();abreFotos()}else vista=='cap'?pintaCap():vista=='bib'?cargaBib():pintaLista();
}
const pinta=()=>vista=='det'?pintaDetalle():vista=='cap'?pintaCap():vista=='bib'?0:pintaLista();
async function refresca(){
 const mio=++nCiclo,[s,m]=await Promise.all([pide('/api/v1/salud'),pide('/api/v1/macetas')]);if(mio!=nCiclo)return;
 const primera=!tipos.length;tipos=s.tipos;macetas=m;$('con').textContent='Servidor en línea';$('con').className='';
 primera?ruta():pinta();
}
async function ciclo(){
 try{await refresca()}
 catch(e){ // Sin servidor no se muestran valores viejos como si fueran actuales
  $('con').textContent='Sin servidor';$('con').className='off';macetas=macetas.map(m=>({...m,conectada:false,vivo:null,calidad:[]}));if(tipos.length)pinta();
 }
 setTimeout(ciclo,3000);
}

$('elige').onchange=e=>location.hash='#m/'+e.target.value;
$('rg').onclick=e=>{const r=e.target.dataset.r;if(r){rango=+r;$('rg').querySelectorAll('button').forEach(b=>b.setAttribute('aria-pressed',b==e.target));cargaHist()}};
/* Una simulada no pide dirección: el servidor la enciende */
const altaSim=()=>tipos.length>1&&$('aO').value=='simulado';
const altaCambia=()=>{const s=altaSim();$('aDir').hidden=s;$('aU').required=!s;$('aSim').hidden=!s};$('aO').onchange=altaCambia;
$('alta').onsubmit=async e=>{e.preventDefault();const b=e.submitter||$('alta').querySelector('button'),m=$('altaMsg');b.disabled=true;
 try{await pide('/api/v1/macetas?personaje='+encodeURIComponent(persAlta()),{m:'POST',b:{nombre:$('aN').value,url:altaSim()?'':$('aU').value,escenario:$('aX').value,especie:$('aE').value,origen:tipos.length>1?$('aO').value:tipos[0]}});m.textContent='Maceta agregada.';cargaPers();$('alta').reset();altaCambia();refresca().catch(()=>{})}
 catch(x){m.textContent='No se agregó: '+x.message}b.disabled=false};
$('dir').onsubmit=async e=>{e.preventDefault();const m=$('dirMsg');
 try{await pide('/api/v1/macetas/'+actual+'/direccion',{m:'PATCH',b:{url:$('dU').value}});m.textContent='Dirección cambiada.';refresca().catch(()=>{})}catch(x){m.textContent='No se cambió: '+x.message}};
addEventListener('hashchange',ruta);
setInterval(()=>{if(actual)cargaHist()},60000);
ciclo();
