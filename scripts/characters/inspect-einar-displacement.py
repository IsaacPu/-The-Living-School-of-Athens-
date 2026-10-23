"""Static raw-coordinate, key-value and displacement-graph diagnosis. No eval."""
from datetime import datetime, timezone
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
NAMES = ['DATA_GEO-einar_head', 'DATA_GEO-einar_head.base', 'DATA_GEO-einar_head.base.001']
KINDS = ('objects', 'meshes', 'materials', 'images', 'collections', 'armatures', 'actions', 'node_groups', 'texts', 'lattices', 'scenes', 'shape_keys', 'libraries')
started = time.perf_counter()


def names():
    return {kind: sorted(x.name for x in getattr(bpy.data, kind)) for kind in KINDS}


def plain(value):
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    try:
        return [plain(v) for v in value]
    except TypeError:
        return str(value)


def socket_record(socket):
    result = {'name': socket.name, 'identifier': socket.identifier,
              'type': socket.type, 'linked': socket.is_linked}
    if hasattr(socket, 'default_value'):
        result['serialized_value_not_evaluated'] = plain(socket.default_value)
    return result


def drivers(owner):
    animation = getattr(owner, 'animation_data', None)
    return [{'data_path': curve.data_path, 'array_index': curve.array_index,
             'mute': curve.mute} for curve in animation.drivers] if animation else []


def coords(points):
    return [tuple(float(c) for c in p.co) for p in points]


def coord_hash(points):
    h = hashlib.sha256()
    for p in points:
        h.update(struct.pack('<3f', *p))
    return h.hexdigest()


def comparison(a, b):
    if len(a) != len(b):
        return {'same_vertex_count': False, 'counts': [len(a), len(b)]}
    squared = [sum((x-y)**2 for x, y in zip(p, q)) for p, q in zip(a, b)]
    largest = max(range(len(squared)), key=squared.__getitem__)
    return {'same_vertex_count': True, 'max_distance': math.sqrt(squared[largest]),
            'rms_distance': math.sqrt(sum(squared) / len(squared)),
            'vertices_different_above_1e_8': sum(v > 1e-16 for v in squared),
            'largest_delta_vertex_index': largest,
            'largest_delta_xyz': [b[largest][i]-a[largest][i] for i in range(3)],
            'hash_a': coord_hash(a), 'hash_b': coord_hash(b)}


before = names()
scene_objects_before = sorted(o.name for o in bpy.context.scene.objects)
with bpy.data.libraries.load(str(SOURCE), link=False) as (data_from, data_to):
    assert all(name in data_from.meshes for name in NAMES)
    data_to.meshes = list(NAMES)
    if 'ReadMe.txt' in data_from.texts:
        data_to.texts = ['ReadMe.txt']
meshes = list(data_to.meshes)
assert all(mesh is not None for mesh in meshes)
arrays = {mesh.name + ':vertices': coords(mesh.vertices) for mesh in meshes}
mesh_records = []
face_arrays = {}
for mesh in meshes:
    key = mesh.shape_keys
    blocks = []
    if key:
        for block in key.key_blocks:
            blocks.append({'name': block.name, 'serialized_value_not_evaluated': block.value,
                'relative_key_name': block.relative_key.name if block.relative_key else None,
                'mute': block.mute, 'slider_min': block.slider_min, 'slider_max': block.slider_max})
        arrays[mesh.name + ':Basis'] = coords(key.key_blocks[0].data)
    face_arrays[mesh.name] = [tuple(p.vertices) for p in mesh.polygons]
    mesh_records.append({'name': mesh.name, 'vertices': len(mesh.vertices),
        'polygons': len(mesh.polygons), 'uv_names': [uv.name for uv in mesh.uv_layers],
        'key_use_relative': key.use_relative if key else None, 'keys': blocks,
        'key_driver_paths_only': drivers(key) if key else [],
        'mesh_driver_paths_only': drivers(mesh)})
comparisons = []
array_names = list(arrays)
for i, a_name in enumerate(array_names):
    for b_name in array_names[i+1:]:
        comparisons.append({'a': a_name, 'b': b_name, **comparison(arrays[a_name], arrays[b_name])})

material = bpy.data.materials.get('einar.skin')
assert material and material.use_nodes
trees = {}


