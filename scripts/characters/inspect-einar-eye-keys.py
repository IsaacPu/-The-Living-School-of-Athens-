"""Prove static eye-shape layers and extract plain arrays without rig evaluation."""
import hashlib
import json
import math
from pathlib import Path
import struct
import time

import bpy

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / 'qa/characters/plato/v002/einar-intake'
SOURCE = Path('D:/AI/PROJECT/hackathon_projects/Aholo_3D_AI_Hackathon/project-management/source-cache/einar-v1/extracted/einar_release_v1.blend')
NAMES = ('DATA_GEO-eye.L', 'DATA_GEO-eye.R')
STATIC_NAMES = ('resize', 'GEO-resize2_pupil', 'GEO-resize2_iris')
started = time.perf_counter()
before = sorted(o.name for o in bpy.context.scene.objects)
points = lambda block: [tuple(float(c) for c in v.co) for v in block]
hash_points = lambda vertices: hashlib.sha256(b''.join(struct.pack('<3f', *v) for v in vertices)).hexdigest()
with bpy.data.libraries.load(str(SOURCE), link=False) as (data_from, data_to):
    assert all(n in data_from.meshes for n in NAMES)
    data_to.meshes = list(NAMES)
records = []
for mesh in data_to.meshes:
    key = mesh.shape_keys
    assert key and key.use_relative
    animation = key.animation_data
    action = animation.action if animation else None
    nla = [{'name': track.name, 'mute': track.mute,
            'strips': [{'name': strip.name, 'action': strip.action.name if strip.action else None}
                       for strip in track.strips]} for track in animation.nla_tracks] if animation else []
    driver_paths = [curve.data_path for curve in animation.drivers] if animation else []
    basis = points(key.reference_key.data)
    mesh_points = points(mesh.vertices)
    static_layers = []
    reconstructed = [list(v) for v in basis]
    eligible = action is None and len(nla) == 0
    for name in STATIC_NAMES:
        block = key.key_blocks.get(name)
        assert block is not None
        value_path = block.path_from_id('value')
        has_driver = value_path in driver_paths
        eligible = eligible and not has_driver and not block.mute and block.relative_key.as_pointer() == key.reference_key.as_pointer()
        block_points = points(block.data)
        relative_points = points(block.relative_key.data)
        squared = [sum((x-y)**2 for x, y in zip(a, b)) for a, b in zip(block_points, relative_points)]
        static_layers.append({'name': name, 'stored_value': block.value,
            'has_value_driver': has_driver, 'mute': block.mute,
            'relative_key': block.relative_key.name, 'value_RNA_path': value_path,
            'max_delta_from_relative_key': math.sqrt(max(squared)),
            'rms_delta_from_relative_key': math.sqrt(sum(squared)/len(squared))})
        for i, (p, relative) in enumerate(zip(block_points, relative_points)):
            for axis in range(3):
                reconstructed[i][axis] += (p[axis]-relative[axis])*block.value
    record = {'mesh': mesh.name, 'shape_key_ID': key.name, 'use_relative': key.use_relative,
        'active_action': action.name if action else None, 'NLA_tracks': nla,
        'all_key_driver_paths': driver_paths, 'static_layers': static_layers,
        'eligible_for_static_relative_key_reconstruction': eligible,
        'basis_sha256': hash_points(basis), 'raw_mesh_sha256': hash_points(mesh_points),
        'raw_mesh_vertices_equal_Basis': mesh_points == basis,
        'excluded_driven_keys': [b.name for b in key.key_blocks if b.path_from_id('value') in driver_paths],
        'formula': 'Basis + sum((key_i - relative_key_i) * authored stored value_i) for the three undriven static keys only. Driven Shrink/Grow excluded; no claim of evaluated rig neutral.',
        'vertices': len(basis), 'polygons': len(mesh.polygons)}
    if eligible:
        record['positions_with_only_proven_static_keys'] = reconstructed
        record['static_reconstruction_sha256'] = hash_points(reconstructed)
        record['faces'] = [list(p.vertices) for p in mesh.polygons]
        record['material_indices'] = [p.material_index for p in mesh.polygons]
        record['polygon_smooth'] = [p.use_smooth for p in mesh.polygons]
        record['UV_layers'] = {uv.name: [[float(c) for c in item.uv] for item in uv.data]
                               for uv in mesh.uv_layers}
        record['loop_vertex_indices'] = [loop.vertex_index for loop in mesh.loops]
    records.append(record)
after = sorted(o.name for o in bpy.context.scene.objects)
assert before == after
result = {'stage': '6_static_eye_key_proof_and_plain_arrays', 'source': str(SOURCE),
    'explicit_data_to_assigned_members': ['meshes'], 'requested_meshes': list(NAMES),
    'eyes': records, 'source_geometry_or_keys_modified': False,
    'source_Objects_linked_or_evaluated': False, 'drivers_Text_or_rig_executed': False,
    'pixels_decoded_blend_saved_or_rendered': False,
    'scene_objects_before': before, 'scene_objects_after': after,
    'elapsed_seconds': round(time.perf_counter()-started, 4)}
(QA / 'stage6-eye-static-keys.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print('EYE_STATIC_KEYS_COMPLETE ' + json.dumps({'seconds': result['elapsed_seconds'],
    'eligible': {r['mesh']: r['eligible_for_static_relative_key_reconstruction'] for r in records}}), flush=True)
