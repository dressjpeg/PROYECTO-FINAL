/* Copia de las gráficas de PaginaWeb.h */
'use strict';
const $=i=>document.getElementById(i),css=v=>getComputedStyle(document.documentElement).getPropertyValue(v).trim();
const num=(v,d=1)=>Number(v).toLocaleString('es-CO',{maximumFractionDigits:d});
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
