"""One authorized raw-head gray preview; source IDs never enter scene evaluation."""
import hashlib
import json
from pathlib import Path
import struct
import time

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'art/characters/plato/v002/einar-base-review'
QA = ROOT / 'qa/characters/plato/v002/einar-intake'
SOURCE = Path('D:/AI/PROJECT/hackathon_projects/Aholo_3D_AI_Hackathon/project-management/source-cache/einar-v1/extracted/einar_release_v1.blend')
SOURCE_SHA = '1c6663da0a2e9d6822978467c244e9186edc76083bae2414e02f9e695e711f7b'
NAME = 'DATA_GEO-einar_head.base'
OUT.mkdir(parents=True, exist_ok=True)
started = time.perf_counter()


def geometry_hash(vertices, faces, smooth):
    h = hashlib.sha256()
    h.update(struct.pack('<II', len(vertices), len(faces)))
    for vertex in vertices:
        h.update(struct.pack('<3f', *vertex))
    for face, flag in zip(faces, smooth):
        h.update(struct.pack('<I', len(face)))
        h.update(struct.pack('<' + 'I' * len(face), *face))
        h.update(struct.pack('<?', flag))
    return h.hexdigest()


with bpy.data.libraries.load(str(SOURCE), link=False) as (data_from, data_to):
    assert NAME in data_from.meshes
    data_to.meshes = [NAME]
raw = data_to.meshes[0]
assert raw is not None and raw.shape_keys is None
raw_driver_count = len(raw.animation_data.drivers) if raw.animation_data else 0
assert raw_driver_count == 0
print('RAW_BASE_STATIC_METADATA ' + json.dumps({'shape_keys': False,
      'own_drivers': raw_driver_count, 'has_animation_container': raw.animation_data is not None}), flush=True)
vertices = [tuple(float(c) for c in v.co) for v in raw.vertices]
faces = [tuple(int(i) for i in p.vertices) for p in raw.polygons]
smooth = [bool(p.use_smooth) for p in raw.polygons]
assert len(vertices) == 4596 and len(faces) == 4522
source_geometry_hash = geometry_hash(vertices, faces, smooth)
implicit_counts = {kind: len(getattr(bpy.data, kind)) for kind in
                   ('objects', 'meshes', 'armatures', 'actions', 'lattices', 'texts', 'images', 'node_groups', 'libraries')}
