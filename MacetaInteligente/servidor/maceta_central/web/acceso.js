'use strict';
/* Acceso desde el celular: en el PC crea códigos de un solo uso; en el celular oculta lo que solo hace el PC */
let celFin=0;
async function cargaAcceso(){
 try{const a=await pide('/api/v1/acceso');
  document.body.classList.toggle('remoto',a.remoto);$('salir').hidden=!a.remoto||!a.con_codigo;$('celK').hidden=!a.con_codigo;$('celA').hidden=a.con_codigo;
  $('cel').hidden=!a.red||a.remoto;if($('cel').hidden)return;
  if(!a.codigo_vigente)celFin=0;
  $('celU').textContent=a.url||'(este PC no está conectado a una red)';$('celH').textContent=a.huella;
  $('celX').textContent='Cerrar todas las sesiones ('+a.sesiones+')';celPinta()}
 catch(e){$('cel').hidden=true}
}
function celPinta(){const s=Math.ceil((celFin-Date.now())/1000);
 if(s>0)$('celM').textContent='vence en '+Math.floor(s/60)+':'+String(s%60).padStart(2,'0');
 else if($('celC').textContent){$('celC').textContent='';$('celM').textContent='El código se usó o venció.'}}
const celHaz=async(u,f)=>{try{f(await pide('/api/v1/acceso/'+u,{m:'POST'}));cargaAcceso()}catch(e){$('celM').textContent=e.message}};
$('celN').onclick=()=>celHaz('codigo',r=>{celFin=Date.now()+r.segundos*1000;$('celC').textContent=r.codigo.replace(/(....)/,'$1 ');celPinta()});
$('celX').onclick=()=>celHaz('cerrar',()=>{celFin=0;$('celC').textContent='';$('celM').textContent='Sesiones cerradas.'});
$('cel').ontoggle=()=>{if($('cel').open)cargaAcceso();else{celFin=0;$('celC').textContent=$('celM').textContent=''}};
$('salir').onclick=async()=>{try{await pide('/salir',{m:'POST'})}catch(e){}location.href='/entrar'};
setInterval(()=>{if($('cel').open&&!$('cel').hidden)celPinta()},1000);
setInterval(()=>{if($('cel').open&&!$('cel').hidden&&celFin)cargaAcceso()},4000);
cargaAcceso();
