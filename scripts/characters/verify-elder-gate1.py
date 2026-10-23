"""Reopen and verify frozen failed elderly-head experiment, without rendering."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import struct
import subprocess

import bpy

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT/'qa/characters/plato/v002/elder-gate1'
ASSET = ROOT/'art/characters/plato/v002/elder-gate1'


def sha(path):
    return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()


def read(path):
    return json.loads((ROOT/path).read_text(encoding='utf-8-sig'))


def write(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


report = read('qa/characters/plato/v002/elder-gate1/experiment.json')
bpy.ops.wm.open_mainfile(filepath=str(ROOT/report['source']), load_ui=False, use_scripts=False)
scene = bpy.context.scene
checks = []


def check(name, condition, detail):
    checks.append({'name': name, 'passed': bool(condition), 'detail': detail})


meshes = [o for o in scene.objects if o.type == 'MESH']
head = next(o for o in meshes if 'Bald_anatomical' in o.name)
eyes = next(o for o in meshes if 'eyeballs' in o.name)
check('source_reopened_hash_matches', sha(report['source']) == report['source_sha256'], sha(report['source']))
check('head_eyes_visible', all(not o.hide_render and o.visible_get() for o in (head, eyes)), [o.name for o in meshes])
check('head_eyes_only', len(meshes) == 2 and not any(o.type in ('CURVE', 'CURVES', 'ARMATURE') for o in scene.objects),
      'Derived head with existing neck cut and eyeballs; no hair/body/rig objects added')
check('editable_form_layer_active', head.data.shape_keys and len(head.data.shape_keys.key_blocks) == 2 and
      head.data.shape_keys.key_blocks[1].value == 1, 'Evaluated C0 basis plus one named anatomical form shape key')
check('no_image_textures', all(n.type != 'TEX_IMAGE' for o in meshes for m in o.data.materials
      if m and m.use_nodes for n in m.node_tree.nodes), 'Neutral gray, no old diffuse or procedural pores')
check('bounded_cpu_render_settings', scene.render.threads == report['cpu_threads'] == 4 and
      scene.cycles.device == 'CPU' and not report['gpu_used'] and scene.cycles.samples == 32,
      {'threads': scene.render.threads, 'device': scene.cycles.device, 'samples': scene.cycles.samples})
check('three_real_png_files', report['render_count'] == len(report['images']) == 3 and
      all(sha(i['path']) == i['sha256'] and (ROOT/i['path']).read_bytes()[:8] == b'\x89PNG\r\n\x1a\n' and
          struct.unpack('>II', (ROOT/i['path']).read_bytes()[16:24]) == (768, 768) for i in report['images']),
      [{'view': i['view'], 'sha256': i['sha256']} for i in report['images']])
log = (QA/'render.log').read_text(encoding='utf-8-sig')
check('three_render_saves_and_exit_logged', sum(line.startswith('Saved:') for line in log.splitlines()) == 3 and
      'ELDER_GATE1_THREE_VIEWS_COMPLETE' in log and 'Blender quit' in log, 'No fourth render or retry')
check('saved_camera_path_matches_quarter', Path(scene.render.filepath).resolve() == (QA/'quarter.png').resolve(), scene.render.filepath)
v001 = read('qa/characters/plato/v002/v001-preservation-before.json')
v001_actual = {p: sha(p) for p in v001}
check('v001_27_files_preserved', len(v001) == 27 and v001_actual == v001, {'files': len(v001)})
protected = {p: {'before': value, 'after': sha(p)} for p, value in report['protected_hashes'].items()}
check('C0_p1_p1b_sources_and_images_preserved', all(v['before'] == v['after'] for v in protected.values()), protected)
study_paths = [p.relative_to(ROOT).as_posix() for p in (ROOT/'qa/characters/plato/v002').glob('*.png')]
study_paths += ['art/characters/plato/v002/work/plato-head-study.blend',
                'art/characters/plato/v002/export/plato-head-geometry-study.glb',
                'art/characters/plato/v002/source/realistic_human_base.blend']
study = {}
for path in study_paths:
    committed = subprocess.run(['git', 'show', 'cb8d3ee:'+path], cwd=ROOT, capture_output=True, check=True).stdout
    study[path] = {'committed': hashlib.sha256(committed).hexdigest(), 'current': sha(path)}
check('13_study_and_donor_files_preserved', len(study) == 13 and all(v['committed'] == v['current'] for v in study.values()), study)
attribution = read('art/characters/plato/v002/source/base-mesh-license.json')
check('head_source_license_preserved', attribution['license'] == 'CC BY 4.0' and attribution['file_internal_attribution_inspected'],
      'Blender Studio / Project Heist; lesson author Julien Kaspar; see ../ATTRIBUTION.md')
report['art_status'] = 'art_not_accepted'
report['age_gate_passed'] = False
report['visual_review'] = {
    'B': 'rejected after viewing all three images',
    'independent_character_reference_check': 'rejected after viewing all three images',
    'project_owner': 'rejected after viewing all three images',
    'visible_changes': ['More submalar concavity', 'Depressed mouth corners'],
    'failures': ['Still reads as a gaunt adult, not a convincing elderly man',
                 'Insufficient upper-lid/brow, perioral and cheek/jowl aging tissue',
                 'Jaw/neck transition remains firm', 'New jagged cut boundary at the neck base'],
    'decision': 'Stop deforming this young base. No more control points, parameters or renders. Screen a genuinely aged base.'}
report['reference']['catalogue_observation'] = 'Official Louvre record identifies Ma 921 as an old man, with identity uncertainty and a right-temple crack. These are limits, not features to reproduce.'
report['reference']['native_scan_downloaded'] = False
report['reference']['original_painting_viewed'] = True
report['reference']['original_painting_role'] = 'Plato identity direction only; no painted face projected onto mesh'
write(QA/'experiment.json', report)
verification = {'schema_version': 1, 'verified_utc': datetime.now(timezone.utc).isoformat(),
    'technical_checks_passed': all(c['passed'] for c in checks), 'checks': checks,
    'scope': 'Integrity, source reopen and preservation only; visible age gate rejected',
    'art_status': 'art_not_accepted', 'age_gate_passed': False, 'source_reopened': True,
    'v001_hashes': v001_actual, 'source_scene_art_status_at_capture': scene.get('art_status'),
    'runtime_replacement_approved': False}
write(QA/'verification.json', verification)
write(ASSET/'delivery.json', {'schema_version': 1, 'asset_id': 'plato-elder-gate1',
    'asset_role': 'rejected_bald_aging_form_experiment', 'art_status': 'art_not_accepted', 'age_gate_passed': False,
    'source_blend': 'plato-elder-gate1.blend', 'source_sha256': sha(report['source']),
    'preview_paths_from_worktree': [i['path'] for i in report['images']],
    'report_from_worktree': 'qa/characters/plato/v002/elder-gate1/REPORT.md',
    'license': 'CC BY 4.0', 'attribution': '../ATTRIBUTION.md',
    'native_scan_geometry_used': False, 'runtime_glb': None, 'runtime_replacement_approved': False,
    'limits': report['limits']})
print('ELDER_GATE1_VERIFIED '+json.dumps({'technical_checks_passed': verification['technical_checks_passed'],
    'checks': len(checks), 'age_gate_passed': False, 'art_status': 'art_not_accepted', 'protected_v001_files': len(v001)}))
if not verification['technical_checks_passed']:
    raise SystemExit(1)
