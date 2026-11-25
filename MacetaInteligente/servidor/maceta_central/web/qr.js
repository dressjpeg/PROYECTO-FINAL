'use strict';
/* Código QR sin internet ni librerías: versión 3, corrección M, hasta 42 caracteres. Devuelve filas de 0 y 1 */
function qr(txt){
 const N=29,D=44,E=26,b=[...new TextEncoder().encode(txt)];if(b.length>42)return null;
 let s='0100'+b.length.toString(2).padStart(8,'0')+b.map(x=>x.toString(2).padStart(8,'0')).join('')+'0000';
 const d=s.match(/.{8}/g).map(x=>parseInt(x,2));for(let i=0;d.length<D;i++)d.push(i%2?17:236);
 // Corrección de errores Reed-Solomon en GF(256)
 const X=[],L=[];for(let i=0,x=1;i<255;i++){X[i]=x;L[x]=i;x<<=1;if(x>255)x^=285}
 const por=(a,c)=>a&&c?X[(L[a]+L[c])%255]:0;
 let g=[1];for(let i=0;i<E;i++){const n=[...g,0];g.forEach((v,j)=>n[j+1]^=por(v,X[i]));g=n}
 const r=[...d,...Array(E).fill(0)];for(let i=0;i<D;i++){const k=r[i];if(k)g.forEach((v,j)=>r[i+j]^=por(v,k))}
 s=[...d,...r.slice(D)].map(x=>x.toString(2).padStart(8,'0')).join('')+'0000000';
 const m=Array.from({length:N},()=>Array(N).fill(null)),pon=(y,x,v)=>{if(y>=0&&x>=0&&y<N&&x<N)m[y][x]=v?1:0};
 const cuadro=(cy,cx,R)=>{for(let y=-R;y<=R;y++)for(let x=-R;x<=R;x++){const k=Math.max(Math.abs(y),Math.abs(x));pon(cy+y,cx+x,R==2?k!=1:k!=2&&k!=4)}};
 cuadro(3,3,4);cuadro(3,N-4,4);cuadro(N-4,3,4);cuadro(22,22,2);
 for(let i=8;i<N-8;i++){pon(6,i,i%2==0);pon(i,6,i%2==0)}
 pon(N-8,8,1);
 [...'101010000010010'].forEach((v,i)=>{v=+v;   // formato: corrección M, máscara 0
  i<6?pon(8,i,v):i==6?pon(8,7,v):i==7?pon(8,8,v):i==8?pon(7,8,v):pon(14-i,8,v);
  i<7?pon(N-1-i,8,v):pon(8,N-15+i,v)});
 let p=0,sube=true;
 for(let x=N-1;x>0;x-=2){if(x==6)x--;
  for(let i=0;i<N;i++){const y=sube?N-1-i:i;for(const c of[x,x-1])if(m[y][c]===null){m[y][c]=(+s[p++])^((y+c)%2==0?1:0)}}
  sube=!sube}
 return m;
}
function qrSvg(txt){
 const m=qr(txt);if(!m)return'';let t='';
 m.forEach((f,y)=>f.forEach((v,x)=>{if(v)t+='M'+(x+4)+' '+(y+4)+'h1v1h-1z'}));
 return'<svg viewBox="0 0 37 37" shape-rendering="crispEdges" role="img" aria-label="Código QR para abrir en el celular"><path fill="#fff" d="M0 0h37v37H0z"/><path fill="#000" d="'+t+'"/></svg>';
}
