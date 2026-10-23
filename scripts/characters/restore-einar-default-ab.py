"""Authorized clean source-parameter restoration; exactly two controlled renders."""
import hashlib
import json
import math
from pathlib import Path
import shutil
import struct
import time

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / 'qa/characters/plato/v002/einar-intake'
OUT = ROOT / 'art/characters/plato/v002/einar-default-sculpt-review'
SOURCE = Path('D:/AI/PROJECT/hackathon_projects/Aholo_3D_AI_Hackathon/project-management/source-cache/einar-v1/extracted/einar_release_v1.blend')
TEX_SOURCE = SOURCE.parent / 'textures/displacement/face/disp_default.exr'
TEX_LOCAL = OUT / 'textures/disp_default.exr'
NAME = 'DATA_GEO-einar_head.base'
started = time.perf_counter()
OUT.mkdir(parents=True, exist_ok=True)
TEX_LOCAL.parent.mkdir(parents=True, exist_ok=True)
texture_hash = hashlib.sha256(TEX_SOURCE.read_bytes()).hexdigest()
if TEX_LOCAL.exists():
    assert hashlib.sha256(TEX_LOCAL.read_bytes()).hexdigest() == texture_hash
else:
    shutil.copyfile(TEX_SOURCE, TEX_LOCAL)
assert hashlib.sha256(TEX_LOCAL.read_bytes()).hexdigest() == texture_hash
tree_data = json.loads((QA / 'stage4-geometry-nodes-static.json').read_text(encoding='utf-8'))['node_trees']['texture_displacement']
assert len(tree_data['nodes']) == 9 and tree_data['driver_count'] == 0
with bpy.data.libraries.load(str(SOURCE), link=False) as (data_from, data_to):
    assert NAME in data_from.meshes
    data_to.meshes = [NAME]
raw = data_to.meshes[0]
assert raw.shape_keys is None
vertices = [tuple(float(c) for c in v.co) for v in raw.vertices]
faces = [tuple(int(i) for i in p.vertices) for p in raw.polygons]
smooth = [bool(p.use_smooth) for p in raw.polygons]
uvs = [tuple(float(c) for c in item.uv) for item in raw.uv_layers['UVMap'].data]
source_loop_vertices = [loop.vertex_index for loop in raw.loops]
creases = {}
for attribute_name in ('crease_edge', 'crease_vert'):
    attr = raw.attributes.get(attribute_name)
    if attr:
        assert attr.data_type == 'FLOAT'
        values = [float(item.value) for item in attr.data]
        if attr.domain == 'EDGE':
            creases[attribute_name] = {'domain': 'EDGE', 'values_by_edge': {
                ','.join(map(str, sorted(edge.vertices))): values[edge.index] for edge in raw.edges}}
        else:
            assert attr.domain == 'POINT'
            creases[attribute_name] = {'domain': 'POINT', 'values': values}
sharp_edges = {tuple(sorted(edge.vertices)): bool(edge.use_edge_sharp) for edge in raw.edges}
uv_hash = hashlib.sha256(b''.join(struct.pack('<2f', *uv) for uv in uvs)).hexdigest()
geometry_hash = hashlib.sha256(json.dumps({'vertices': vertices, 'faces': faces}, separators=(',', ':')).encode()).hexdigest()
del raw, data_from, data_to
bpy.ops.wm.read_factory_settings(use_empty=True)
for kind in ('objects', 'meshes', 'materials', 'armatures', 'actions', 'lattices', 'texts', 'libraries', 'images', 'node_groups', 'shape_keys'):
    assert len(getattr(bpy.data, kind)) == 0, kind

mesh = bpy.data.meshes.new('EinarDefaultRawBase')
mesh.from_pydata(vertices, [], faces)
for polygon, flag in zip(mesh.polygons, smooth):
    polygon.use_smooth = flag
assert [loop.vertex_index for loop in mesh.loops] == source_loop_vertices
uv_layer = mesh.uv_layers.new(name='UVMap')
for item, uv in zip(uv_layer.data, uvs):
    item.uv = uv
assert hashlib.sha256(b''.join(struct.pack('<2f', *item.uv) for item in uv_layer.data)).hexdigest() == uv_hash
assert hashlib.sha256(json.dumps({'vertices': [tuple(v.co) for v in mesh.vertices],
    'faces': [tuple(p.vertices) for p in mesh.polygons]}, separators=(',', ':')).encode()).hexdigest() == geometry_hash
for name, crease in creases.items():
    attr = mesh.attributes.new(name, 'FLOAT', crease['domain'])
    if crease['domain'] == 'EDGE':
        for edge in mesh.edges:
            attr.data[edge.index].value = crease['values_by_edge'][','.join(map(str, sorted(edge.vertices)))]
    else:
        for item, value in zip(attr.data, crease['values']):
            item.value = value
for edge in mesh.edges:
    edge.use_edge_sharp = sharp_edges[tuple(sorted(edge.vertices))]
