"""One static append of the two eye Objects; saved transforms are not rig eval."""
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import time

import bpy

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / 'qa/characters/plato/v002/einar-intake'
SOURCE = Path('D:/AI/PROJECT/hackathon_projects/Aholo_3D_AI_Hackathon/project-management/source-cache/einar-v1/extracted/einar_release_v1.blend')
NAMES = ('GEO-eye.L', 'GEO-eye.R')
KINDS = ('objects', 'meshes', 'materials', 'images', 'collections', 'armatures', 'actions', 'node_groups', 'texts', 'lattices', 'scenes', 'shape_keys', 'libraries')
started = time.perf_counter()


def plain(value):
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    if isinstance(value, bpy.types.ID):
        return {'ID_name': value.name, 'ID_type': value.id_type}
    try:
        return [plain(v) for v in value]
    except TypeError:
        return str(value)


def matrix(value):
    return [[float(c) for c in row] for row in value]


def fields(owner, attributes):
    return {key: plain(getattr(owner, key)) for key in attributes if hasattr(owner, key)}


def drivers(owner):
    animation = getattr(owner, 'animation_data', None)
    return [{'data_path': f.data_path, 'array_index': f.array_index, 'mute': f.mute}
            for f in animation.drivers] if animation else []


def bounds(points):
    return {'min': [min(p[i] for p in points) for i in range(3)],
            'max': [max(p[i] for p in points) for i in range(3)]}


def names():
    return {kind: sorted(item.name for item in getattr(bpy.data, kind)) for kind in KINDS}


def collect_images(tree, seen=None):
    seen = set() if seen is None else seen
    if tree is None or tree.as_pointer() in seen:
        return {}
    seen.add(tree.as_pointer())
    images = {}
    for node in tree.nodes:
        if node.type == 'TEX_IMAGE' and node.image:
            image = node.image
            images[image.name] = {'name': image.name, 'filepath': image.filepath,
                'colorspace': image.colorspace_settings.name, 'source': image.source,
                'alpha_mode': image.alpha_mode}
        elif node.type == 'GROUP':
            images.update(collect_images(node.node_tree, seen))
    return images


before = names()
scene_before = sorted(o.name for o in bpy.context.scene.objects)
with bpy.data.libraries.load(str(SOURCE), link=False) as (data_from, data_to):
    assert all(name in data_from.objects for name in NAMES)
    data_to.objects = list(NAMES)