provenance = {
    'source_page': 'https://studio.blender.org/characters/einar/v1/',
    'source_mesh': NAME, 'source_blend_sha256': SOURCE_SHA,
    'license': 'CC BY 4.0', 'license_url': 'https://creativecommons.org/licenses/by/4.0/',
    'required_credit': 'Einar Rig (CC-BY) Blender Foundation | studio.blender.org',
    'changes': 'Copied raw vertex/face arrays and polygon smooth flags only into a clean scene; gray material, new camera/lights. No geometric deformation, UV, original material, shape keys, rig, eyes, hair or displacement.',
    'status': 'base_age_review_only_art_not_accepted',
    'raw_geometry_sha256': source_geometry_hash,
}
(OUT / 'raw-head-geometry.json').write_text(json.dumps({
    'provenance': provenance, 'vertices': vertices, 'faces': faces,
    'polygon_smooth': smooth}, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8')
# All values retained above are plain Python values. No original RNA is copied.
del raw, data_from, data_to
bpy.ops.wm.read_factory_settings(use_empty=True)
assert len(bpy.context.scene.objects) == 0
for kind in ('objects', 'meshes', 'armatures', 'actions', 'lattices', 'texts', 'libraries', 'images', 'node_groups', 'materials', 'shape_keys'):
    assert len(getattr(bpy.data, kind)) == 0, f'Source ID remains: {kind}'
print('CLEAN_RESET_VERIFIED', flush=True)

mesh = bpy.data.meshes.new('EinarRawBaseCleanMesh')
mesh.from_pydata(vertices, [], faces)
for p, flag in zip(mesh.polygons, smooth):
    p.use_smooth = flag
mesh.update()
new_vertices = [tuple(float(c) for c in v.co) for v in mesh.vertices]
new_faces = [tuple(int(i) for i in p.vertices) for p in mesh.polygons]
new_smooth = [bool(p.use_smooth) for p in mesh.polygons]
clean_geometry_hash = geometry_hash(new_vertices, new_faces, new_smooth)
assert clean_geometry_hash == source_geometry_hash
assert mesh.shape_keys is None and mesh.animation_data is None and len(mesh.uv_layers) == 0
head = bpy.data.objects.new('EinarRawBaseCleanHead', mesh)
scene = bpy.context.scene
scene.collection.objects.link(head)
for key, value in provenance.items():
    scene[key] = value
assert len(head.modifiers) == 0 and head.animation_data is None
gray = bpy.data.materials.new('NeutralGray')
gray.use_nodes = True
bsdf = gray.node_tree.nodes.get('Principled BSDF')
bsdf.inputs['Base Color'].default_value = (0.34, 0.34, 0.34, 1)
bsdf.inputs['Roughness'].default_value = 0.72
mesh.materials.append(gray)

target = Vector((0, -0.03, 1.59))
camera_data = bpy.data.cameras.new('ReviewCamera')
camera = bpy.data.objects.new('ReviewCamera', camera_data)
scene.collection.objects.link(camera)
camera.location = (0.70, -1.10, 1.77)
camera.rotation_euler = (target - camera.location).to_track_quat('-Z', 'Y').to_euler()
camera_data.type = 'ORTHO'
camera_data.ortho_scale = 0.43
scene.camera = camera

for name, position, power, size in (
    ('Key', (-0.45, -0.60, 2.10), 65, 0.55),
    ('Fill', (0.60, -0.35, 1.85), 18, 0.60),
    ('Rim', (0.25, 0.35, 1.95), 42, 0.40)):
    data = bpy.data.lights.new(name, type='AREA')
    light = bpy.data.objects.new(name, data)
    scene.collection.objects.link(light)
    light.location = position
    light.rotation_euler = (target - light.location).to_track_quat('-Z', 'Y').to_euler()
    data.energy = power
    data.shape = 'DISK'
    data.size = size

world = bpy.data.worlds.new('NeutralWorld')
world.use_nodes = True
world.node_tree.nodes['Background'].inputs[0].default_value = (0.055, 0.055, 0.055, 1)
world.node_tree.nodes['Background'].inputs[1].default_value = 0.30
scene.world = world
assert sorted(o.name for o in scene.objects) == sorted(['EinarRawBaseCleanHead', 'ReviewCamera', 'Key', 'Fill', 'Rim'])
for kind in ('armatures', 'actions', 'lattices', 'texts', 'libraries', 'images', 'node_groups', 'shape_keys'):
    assert len(getattr(bpy.data, kind)) == 0, kind
assert list(bpy.data.meshes) == [mesh] and len(bpy.data.materials) == 1
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 16
scene.cycles.use_denoising = False
scene.render.threads_mode = 'FIXED'
scene.render.threads = 4
scene.render.resolution_x = scene.render.resolution_y = 768
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.film_transparent = False
scene.view_settings.view_transform = 'AgX'
scene.render.filepath = str(QA / 'einar-raw-base-quarter.png')
blend_path = OUT / 'einar-raw-base-gray.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(blend_path), check_existing=False)
result = {
    'stage': '2_clean_raw_base_single_gray_review', 'provenance': provenance,
    'implicit_ID_counts_before_factory_reset': implicit_counts,
    'source_IDs_cleared_before_scene_evaluation': True,
    'geometry_sha256_before': source_geometry_hash, 'geometry_sha256_after': clean_geometry_hash,
    'geometry_coordinates_face_order_and_smooth_flags_identical': True,
    'vertices': len(mesh.vertices), 'polygons': len(mesh.polygons),
    'new_scene_object_names': sorted(o.name for o in scene.objects),
    'raw_geometry_saved_as_json': str(OUT / 'raw-head-geometry.json'),
    'independent_blend': str(blend_path), 'image': scene.render.filepath,
    'render_count': 1, 'samples': 16, 'cpu_threads': 4, 'resolution': [768, 768],
    'eyes_included': False, 'source_rig_or_modifiers_evaluated': False,
    'source_image_pixels_accessed': False, 'art_accepted': False,
    'pre_render_seconds': round(time.perf_counter() - started, 4),
}
(QA / 'stage2-clean-base.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('CLEAN_HEAD_SAVED_RENDER_START', flush=True)
bpy.ops.render.render(write_still=True)
result['render_completed'] = True
result['total_script_seconds'] = round(time.perf_counter() - started, 4)
(QA / 'stage2-clean-base.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('EINAR_SINGLE_PREVIEW_COMPLETE', flush=True)
