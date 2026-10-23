"""Verify and package one rejected portrait experiment. Does not launch Blender."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import struct
import subprocess

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT/'qa/characters/plato/v002/portrait-p1b'
ASSET = ROOT/'art/characters/plato/v002/portrait-p1b'
BASE = 'cb8d3ee'


def read(path):
    return json.loads((ROOT/path).read_text(encoding='utf-8-sig'))


def sha(path):
    return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()


def write(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')


portrait = read('qa/characters/plato/v002/portrait-p1b/portrait.json')
inspection = read('qa/characters/plato/v002/portrait-p1b/static-inspection.json')
image_path, blend_path = portrait['image'], portrait['blend']
png = (ROOT/image_path).read_bytes()
checks = []


def check(name, condition, detail):
    checks.append({'name': name, 'passed': bool(condition), 'detail': detail})


check('source_and_image_exist', bool(png) and (ROOT/blend_path).is_file(), 'Independent p1b paths')
check('png_resolution', png[:8] == b'\x89PNG\r\n\x1a\n' and struct.unpack('>II', png[16:24]) == (768, 768),
      list(struct.unpack('>II', png[16:24])))
check('saved_source_hash', sha(blend_path) == portrait['blend_sha256'] == inspection['source_sha256'], sha(blend_path))
check('saved_output_path', Path(inspection['image_path']).resolve() == (ROOT/image_path).resolve(), inspection['image_path'])
objects = inspection['objects']
head = next(o for o in objects if 'Elder_long_face' in o['name'])
eyes = next(o for o in objects if 'Eyeballs' in o['name'])
clothing = next(o for o in objects if 'clothing' in o['name'])
check('head_eyes_visible_in_reopened_source', all(o['visible'] and not o['hide_render'] for o in (head, eyes)),
      {'head': head['visible'], 'eyes': eyes['visible']})
check('new_head_no_image_texture_nodes', head['image_texture_nodes'] == 0, head['image_texture_nodes'])
check('old_head_excluded_from_crop', clothing['bounds']['max'][2] <= 1.43001, clothing['bounds']['max'][2])
check('cpu_resource_limit', portrait['cpu_threads'] == inspection['cpu_threads'] == 4 and
      not portrait['gpu_used'] and inspection['device'] == 'CPU', '4 CPU threads; no GPU render')
log = (QA/'render.log').read_text(encoding='utf-8-sig')
check('one_completed_render_logged', sum(line.startswith('Saved:') for line in log.splitlines()) == 1 and
      'PORTRAIT_P1B_ONE_FRAME_COMPLETE' in log and 'Blender quit' in log, 'One saved PNG, completion marker, Blender exit')
before = read('qa/characters/plato/v002/v001-preservation-before.json')
protected = {path: {'before': digest, 'after': sha(path)} for path, digest in before.items()}
check('v001_27_hashes_preserved', len(protected) == 27 and all(v['before'] == v['after'] for v in protected.values()),
      {'files': len(protected), 'modified': [p for p, v in protected.items() if v['before'] != v['after']]})
study_paths = [p.relative_to(ROOT).as_posix() for p in (ROOT/'qa/characters/plato/v002').glob('*.png')]
study_paths += ['art/characters/plato/v002/work/plato-head-study.blend',
                'art/characters/plato/v002/export/plato-head-geometry-study.glb',
                'art/characters/plato/v002/source/realistic_human_base.blend']
study = {}
for path in study_paths:
    original = subprocess.run(['git', 'show', BASE+':'+path], cwd=ROOT, capture_output=True, check=True).stdout
    study[path] = {'committed': hashlib.sha256(original).hexdigest(), 'current': sha(path)}
check('study_and_donor_preserved', all(v['committed'] == v['current'] for v in study.values()),
      {'files': len(study), 'base_commit': BASE})
failed = read('qa/characters/plato/v002/portrait-p1/portrait.json')
check('p1_failed_source_preserved', sha(failed['blend']) == failed['blend_sha256'] and
      (ROOT/failed['image']).is_file() and failed['art_status'] == 'rejected_render_visibility_failure',
      {'blend_sha256': sha(failed['blend']), 'image_sha256': sha(failed['image'])})
license_record = read('art/characters/plato/v002/source/base-mesh-license.json')
check('source_attribution_recorded', license_record['license'] == 'CC BY 4.0' and
      license_record['file_internal_attribution_inspected'] and (ASSET.parent/'ATTRIBUTION.md').is_file(),
      'Blender Studio / Project Heist; lesson author Julien Kaspar; CC BY 4.0')
check('remaining_clothing_limits_disclosed', portrait['clothing_boundary_repair']['boundary_edges_after'] == clothing['boundary_edges'] and
      portrait['clothing_boundary_repair']['edges_with_more_than_two_faces'] == clothing['nonmanifold_edges'],
      {'boundary_edges': clothing['boundary_edges'], 'edges_with_more_than_two_faces': clothing['nonmanifold_edges'],
       'acceptance_basis': 'Visible collar/shoulder tears, not a zero-boundary criterion'})
portrait['art_status'] = 'art_not_accepted'
portrait['image_sha256'] = sha(image_path)
portrait['visual_self_review'] = {
    'reviewer': 'B', 'actual_image_viewed': True, 'verdict': 'rejected',
    'improvements': ['Head/eyes now visible', 'Readable eyelid, nose and lip geometry'],
    'failures': ['Age/likeness still reads as a generic young adult',
                 'Scalp shell has hard stepped margins and sparse regular white strands',
                 'Beard is a flat tapering curtain with hard roots; moustache is mechanical',
                 'Visible shoulder tears, skin-colored cut caps, and hard purple collar transition'],
    'boundary_policy': 'Natural garment openings may remain. Counts alone are not a visual acceptance gate.',
    'source_capture_status': 'Blend metadata was captured before visual review; this report is the later review verdict.'}
portrait['owner_review'] = {
    'reviewer': 'project_owner', 'actual_image_viewed': True, 'verdict': 'rejected',
    'recorded_date': '2026-10-23',
    'findings': ['Visible face and clear facial volume are retained as technical results',
                 'Young appearance, curtain-like beard, hard scalp boundary, shoulder tears and exposed skin-colored caps'],
    'constraints': ['No Unity integration', 'No batch character production', 'No new render in this round']}
portrait['independent_visual_review'] = {
    'reviewer': 'character_reference_check', 'actual_image_viewed': True, 'verdict': 'rejected',
    'findings': ['Readable face but young appearance', 'Hard stepped scalp shell and parallel curtain-like beard',
                 'Visible shoulder plates and black collar/shoulder tears'],
    'basis': 'Specific visible defects, not boundary-edge counts'}
write(QA/'portrait.json', portrait)
verification = {'schema_version': 1, 'verified_utc': datetime.now(timezone.utc).isoformat(),
                'scope': 'File integrity, reopened source state and preservation only; not character-art acceptance',
                'technical_checks_passed': all(c['passed'] for c in checks), 'art_status': 'art_not_accepted',
                'checks': checks, 'v001_files': protected, 'study_files': study}
write(QA/'verification.json', verification)
manifest = {'schema_version': 1, 'asset_id': 'plato-v002-portrait-p1b',
            'asset_role': 'rejected_shaded_head_shoulders_experiment', 'art_status': 'art_not_accepted',
            'runtime_replacement_approved': False, 'runtime_glb': None,
            'blend': {'path': 'plato-portrait-p1b.blend', 'sha256': sha(blend_path)},
            'preview': {'path_from_worktree': image_path, 'sha256': sha(image_path)},
            'report_from_worktree': 'qa/characters/plato/v002/portrait-p1b/REPORT.md',
            'source_attribution': '../ATTRIBUTION.md', 'license_record': '../source/base-mesh-license.json',
            'clothing_provenance': '../../v001/source/provenance.json',
            'limits': portrait['limits']}
write(ASSET/'delivery.json', manifest)
print(json.dumps({'technical_checks_passed': verification['technical_checks_passed'], 'checks': len(checks),
                  'art_status': manifest['art_status'], 'v001_preserved': len(protected), 'study_preserved': len(study)}))
if not verification['technical_checks_passed']:
    raise SystemExit(1)