objects = list(data_to.objects)
records = []
materials = {}
for obj in objects:
    assert obj and obj.type == 'MESH'
    mesh = obj.data
    saved_world = obj.matrix_world.copy()
    record = {'name': obj.name, 'mesh': mesh.name, 'vertices': len(mesh.vertices),
        'polygons': len(mesh.polygons), 'polygon_arities': dict(Counter(len(p.vertices) for p in mesh.polygons)),
        'raw_mesh_local_bounds': bounds([v.co for v in mesh.vertices]),
        'bounds_using_saved_world_matrix_no_rig_evaluation': bounds([saved_world @ v.co for v in mesh.vertices]),
        'saved_matrices_not_evaluated': {'world': matrix(saved_world), 'local': matrix(obj.matrix_local),
            'basis': matrix(obj.matrix_basis), 'parent_inverse': matrix(obj.matrix_parent_inverse)},
        'serialized_transform': fields(obj, ('location', 'rotation_mode', 'rotation_euler',
            'rotation_quaternion', 'rotation_axis_angle', 'scale', 'delta_location', 'delta_rotation_euler', 'delta_scale')),
        'parent': {'name': obj.parent.name if obj.parent else None,
            'type': obj.parent_type, 'bone': obj.parent_bone,
            'saved_world_matrix_not_evaluated': matrix(obj.parent.matrix_world) if obj.parent else None},
        'constraints': [], 'object_driver_paths': drivers(obj),
        'mesh_driver_paths': drivers(mesh), 'key_driver_paths': drivers(mesh.shape_keys) if mesh.shape_keys else [],
        'shape_keys': [{'name': k.name, 'serialized_value_not_evaluated': k.value,
                       'relative_key_name': k.relative_key.name if k.relative_key else None}
                      for k in mesh.shape_keys.key_blocks] if mesh.shape_keys else [],
        'UV_layers': [uv.name for uv in mesh.uv_layers], 'modifiers': [], 'material_slots': []}
    if obj.parent and obj.parent.type == 'ARMATURE' and obj.parent_type == 'BONE':
        bone = obj.parent.data.bones.get(obj.parent_bone)
        record['parent']['bone_rest_matrix_local'] = matrix(bone.matrix_local) if bone else None
    for constraint in obj.constraints:
        record['constraints'].append({'name': constraint.name, 'type': constraint.type,
            **fields(constraint, ('mute', 'influence', 'target', 'subtarget', 'owner_space', 'target_space',
                                 'track_axis', 'up_axis', 'use_x', 'use_y', 'use_z'))})
    for mod in obj.modifiers:
        record['modifiers'].append({'name': mod.name, 'type': mod.type,
            **fields(mod, ('show_viewport', 'show_render', 'levels', 'render_levels', 'subdivision_type',
                           'uv_smooth', 'boundary_smooth', 'use_creases', 'use_limit_surface', 'object', 'strength', 'vertex_group'))})
    for slot_index, slot in enumerate(obj.material_slots):
        polygons = [p for p in mesh.polygons if p.material_index == slot_index]
        indices = sorted({v for p in polygons for v in p.vertices})
        record['material_slots'].append({'index': slot_index, 'slot_link': slot.link,
            'material': slot.material.name if slot.material else None,
            'polygon_count': len(polygons), 'unique_vertices': len(indices),
            'raw_local_partition_bounds': bounds([mesh.vertices[i].co for i in indices]) if indices else None})
        mat = slot.material
        if mat and mat.name not in materials:
            entry = {'name': mat.name, 'uses_nodes': mat.use_nodes, 'drivers': drivers(mat),
                     'images_in_static_graph': collect_images(mat.node_tree) if mat.use_nodes else {},
                     'root_nodes': [], 'root_links': []}
            if mat.use_nodes:
                entry['node_tree_drivers'] = drivers(mat.node_tree)
                for node in mat.node_tree.nodes:
                    n = {'name': node.name, 'type': node.bl_idname, 'label': node.label,
                        'inputs': [{'name': s.name, 'identifier': s.identifier, 'linked': s.is_linked,
                                    'serialized_value_not_evaluated': plain(getattr(s, 'default_value', None))}
                                   for s in node.inputs]}
                    if node.type == 'GROUP' and node.node_tree:
                        n['group'] = node.node_tree.name
                    entry['root_nodes'].append(n)
                entry['root_links'] = [{'from_node': link.from_node.name, 'from_socket': link.from_socket.name,
                    'to_node': link.to_node.name, 'to_socket': link.to_socket.name}
                    for link in mat.node_tree.links]
            materials[mat.name] = entry
    records.append(record)
scene_after = sorted(o.name for o in bpy.context.scene.objects)
assert scene_before == scene_after and all(not obj.users_scene for obj in objects)
head = bpy.data.objects.get('GEO-einar_head')
head_reference = None
if head:
    head_reference = {'name': head.name, 'implicitly_loaded_only': True,
        'saved_world_matrix_not_evaluated': matrix(head.matrix_world),
        'saved_basis_matrix_not_evaluated': matrix(head.matrix_basis),
        'parent_name': head.parent.name if head.parent else None}
after = names()
result = {'schema_version': 1, 'stage': '6_two_eye_Objects_saved_metadata_only',
    'created_utc': datetime.now(timezone.utc).isoformat(), 'source': str(SOURCE),
    'explicit_data_to_assigned_members': ['objects'], 'requested_Objects': list(NAMES),
    'eye_Objects': records, 'materials': materials, 'head_reference_if_implicit': head_reference,
    'new_ID_names': {kind: sorted(set(after[kind])-set(before[kind])) for kind in KINDS},
    'scene_objects_before': scene_before, 'scene_objects_after': scene_after,
    'source_Objects_linked_or_depsgraph_evaluated': False, 'drivers_Text_or_rig_executed': False,
    'image_pixels_decoded_blend_saved_or_rendered': False,
    'saved_matrices_do_not_establish_evaluated_neutral_pose': True,
    'elapsed_seconds': round(time.perf_counter()-started, 4)}
(QA / 'stage6-eye-metadata.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print('EYE_STATIC_METADATA_COMPLETE ' + json.dumps({'seconds': result['elapsed_seconds'],
    'objects': [o.name for o in objects], 'head_reference_implicit': bool(head_reference)}), flush=True)
