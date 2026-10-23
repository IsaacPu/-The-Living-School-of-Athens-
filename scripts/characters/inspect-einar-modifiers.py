"""Read only three source head Objects and static modifier data; never evaluate."""
from datetime import datetime, timezone
import json
from pathlib import Path
import time

import bpy

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / 'qa/characters/plato/v002/einar-intake'
SOURCE = Path('D:/AI/PROJECT/hackathon_projects/Aholo_3D_AI_Hackathon/project-management/source-cache/einar-v1/extracted/einar_release_v1.blend')
NAMES = ('GEO-einar_head', 'GEO-einar_head.base', 'GEO-einar_head.base.001')
KINDS = ('objects', 'meshes', 'materials', 'images', 'collections', 'armatures', 'actions', 'node_groups', 'texts', 'lattices', 'scenes', 'shape_keys', 'libraries', 'textures')
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


def fields(owner, attributes):
    return {key: plain(getattr(owner, key)) for key in attributes if hasattr(owner, key)}


def drivers(owner):
    animation = getattr(owner, 'animation_data', None)
    return [{'data_path': f.data_path, 'array_index': f.array_index, 'mute': f.mute}
            for f in animation.drivers] if animation else []


def names():
    return {kind: sorted(item.name for item in getattr(bpy.data, kind)) for kind in KINDS}


before = names()
scene_before = sorted(o.name for o in bpy.context.scene.objects)
with bpy.data.libraries.load(str(SOURCE), link=False) as (data_from, data_to):
    assert all(n in data_from.objects for n in NAMES)
    data_to.objects = list(NAMES)
objects = list(data_to.objects)
assert len(objects) == 3 and all(o is not None for o in objects)
records = []
for obj in objects:
    record = {'name': obj.name, 'type': obj.type,
        'data_name': obj.data.name if obj.data else None,
        'parent_name': obj.parent.name if obj.parent else None,
        'serialized_transform_not_evaluated': fields(obj, ('location', 'rotation_euler', 'scale', 'parent_type', 'parent_bone')),
        'hide_viewport': obj.hide_viewport, 'hide_render': obj.hide_render,
        'source_scene_memberships': [scene.name for scene in obj.users_scene],
        'object_driver_paths_only': drivers(obj), 'modifiers': [],
        'vertex_group_names': [g.name for g in obj.vertex_groups]}
    for index, mod in enumerate(obj.modifiers):
        m = {'stack_index': index, 'name': mod.name, 'type': mod.type,
             **fields(mod, ('show_viewport', 'show_render', 'show_in_editmode', 'show_on_cage'))}
        if mod.type == 'SUBSURF':
            m['settings'] = fields(mod, ('subdivision_type', 'levels', 'render_levels',
                'quality', 'uv_smooth', 'boundary_smooth', 'use_creases', 'use_limit_surface'))
        elif mod.type == 'DISPLACE':
            m['settings'] = fields(mod, ('strength', 'mid_level', 'direction', 'space',
                'texture_coords', 'uv_layer', 'vertex_group', 'invert_vertex_group', 'texture_coords_bone'))
            m['texture_coords_object'] = mod.texture_coords_object.name if mod.texture_coords_object else None
            texture = mod.texture
            m['texture'] = None
            if texture:
                m['texture'] = {'name': texture.name, 'type': texture.type,
                    'driver_paths_only': drivers(texture),
                    'settings': fields(texture, ('use_color_ramp', 'intensity', 'contrast',
                        'saturation', 'use_clamp', 'extension', 'use_interpolation', 'use_mipmap',
                        'use_normal_map', 'use_alpha', 'use_flip_axis', 'repeat_x', 'repeat_y',
                        'crop_min_x', 'crop_min_y', 'crop_max_x', 'crop_max_y'))}
                image = texture.image if hasattr(texture, 'image') else None
                m['texture']['image'] = {'name': image.name, 'filepath': image.filepath,
                    'source': image.source, 'colorspace': image.colorspace_settings.name,
                    'alpha_mode': image.alpha_mode} if image else None
                if texture.use_color_ramp:
                    m['texture']['color_ramp'] = [{'position': e.position, 'color': list(e.color)}
                                                for e in texture.color_ramp.elements]
            if mod.vertex_group:
                group = obj.vertex_groups.get(mod.vertex_group)
                weights = [entry.weight for vertex in obj.data.vertices for entry in vertex.groups
                           if group and entry.group == group.index]
                m['raw_vertex_group_weights'] = {'name': mod.vertex_group,
                    'assigned_vertex_count': len(weights),
                    'nonzero_count': sum(w > 0 for w in weights),
                    'min': min(weights) if weights else None, 'max': max(weights) if weights else None}
        elif mod.type == 'MULTIRES':
            m['settings'] = fields(mod, ('levels', 'sculpt_levels', 'render_levels',
                'total_levels', 'is_external', 'filepath', 'uv_smooth', 'boundary_smooth',
                'use_sculpt_base_mesh', 'use_creases'))
        elif mod.type == 'NODES':
            m['node_group'] = mod.node_group.name if mod.node_group else None
            m['public_parameters_serialized'] = {key: plain(value) for key, value in mod.items()}
            m['interface'] = []
            if mod.node_group:
                for item in mod.node_group.interface.items_tree:
                    if item.item_type == 'SOCKET':
                        m['interface'].append({'name': item.name, 'identifier': item.identifier,
                            'in_out': item.in_out, 'socket_type': item.socket_type,
                            'serialized_value_not_evaluated': plain(getattr(item, 'default_value', None))})
        elif mod.type == 'ARMATURE':
            m['settings'] = fields(mod, ('object', 'use_vertex_groups', 'use_bone_envelopes',
                'use_deform_preserve_volume', 'vertex_group', 'invert_vertex_group'))
        else:
            m['settings'] = fields(mod, ('vertex_group', 'strength', 'factor', 'iterations',
                'wrap_method', 'wrap_mode', 'target', 'object', 'use_x', 'use_y', 'use_z'))
        record['modifiers'].append(m)
    records.append(record)
scene_after = sorted(o.name for o in bpy.context.scene.objects)
assert scene_before == scene_after
assert all(not obj.users_scene for obj in objects)
after = names()
result = {'schema_version': 1, 'stage': '4_static_head_Object_modifiers_only',
    'created_utc': datetime.now(timezone.utc).isoformat(), 'source': str(SOURCE),
    'blender_version': bpy.app.version_string, 'requested_Objects': list(NAMES),
    'explicit_data_to_assigned_members': ['objects'], 'source_Objects': records,
    'new_ID_names': {kind: sorted(set(after[kind])-set(before[kind])) for kind in KINDS},
    'scene_object_names_before': scene_before, 'scene_object_names_after': scene_after,
    'source_Objects_linked_to_any_scene': False, 'depsgraph_or_modifiers_evaluated': False,
    'drivers_or_Text_executed': False, 'image_pixels_decoded': False,
    'blend_saved_or_rendered': False, 'serialized_values_are_not_neutral_rig_evaluation': True,
    'inspection_elapsed_seconds': round(time.perf_counter()-started, 4)}
(QA / 'stage4-head-modifiers-static.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('STAGE4_STATIC_MODIFIERS_COMPLETE ' + json.dumps({'seconds': result['inspection_elapsed_seconds'],
      'objects': [{'name': r['name'], 'modifiers': len(r['modifiers'])} for r in records]}), flush=True)
