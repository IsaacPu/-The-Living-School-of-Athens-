"""Static expansion of the two identified geometry displacement groups only."""
import json
from pathlib import Path
import time

import bpy

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / 'qa/characters/plato/v002/einar-intake'
SOURCE = Path('D:/AI/PROJECT/hackathon_projects/Aholo_3D_AI_Hackathon/project-management/source-cache/einar-v1/extracted/einar_release_v1.blend')
NAMES = ('texture_displacement', 'Displacement_Face')
started = time.perf_counter()


def plain(value):
    if value is None or isinstance(value, (str, bool, float, int)):
        return value
    if isinstance(value, bpy.types.ID):
        result = {'ID_name': value.name, 'ID_type': value.id_type}
        if isinstance(value, bpy.types.Image):
            result.update(filepath=value.filepath, colorspace=value.colorspace_settings.name,
                          source=value.source)
        return result
    try:
        return [plain(v) for v in value]
    except TypeError:
        return str(value)


def socket(s):
    return {'name': s.name, 'identifier': s.identifier, 'type': s.type,
        'is_linked': s.is_linked,
        'serialized_value_not_evaluated': plain(getattr(s, 'default_value', None))}


scene_before = sorted(o.name for o in bpy.context.scene.objects)
with bpy.data.libraries.load(str(SOURCE), link=False) as (data_from, data_to):
    assert all(name in data_from.node_groups for name in NAMES)
    data_to.node_groups = list(NAMES)
trees = {}


def dump(tree):
    if tree.name in trees:
        return
    animation = tree.animation_data
    record = {'name': tree.name, 'bl_idname': tree.bl_idname,
        'driver_count': len(animation.drivers) if animation else 0,
        'interface': [], 'nodes': [], 'links': []}
    trees[tree.name] = record
    for item in tree.interface.items_tree:
        if item.item_type == 'SOCKET':
            record['interface'].append({'name': item.name, 'identifier': item.identifier,
                'in_out': item.in_out, 'socket_type': item.socket_type,
                'serialized_value_not_evaluated': plain(getattr(item, 'default_value', None))})
    for node in tree.nodes:
        n = {'name': node.name, 'label': node.label, 'type': node.bl_idname, 'mute': node.mute,
             'inputs': [socket(s) for s in node.inputs], 'outputs': [socket(s) for s in node.outputs]}
        for attr in ('operation', 'data_type', 'domain', 'mode', 'space', 'attribute_name',
                     'interpolation', 'extension', 'is_active_output', 'input_type'):
            if hasattr(node, attr):
                n[attr] = plain(getattr(node, attr))
        if node.type == 'GROUP' and node.node_tree:
            n['node_group'] = node.node_tree.name
            dump(node.node_tree)
        record['nodes'].append(n)
    for link in tree.links:
        record['links'].append({'from_node': link.from_node.name,
            'from_socket': link.from_socket.name, 'from_identifier': link.from_socket.identifier,
            'to_node': link.to_node.name, 'to_socket': link.to_socket.name,
            'to_identifier': link.to_socket.identifier, 'is_valid': link.is_valid,
            'is_muted': link.is_muted})


for tree in data_to.node_groups:
    assert tree is not None
    dump(tree)
scene_after = sorted(o.name for o in bpy.context.scene.objects)
assert scene_after == scene_before
result = {'stage': '4_geometry_group_static_expansion_only', 'source': str(SOURCE),
    'explicit_data_to_assigned_members': ['node_groups'], 'requested_groups': list(NAMES),
    'node_trees': trees, 'scene_object_names_before': scene_before,
    'scene_object_names_after': scene_after, 'source_Objects_linked_or_evaluated': False,
    'node_groups_evaluated': False, 'drivers_or_Text_executed': False,
    'image_pixels_decoded': False, 'blend_saved_or_rendered': False,
    'elapsed_seconds': round(time.perf_counter()-started, 4)}
(QA / 'stage4-geometry-nodes-static.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('GEOMETRY_GROUP_STATIC_COMPLETE ' + json.dumps({'seconds': result['elapsed_seconds'],
      'trees': {name: len(tree['nodes']) for name, tree in trees.items()}}), flush=True)
