'use strict';
/* Borrar una maceta. Con historial pide escribir el nombre. */
let bM=null;
const listoBorrar=()=>{$('bSi').disabled=!!(bM.lecturas||bM.fotos)&&$('bN').value.trim()!=bM.nombre};
function pideBorrar(id){
 bM=macetas.find(m=>m.id==id);if(!bM)return;
 $('bT').textContent='Borrar «'+bM.nombre+'»';
 $('bTxt').textContent=bM.lecturas||bM.fotos?'Se borrará del servidor con sus '+num(bM.lecturas,0)+' lecturas y '+num(bM.fotos,0)+' fotos. Antes se guarda una copia de seguridad.':'No tiene lecturas ni fotos guardadas.';
 $('bNom').hidden=!bM.lecturas&&!bM.fotos;$('bN').value=$('bMsg').textContent='';listoBorrar();$('borrar').showModal();
}
$('bN').oninput=listoBorrar;$('bNo').onclick=()=>$('borrar').close();
$('dBorrar').onclick=()=>pideBorrar(actual);
$('bForm').onsubmit=async e=>{e.preventDefault();const m=bM;$('bSi').disabled=true;
 try{await pide('/api/v1/macetas/'+m.id+'?nombre='+encodeURIComponent($('bN').value.trim()),{m:'DELETE'});
  macetas=macetas.filter(x=>x.id!=m.id);$('borrar').close();nCiclo++;if(actual==m.id)location.hash='';else pinta();refresca().catch(()=>{})}
 catch(x){$('bMsg').textContent='No se borró: '+x.message;listoBorrar()}};
