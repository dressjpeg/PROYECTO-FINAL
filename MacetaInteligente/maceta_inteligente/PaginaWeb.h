// Página del dashboard. Va en un .h porque el IDE de Arduino confunde el JavaScript con C++ en un .ino
#pragma once
const char PAGINA[] = R"rawliteral(<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Maceta inteligente</title><link rel="icon" href="data:,">
<style>
:root{color-scheme:light dark;--bg:#f2f4ef;--sup:#fcfcfb;--tx:#12160f;--tx2:#52564c;--bd:#d8dcd2;--hum:#2a78d6;--luz:#eda100;--ind:#1baf7a;--alt:#008300;--rojo:#b3261e;--nar:#8a4b00;--pri:#1d5b38;--prit:#fff}
@media(prefers-color-scheme:dark){:root{--bg:#10120f;--sup:#1a1a19;--tx:#f0efec;--tx2:#c3c2b7;--bd:#3a3c37;--hum:#3987e5;--luz:#c98500;--ind:#199e70;--alt:#0ca30c;--rojo:#b3261e;--nar:#8a4b00;--pri:#7fd0a0;--prit:#0c2416}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--tx);font:17px/1.4 system-ui,sans-serif}
main,header{max-width:760px;margin:auto;padding:12px 16px}header{display:flex;justify-content:space-between;align-items:center;gap:8px}
h1{font-size:21px;margin:0}h2{font-size:19px;margin:22px 0 8px}h3{font-size:16px;margin:12px 0 2px}p{margin:6px 0}
#con{font-size:15px;font-weight:600}.off #con{background:var(--rojo);color:#fff;padding:5px 11px;border-radius:99px}
nav{position:sticky;top:0;z-index:2;background:var(--bg);border-bottom:1px solid var(--bd)}nav div{max-width:760px;margin:auto;display:flex;padding:0 8px}
nav button{flex:1;min-width:0;border:0;border-radius:0;background:none;color:var(--tx2);font:600 15px system-ui;padding:14px 2px;border-bottom:3px solid transparent}
nav button[aria-selected=true]{color:var(--tx);border-color:var(--pri)}
.g{display:grid;grid-template-columns:1fr 1fr;gap:12px}.a{grid-column:1/-1}
.c{background:var(--sup);border:1px solid var(--bd);border-radius:12px;padding:14px;min-width:0}
.est{border-style:dashed;border-width:2px}.n{font-size:46px;font-weight:700;line-height:1.15}.n small{font-size:22px}
.et{font-size:14px;color:var(--tx2)}.tag{display:inline-block;font-size:13px;border:1px solid var(--bd);border-radius:6px;padding:1px 7px;color:var(--tx2)}
.est .tag{border-style:dashed}.ba{height:8px;background:var(--bd);border-radius:4px;overflow:hidden;margin-top:8px}.ba i{display:block;height:100%;width:0}
.al{color:#fff;border-radius:12px;padding:14px;margin-bottom:10px;font-weight:600}.rojo{background:var(--rojo)}.nar{background:var(--nar)}
button,.bt{font:600 16px system-ui;border:1px solid var(--bd);background:var(--sup);color:var(--tx);border-radius:10px;padding:11px 14px;text-decoration:none;display:inline-block;cursor:pointer}
.p{background:var(--pri);color:var(--prit);border-color:var(--pri)}.sel{display:flex;gap:8px;margin:8px 0}.sel button{flex:1}.sel [aria-pressed=true]{background:var(--pri);color:var(--prit)}
button:focus-visible,a:focus-visible,input:focus-visible{outline:3px solid var(--hum);outline-offset:2px}
canvas{width:100%;display:block;touch-action:pan-y}ul{padding:0;list-style:none;margin:0}li{padding:10px 0;border-bottom:1px solid var(--bd)}
label{display:block;margin:10px 0 4px;font-weight:600}input{width:100%;font:17px system-ui;padding:11px;border:1px solid var(--bd);border-radius:10px;background:var(--bg);color:var(--tx)}
table{width:100%;border-collapse:collapse}td{padding:9px 0;border-bottom:1px solid var(--bd);overflow-wrap:anywhere}td:last-child{text-align:right;font-variant-numeric:tabular-nums}
.f{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px}.x{float:right;padding:6px 10px;font-size:14px}[hidden]{display:none!important}
.off .vivo{display:none}#sin{display:none}.off #sin{display:block}
</style></head><body class="off">
<header><h1>Maceta inteligente</h1><span id="con" role="status">Conectando…</span></header>
<nav><div role="tablist"><button role="tab" data-t="vivo" aria-selected="true">En vivo</button><button role="tab" data-t="hist" aria-selected="false">Historial</button><button role="tab" data-t="crec" aria-selected="false">Crecer</button><button role="tab" data-t="tec" aria-selected="false">Técnico</button></div></nav>
<main>
<section id="vivo"><div id="sin" class="c"><b id="sint">Conectando con la maceta…</b><p class="et" id="sind">Los datos aparecerán al recibir la primera lectura.</p></div>
<div class="vivo"><div id="banner" aria-live="assertive"></div><div class="g">
<div class="c"><span class="tag">Medido por sensor</span><h3>Humedad</h3><div class="n"><span id="h"></span><small>%</small></div><div class="ba"><i id="hb" style="background:var(--hum)"></i></div></div>
<div class="c"><span class="tag">Medido por sensor</span><h3>Luz</h3><div class="n"><span id="l"></span><small>%</small></div><div class="ba"><i id="lb" style="background:var(--luz)"></i></div></div>
<div class="c est a"><span class="tag">Estimado por reglas</span><h3>Índice de salud (estimado)</h3><div class="n"><span id="i"></span><small>/100</small></div><div class="ba"><i id="ib" style="background:var(--ind)"></i></div><p class="et">Es una estimación por reglas (humedad 50 %, luz 30 %, tiempo sin regar 20 %). No es una medición de la salud de la planta.</p></div>
<div class="c est a"><span class="tag">Estimado por reglas</span><h3>Estado</h3><div style="font-size:30px;font-weight:700" id="e"></div><p id="fr"></p><div id="av" class="et"></div></div>
<div class="c a"><span class="tag">Calculado por el firmware</span><h3>Horas sin regar</h3><div class="n"><span id="hr"></span><small> h</small></div><p class="et">Desde el último riego detectado o desde el encendido: al reiniciar, la maceta se asume recién regada.</p><button id="riego">Marcar riego ahora</button></div>
</div><h2>Alertas activas</h2><ul id="act"></ul><h2>Alertas resueltas</h2><ul id="res"></ul>
<div class="f"><button id="vib" aria-pressed="false">Vibrar con alertas: no</button></div></div></section>

<section id="hist" hidden><h2>Historial</h2><div class="sel" id="rg"><button data-r="1h" aria-pressed="false">1 h</button><button data-r="24h" aria-pressed="true">24 h</button><button data-r="7d" aria-pressed="false">7 días</button></div>
<p class="et" id="hmsg"></p>
<div class="c"><h3>Humedad (%) <span class="tag">Medido</span></h3><canvas id="ch" height="190"></canvas></div><br>
<div class="c"><h3>Luz (%) <span class="tag">Medido</span></h3><canvas id="cl" height="190"></canvas></div><br>
<div class="c est"><h3>Índice de salud <span class="tag">Estimado</span></h3><canvas id="ci" height="190"></canvas></div>
<p class="et">Una lectura cada 5 minutos. Líneas punteadas: umbrales. Toca una gráfica para ver valores.</p><div class="f"><a class="bt" href="/api/historial.csv">Descargar historial.csv</a></div></section>

<section id="crec" hidden><h2>Registrar crecimiento</h2><div class="c"><span class="tag">Registrado a mano</span><p class="et">Ningún sensor mide el crecimiento: estos datos los escribes tú.</p>
<form id="fm"><label for="ff">Fecha</label><input id="ff" type="date" required><label for="fa">Altura (cm)</label><input id="fa" type="text" inputmode="decimal" placeholder="12,5" required><label for="fh">Número de hojas</label><input id="fh" type="number" min="0" max="999" step="1" inputmode="numeric" required><label for="fn">Nota (opcional)</label><input id="fn" maxlength="60" placeholder="hoja nueva, trasplante, poda"><div class="f"><button class="p">Guardar</button></div><p id="fmsg" role="status"></p></form></div>
<h2>Crecimiento</h2><div class="c"><h3>Altura (cm) <span class="tag">A mano</span></h3><canvas id="ca" height="180"></canvas><h3>Hojas <span class="tag">A mano</span></h3><canvas id="cj" height="150"></canvas><p class="et">El rombo marca un registro con nota.</p></div>
<h2>Crecimiento vs. condiciones</h2><div class="sel" id="dg"><button data-d="30" aria-pressed="true">30 días</button><button data-d="90" aria-pressed="false">90 días</button><button data-d="365" aria-pressed="false">365 días</button></div>
<div class="c"><h3>Altura (cm) <span class="tag">A mano</span></h3><canvas id="va" height="150"></canvas><h3>Humedad promedio por día (%) <span class="tag">Medido</span></h3><canvas id="vh" height="130"></canvas><h3>Luz promedio por día (%) <span class="tag">Medido</span></h3><canvas id="vl" height="130"></canvas><p><b>Relación observada, no causa comprobada</b></p><p class="et" id="dmsg"></p></div>
<h2>Registros</h2><ul id="cr"></ul><div class="f"><a class="bt" href="/api/crecimiento.csv">Descargar crecimiento.csv</a><a class="bt" href="/api/diario.csv">Descargar diario.csv</a></div></section>

<section id="tec" hidden><h2>Vista técnica</h2><div class="c"><table class="vivo"><tbody id="tt"></tbody></table><p id="tsin" class="et">Se muestra al recibir datos.</p></div><h2>Umbrales y calibración</h2><div class="c"><table><tbody id="tc"></tbody></table></div></section>
</main>
<script>
'use strict';
const $=i=>document.getElementById(i),css=v=>getComputedStyle(document.documentElement).getPropertyValue(v).trim();
const esc=s=>String(s).replace(/[&<>"']/g,c=>'&#'+c.charCodeAt(0)+';');
let cfg=null,est=null,rango='24h',dias=30,regs=[],diario=null,vistas=null,vib=false;
try{vib=localStorage.vib=='1'}catch(e){}
async function pide(u,o={}){const c=new AbortController(),t=setTimeout(()=>c.abort(),o.ms||5000);
 try{const r=await fetch(u,{method:o.m||'GET',body:o.b,signal:c.signal,cache:'no-store',headers:o.m?{'X-Maceta':'1'}:{}}),j=await r.json();if(!r.ok)throw new Error(j.error||'Error '+r.status);return j}
 catch(e){throw e.name=='AbortError'||e instanceof TypeError?new Error('Sin conexión con la maceta'):e}finally{clearTimeout(t)}}
const dur=s=>{s=Math.floor(s);const d=Math.floor(s/86400),h=Math.floor(s%86400/3600),m=Math.floor(s%3600/60);return d?d+' d '+h+' h':h?h+' h '+m+' min':m?m+' min':s+' s'};
const fh=t=>new Date(t*1000).toLocaleString('es-CO',{day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit'});
const num=(v,d=1)=>Number(v).toLocaleString('es-CO',{maximumFractionDigits:d});
const filas=a=>a.map(([k,v])=>'<tr><td>'+esc(k)+'</td><td>'+esc(v)+'</td></tr>').join('');
const poner=(id,h)=>{const e=$(id);if(e._h!==h){e._h=h;e.innerHTML=h}};
function pinta(d){
 document.body.classList.remove('off');$('con').textContent='En línea';$('tsin').hidden=true;
 $('h').textContent=d.hum_pct;$('l').textContent=d.luz_pct;$('i').textContent=d.indice;$('hb').style.width=d.hum_pct+'%';$('lb').style.width=d.luz_pct+'%';$('ib').style.width=d.indice+'%';
 $('e').textContent=d.estado_texto;$('fr').textContent='«'+d.frase+'»';$('hr').textContent=d.horas_sin_regar;
 $('av').textContent=d.avisos.length?'Avisos actuales: '+d.avisos.map(a=>a.texto).join(', '):'Sin avisos.';
 const ahora=Date.now()/1000;
 poner('banner',d.alertas.map(a=>'<div class="al '+(a.estado<2?'rojo':'nar')+'">⚠ '+esc(a.texto)+' desde hace '+dur(a.desde_s)+'</div>').join(''));
 poner('act',d.alertas.map(a=>'<li><b>'+esc(a.texto)+'</b><br>Inicio: '+fh(a.inicio||ahora-a.desde_s)+' · dura '+dur(a.desde_s)+(a.inicio?'':' (hora del celular)')+'</li>').join('')||'<li class="et">Ninguna</li>');
 poner('res',d.resueltas.map(a=>'<li><b>'+esc(a.texto)+'</b><br>'+(a.inicio?'Inicio: '+fh(a.inicio)+' · fin: '+fh(a.fin):'Sin hora real')+' · duró '+dur(a.duracion_s)+'</li>').join('')||'<li class="et">Ninguna</li>');
 const cl=d.alertas.map(a=>a.clave);if(vistas&&vib&&cl.some(c=>!vistas.includes(c))&&navigator.vibrate)navigator.vibrate([300,150,300]);vistas=cl;
 poner('tt',filas([['hum_raw',d.hum_raw],['luz_raw',d.luz_raw],['RSSI (dBm)',d.wifi_rssi],['IP',d.ip],['Encendida hace',dur(d.uptime_s)],['uptime_s',d.uptime_s],['Hora real (NTP)',d.hora_real?fh(d.epoch):'No disponible'],['LittleFS',d.fs_ok?num(d.fs_usado/1024)+' de '+num(d.fs_total/1024)+' KB ('+num(100*d.fs_usado/d.fs_total)+' %)':'No disponible'],['RAM libre',num(d.heap_libre/1024)+' KB'],['RAM libre mínima',num(d.heap_min/1024)+' KB'],['Arranque n.º',d.arranque]]))}
function sinCon(t,x){est=null;document.body.classList.add('off');$('con').textContent=t;$('sint').textContent=t;$('sind').textContent=x;$('tsin').hidden=false;
 for(const k of['h','l','i','e','fr','hr','av'])$(k).textContent='';for(const k of['banner','act','res','tt'])poner(k,'')}
async function ciclo(){try{const d=await pide('/api/estado');if(d.listo){est=d;pinta(d)}else sinCon('Leyendo…','El sensor aún no entrega su primera lectura.');if(!cfg)cargaCfg()}
 catch(e){sinCon('Sin conexión','No hay respuesta de la maceta. Revisa que esté encendida y en la misma red.')}setTimeout(ciclo,1000)}
let cfgPide=false;
async function cargaCfg(){if(cfgPide)return;cfgPide=true;try{cfg=await pide('/api/config');const u=cfg.umbrales,c=cfg.calibracion,t=cfg.tiempos;
 poner('tc',filas([['Sed: humedad <',u.sed+' %'],['Encharcada: humedad >',u.encharcada+' %'],['Poca luz: luz <',u.poca_luz+' %'],['Mucha luz: luz >',u.mucha_luz+' %'],['Estresada: índice <',u.estres],['HUM_SECO',c.hum_seco],['HUM_HUMEDO',c.hum_humedo],['LUZ_OSCURO_LOG',c.luz_oscuro_log],['LUZ_CLARO_LOG',c.luz_claro_log],['Escala de luz',c.luz_escala],['Confirmación',t.confirmar_ms/1000+' s'],['Alerta de agua',t.alerta_agua_min+' min'],['Otras alertas',t.alerta_otras_min+' min']]));if(!$('hist').hidden)cargaHist()}catch(e){}cfgPide=false}

/* Gráfica propia en canvas */
function grafica(id,o){const cv=$(id);cv._o=o;const w=cv.clientWidth,hh=+(cv.dataset.h=cv.dataset.h||cv.getAttribute('height')),r=devicePixelRatio||1;if(!w)return;
 cv.width=w*r;cv.height=hh*r;cv.style.height=hh+'px';
 const x=cv.getContext('2d');x.setTransform(r,0,0,r,0,0);x.clearRect(0,0,w,hh);x.font='12px system-ui';
 const L=34,R=w-10,T=12,B=hh-22,px=t=>L+(t-o.x0)/(o.x1-o.x0||1)*(R-L),py=v=>B-(v-o.y0)/(o.y1-o.y0||1)*(B-T);
 const tx2=css('--tx2'),bd=css('--bd'),col=css(o.col);x.lineWidth=1;x.fillStyle=tx2;x.textAlign='right';x.textBaseline='middle';
 for(let k=0;k<=2;k++){const v=o.y0+(o.y1-o.y0)*k/2,y=py(v);x.strokeStyle=bd;x.beginPath();x.moveTo(L,y);x.lineTo(R,y);x.stroke();x.fillText(num(v),L-5,y)}
 x.textBaseline='alphabetic';const nt=w<500?2:4;for(let k=0;k<=nt;k++){const t=o.x0+(o.x1-o.x0)*k/nt;x.textAlign=k==0?'left':k==nt?'right':'center';x.fillText(o.fx(t),px(t),hh-5)}
 (o.um||[]).forEach(u=>{const y=py(u[0]);x.strokeStyle=tx2;x.setLineDash([4,4]);x.beginPath();x.moveTo(L,y);x.lineTo(R,y);x.stroke();x.setLineDash([]);x.textAlign='left';x.fillStyle=tx2;x.fillText(u[1]+' '+u[0],L+4,y-3)});
 const p=o.pts;if(!p.length){x.textAlign='center';x.fillStyle=tx2;x.font='15px system-ui';x.fillText('Aún no hay datos',(L+R)/2,(T+B)/2);cv._px=null;return}
 x.save();x.beginPath();x.rect(L-6,0,R-L+12,B+6);x.clip();x.fillStyle=x.strokeStyle=col;x.lineWidth=2;x.lineJoin='round';
 if(o.bar){const bw=Math.max(1,Math.min(22,(R-L)/((o.x1-o.x0)/86400)-2));p.forEach(q=>{const X=px(q[0])-bw/2,y=py(q[1]);x.beginPath();x.roundRect?x.roundRect(X,y,bw,Math.max(1,B-y),[Math.min(4,bw/2),Math.min(4,bw/2),0,0]):x.rect(X,y,bw,Math.max(1,B-y));x.fill()})}
 else{if(o.dash)x.setLineDash([6,3]);x.beginPath();p.forEach((q,k)=>{const c=k&&(!o.gap||q[0]-p[k-1][0]<=o.gap);c?x.lineTo(px(q[0]),py(q[1])):x.moveTo(px(q[0]),py(q[1]))});x.stroke();x.setLineDash([]);
  p.forEach((q,k)=>{const solo=o.gap&&(!k||q[0]-p[k-1][0]>o.gap)&&(k==p.length-1||p[k+1][0]-q[0]>o.gap);if(!o.pt&&!solo)return;const X=px(q[0]),Y=py(q[1]);x.strokeStyle=css('--sup');x.beginPath();
   if(q[2]){x.moveTo(X,Y-8);x.lineTo(X+8,Y);x.lineTo(X,Y+8);x.lineTo(X-8,Y);x.closePath()}else x.arc(X,Y,4.5,0,7);x.fill();x.stroke()})}
 x.restore();cv._px=px;
 if(o.sel!=null&&p[o.sel]){const q=p[o.sel],X=px(q[0]),Y=py(q[1]);x.strokeStyle=tx2;x.lineWidth=1;x.beginPath();x.moveTo(X,T);x.lineTo(X,B);x.stroke();x.fillStyle=col;x.beginPath();x.arc(X,Y,5,0,7);x.fill();
  x.font='600 13px system-ui';let s=o.ft(q);while(x.measureText(s).width>R-L-16&&s.length>8)s=s.slice(0,-2)+'…';const W=x.measureText(s).width+14,X0=Math.max(L,Math.min(R-W,X-W/2));x.fillStyle=css('--tx');x.fillRect(X0,0,W,23);x.fillStyle=css('--sup');x.textAlign='left';x.fillText(s,X0+7,16)}}
document.querySelectorAll('canvas').forEach(cv=>{const m=e=>{const o=cv._o;if(!o||!cv._px||!o.pts.length)return;const X=e.clientX-cv.getBoundingClientRect().left;let b=0,bd=1e9;o.pts.forEach((q,k)=>{const d=Math.abs(cv._px(q[0])-X);if(d<bd){bd=d;b=k}});if(o.sel!==b){o.sel=b;grafica(cv.id,o)}};
 cv.onpointermove=m;cv.onpointerdown=m;cv.onpointerleave=e=>{if(e.pointerType=='mouse'&&cv._o){cv._o.sel=null;grafica(cv.id,cv._o)}}});
let rt;addEventListener('resize',()=>{clearTimeout(rt);rt=setTimeout(()=>document.querySelectorAll('canvas').forEach(c=>c._o&&grafica(c.id,c._o)),150)});

let hn=0;
async function cargaHist(){const mio=++hn;$('hmsg').textContent='Cargando…';try{const r=await pide('/api/historial?rango='+rango,{ms:20000});if(mio!=hn)return;
 const n=Date.now()/1000,s={'1h':3600,'24h':86400,'7d':604800}[rango],ah=r.hora_real?r.ahora:n;let sin=0,cel=0;const P=[];
 r.datos.forEach(d=>{let t=d[0];if(d[1]==0){if(d[8]==r.arranque){t=n-(r.uptime_s-d[0]);cel++}else{sin++;return}}if(t>=ah-s&&t<=ah+300)P.push([t,d[2],d[3],d[4]])});P.sort((a,b)=>a[0]-b[0]);
 $('hmsg').textContent=P.length+' lecturas.'+(cel?' '+cel+' ubicadas con la hora del celular.':'')+(sin?' '+sin+' sin hora conocida: solo aparecen en el CSV.':'');
 const u=cfg&&cfg.umbrales,fx=t=>new Date(t*1000).toLocaleString('es-CO',rango=='7d'?{day:'numeric',month:'short'}:{hour:'2-digit',minute:'2-digit'});
 const g=(id,k,col,um,dash)=>grafica(id,{x0:ah-s,x1:ah,y0:0,y1:100,pts:P.map(q=>[q[0],q[k]]),col,um,dash,gap:960,fx,ft:q=>fh(q[0])+' · '+q[1]+(k==3?'':' %')});
 g('ch',1,'--hum',u&&[[u.sed,'Sed'],[u.encharcada,'Encharcada']]);g('cl',2,'--luz',u&&[[u.poca_luz,'Poca luz'],[u.mucha_luz,'Mucha luz']]);g('ci',3,'--ind',u&&[[u.estres,'Estresada']],true)}
 catch(e){if(mio!=hn)return;$('hmsg').textContent='No se pudo cargar: '+e.message;['ch','cl','ci'].forEach(limpia)}}
function limpia(id){const c=$(id);c._o=null;c._px=null;c.getContext('2d').clearRect(0,0,1e5,1e5)}

const tf=f=>new Date(f+'T12:00:00').getTime()/1000,fd=t=>new Date(t*1000).toLocaleDateString('es-CO',{day:'2-digit',month:'2-digit',year:'2-digit'});
const hoy=()=>{const d=new Date();return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0')};
async function cargaCrec(){try{const a=await pide('/api/crecimiento',{ms:10000});regs=a.registros.sort((x,y)=>x.fecha<y.fecha?-1:x.fecha>y.fecha?1:x.id-y.id);pintaCrec()}
 catch(e){poner('cr','<li>No se pudo cargar: '+esc(e.message)+'</li>');['ca','cj'].forEach(limpia)}cargaDia()}
function pintaCrec(){const pa=regs.map(r=>[tf(r.fecha),r.altura,r.nota]),pj=regs.map(r=>[tf(r.fecha),r.hojas,r.nota]);
 let a=pa.length?pa[0][0]:tf(hoy()),b=pa.length?pa[pa.length-1][0]:a;if(b-a<86400*2){a-=86400;b+=86400}
 const op=(p,u)=>({x0:a,x1:b,y0:0,y1:tope(p),pts:p,pt:true,fx:fd,ft:q=>fd(q[0])+' · '+num(q[1])+u+(q[2]?' · '+q[2]:'')});
 grafica('ca',{...op(pa,' cm'),col:'--alt'});grafica('cj',{...op(pj,' hojas'),col:'--alt',dash:true});
 poner('cr',regs.map((r,k)=>{let v='';if(k){const d=(tf(r.fecha)-tf(regs[k-1].fecha))/604800;v=d>0?' · '+num((r.altura-regs[k-1].altura)/d,2)+' cm/semana':' · tasa no calculable (misma fecha)'}
  return '<li><button class="x" data-id="'+r.id+'">Borrar</button><b>'+fd(tf(r.fecha))+'</b><br>'+num(r.altura)+' cm · '+r.hojas+' hojas'+v+(r.nota?'<br>«'+esc(r.nota)+'»':'')+'</li>'}).reverse().join('')||'<li class="et">Aún no hay registros</li>')}
const tope=p=>{let m=0;p.forEach(q=>m=Math.max(m,q[1]));const e=m<=10?2:m<=50?10:20;return Math.max(e,Math.ceil(m*1.1/e)*e)};
let dn=0;
async function cargaDia(){const mio=++dn;try{const r=await pide('/api/diario?dias='+dias,{ms:15000});if(mio!=dn)return;
 const b=tf(hoy())+43200,a=b-dias*86400,F=r.dias.concat(r.hoy_parcial?[r.hoy_parcial]:[]),D=F.filter(d=>d[0]!='sin_hora').map(d=>[tf(d[0]),...d.slice(1)]).filter(d=>d[0]>=a),sin=F.filter(d=>d[0]=='sin_hora').length;
 const pa=regs.map(q=>[tf(q.fecha),q.altura,q.nota]).filter(q=>q[0]>=a),base={x0:a,x1:b,y0:0,fx:fd};
 grafica('va',{...base,y1:tope(pa),pts:pa,pt:true,col:'--alt',ft:q=>fd(q[0])+' · '+num(q[1])+' cm'+(q[2]?' · '+q[2]:'')});
 const g=(id,k,col)=>grafica(id,{...base,y1:100,bar:true,pts:D.map(d=>[d[0],d[k],d[k+1],d[k+2]]),col,ft:q=>fd(q[0])+' · '+num(q[1])+' % (mín '+q[2]+', máx '+q[3]+')'});g('vh',1,'--hum');g('vl',4,'--luz');
 $('dmsg').textContent=D.length+' días con condiciones; el de hoy es parcial.'+(sin?' '+sin+' sin hora real: solo en diario.csv.':'')}
 catch(e){if(mio!=dn)return;$('dmsg').textContent='No se pudo cargar: '+e.message;['va','vh','vl'].forEach(limpia)}}
$('fm').onsubmit=async e=>{e.preventDefault();const a=$('fa').value.trim().replace(',','.'),m=$('fmsg'),bt=$('fm').querySelector('button');if(!/^\d{1,3}(\.\d{1,2})?$/.test(a)||+a>300){m.textContent='La altura debe estar entre 0 y 300 cm.';return}
 bt.disabled=true;try{await pide('/api/crecimiento',{m:'POST',ms:8000,b:new URLSearchParams({fecha:$('ff').value,altura:a,hojas:$('fh').value,nota:$('fn').value.trim()})});m.textContent='Registro guardado.';$('fa').value=$('fh').value=$('fn').value='';cargaCrec()}catch(x){m.textContent='No se guardó: '+x.message}bt.disabled=false};
$('cr').onclick=async e=>{const id=e.target.dataset.id;if(!id||!confirm('¿Borrar este registro?'))return;try{await pide('/api/crecimiento?id='+id,{m:'DELETE',ms:8000});cargaCrec()}catch(x){alert(x.message)}};
$('riego').onclick=async()=>{if(!confirm('¿Marcar un riego ahora? Reinicia las horas sin regar.'))return;try{await pide('/api/riego',{m:'POST'})}catch(x){alert('No se marcó: '+x.message)}};
const tv=()=>{$('vib').textContent='Vibrar con alertas: '+(vib?'sí':'no');$('vib').setAttribute('aria-pressed',vib)};tv();if(!navigator.vibrate)$('vib').hidden=true;
$('vib').onclick=()=>{vib=!vib;try{localStorage.vib=vib?'1':'0'}catch(e){}tv();if(vib)navigator.vibrate(80)};
const marca=(c,b)=>c.querySelectorAll('button').forEach(x=>x.setAttribute('aria-pressed',x==b));
$('rg').onclick=e=>{const r=e.target.dataset.r;if(r){rango=r;marca($('rg'),e.target);cargaHist()}};
$('dg').onclick=e=>{const d=e.target.dataset.d;if(d){dias=+d;marca($('dg'),e.target);cargaDia()}};
const abre={hist:cargaHist,crec:cargaCrec,vivo(){},tec(){}};
document.querySelectorAll('nav button').forEach(b=>b.onclick=()=>{document.querySelectorAll('nav button').forEach(x=>{x.setAttribute('aria-selected',x==b);$(x.dataset.t).hidden=x!=b});scrollTo(0,0);abre[b.dataset.t]()});
setInterval(()=>{if(!$('hist').hidden)cargaHist()},300000);
$('ff').value=hoy();ciclo();
</script></body></html>)rawliteral";