def dump_tree(tree):
    if tree.name in trees:
        return
    result = {'name': tree.name, 'drivers': drivers(tree), 'nodes': [], 'links': [], 'interface': []}
    trees[tree.name] = result
    if hasattr(tree, 'interface'):
        for item in tree.interface.items_tree:
            if item.item_type == 'SOCKET':
                result['interface'].append({'name': item.name, 'identifier': item.identifier,
                    'in_out': item.in_out, 'socket_type': item.socket_type,
                    'serialized_value_not_evaluated': plain(getattr(item, 'default_value', None))})
    for node in tree.nodes:
        record = {'name': node.name, 'label': node.label, 'bl_idname': node.bl_idname,
                  'type': node.type, 'mute': node.mute,
                  'inputs': [socket_record(s) for s in node.inputs],
                  'outputs': [socket_record(s) for s in node.outputs]}
        for attr in ('operation', 'space', 'uv_map', 'blend_type', 'data_type', 'mode',
                     'clamp_factor', 'clamp_result', 'use_clamp', 'interpolation',
                     'projection', 'extension', 'is_active_output'):
            if hasattr(node, attr):
                record[attr] = plain(getattr(node, attr))
        if node.type == 'TEX_IMAGE' and node.image:
            record['image'] = {'name': node.image.name, 'filepath': node.image.filepath,
                'colorspace': node.image.colorspace_settings.name, 'source': node.image.source,
                'alpha_mode': node.image.alpha_mode}
        if node.type == 'VALTORGB':
            record['color_ramp'] = [{'position': e.position, 'color': list(e.color)} for e in node.color_ramp.elements]
        if node.type == 'GROUP' and node.node_tree:
            record['node_tree'] = node.node_tree.name
            dump_tree(node.node_tree)
        result['nodes'].append(record)
    for link in tree.links:
        result['links'].append({'from_node': link.from_node.name, 'from_socket': link.from_socket.name,
            'from_identifier': link.from_socket.identifier, 'to_node': link.to_node.name,
            'to_socket': link.to_socket.name, 'to_identifier': link.to_socket.identifier,
            'is_valid': link.is_valid, 'is_muted': link.is_muted})


dump_tree(material.node_tree)
visited = set()
upstream = []


def socket_match(sockets, target, fallback_index):
    matched = next((s for s in sockets if s.identifier == target.identifier), None)
    if matched is None:
        matched = next((s for s in sockets if s.name == target.name), None)
    return matched if matched is not None else sockets[fallback_index]


def walk_input(tree, socket, context):
    for link in socket.links:
        if link.is_valid and not link.is_muted:
            walk_output(tree, link.from_socket, context)


def walk_output(tree, socket, context):
    node = socket.node
    context_path = tuple(c[1].name for c in context)
    identity = (tree.as_pointer(), node.as_pointer(), socket.identifier, context_path)
    if identity in visited:
        return
    visited.add(identity)
    upstream.append({'tree': tree.name, 'group_instance_path': list(context_path),
                     'node': node.name, 'type': node.bl_idname, 'output': socket.name,
                     'muted_node': node.mute})
    if node.type == 'GROUP' and node.node_tree:
        outputs = [n for n in node.node_tree.nodes if n.type == 'GROUP_OUTPUT' and n.is_active_output]
        index = list(node.outputs).index(socket)
        for output in outputs:
            walk_input(node.node_tree, socket_match(output.inputs, socket, index), context + [(tree, node)])
    elif node.type == 'GROUP_INPUT' and context:
        parent_tree, parent_node = context[-1]
        index = list(node.outputs).index(socket)
        walk_input(parent_tree, socket_match(parent_node.inputs, socket, index), context[:-1])
    else:
        for input_socket in node.inputs:
            walk_input(tree, input_socket, context)


output_records = []
for output in material.node_tree.nodes:
    if output.type == 'OUTPUT_MATERIAL':
        output_records.append({'name': output.name, 'active': output.is_active_output,
            'displacement': socket_record(output.inputs['Displacement'])})
        if output.is_active_output:
            walk_input(material.node_tree, output.inputs['Displacement'], [])
after = names()
scene_objects_after = sorted(o.name for o in bpy.context.scene.objects)
assert scene_objects_before == scene_objects_after
readme = bpy.data.texts.get('ReadMe.txt')
material_settings = {}
for attr in ('displacement_method', 'max_vertex_displacement', 'surface_render_method'):
    if hasattr(material, attr):
        material_settings[attr] = plain(getattr(material, attr))
result = {'schema_version': 1, 'stage': '3_static_displacement_diagnosis_no_render',
    'created_utc': datetime.now(timezone.utc).isoformat(), 'blender_version': bpy.app.version_string,
    'source': str(SOURCE), 'explicit_library_members_assigned': ['meshes', 'texts(ReadMe.txt only)'],
    'mesh_records': mesh_records, 'coordinate_comparisons': comparisons,
    'all_three_mesh_face_index_orders_identical': all(v == face_arrays[NAMES[0]] for v in face_arrays.values()),
    'material': {'name': material.name, 'node_tree': material.node_tree.name,
                 'settings': material_settings, 'drivers': drivers(material), 'outputs': output_records},
    'upstream_of_active_displacement': upstream, 'node_trees': trees,
    'readme_static_text_untrusted_reference_only': readme.as_string() if readme else None,
    'new_ID_names': {kind: sorted(set(after[kind]) - set(before[kind])) for kind in before},
    'scene_objects_before': scene_objects_before, 'scene_objects_after': scene_objects_after,
    'source_objects_linked_or_evaluated': False, 'drivers_or_Text_executed': False,
    'image_pixels_decoded': False, 'blend_saved_or_rendered': False,
    'serialized_values_are_not_neutral_rig_evaluation': True,
    'elapsed_seconds': round(time.perf_counter() - started, 4)}
(QA / 'stage3-displacement-static.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('STAGE3_STATIC_COMPLETE ' + json.dumps({'seconds': result['elapsed_seconds'],
      'upstream_socket_count': len(upstream), 'node_tree_count': len(trees)}), flush=True)
