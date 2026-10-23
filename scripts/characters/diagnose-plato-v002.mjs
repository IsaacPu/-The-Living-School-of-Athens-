import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const file = path.join(root, 'art/characters/plato/v001/source/plato-lux3d-task-4277623.glb');
const b = fs.readFileSync(file);
let g, bin;
for (let o=12; o<b.length;) {
  const n=b.readUInt32LE(o), t=b.readUInt32LE(o+4);
  if(t===0x4e4f534a) g=JSON.parse(b.subarray(o+8,o+8+n));
  if(t===0x004e4942) bin=o+8;
  o+=8+n;
}
function read(i) {
  const a=g.accessors[i], v=g.bufferViews[a.bufferView], d={SCALAR:1,VEC2:2,VEC3:3}[a.type];
  const len={5123:2,5125:4,5126:4}[a.componentType], stride=v.byteStride||d*len, offset=bin+(v.byteOffset||0)+(a.byteOffset||0);
  return Array.from({length:a.count},(_,r)=>Array.from({length:d},(_,c)=>{
    const o=offset+r*stride+c*len;
    return a.componentType===5126?b.readFloatLE(o):a.componentType===5125?b.readUInt32LE(o):b.readUInt16LE(o);
  }));
}
const primitive=g.meshes[0].primitives[0], P=read(primitive.attributes.POSITION), N=read(primitive.attributes.NORMAL), U=read(primitive.attributes.TEXCOORD_0), I=read(primitive.indices).flat();
const dot=(a,b)=>a.reduce((s,x,i)=>s+x*b[i],0), sub=(a,b)=>a.map((x,i)=>x-b[i]);
const norm=a=>a.map(x=>x/Math.hypot(...a)), cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
const angle=(a,b)=>Math.acos(Math.max(-1,Math.min(1,dot(norm(a),norm(b)))))*180/Math.PI;
const key=p=>p.map(x=>Math.round(x*1e6)).join(',');
const regions={all:{triangles:0,flat_three_normals:0,uv_area_texels:0},head:{triangles:0,flat_three_normals:0,uv_area_texels:0}};
const edges=new Map();
for(let k=0;k<I.length;k+=3) {
  const ids=I.slice(k,k+3), ps=ids.map(i=>P[i]), ns=ids.map(i=>N[i]);
  const head=ps.every(p=>p[1]+.875>1.42), fn=norm(cross(sub(ps[1],ps[0]),sub(ps[2],ps[0])));
  for(const [region, include] of [[regions.all,true],[regions.head,head]]) if(include) {
    region.triangles++;
    if(dot(norm(ns[0]),norm(ns[1]))>.99999&&dot(norm(ns[0]),norm(ns[2]))>.99999) region.flat_three_normals++;
    const [a,c,d]=ids.map(i=>U[i]);
    region.uv_area_texels+=Math.abs((c[0]-a[0])*(d[1]-a[1])-(c[1]-a[1])*(d[0]-a[0]))*.5*2048*2048;
  }
  for(let j=0;j<3;j++) {
    let one=ids[j],two=ids[(j+1)%3], keys=[key(P[one]),key(P[two])];
    if(keys[0]>keys[1]){keys.reverse();[one,two]=[two,one];}
    const e=keys.join('|'); if(!edges.has(e))edges.set(e,[]);
    edges.get(e).push({ids:[one,two],normal:fn,head});
  }
}
let suspiciousHead=0, gentleHead=0;
for(const tris of edges.values()) if(tris.length===2&&tris.every(t=>t.head)) {
  const dihedral=angle(tris[0].normal,tris[1].normal);
  const jump=Math.max(...[0,1].map(k=>angle(N[tris[0].ids[k]],N[tris[1].ids[k]])));
  if(dihedral<15){gentleHead++;if(jump>30)suspiciousHead++;}
}
for(const value of Object.values(regions)) {
  value.flat_three_normals_pct=100*value.flat_three_normals/value.triangles;
  value.uv_area_equivalent_square_px=Math.sqrt(value.uv_area_texels);
}
const result={schema_version:1,source:'v001 original Lux3D GLB',units:'meters',regions,
  head_roi:'Every triangle vertex above canonical height 1.42m; source Y + 0.875m.',
  suspicious_head_edges:{count:suspiciousHead,gentle_edges_examined:gentleHead,criterion:'2-triangle positional-welded edge, geometric dihedral <15deg, stored endpoint normal jump >30deg'},
  source_normal_map:false,source_color_texture_size:[2048,2048],
  limits:['UV area is summed triangle area, not a unique pixel-coverage raster or actual image width. UV overlap can affect this estimate.',
    'A suspicious normal discontinuity is a candidate for inspection, not proof of wrong anatomy.',
    'No stored image can restore geometry or historical facial features absent from the source.']};
fs.writeFileSync(path.join(root,'qa/characters/plato/v002/diagnosis.json'),JSON.stringify(result,null,2));
console.log(JSON.stringify(result,null,2));
