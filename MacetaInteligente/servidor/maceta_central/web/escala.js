'use strict';
/* Escalabilidad: conectadas, registradas, capacidad y cupo. Solo cuentan las macetas reales. */
let capCfg=false;
const PC='<rect x="3" y="5" width="18" height="11" rx="1.5"/><path d="M8 20h8M12 16v4"/>';
ICONO.con='<path d="M3 9a13 13 0 0 1 18 0M6 12.5a8.5 8.5 0 0 1 12 0M9 16a4 4 0 0 1 6 0"/><path d="M12 19v.5"/>';
ICONO.reg=MACETA;ICONO.cap='<path d="M4 18a9 9 0 1 1 16 0M12 15l4-5"/>';ICONO.dis='<path d="M12 5v14M5 12h14"/>';
function kpi(k,titulo,valor,pct,nota,i){
 const z=$('kpis');let e=z.querySelector('.kpi.'+k);
 if(!e){e=document.createElement('div');e.className='kpi '+k;e.style.animationDelay=i*90+'ms';
  e.innerHTML='<h3></h3><svg viewBox="0 0 100 100" aria-hidden="true">'+aro(42,'fondo')+aro(42,'nivel')+'<g transform="translate(29 29) scale(1.75)" class="ico">'+ICONO[k]+'</g></svg><b class="grande"></b><span class="et"></span>';z.append(e)}
 e.querySelector('h3').textContent=titulo;nivel(e.querySelector('.nivel'),pct);
 const b=e.querySelector('b');if(valor==null){cancelAnimationFrame(b._r);b._t=b._n=null;b.textContent='—'}else numero(b,String(valor));
 e.querySelector('span').textContent=nota;
}
async function pintaCap(){
 try{
  const d=await pide('/api/v1/capacidad');if(vista!='cap')return;const c=d.capacidad,f=d.config,pc=n=>c?100*n/c:0;
  $('capError').hidden=true;
  kpi('con','Conectadas ahora',d.conectadas,pc(d.conectadas),'Respondieron en los últimos 30 s',0);
  kpi('reg','Registradas',d.registradas,pc(d.registradas),'Ocupan cupo aunque estén apagadas',1);
  kpi('cap','Capacidad máxima estimada',c,c==null?0:100,c==null?'Falta el límite de la red':'La limita: '+d.limitante,2);
  kpi('dis','Cupo disponible',d.disponible,pc(d.disponible||0),d.excedida?'⚠ Hay más registradas que cupos':'Macetas que aún se pueden agregar',3);
  const reales=macetas.filter(m=>m.origen=='real'),L=[],ic=(cl,t,p)=>L.push('<i class="'+cl+'" title="'+esc(t)+'"><svg viewBox="0 0 24 24">'+p+'</svg></i>'),tope=f.limite_wifi;
  if(tope!=null&&tope<=64){
   for(let i=0;i<Math.min(f.otros_equipos,tope);i++)ic('equipo','Equipo que no es maceta (por ejemplo, el PC)',PC);
   reales.forEach(m=>ic(m.conectada?'si':'apagada',m.nombre+(m.conectada?': conectada':': registrada, sin conexión'),MACETA));
   while(L.length<tope)ic('','Cupo libre','<path d="M12 8v8M8 12h8"/>')}
  $('cuposCaja').hidden=!L.length;poner('cupos',L.join(''));
  $('cuposTxt').textContent=tope==null?'':f.red+': '+tope+' cupos en total. Gris: otros equipos. Verde: maceta conectada. Azul: registrada sin conexión. Punteado: libre.';
  poner('recursos',d.recursos.map(r=>{const lim=r.limite!=null&&r.limite===c;
   return'<div class="rec'+(lim?' limita':'')+'"><div class="fila1"><b>'+esc(r.nombre)+(lim?' · recurso limitante':'')+'</b><span>'+(r.limite==null?'Sin dato':(r.al_menos?'al menos ':'')+num(r.limite,0)+' macetas')+' <span class="tag">'+esc(r.origen)+'</span></span></div><div class="barra2'+(r.limite==null?' nd':'')+'"><i style="width:'+(r.limite?Math.min(100,100*d.registradas/r.limite):100)+'%"></i></div><p class="et">'+esc(r.detalle)+(r.fecha?' ('+fh(r.fecha)+')':'')+'</p></div>'}).join(''));
  $('capLat').textContent=d.latencia_p95_s==null?'Tiempo de respuesta de las macetas reales: aún sin suficientes consultas.':'Tiempo de respuesta de las macetas reales: el 95 % contesta en '+num(d.latencia_p95_s,2)+' s o menos ('+d.consultas_medidas+' consultas). Se consulta cada 10 s.';
  if(!capCfg){capCfg=true;$('cR').value=f.red;$('cL').value=f.limite_wifi??'';$('cO').value=f.otros_equipos;$('cA').value=f.anios}
 }catch(e){if(vista=='cap'){$('capError').hidden=false;$('capError').textContent='No se pudo actualizar: '+e.message}}
}
$('capForm').onsubmit=async e=>{e.preventDefault();const m=$('capMsg');
 try{await pide('/api/v1/capacidad',{m:'PUT',b:{red:$('cR').value,limite_wifi:$('cL').value===''?null:+$('cL').value,otros_equipos:+$('cO').value,anios:+$('cA').value}});m.textContent='Guardado.';pintaCap()}catch(x){m.textContent='No se guardó: '+x.message}};
