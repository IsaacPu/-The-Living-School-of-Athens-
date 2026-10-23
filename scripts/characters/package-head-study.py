"""Package/verify v002 geometry study from real files; does not render."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import struct
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
ASSET = ROOT/'art/characters/plato/v002'
QA = ROOT/'qa/characters/plato/v002'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
experiment = json.loads((QA/'experiment.json').read_text(encoding='utf-8'))
roundtrip = json.loads((QA/'roundtrip.json').read_text(encoding='utf-8'))
frozen = json.loads((QA/'v001-preservation-before.json').read_text(encoding='utf-8'))
images = [i['file'] for i in experiment['images']]
checks = []


def check(name, passed, evidence):
    checks.append({'name': name, 'passed': bool(passed), 'evidence': evidence})


def glb_json(p):
    data = p.read_bytes()
    assert data[:4] == b'glTF' and struct.unpack_from('<I', data, 4)[0] == 2
    assert struct.unpack_from('<I', data, 8)[0] == len(data)
    length, kind = struct.unpack_from('<II', data, 12)
    assert kind == 0x4e4f534a
    return json.loads(data[20:20+length])


preserved = {name: sha(ROOT/name) == expected for name, expected in frozen.items()}
(QA/'v001-preservation-after.json').write_text(json.dumps({'passed': all(preserved.values()),
    'file_count': len(preserved), 'files': preserved}, indent=2), encoding='utf-8')
check('v001_all_27_files_unchanged', all(preserved.values()) and len(preserved) == 27, preserved)
check('baseline_hash_unchanged', sha(ROOT/'art/characters/plato/v001/export/plato-baseline-diagnostic.glb') == experiment['baseline_sha256'], experiment['baseline_sha256'])
check('B_vertex_and_topology_hash_unchanged', experiment['mesh_stats']['A_P0_unchanged']['geometry_hash_local'] == experiment['mesh_stats']['B_Targeted_normal_diagnostic']['geometry_hash_local'], experiment['baseline_geometry_hash'])
check('B_uv_unchanged', experiment['baseline_uv_preserved_in_B'], 'Exact in-memory UV coordinate equality asserted')
check('B_only_identified_normal_edits', len(experiment['normals_experiment']['flagged_edges']) == 12 and len(experiment['normals_experiment']['changed_corner_normals']) == 135, '12 candidate edges, 135 corner-normal vectors')
check('C1_actual_local_shape_changes', experiment['geometry_experiment']['vertices_actually_displaced'] == 3332 and .003 < experiment['geometry_experiment']['max_displacement_donor_m'] < .005, experiment['geometry_experiment'])
check('C0_C1_different_vertex_positions', experiment['mesh_stats']['C0_Licensed_head_proportion_control']['geometry_hash_local'] != experiment['mesh_stats']['C1_Local_head_form_candidate']['geometry_hash_local'], 'Same topology and placement, different actual coordinates')
check('all_10_real_images_open', len(images) == 10 and all(Image.open(QA/p).size == (768, 768) for p in images), images)
for name in ('front', 'side', 'quarter'):
    baseline = next(i for i in experiment['images'] if i['file'] == f'A_{name}_gray.png')
    candidate = next(i for i in experiment['images'] if i['file'] == f'C1_{name}_reshaped_head_gray.png')
    check('same_conditions_'+name, all(baseline[k] == candidate[k] for k in ('camera_blender_m','target_blender_m','orthographic_span_m','resolution','samples','denoising','mode')), 'Camera, light scene, framing, samples and gray material fixed')
check('actual_blend_reopen_glb_reimport', roundtrip['passed'] and roundtrip['blend_reopened'] and roundtrip['glb_reimported_in_empty_scene'] and roundtrip['head_position_set_preserved_at_0_01mm'], roundtrip)
head = ASSET/experiment['outputs']['head_study']['file']
g = glb_json(head)
check('head_has_two_meshes_no_rig_or_animation', len(g.get('meshes', [])) == 2 and not g.get('skins') and not g.get('animations'), {'meshes': len(g.get('meshes', []))})
check('head_has_no_external_resources', all(not b.get('uri') or b['uri'].startswith('data:') for b in g['buffers']) and all(i.get('bufferView') is not None or i.get('uri','').startswith('data:') for i in g.get('images', [])), 'Geometry gray study, embedded BIN')
check('CC_BY_attribution_embedded', len([n for n in g['nodes'] if n.get('extras',{}).get('source_license') == 'CC BY 4.0']) == 2, [n.get('extras', {}) for n in g['nodes']])
license_record = json.loads((ASSET/'source/base-mesh-license.json').read_text(encoding='utf-8'))
check('official_base_digest_and_license', sha(ASSET/'source/realistic_human_base.blend') == license_record['sha256'] and license_record['license'] == 'CC BY 4.0', license_record)
limits = [
    'Generic bald head study: not accepted as Plato or an elderly final character.',
    'A to C improvement primarily comes from retained anatomy authored in the licensed base. C0 to C1 is small procedural form editing, not newly hand-sculpted anatomy.',
    'Under-eye rolls are overly regular; cheek/jaw and cranium still read young. Further reference-led form work is required.',
    'Head/neck cut is capped, but no connection to the existing torso/collar has been made.',
    'No hair/beard, skin color/normal textures, new UV layout, production retopology, baking, rigging or animation is claimed.',
    'B is rejected as a sufficient visual refinement. No source smoothing, upscaling or sharpening is accepted as refinement.',
    'Head coordinate top remains about Y=1.743m in the character frame; this isolated asset is not a complete 1.75m body.',
]
bounds = roundtrip['reimport_bounds_blender_m']
delivery = {'schema_version': 1, 'asset_id': 'plato-v002-head-geometry-study',
    'asset_role': 'standalone_head_geometry_study', 'technical_status': 'local_export_and_reimport_verified',
    'art_status': 'art_not_accepted', 'geometry_study_status': 'visible_structure_improvement',
    'relative_glb_path': experiment['outputs']['head_study']['file'], 'sha256': sha(head), 'bytes': head.stat().st_size,
    'relative_blend_path': experiment['relative_blend_path'], 'blend_sha256': sha(ASSET/experiment['relative_blend_path']),
    'units': 'meters', 'up_axis': '+Y', 'forward_axis': '+Z', 'orientation_verified': True,
    'bounds_m': {'min': [bounds['min'][0], bounds['min'][2], -bounds['max'][1]],
                 'max': [bounds['max'][0], bounds['max'][2], -bounds['min'][1]]},
    'body_height_m': None, 'runtime_replacement_approved': False,
    'source': {'attribution': license_record['attribution'], 'license': 'CC BY 4.0',
               'license_url': license_record['license_url'], 'record': 'source/base-mesh-license.json',
               'sha256': license_record['sha256'], 'attribution_file': 'ATTRIBUTION.md'},
    'triangles': sum(experiment['mesh_stats'][k]['triangles'] for k in ('C1_Local_head_form_candidate','C_Eyeballs_anatomy_check')),
    'materials': {'count': len(g.get('materials', [])), 'policy': 'controlled_untextured_gray', 'source_diffuse_reprojected': False},
    'skins': 0, 'animations': 0, 'geometry_changed': True, 'changes': experiment['geometry_experiment'],
    'normals_diagnostic': {**experiment['outputs']['normals_diagnostic'], 'status': 'rejected_as_sufficient_refinement'},
    'qa_images': ['../../../../qa/characters/plato/v002/'+name for name in images],
    'reports': {'research': '../../../../qa/characters/plato/v002/RESEARCH.md',
                'diagnosis': '../../../../qa/characters/plato/v002/diagnosis.json',
                'experiment': '../../../../qa/characters/plato/v002/experiment.json',
                'review': '../../../../qa/characters/plato/v002/REPORT.md',
                'verification': '../../../../qa/characters/plato/v002/verification.json',
                'roundtrip': '../../../../qa/characters/plato/v002/roundtrip.json'},
    'known_limits': limits, 'rollback': 'Use frozen v001 for the body/baseline. C0 retains the licensed pre-form-edit control inside the editable blend. v002 does not replace A runtime model.',
    'reproduce': ['node scripts/characters/diagnose-plato-v002.mjs',
                  '<verified-blender> --background --factory-startup --disable-autoexec --python-exit-code 1 --python scripts/characters/plato-head-study.py -- --samples 32',
                  '<verified-blender> --background --factory-startup --disable-autoexec --python-exit-code 1 --python scripts/characters/finalize-head-study.py',
                  'python scripts/characters/package-head-study.py']}
(ASSET/'delivery.json').write_text(json.dumps(delivery, ensure_ascii=False, indent=2), encoding='utf-8')
# This output is written below, so validate all other manifest references now.
paths = [delivery['relative_glb_path'], delivery['relative_blend_path'], 'ATTRIBUTION.md', 'source/base-mesh-license.json', *delivery['qa_images'], *[p for k,p in delivery['reports'].items() if k != 'verification']]
check('all_delivery_references_resolve', all((ASSET/p).is_file() for p in paths), paths)
check('truthful_scope_and_status', delivery['art_status'] == 'art_not_accepted' and not delivery['runtime_replacement_approved'] and len(delivery['known_limits']) > 0, delivery['asset_role'])
result = {'schema_version': 1, 'verified_utc': datetime.now(timezone.utc).isoformat(),
          'passed': all(c['passed'] for c in checks), 'checks': checks,
          'scope': 'Technical evidence and scope truthfulness only; no final likeness/material/animation acceptance.'}
(QA/'verification.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'passed': result['passed'], 'checks': len(checks), 'failed': [c['name'] for c in checks if not c['passed']], 'head_sha256': delivery['sha256'], 'head_triangles': delivery['triangles']}, ensure_ascii=False))
if not result['passed']:
    raise SystemExit(1)