head = bpy.data.objects.new('EinarDefaultCleanHead', mesh)
scene = bpy.context.scene
scene.collection.objects.link(head)
sub = head.modifiers.new('SourceCatmullClark2', 'SUBSURF')
sub.subdivision_type = 'CATMULL_CLARK'
sub.levels = sub.render_levels = 2
sub.quality = 3
sub.uv_smooth = 'PRESERVE_BOUNDARIES'
sub.boundary_smooth = 'ALL'
sub.use_creases = sub.use_limit_surface = True

group = bpy.data.node_groups.new('SourceDefaultScalarDisplacementClean', 'GeometryNodeTree')
interface = {}
for item in tree_data['interface']:
    s = group.interface.new_socket(name=item['name'], in_out=item['in_out'], socket_type=item['socket_type'])
    interface[(item['in_out'], item['name'])] = s
    value = item['serialized_value_not_evaluated']
    if value is not None and hasattr(s, 'default_value'):
        s.default_value = value
nodes = {}
for record in tree_data['nodes']:
    node = group.nodes.new(record['type'])
    node.name = record['name']
    node.label = record['label']
    node.mute = record['mute']
    if node.bl_idname == 'GeometryNodeCaptureAttribute':
        node.capture_items.clear()
        node.capture_items.new('VECTOR', 'Value')
    for key in ('operation', 'domain', 'interpolation', 'extension'):
        if key in record:
            setattr(node, key, record[key])
    nodes[node.name] = node


def find_socket(node, direction, identifier, name):
    sockets = getattr(node, direction)
    if node.type not in ('GROUP_INPUT', 'GROUP_OUTPUT'):
        match = next((s for s in sockets if s.identifier == identifier), None)
        if match is not None:
            return match
    candidates = [s for s in sockets if s.name == name]
    assert len(candidates) == 1, (node.name, direction, identifier, name)
    return candidates[0]


for record in tree_data['nodes']:
    node = nodes[record['name']]
    for data in record['inputs']:
        value = data['serialized_value_not_evaluated']
        if data['name'] and value is not None:
            s = find_socket(node, 'inputs', data['identifier'], data['name'])
            if hasattr(s, 'default_value'):
                s.default_value = value
for link in tree_data['links']:
    assert link['is_valid'] and not link['is_muted']
    group.links.new(find_socket(nodes[link['from_node']], 'outputs', link['from_identifier'], link['from_socket']),
                    find_socket(nodes[link['to_node']], 'inputs', link['to_identifier'], link['to_socket']))
assert len(group.nodes) == 9 and len(group.links) == 13 and group.animation_data is None
image = bpy.data.images.load(str(TEX_LOCAL), check_existing=False)
image.colorspace_settings.name = 'Non-Color'
gn = head.modifiers.new('SourceDefaultSculptOnly', 'NODES')
gn.node_group = group
gn[interface[('INPUT', 'Image')].identifier] = image
vector_id = interface[('INPUT', 'Vector')].identifier
gn[vector_id + '_use_attribute'] = True
gn[vector_id + '_attribute_name'] = 'UVMap'
gn[interface[('INPUT', 'Midlevel')].identifier] = 0.5
gn[interface[('INPUT', 'Scale')].identifier] = 0.00800000037997961
assert len(bpy.data.images) == 1 and len(bpy.data.node_groups) == 1
for kind in ('armatures', 'actions', 'lattices', 'texts', 'libraries', 'shape_keys'):
    assert len(getattr(bpy.data, kind)) == 0, kind
assert head.animation_data is None and mesh.animation_data is None

gray = bpy.data.materials.new('ControlledGray')
gray.use_nodes = True
gray.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.24, 0.24, 0.24, 1)
gray.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.72
mesh.materials.append(gray)
target = Vector((0, -0.03, 1.59))
camera_data = bpy.data.cameras.new('ABCamera')
camera = bpy.data.objects.new('ABCamera', camera_data)
scene.collection.objects.link(camera)
camera.location = (0.70, -1.10, 1.77)
camera.rotation_euler = (target-camera.location).to_track_quat('-Z', 'Y').to_euler()
camera_data.type = 'ORTHO'
camera_data.ortho_scale = 0.43
scene.camera = camera
for name, position, power, size in (
    ('Key', (-0.45, -0.60, 2.10), 8, 0.55),
    ('Fill', (0.60, -0.35, 1.85), 2, 0.60),
    ('Rim', (0.25, 0.35, 1.95), 6, 0.40)):
    data = bpy.data.lights.new(name, 'AREA')
    light = bpy.data.objects.new(name, data)
    scene.collection.objects.link(light)
    light.location = position
    light.rotation_euler = (target-light.location).to_track_quat('-Z', 'Y').to_euler()
    data.energy, data.size, data.shape = power, size, 'DISK'
world = bpy.data.worlds.new('ABWorld')
world.use_nodes = True
world.node_tree.nodes['Background'].inputs[0].default_value = (0.055, 0.055, 0.055, 1)
world.node_tree.nodes['Background'].inputs[1].default_value = 0.20
scene.world = world
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 16
scene.cycles.use_denoising = False
scene.render.threads_mode = 'FIXED'
scene.render.threads = 4
scene.render.resolution_x = scene.render.resolution_y = 768
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.view_settings.view_transform = 'AgX'
scene.view_settings.exposure = 0


