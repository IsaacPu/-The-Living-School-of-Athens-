"""Open the saved editable file, add QA-only metric ruler, and reimport GLB."""
import argparse
import json
from collections import Counter
from pathlib import Path

import bpy
from mathutils import Vector


parser = argparse.ArgumentParser()
parser.add_argument('--asset-dir', required=True)
parser.add_argument('--qa-dir', required=True)
args = parser.parse_args(__import__('sys').argv[__import__('sys').argv.index('--') + 1:])
asset, qa = Path(args.asset_dir), Path(args.qa_dir)
bpy.ops.wm.open_mainfile(filepath=str(asset / 'work/plato-baseline-diagnostic.blend'))
scene = bpy.context.scene
root = bpy.data.objects.get('Plato_CANONICAL_FEET_ROOT')
assert root is not None
meshes = [o for o in root.children_recursive if o.type == 'MESH']
height = max((o.matrix_world @ v.co).z for o in meshes for v in o.data.vertices)
# Independent same-condition comparison using a fresh import of the true original.
stage = [o for o in scene.objects if o.type in {'CAMERA', 'LIGHT'} or o.name == 'QA_GROUND_NOT_EXPORTED']
stage_original = {o.name: o.location.copy() for o in stage}
for col in scene.collection.children:
    if col.name.startswith('QA_ONLY_'):
        col.hide_render = True
scene.camera.location = (2.7, -4, height / 2)
scene.camera.rotation_euler = (Vector((0, 0, height / 2)) - scene.camera.location).to_track_quat('-Z', 'Y').to_euler()
stage_original[scene.camera.name] = scene.camera.location.copy()
scene.camera.data.type = 'ORTHO'
scene.camera.data.ortho_scale = height * 1.17
scene.render.resolution_x, scene.render.resolution_y = 768, 1024
for obj in meshes:
    obj.hide_render = True
previous = set(scene.objects)
bpy.ops.import_scene.gltf(filepath=str(asset / 'source/plato-lux3d-task-4277623.glb'))
source_objects = list(set(scene.objects) - previous)
for obj in stage:
    obj.location = stage_original[obj.name] + Vector((0, 0, -.875))
scene.render.filepath = str(qa / 'source_before_same_conditions.png')
bpy.ops.render.render(write_still=True)
for obj in source_objects:
    bpy.data.objects.remove(obj, do_unlink=True)
for obj in meshes:
    obj.hide_render = False
for obj in stage:
    obj.location = stage_original[obj.name]
scene.render.filepath = str(qa / 'delivery_after_same_conditions.png')
bpy.ops.render.render(write_still=True)
collection = bpy.data.collections.new('QA_ONLY_METRIC_RULER_NOT_EXPORTED')
scene.collection.children.link(collection)
mat = bpy.data.materials.new('QA scale neutral white')
mat.diffuse_color = (.85, .85, .85, 1)


def line(name, a, b, thickness=.002):
    data = bpy.data.curves.new(name, 'CURVE')
    data.dimensions = '3D'
    data.bevel_depth = thickness
    data.bevel_resolution = 0
    spline = data.splines.new('POLY')
    spline.points.add(1)
    for p, xyz in zip(spline.points, (a, b)):
        p.co = (*xyz, 1)
    obj = bpy.data.objects.new(name, data)
    collection.objects.link(obj)
    data.materials.append(mat)


def text(label, location, size=.045):
    data = bpy.data.curves.new(label, 'FONT')
    data.body, data.size, data.align_x = label, size, 'RIGHT'
    obj = bpy.data.objects.new('QA_' + label, data)
    collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler = (1.5707963267948966, 0, 0)
    data.materials.append(mat)


x, y = -.48, -.01
line('QA_meter_ruler', (x, y, 0), (x, y, height))
for n in range(8):
    z = .25 * n
    if z <= height + .0001:
        line('QA_tick_' + str(n), (x - .025, y, z), (x + .025, y, z))
        text(f'{z:.2f} m', (x - .045, y, z - .012))
line('QA_floor_line', (-.75, 0, 0), (.45, 0, 0))
text('FEET Y=0', (-.46, y, -.075), .035)
text('glTF +Z FRONT', (.28, y, height + .09), .04)
scene.camera.location = (-.09, -4, height / 2)
scene.camera.rotation_euler = (Vector((-.09, 0, height / 2)) - scene.camera.location).to_track_quat('-Z', 'Y').to_euler()
scene.camera.data.type = 'ORTHO'
scene.camera.data.ortho_scale = 2.15
scene.render.resolution_x, scene.render.resolution_y = 1024, 1280
scene.render.filepath = str(qa / 'front_metric_ruler.png')
bpy.ops.render.render(write_still=True)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(asset / 'work/plato-baseline-diagnostic.blend'))
editable_result = {'blend_reopened': True, 'mesh_objects': len(meshes), 'packed_images': sum(bool(i.packed_file) for i in bpy.data.images),
                   'height_m': height, 'metric_ruler_exported': False,
                   'before_after': {'before': 'source_before_same_conditions.png', 'after': 'delivery_after_same_conditions.png',
                                    'same_relative_camera_lights_ground': True, 'before_stage_offset_blender_m': [0, 0, -.875],
                                    'note': 'Original source freshly imported; stage translated with source solely to preserve identical relative framing and lighting.'}}
# Fresh empty scene proves the exported model, rather than a screenshot of source, reimports.
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(asset / 'export/plato-baseline-diagnostic.glb'))
objects = [o for o in bpy.context.scene.objects if o.type == 'MESH']
points = [o.matrix_world @ v.co for o in objects for v in o.data.vertices]
low = [min(p[k] for p in points) for k in range(3)]
high = [max(p[k] for p in points) for k in range(3)]
assert abs(low[2]) < 1e-5
assert abs(high[2] - height) < 1e-5
assert all(n.image.packed_file for m in bpy.data.materials if m.use_nodes for n in m.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image)
edges = Counter()
for obj in objects:
    obj.data.calc_loop_triangles()
    for tri in obj.data.loop_triangles:
        points_q = [tuple(round(c / .000001) for c in (obj.matrix_world @ obj.data.vertices[i].co)) for i in tri.vertices]
        for a, b in zip(points_q, points_q[1:] + points_q[:1]):
            edges[tuple(sorted((a, b)))] += 1
editable_result['quantized_topology_audit'] = {'weld_tolerance_m': .000001,
    'boundary_edges': sum(v == 1 for v in edges.values()), 'edges_more_than_two_triangles': sum(v > 2 for v in edges.values()),
    'note': 'Position-welded diagnostic only. Boundary edges can be garment openings; no automatic repair performed.'}
editable_result.update({'export_reimported': True, 'export_mesh_objects': len(objects), 'export_bounds_blender_m': {'min': low, 'max': high},
                        'passed': True})
(qa / 'roundtrip.json').write_text(json.dumps(editable_result, indent=2), encoding='utf-8')
print('ROUNDTRIP_AND_RULER_OK ' + json.dumps(editable_result))
