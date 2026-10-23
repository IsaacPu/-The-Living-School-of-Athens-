"""No render: embed attribution, reopen/export/reimport the actual head study."""
import hashlib
import json
from pathlib import Path
import bpy

root = Path(__file__).resolve().parents[2]
asset = root/'art/characters/plato/v002'
qa = root/'qa/characters/plato/v002'
blend = asset/'work/plato-head-study.blend'
glb = asset/'export/plato-head-geometry-study.glb'
bpy.ops.wm.open_mainfile(filepath=str(blend), load_ui=False, use_scripts=False)
head = bpy.data.objects['C1_Local_head_form_candidate']
eyes = bpy.data.objects['C_Eyeballs_anatomy_check']
neutral = bpy.data.objects['C0_Licensed_head_proportion_control']
before = [head.matrix_world @ v.co for v in head.data.vertices]
for obj in (head, neutral, eyes):
    obj['source_attribution'] = 'Blender Studio / Project Heist; lesson author Julien Kaspar'
    obj['source_license'] = 'CC BY 4.0'
    obj['source_license_url'] = 'https://creativecommons.org/licenses/by/4.0/'
    obj['source_page'] = 'https://studio.blender.org/training/realistic-human-research/use-of-base-meshes/'
    obj['modifications'] = 'Head extraction, proportion placement and localized form edits; see accompanying experiment.json.'
bpy.context.scene['art_status'] = 'art_not_accepted'
bpy.context.scene['asset_role'] = 'standalone_head_geometry_study'
bpy.ops.object.select_all(action='DESELECT')
for obj in (head, eyes):
    obj.hide_set(False)
    obj.hide_render = False
    obj.select_set(True)
bpy.context.view_layer.objects.active = head
bpy.ops.export_scene.gltf(filepath=str(glb), export_format='GLB', use_selection=True, export_yup=True,
    export_animations=False, export_skins=False, export_cameras=False, export_lights=False, export_extras=True)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(blend))
head_points = [list(p) for p in before]
head_info = {'vertices': len(before), 'min': [min(p[k] for p in before) for k in range(3)],
             'max': [max(p[k] for p in before) for k in range(3)]}
# Real clean-file reimport; do not count QA lights or the baseline body.
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(glb))
objects = [o for o in bpy.context.scene.objects if o.type == 'MESH']
points = [o.matrix_world @ v.co for o in objects for v in o.data.vertices]
after_head = next(o for o in objects if o.name.startswith('C1_'))
key = lambda p: tuple(round(x*1e5) for x in p)
head_shape_preserved = set(map(key, before)) == {key(after_head.matrix_world @ v.co) for v in after_head.data.vertices}
if not head_shape_preserved:
    raise RuntimeError('Head vertex positions changed in export/reimport')
result = {'passed': True, 'blend_reopened': True, 'glb_reimported_in_empty_scene': True,
          'head_position_set_preserved_at_0_01mm': head_shape_preserved, 'mesh_objects': len(objects),
          'source_head_blender_bounds_m': head_info,
          'reimport_bounds_blender_m': {'min': [min(p[k] for p in points) for k in range(3)],
                                      'max': [max(p[k] for p in points) for k in range(3)]},
          'embedded_attribution': [{'object': o.name, 'license': o.get('source_license'),
                                    'attribution': o.get('source_attribution')} for o in objects],
          'art_status': 'art_not_accepted', 'asset_role': 'standalone_head_geometry_study'}
(qa/'roundtrip.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
experiment = json.loads((qa/'experiment.json').read_text(encoding='utf-8'))
experiment['outputs']['head_study'].update(sha256=hashlib.sha256(glb.read_bytes()).hexdigest(), bytes=glb.stat().st_size)
experiment['art_status'] = 'art_not_accepted'
experiment['asset_role'] = 'standalone_head_geometry_study'
(qa/'experiment.json').write_text(json.dumps(experiment, indent=2), encoding='utf-8')
print('HEAD_ROUNDTRIP_OK ' + json.dumps(result))
