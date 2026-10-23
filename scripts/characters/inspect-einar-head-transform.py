"""Static main-head transform reference; no source evaluation or placement."""
import json
from pathlib import Path
import time

import bpy
from mathutils import Matrix

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / 'qa/characters/plato/v002/einar-intake'
SOURCE = Path('D:/AI/PROJECT/hackathon_projects/Aholo_3D_AI_Hackathon/project-management/source-cache/einar-v1/extracted/einar_release_v1.blend')
started = time.perf_counter()
before = sorted(obj.name for obj in bpy.context.scene.objects)
with bpy.data.libraries.load(str(SOURCE), link=False) as (data_from, data_to):
    assert 'GEO-einar_head' in data_from.objects
    data_to.objects = ['GEO-einar_head']
head = data_to.objects[0]
assert head is not None
to_list = lambda matrix: [[float(v) for v in row] for row in matrix]
constraints = []
for constraint in head.constraints:
    record = {'name': constraint.name, 'type': constraint.type,
        'influence_serialized': constraint.influence, 'mute': constraint.mute}
    if hasattr(constraint, 'targets'):
        record['targets'] = [{'target': target.target.name if target.target else None,
            'subtarget': target.subtarget, 'weight': target.weight} for target in constraint.targets]
    constraints.append(record)
record = {'name': head.name, 'data': head.data.name,
    'parent_name': head.parent.name if head.parent else None, 'parent_type': head.parent_type,
    'parent_bone': head.parent_bone,
    'API_matrices_after_append_without_evaluation': {'world': to_list(head.matrix_world),
        'local': to_list(head.matrix_local), 'basis': to_list(head.matrix_basis),
        'parent_inverse': to_list(head.matrix_parent_inverse)},
    'parent_API_world_not_evaluated': to_list(head.parent.matrix_world) if head.parent else None,
    'location': list(head.location), 'rotation_euler': list(head.rotation_euler), 'scale': list(head.scale),
    'constraints': constraints}
eyes = json.loads((QA / 'stage6-eye-metadata.json').read_text(encoding='utf-8'))
relative = []
for eye in eyes['eye_Objects']:
    world = Matrix(eye['saved_matrices_not_evaluated']['world'])
    basis = Matrix(eye['saved_matrices_not_evaluated']['basis'])
    relative.append({'eye': eye['name'],
        'M_head_world_inverse_times_M_eye_world_API_unreliable': to_list(head.matrix_world.inverted() @ world),
        'M_head_basis_inverse_times_M_eye_basis_constrained_pose_not_included': to_list(head.matrix_basis.inverted() @ basis),
        'eye_parent_same_name_as_head': eye['parent']['name'] == record['parent_name'],
        'not_validated_for_geometry_placement': True})
after = sorted(obj.name for obj in bpy.context.scene.objects)
assert before == after and not head.users_scene
result = {'stage': '6_main_head_saved_transform_reference_only',
    'explicit_data_to_assigned_members': ['objects'], 'requested_Object': 'GEO-einar_head',
    'source': str(SOURCE), 'head': record, 'eye_to_head_static_matrix_candidates': relative,
    'scene_object_names_before': before, 'scene_object_names_after': after,
    'source_object_linked_or_evaluated': False, 'drivers_Text_or_rig_executed': False,
    'pixels_decoded_blend_saved_or_rendered': False,
    'caution': 'World/local API matrices after unlinked append may be identity/uninitialized. Basis is transform-channel data and excludes source Armature constraints and deformation. Neither proves evaluated neutral eye placement.',
    'elapsed_seconds': round(time.perf_counter()-started, 4)}
(QA / 'stage6-head-transform-reference.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print('HEAD_STATIC_TRANSFORM_REFERENCE_COMPLETE ' + json.dumps({'seconds': result['elapsed_seconds'],
    'head_world': record['API_matrices_after_append_without_evaluation']['world']}), flush=True)
