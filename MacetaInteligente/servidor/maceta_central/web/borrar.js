'use strict';
/* Borrar una maceta. En el PC, con historial, pide el nombre; desde el celular, un código que aparece en el PC. */
let bM=null;const bRem=()=>document.body.classList.contains('remoto');
const listoBorrar=()=>{$('bSi').disabled=bRem()?!/^\d{6}$/.test($('bC').value.replace(/\s/g,'')):!!(bM.lecturas||bM.fotos)&&$('bN').value.trim()!=bM.nombre};
function pideBorrar(id){
 bM=macetas.find(m=>m.id==id);if(!bM)return;
 $('bT').textContent='Borrar «'+bM.nombre+'»';
 $('bTxt').textContent=bM.lecturas||bM.fotos?'Se borrará del servidor con sus '+num(bM.lecturas,0)+' lecturas y '+num(bM.fotos,0)+' fotos. Antes se guarda una copia de seguridad.':'No tiene lecturas ni fotos guardadas.';
 $('bAut').hidden=!bRem();$('bC').value='';$('bNom').hidden=bRem()||!bM.lecturas&&!bM.fotos;$('bN').value=$('bMsg').textContent='';listoBorrar();$('borrar').showModal();
}
$('bN').oninput=$('bC').oninput=listoBorrar;$('bNo').onclick=()=>$('borrar').close();
$('bPed').onclick=async()=>{const m=bM;$('bPed').disabled=true;try{await pide('/api/v1/macetas/'+m.id+'/autorizacion',{m:'POST'});$('bMsg').textContent='Mira el dashboard abierto en el PC. El código vence en 2 minutos.';$('bC').focus()}catch(x){$('bMsg').textContent=x.message}$('bPed').disabled=false};
$('dBorrar').onclick=()=>pideBorrar(actual);
$('bForm').onsubmit=async e=>{e.preventDefault();const m=bM;$('bSi').disabled=true;
 try{await pide('/api/v1/macetas/'+m.id+'?nombre='+encodeURIComponent(bRem()?m.nombre:$('bN').value.trim()),{m:'DELETE',h:bRem()?{'X-Autorizacion':$('bC').value}:{}});
  macetas=macetas.filter(x=>x.id!=m.id);$('borrar').close();nCiclo++;if(actual==m.id)location.hash='';else pinta();refresca().catch(()=>{})}
 catch(x){$('bMsg').textContent='No se borró: '+x.message;listoBorrar()}};