def snapshot():
    bpy.context.view_layer.update()
    graph = bpy.context.evaluated_depsgraph_get()
    evaluated = head.evaluated_get(graph)
    evaluated_mesh = evaluated.to_mesh()
    points = [tuple(v.co) for v in evaluated_mesh.vertices]
    polygons = [tuple(p.vertices) for p in evaluated_mesh.polygons]
    evaluated_mesh.calc_loop_triangles()
    counts = {'vertices': len(points), 'polygons': len(polygons), 'triangles': len(evaluated_mesh.loop_triangles)}
    evaluated.to_mesh_clear()
    return points, polygons, counts


gn.show_viewport = gn.show_render = False
a_points, a_faces, a_counts = snapshot()
gn.show_viewport = gn.show_render = True
b_points, b_faces, b_counts = snapshot()
assert a_faces == b_faces and a_counts == b_counts and a_counts['vertices'] > len(vertices)
distances_squared = [sum((x-y)**2 for x, y in zip(a, b)) for a, b in zip(a_points, b_points)]
max_distance = math.sqrt(max(distances_squared))
assert max_distance > 1e-8, 'Default displacement produced no measured deformation'
bounds = lambda points: {'min': [min(p[i] for p in points) for i in range(3)], 'max': [max(p[i] for p in points) for i in range(3)]}
result = {'stage': '5_source_default_sculpt_AB', 'source_mesh': NAME,
    'source_page': 'https://studio.blender.org/characters/einar/v1/',
    'required_credit': 'Einar Rig (CC-BY) Blender Foundation | studio.blender.org',
    'license': 'CC BY 4.0', 'license_url': 'https://creativecommons.org/licenses/by/4.0/',
    'changes': 'Independent clean raw base with preserved UVMap/crease/sharp data; source Catmull-Clark L2 and reconstructed nine-node scalar default sculpt. Gray controlled A/B lighting; no artistic deformation or source rig/expression/hair/eyes.',
    'raw_geometry_sha256': geometry_hash, 'source_and_copy_UVMap_sha256': uv_hash,
    'preserved_crease_attributes': list(creases), 'texture_source': str(TEX_SOURCE),
    'texture_local_copy': str(TEX_LOCAL), 'texture_sha256': texture_hash,
    'default_parameters': {'midlevel': 0.5, 'scale': 0.00800000037997961, 'UV': 'UVMap', 'sampling': 'Linear/REPEAT', 'capture_domain': 'CORNER'},
    'A_counts': a_counts, 'B_counts': b_counts, 'same_evaluated_topology': True,
    'max_displacement_source_units': max_distance,
    'rms_displacement_source_units': math.sqrt(sum(distances_squared)/len(distances_squared)),
    'vertices_moved_above_1e_8': sum(d > 1e-16 for d in distances_squared),
    'A_bounds': bounds(a_points), 'B_bounds': bounds(b_points),
    'A_image': str(QA / 'einar-default-A-subdiv2.png'), 'B_image': str(QA / 'einar-default-B-sculpt.png'),
    'requested_render_count': 2, 'completed_render_count': 0,
    'render_settings': {'resolution': [768, 768], 'samples': 16, 'CPU_threads': 4,
        'gray_base_color': [0.24, 0.24, 0.24, 1], 'exposure': 0, 'light_watts': [8, 2, 6]},
    'source_IDs_cleared_before_any_geometry_evaluation': True,
    'only_clean_geometry_evaluated': True, 'source_drivers_Text_Objects_or_rig_evaluated': False,
    'loaded_source_texture_files': ['disp_default.exr'], 'art_accepted': False}
metadata_path = QA / 'stage5-default-sculpt-ab.json'
metadata_path.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
for enabled, label in ((False, 'A_image'), (True, 'B_image')):
    gn.show_viewport = gn.show_render = enabled
    bpy.context.view_layer.update()
    scene.render.filepath = result[label]
    bpy.ops.render.render(write_still=True)
    result['completed_render_count'] += 1
    metadata_path.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
assert result['completed_render_count'] == 2
image.filepath = '//textures/disp_default.exr'
for key in ('source_page', 'required_credit', 'license', 'license_url', 'changes', 'texture_sha256', 'source_and_copy_UVMap_sha256'):
    scene[key] = result[key]
scene['acceptance_status'] = 'source_default_restoration_review_art_not_accepted'
scene['source_midlevel'] = 0.5
scene['source_scale'] = 0.00800000037997961
blend_path = OUT / 'einar-default-sculpt-AB.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(blend_path), check_existing=False)
result['editable_blend'] = str(blend_path)
result['relative_texture_path_in_blend'] = image.filepath
result['total_script_seconds'] = round(time.perf_counter()-started, 4)
metadata_path.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print('EINAR_DEFAULT_AB_COMPLETE ' + json.dumps({'seconds': result['total_script_seconds'],
    'max_displacement': max_distance, 'counts': b_counts, 'images': 2}), flush=True)
