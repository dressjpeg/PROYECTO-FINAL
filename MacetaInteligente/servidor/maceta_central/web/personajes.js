'use strict';
/* Personajes: aspecto elegible por maceta. Se apoya en setAvatar, crear, actualizar y pintaDetalle sin cambiarlos.
   Los de imágenes usan personajes/<id>/<estado>.webp con los mismos 7 estados del avatar. */
let persCat=[],persDe={},persN=0;
const persBase={setAvatar,crear,actualizar,pintaDetalle};
const persId=id=>persDe[id]||'maceta',persImg=(p,k)=>'personajes/'+p+'/'+k+'.webp';

/* Capas: cuerpo (salta, tiembla o respira) con ojos, boca y copa, y efectos sueltos, como en el avatar clásico */
const persCapas={},NUBE='<svg class="pjNube" viewBox="74 -15 58 37" aria-hidden="true"><circle cx="88" cy="8" r="12"/><circle cx="104" cy="1" r="14"/><circle cx="119" cy="9" r="10"/><rect x="77" y="8" width="51" height="12" rx="6"/></svg>';
function persCapa(p,c){return'<img alt="" class="pjL" data-a="'+c.a+'" src="personajes/'+p+'/'+c.f+'" style="left:'+c.x+'%;top:'+c.y+'%;width:'+c.w+'%;height:'+c.h+'%'+(c.o?';transform-origin:'+c.o[0]+'% '+c.o[1]+'%':'')+(c.d?';--d:'+c.d+'s':'')+'">'}
function persViste(av){
 const pc=av.parentNode,p=persCat.find(x=>x.id==pc.dataset.per&&x.imagenes&&(!x.capas||persCapas[x.id]));let z=pc.querySelector('.pj');
 if(!p){if(z)z.remove();pc.classList.remove('conpj');return}
 if(!z){z=document.createElement('div');z.className='pj';z.setAttribute('role','img');pc.append(z)}
 const k=pc.dataset.k,luz=k=='off'?'ok':av.dataset.luz,u=p.id+' '+k+' '+luz;z.dataset.pers=av.dataset.pers||'0';z.setAttribute('aria-label',p.nombre+': '+av.getAttribute('aria-label'));
 if(z._u===u)return;z._u=u;
 const g=document.createElement('div'),C=persCapas[p.id]||{estados:{}},e=C.estados[k]||{cuerpo:[],efectos:[]};g.className='pjG';g.dataset.k=k;
 g.innerHTML='<div class="pjB"><img alt="" class="pjI" src="'+persImg(p.id,k)+'">'+e.cuerpo.map(c=>persCapa(p.id,c)).join('')+'</div>'+e.efectos.map(c=>persCapa(p.id,c)).join('')+(luz=='mucha'&&C.sol?persCapa(p.id,C.sol):'')+(luz=='poca'?NUBE:'');
 Promise.all([...g.querySelectorAll('img')].map(i=>i.decode())).then(()=>{if(z._u!==u)return;const v=[...z.children];z.append(g);pc.classList.add('conpj');
  requestAnimationFrame(()=>{g.classList.add('ve');v.forEach(x=>x.classList.remove('ve'))});setTimeout(()=>v.forEach(x=>x.remove()),450)},
  ()=>{if(z._u===u){z.remove();pc.classList.remove('conpj')}});   // sin imagen: queda el avatar clásico
}
setAvatar=function(e,p,o,a){persBase.setAvatar(e,p,o,a);persViste(a||$('av'))};
crear=function(m){const e=persBase.crear(m),z=e.querySelector('.pj');if(z)z.remove();e._av.parentNode.classList.remove('conpj');return e};
actualizar=function(e,m){e._av.parentNode.dataset.per=persId(m.id);persBase.actualizar(e,m)};
pintaDetalle=function(){$('av').parentNode.dataset.per=persId(actual);persBase.pintaDetalle();if($('perD').dataset.m!=actual)persDetalle()};

/* Selector con miniaturas. La clásica usa una copia del avatar animado */
function persOpciones(z,nombre,elegido,alCambiar){
 z.innerHTML=persCat.map(p=>'<label class="perOp"><input type="radio" name="'+nombre+'" value="'+esc(p.id)+'"'+(p.id==elegido?' checked':'')+'><span class="mini">'+(p.imagenes?'<img alt="" src="'+persImg(esc(p.id),'mini')+'">':'')+'</span><b>'+esc(p.nombre)+'</b><small>'+esc(p.descripcion)+'</small></label>').join('');
 z.querySelectorAll('.mini:empty').forEach(s=>{const a=$('av').cloneNode(true);a.removeAttribute('id');a.querySelector('defs').remove();a.dataset.c='feliz';a.dataset.agua=a.dataset.luz='ok';a.setAttribute('aria-hidden','true');s.append(a)});
 z.onchange=e=>alCambiar&&alCambiar(e.target.value);
}
function persDetalle(){
 $('perD').dataset.m=actual||'';$('perM').textContent='';
 persOpciones($('perD'),'perD',persId(actual),async p=>{const id=actual;$('perM').textContent='';
  try{await pide('/api/v1/macetas/'+id+'/personaje',{m:'PUT',b:{personaje:p}});persN++;persDe[id]=p;if(id==actual){$('perM').textContent='Personaje cambiado.';pintaDetalle()}}
  catch(e){if(id==actual){persDetalle();$('perM').textContent='No se cambió: '+e.message}}});
}
const persAlta=()=>{const r=document.querySelector('[name=perA]:checked');return r?r.value:'maceta'};
async function cargaPers(){
 const n=persN;
 try{const d=await pide('/api/v1/personajes');if(n!=persN)return;
  const nuevo=JSON.stringify(d.catalogo)!=JSON.stringify(persCat);for(const p of d.catalogo)if(p.capas&&!persCapas[p.id])try{const r=await fetch('personajes/'+p.id+'/capas.json');if(r.ok)persCapas[p.id]=await r.json()}catch(e){}
  if(n!=persN)return;persCat=d.catalogo;persDe=d.asignados;
  if(nuevo){persOpciones($('perA'),'perA','maceta');$('perD').dataset.m=''}
  pinta()}
 catch(e){/* sin personajes todo sigue con el avatar clásico */}
}
(()=>{const a=document.createElement('fieldset');a.className='pers';a.innerHTML='<legend>Personaje</legend><div id="perA" class="perOps"></div>';
 $('aOrigen').before(a);
 const d=document.createElement('details');d.className='c sololocal';d.innerHTML='<summary>Personaje</summary><p class="et">Cambia solo el aspecto. Mediciones, estados y alertas son los mismos.</p><div id="perD" class="perOps"></div><p id="perM" role="status"></p>';
 document.querySelector('#detalle .dos').after(d);
 cargaPers();setInterval(cargaPers,15000)})();
