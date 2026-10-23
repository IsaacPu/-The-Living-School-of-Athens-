"""One authorized source-informed rest-candidate closeup, no source rig eval."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil
import struct
import time

import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / 'qa/characters/plato/v002/einar-intake'
OUT = ROOT / 'art/characters/plato/v002/einar-static-closeup-review'
SOURCE = Path('D:/AI/PROJECT/hackathon_projects/Aholo_3D_AI_Hackathon/project-management/source-cache/einar-v1/extracted/einar_release_v1.blend')
AB = ROOT / 'art/characters/plato/v002/einar-default-sculpt-review/einar-default-sculpt-AB.blend'
STATIC_KEYS = ('resize', 'GEO-resize2_pupil', 'GEO-resize2_iris')
started = time.perf_counter()
OUT.mkdir(parents=True, exist_ok=True)
(OUT / 'textures').mkdir(parents=True, exist_ok=True)
eye_meta = json.loads((QA / 'stage6-eye-metadata.json').read_text(encoding='utf-8'))
head_meta = json.loads((QA / 'stage6-head-transform-reference.json').read_text(encoding='utf-8'))
assert Matrix(head_meta['head']['API_matrices_after_append_without_evaluation']['parent_inverse']) == Matrix.Identity(4)
head_basis = Matrix(head_meta['head']['API_matrices_after_append_without_evaluation']['basis'])
eye_data = []
with bpy.data.libraries.load(str(SOURCE), link=False) as (data_from, data_to):
    data_to.meshes = ['DATA_GEO-eye.L', 'DATA_GEO-eye.R']
for raw in data_to.meshes:
    key = raw.shape_keys
    assert key and key.use_relative
    animation = key.animation_data
    assert not animation or (animation.action is None and len(animation.nla_tracks) == 0)
    driver_paths = {f.data_path for f in animation.drivers} if animation else set()
    basis = [tuple(v.co) for v in key.reference_key.data]
    positions = [list(v) for v in basis]
    key_evidence = []
    for name in STATIC_KEYS:
        block = key.key_blocks[name]
        assert not block.mute and block.value == 1
        assert block.path_from_id('value') not in driver_paths
        assert block.relative_key.as_pointer() == key.reference_key.as_pointer()
        for index, (point, relative) in enumerate(zip(block.data, block.relative_key.data)):
            for axis in range(3):
                positions[index][axis] += (float(point.co[axis])-float(relative.co[axis]))*block.value
        key_evidence.append({'name': name, 'value': block.value, 'driver': False,
                             'relative_key': block.relative_key.name})
    obj_meta = next(o for o in eye_meta['eye_Objects'] if o['mesh'] == raw.name)
    assert Matrix(obj_meta['saved_matrices_not_evaluated']['parent_inverse']) == Matrix.Identity(4)
    assert obj_meta['parent']['name'] == head_meta['head']['parent_name']
    rest_matrix = head_basis.inverted() @ Matrix(obj_meta['saved_matrices_not_evaluated']['basis'])
    crease = raw.attributes.get('crease_edge')
    crease_by_edge = {tuple(sorted(edge.vertices)): float(crease.data[edge.index].value)
                      for edge in raw.edges} if crease else {}
    eye_data.append({'source_name': obj_meta['name'], 'source_mesh': raw.name,
        'positions': positions, 'faces': [tuple(p.vertices) for p in raw.polygons],
        'material_indices': [p.material_index for p in raw.polygons],
        'smooth': [p.use_smooth for p in raw.polygons],
        'UV': {uv.name: [tuple(item.uv) for item in uv.data] for uv in raw.uv_layers},
        'loop_vertex_indices': [loop.vertex_index for loop in raw.loops],
        'crease_by_edge': crease_by_edge,
        'rest_matrix': [[float(c) for c in row] for row in rest_matrix],
        'static_keys': key_evidence})
del raw, key, data_from, data_to

# Opening this already-clean source replaces every ID appended from the original.
bpy.ops.wm.open_mainfile(filepath=str(AB), load_ui=False, use_scripts=False)
for kind in ('armatures', 'actions', 'lattices', 'texts', 'libraries', 'shape_keys'):
    assert len(getattr(bpy.data, kind)) == 0, kind
print('REOPENED_CLEAN_ID_INVENTORY '+json.dumps({'meshes':[m.name for m in bpy.data.meshes],
    'images':[{'name':i.name,'type':i.type,'source':i.source} for i in bpy.data.images],
    'node_groups':[g.name for g in bpy.data.node_groups]}),flush=True)
for internal_image in list(bpy.data.images):
    if internal_image.type in ('RENDER_RESULT', 'COMPOSITING'):
        bpy.data.images.remove(internal_image)
assert len(bpy.data.meshes) == 1 and len(bpy.data.images) == 1 and len(bpy.data.node_groups) == 1
head = bpy.data.objects['EinarDefaultCleanHead']
assert head.matrix_world == Matrix.Identity(4)
assert head.animation_data is None and head.data.animation_data is None
assert len(head.modifiers) == 2 and head.modifiers[0].render_levels == 2
gn = head.modifiers[1]
assert len(gn.node_group.nodes) == 9 and gn.node_group.animation_data is None
gn.show_viewport = gn.show_render = True
assert gn[ next(s.identifier for s in gn.node_group.interface.items_tree if s.item_type == 'SOCKET' and s.in_out == 'INPUT' and s.name == 'Scale') ] == 0.00800000037997961
default_image = bpy.data.images[0]
default_resolved = Path(bpy.path.abspath(default_image.filepath)).resolve()
ab_report = json.loads((QA / 'stage5-default-sculpt-ab.json').read_text(encoding='utf-8'))
assert default_resolved.is_file()
assert hashlib.sha256(default_resolved.read_bytes()).hexdigest() == ab_report['texture_sha256']
texture_records = []


def copied_texture(name, original):
    destination = OUT / 'textures' / original.name
    before_hash = hashlib.sha256(original.read_bytes()).hexdigest()
    if destination.exists():
        assert hashlib.sha256(destination.read_bytes()).hexdigest() == before_hash
    else:
        shutil.copyfile(original, destination)
    assert hashlib.sha256(destination.read_bytes()).hexdigest() == before_hash
    texture_records.append({'role': name, 'source': str(original), 'local_copy': str(destination),
        'sha256': before_hash, 'bytes': destination.stat().st_size,
        'final_relative_path': '//textures/'+destination.name})
    return destination


default_local = copied_texture('default_scalar_sculpt', default_resolved)
default_image.filepath = str(default_local)
albedo_path = copied_texture('skin_base_albedo_sRGB', SOURCE.parent / 'textures/face/einar_skin.albedo.tif')
roughness_path = copied_texture('skin_base_roughness_NonColor', SOURCE.parent / 'textures/face/einar_skin.roughness.tif')
albedo = bpy.data.images.load(str(albedo_path), check_existing=False)
albedo.colorspace_settings.name = 'sRGB'
roughness = bpy.data.images.load(str(roughness_path), check_existing=False)
roughness.colorspace_settings.name = 'Non-Color'
skin = bpy.data.materials.new('ReviewSimplifiedSourceBaseSkin')
skin.use_nodes = True
bsdf = skin.node_tree.nodes.get('Principled BSDF')
bsdf.inputs['IOR'].default_value = 1.45
bsdf.inputs['Subsurface Weight'].default_value = 0.0
uv_node = skin.node_tree.nodes.new('ShaderNodeUVMap')
uv_node.uv_map = 'UVMap'
for image, target_input in ((albedo, 'Base Color'), (roughness, 'Roughness')):
    tex = skin.node_tree.nodes.new('ShaderNodeTexImage')
    tex.image = image
    tex.interpolation = 'Linear'
    tex.extension = 'REPEAT'
    skin.node_tree.links.new(uv_node.outputs['UV'], tex.inputs['Vector'])
    skin.node_tree.links.new(tex.outputs['Color'], bsdf.inputs[target_input])
head.data.materials.clear()
head.data.materials.append(skin)

eye_mats = []
eye_material_settings = (
    ('ReviewPupilNearBlack', (0.006, 0.004, 0.003, 1), 0.25),
    ('ReviewIrisMutedBrown', (0.12, 0.085, 0.055, 1), 0.32),
    ('ReviewScleraWarmGray', (0.48, 0.43, 0.37, 1), 0.32))
for name, color, rough in eye_material_settings:
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    shader = mat.node_tree.nodes['Principled BSDF']
    shader.inputs['Base Color'].default_value = color
    shader.inputs['Roughness'].default_value = rough
    eye_mats.append(mat)
scene = bpy.context.scene
eye_records = []
for payload in eye_data:
    mesh = bpy.data.meshes.new(payload['source_mesh'] + '_ThreeStaticLayersClean')
    mesh.from_pydata(payload['positions'], [], payload['faces'])
    assert [loop.vertex_index for loop in mesh.loops] == payload['loop_vertex_indices']
    for layer_name, values in payload['UV'].items():
        layer = mesh.uv_layers.new(name=layer_name)
        for item, uv in zip(layer.data, values):
            item.uv = uv
    for mat in eye_mats:
        mesh.materials.append(mat)
    for polygon, mat_index, smooth in zip(mesh.polygons, payload['material_indices'], payload['smooth']):
        polygon.material_index, polygon.use_smooth = mat_index, smooth
    if payload['crease_by_edge']:
        crease = mesh.attributes.new('crease_edge', 'FLOAT', 'EDGE')
        for edge in mesh.edges:
            crease.data[edge.index].value = payload['crease_by_edge'][tuple(sorted(edge.vertices))]
    obj = bpy.data.objects.new(payload['source_name'] + '_SavedChannelRestCandidate', mesh)
    scene.collection.objects.link(obj)
    obj.matrix_world = Matrix(payload['rest_matrix'])
    sub = obj.modifiers.new('SourceEyeSubdivision2', 'SUBSURF')
    sub.levels = sub.render_levels = 2
    sub.uv_smooth = 'PRESERVE_BOUNDARIES'
    sub.boundary_smooth = 'ALL'
    sub.use_creases = sub.use_limit_surface = True
    assert mesh.shape_keys is None and mesh.animation_data is None and obj.animation_data is None
    eye_records.append({'source_name': payload['source_name'], 'new_object': obj.name,
        'static_key_evidence': payload['static_keys'], 'source_raw_vertices': len(mesh.vertices),
        'source_raw_polygons': len(mesh.polygons),
        'polygon_material_counts': dict(Counter(p.material_index for p in mesh.polygons)),
        'rest_relative_matrix': payload['rest_matrix'],
        'static_geometry_sha256': hashlib.sha256(b''.join(struct.pack('<3f', *v) for v in payload['positions'])).hexdigest(),
        'source_Armature_constraint_and_deformation_ignored': True})
assert len(bpy.data.images) == 3
for kind in ('armatures', 'actions', 'lattices', 'texts', 'libraries', 'shape_keys'):
    assert len(getattr(bpy.data, kind)) == 0, kind
assert all(obj.animation_data is None and len(obj.constraints) == 0 for obj in scene.objects)

target = Vector((0, -0.03, 1.62))
camera = scene.camera
camera.location = (0.70, -1.10, 1.77)
camera.rotation_euler = (target-camera.location).to_track_quat('-Z', 'Y').to_euler()
camera.data.type, camera.data.ortho_scale = 'ORTHO', 0.36
camera.data.dof.use_dof = False
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 16
scene.cycles.use_denoising = False
scene.render.threads_mode, scene.render.threads = 'FIXED', 4
scene.render.resolution_x = scene.render.resolution_y = 768
scene.render.resolution_percentage = 100
scene.view_settings.exposure = 0
scene.use_nodes = False
scene.render.filepath = str(QA / 'einar-static-rest-skin-closeup.png')
result = {'stage': '7_one_static_rest_eye_basic_skin_closeup',
    'opened_clean_stage5_source': str(AB), 'relative_default_EXR_reopen_hash_verified': True,
    'source_default_midlevel_scale_preserved': [0.5, 0.00800000037997961],
    'textures': texture_records, 'skin_material': 'Simplified source albedo/Roughness via UVMap, IOR1.45, Subsurface0; not full source neutral shader.',
    'eye_materials_are_simplified_not_source_atlas_or_cornea': True,
    'eye_material_settings': [{'name': n, 'linear_base_color': list(c), 'roughness': r} for n,c,r in eye_material_settings],
    'eyes': eye_records,
    'placement_assumption': 'Main-head basis inverse times eye basis in common RIG parent with identity parent inverses. Only three proven undriven static resize keys included. Armature constraints/deformation and driven Shrink/Grow ignored; not an evaluated source rig neutral restoration.',
    'source_Objects_drivers_Text_or_rig_evaluated': False,
    'only_new_clean_scene_evaluated': True, 'loaded_image_count': 3,
    'packed_detail_expression_bruises_atlas_hair_body_or_Unity_included': False,
    'render_settings': {'resolution': [768,768], 'samples':16, 'CPU_threads':4,
        'depth_of_field':False, 'denoising':False, 'compositor':False, 'exposure':0},
    'image': scene.render.filepath, 'requested_render_count':1, 'completed_render_count':0,
    'eye_alignment_visual_review': 'Pending actual single image; no eye offsets adjusted.',
    'art_accepted': False, 'license':'CC BY 4.0',
    'source_page':'https://studio.blender.org/characters/einar/v1/',
    'required_credit':'Einar Rig (CC-BY) Blender Foundation | studio.blender.org'}
metadata = QA / 'stage7-static-closeup.json'
metadata.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
bpy.ops.render.render(write_still=True)
result['completed_render_count'] = 1
for image in (default_image, albedo, roughness):
    image.filepath = '//textures/' + Path(image.filepath).name
scene['license'] = result['license']
scene['source_page'] = result['source_page']
scene['required_credit'] = result['required_credit']
scene['changes'] = result['skin_material']+' '+result['placement_assumption']+' No source rig, hair, body or artistic age deformation.'
scene['acceptance_status'] = 'single_source_informed_static_prototype_art_not_accepted'
blend_path = OUT / 'einar-static-rest-skin-closeup.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(blend_path), check_existing=False, relative_remap=False)
result['editable_blend'] = str(blend_path)
result['all_texture_paths_relative_to_new_blend'] = [image.filepath for image in (default_image, albedo, roughness)]
result['elapsed_seconds'] = round(time.perf_counter()-started,4)
metadata.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print('STATIC_REST_SKIN_CLOSEUP_COMPLETE '+json.dumps({'seconds':result['elapsed_seconds'],
    'render_count':1,'new_clean_eye_count':len(eye_records)}),flush=True)
