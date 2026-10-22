// Independent byte-level checks of the real exported artifact; no Blender needed.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {fileURLToPath} from 'node:url';

const production = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const asset = path.join(production, 'art/characters/plato/v001');
const qa = path.join(production, 'qa/characters/plato/v001');
const hash = b => crypto.createHash('sha256').update(b).digest('hex');
const checks = [];
function check(name, passed, detail) {checks.push({name, passed: Boolean(passed), detail});}
function readGlb(file) {
  const bytes = fs.readFileSync(file);
  if (bytes.toString('ascii', 0, 4) !== 'glTF' || bytes.readUInt32LE(4) !== 2 || bytes.readUInt32LE(8) !== bytes.length) throw new Error('Invalid GLB container');
  let json, bin;
  for (let o = 12; o < bytes.length;) {
    const n = bytes.readUInt32LE(o), t = bytes.readUInt32LE(o + 4);
    if (o + n + 8 > bytes.length) throw new Error('GLB chunk exceeds file');
    if (t === 0x4e4f534a) json = JSON.parse(bytes.subarray(o + 8, o + 8 + n).toString('utf8'));
    if (t === 0x004e4942) bin = bytes.subarray(o + 8, o + 8 + n);
    o += n + 8;
  }
  if (!json || !bin) throw new Error('Missing GLB JSON/BIN');
  const identity = () => [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1];
  const mul = (a, b) => Array.from({length: 16}, (_, i) => {
    const r = i % 4, c = Math.floor(i / 4);
    return [0, 1, 2, 3].reduce((sum, k) => sum + a[r + k * 4] * b[k + c * 4], 0);
  });
  function matrix(n) {
    if (n.matrix) return n.matrix;
    const [x, y, z, w] = n.rotation || [0, 0, 0, 1], s = n.scale || [1, 1, 1], t = n.translation || [0, 0, 0];
    return [(1-2*y*y-2*z*z)*s[0], (2*x*y+2*w*z)*s[0], (2*x*z-2*w*y)*s[0], 0,
      (2*x*y-2*w*z)*s[1], (1-2*x*x-2*z*z)*s[1], (2*y*z+2*w*x)*s[1], 0,
      (2*x*z+2*w*y)*s[2], (2*y*z-2*w*x)*s[2], (1-2*x*x-2*y*y)*s[2], 0, ...t, 1];
  }
  function accessor(i) {
    const a = json.accessors[i], v = json.bufferViews[a.bufferView];
    const dims = {SCALAR: 1, VEC2: 2, VEC3: 3, VEC4: 4}[a.type];
    const len = {5121: 1, 5123: 2, 5125: 4, 5126: 4}[a.componentType];
    const stride = v.byteStride || dims * len, start = (v.byteOffset || 0) + (a.byteOffset || 0);
    return Array.from({length: a.count}, (_, row) => Array.from({length: dims}, (_, col) => {
      const offset = start + row * stride + col * len;
      return a.componentType === 5126 ? bin.readFloatLE(offset) : a.componentType === 5125 ? bin.readUInt32LE(offset) : a.componentType === 5123 ? bin.readUInt16LE(offset) : bin.readUInt8(offset);
    }));
  }
  const points = [], triangles = [];
  function visit(index, parent) {
    const node = json.nodes[index], world = mul(parent, matrix(node));
    if (node.mesh !== undefined) for (const primitive of json.meshes[node.mesh].primitives) {
      if ((primitive.mode ?? 4) !== 4) throw new Error('Unexpected non-triangle primitive');
      const pos = accessor(primitive.attributes.POSITION).map(v => [0, 1, 2].map(r => world[r] * v[0] + world[r+4] * v[1] + world[r+8] * v[2] + world[r+12]));
      points.push(...pos);
      const indices = primitive.indices === undefined ? pos.map((_, i) => i) : accessor(primitive.indices).flat();
      for (let i = 0; i < indices.length; i += 3) triangles.push(indices.slice(i, i+3).map(index => pos[index]));
    }
    for (const child of node.children || []) visit(child, world);
  }
  for (const index of json.scenes[json.scene ?? 0].nodes) visit(index, identity());
  const low = [0,1,2].map(k => Math.min(...points.map(p => p[k]))), high = [0,1,2].map(k => Math.max(...points.map(p => p[k])));
  return {bytes, json, points, triangles, low, high};
}
const original = readGlb(path.join(asset, 'source/plato-lux3d-task-4277623.glb'));
const exported = readGlb(path.join(asset, 'export/plato-baseline-diagnostic.glb'));
check('source_hash', hash(original.bytes) === '904ab6adec70c941a877918435b3c655a89a6d67be5c52610d4d210689afd8ce', hash(original.bytes));
check('triangles_preserved', exported.triangles.length === original.triangles.length && exported.triangles.length === 28314, exported.triangles.length);
check('feet_y_zero', Math.abs(exported.low[1]) < 1e-5, exported.low[1]);
check('no_rescale', Math.abs((exported.high[1]-exported.low[1]) - (original.high[1]-original.low[1])) < 1e-5, exported.high[1]-exported.low[1]);
check('finite_geometry', exported.points.every(p => p.every(Number.isFinite)), exported.points.length);
check('no_skins_or_animations', !(exported.json.skins?.length || exported.json.animations?.length), {skins: exported.json.skins?.length || 0, animations: exported.json.animations?.length || 0});
check('embedded_images', exported.json.images?.length === 2 && exported.json.images.every(i => i.bufferView !== undefined || i.uri?.startsWith('data:')), exported.json.images);
check('no_external_buffers', exported.json.buffers.every(b => !b.uri || b.uri.startsWith('data:')), exported.json.buffers);
check('no_unrequested_helpers', exported.json.nodes.every(n => !/QA_|light|camera|ground/i.test(n.name || '')), exported.json.nodes.map(n => n.name));
// Rigid translation must preserve every triangle, not just count/bounds.
const centerX = (original.low[0] + original.high[0])/2, centerZ = (original.low[2] + original.high[2])/2;
const key = p => p.map(x => Math.round(x / 0.0001)).join(',');
const triKey = t => t.map(key).sort().join('|');
const expected = original.triangles.map(t => triKey(t.map(p => [p[0]-centerX, p[1]-original.low[1], p[2]-centerZ]))).sort();
const actual = exported.triangles.map(triKey).sort();
check('triangle_shape_preserved_after_rebase', expected.length === actual.length && expected.every((v, i) => v === actual[i]), 'Triangle corner positions compared at 0.1mm quantization; no smoothing/remeshing.');
const blend = path.join(asset, 'work/plato-baseline-diagnostic.blend');
check('blend_header', fs.existsSync(blend) && fs.readFileSync(blend).subarray(0, 7).toString('ascii') === 'BLENDER', path.basename(blend));
const report = JSON.parse(fs.readFileSync(path.join(qa, 'blender-inspection.json'), 'utf8'));
check('all_real_render_files_present', report.qa_images.length >= 12 && report.qa_images.every(i => {
  const b = fs.readFileSync(path.resolve(asset, i.path));
  return b.subarray(0, 8).equals(Buffer.from([137,80,78,71,13,10,26,10])) && b.readUInt32BE(16) === i.resolution[0] && b.readUInt32BE(20) === i.resolution[1];
}), report.qa_images.length);
const deliveryPath = path.join(asset, 'delivery.json');
if (fs.existsSync(deliveryPath)) {
  const delivery = JSON.parse(fs.readFileSync(deliveryPath, 'utf8').replace(/^\uFEFF/, ''));
  check('delivery_hash_and_bytes', delivery.sha256 === hash(exported.bytes) && delivery.bytes === exported.bytes.length, {sha256: delivery.sha256, bytes: delivery.bytes});
  check('delivery_paths_exist', [delivery.relative_glb_path, delivery.relative_blend_path, ...delivery.qa_images].every(p => fs.existsSync(path.resolve(asset, p))), 'All handoff paths resolve from manifest');
  check('all_report_references_exist', [delivery.qa_report, delivery.verification_report, delivery.roundtrip_report, delivery.reference_sources, delivery.source.provenance, delivery.reproduction,
    ...delivery.known_defects.map(d => d.qa_image)].every(p => typeof p === 'string' && fs.existsSync(path.resolve(asset, p))), 'Reports, provenance, reproduction script and every defect image resolve');
  check('blend_reopened_and_export_reimported', (() => {const r = JSON.parse(fs.readFileSync(path.join(qa, 'roundtrip.json'), 'utf8')); return r.passed && r.blend_reopened && r.export_reimported;})(), 'Actual fresh Blender open/import recorded');
  check('honest_art_status', delivery.art_status === 'baseline_diagnostic' && delivery.geometry_changed === false && delivery.known_defects.length > 0, delivery.art_status);
}
const result = {schema_version: 1, verified_utc: new Date().toISOString(), passed: checks.every(c => c.passed), checks,
  actual_sha256: hash(exported.bytes), actual_bytes: exported.bytes.length, actual_bounds_m: {min: exported.low, max: exported.high},
  scope: 'Real source/export bytes and output existence. Does not replace visual likeness, topology, licensing or Unity acceptance.'};
fs.writeFileSync(path.join(qa, 'verification.json'), JSON.stringify(result, null, 2));
console.log(JSON.stringify(result, null, 2));
if (!result.passed) process.exitCode = 1;
