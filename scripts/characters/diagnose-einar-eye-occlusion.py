"""Read-only BVH rays on saved clean closeup, no source rig or new render."""
import hashlib
import json
from pathlib import Path
import time

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / 'qa/characters/plato/v002/einar-intake'
BLEND = ROOT / 'art/characters/plato/v002/einar-static-closeup-review/einar-static-rest-skin-closeup.blend'
started = time.perf_counter()
bpy.ops.wm.open_mainfile(filepath=str(BLEND), load_ui=False, use_scripts=False)
for kind in ('armatures', 'actions', 'lattices', 'texts', 'libraries', 'shape_keys'):
    assert len(getattr(bpy.data, kind)) == 0, kind
scene = bpy.context.scene
assert all(obj.animation_data is None and not obj.constraints for obj in scene.objects)
previous = json.loads((QA / 'stage7-static-closeup.json').read_text(encoding='utf-8'))
texture_checks = []
actual_images = {image.filepath.replace('\\', '/').rsplit('/', 1)[-1]: image
                 for image in bpy.data.images if image.source == 'FILE'}
for record in previous['textures']:
    expected_relative = record['final_relative_path']
    actual_image = actual_images[expected_relative.replace('\\', '/').rsplit('/', 1)[-1]]
    assert actual_image.filepath.replace('\\', '/') == expected_relative.replace('\\', '/'), (actual_image.filepath, expected_relative)
    path = Path(bpy.path.abspath(actual_image.filepath)).resolve()
    assert path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == record['sha256']
    texture_checks.append({'relative_path':record['final_relative_path'], 'resolved':str(path), 'hash_match':True})
graph = bpy.context.evaluated_depsgraph_get()
head = bpy.data.objects['EinarDefaultCleanHead']
evaluated_head = head.evaluated_get(graph)
head_mesh = evaluated_head.to_mesh()
head_points = [head.matrix_world @ vertex.co for vertex in head_mesh.vertices]
head_faces = [tuple(p.vertices) for p in head_mesh.polygons]
bvh = BVHTree.FromPolygons(head_points, head_faces, all_triangles=False)
head_counts = {'vertices':len(head_points), 'polygons':len(head_faces)}
evaluated_head.to_mesh_clear()
camera = scene.camera
forward = (camera.matrix_world.to_quaternion() @ Vector((0,0,-1))).normalized()
camera_inverse = camera.matrix_world.inverted()
width = scene.render.resolution_x
height = scene.render.resolution_y
assert camera.data.type == 'ORTHO' and width == height
results = []
for eye in [o for o in scene.objects if o.type == 'MESH' and o != head]:
    evaluated_eye = eye.evaluated_get(graph)
    mesh = evaluated_eye.to_mesh()
    points = [eye.matrix_world @ v.co for v in mesh.vertices]
    normal_matrix = eye.matrix_world.to_3x3().inverted().transposed()
    slots = []
    for slot, label in ((0,'pupil'),(1,'iris'),(2,'sclera')):
        polygons = [p for p in mesh.polygons if p.material_index == slot and
                    (normal_matrix @ p.normal).normalized().dot(-forward) > 0.01]
        stride = max(1, len(polygons)//64)
        samples = []
        for poly in polygons[::stride][:64]:
            center = sum((points[i] for i in poly.vertices), Vector())/len(poly.vertices)
            local = camera_inverse @ center
            pixel = [width*(0.5+local.x/camera.data.ortho_scale),
                     height*(0.5-local.y/camera.data.ortho_scale)]
            origin = center-forward*2.0
            hit, normal, face, distance = bvh.ray_cast(origin, forward, 2.05)
            head_in_front = hit is not None and distance < 2.0-1e-5
            samples.append({'face':poly.index, 'pixel':pixel,
                'in_frame':0<=pixel[0]<width and 0<=pixel[1]<height,
                'head_hit_before_eye_surface':head_in_front,
                'head_depth_in_front_of_eye_sample_source_units':2.0-distance if head_in_front else None})
        visible_samples = [s for s in samples if s['in_frame']]
        covered = [s for s in visible_samples if s['head_hit_before_eye_surface']]
        depths = [s['head_depth_in_front_of_eye_sample_source_units'] for s in covered]
        slots.append({'partition':label, 'front_facing_polygon_count':len(polygons),
            'sampled_in_frame_count':len(visible_samples), 'head_occluded_samples':len(covered),
            'head_occlusion_fraction':len(covered)/len(visible_samples) if visible_samples else None,
            'occluded_depth_min_max_source_units':[min(depths),max(depths)] if depths else None,
            'samples':samples})
    results.append({'eye':eye.name, 'evaluated_vertices':len(mesh.vertices),
                    'evaluated_polygons':len(mesh.polygons), 'partitions':slots})
    evaluated_eye.to_mesh_clear()
result = {'stage':'7_post_closeup_read_only_eye_occlusion', 'input_clean_blend':str(BLEND),
    'all_three_new_relative_texture_paths_reopened_and_hash_verified':texture_checks,
    'head_evaluated_counts':head_counts, 'eyes':results,
    'method':'Uniformly subsample up to64 front-facing evaluated faces per material partition. Cast parallel orthographic camera rays from2 source units before each eye-face centroid against evaluated head-only BVH. Head hit before sample by>1e-5 indicates head occlusion in this saved view.',
    'limits':['This identifies current-view head occlusion, not the original rig neutral pose or a justified corrective eye offset.',
              'Head-only occlusion test does not count eye self-occlusion, cornea or optical transparency.',
              'Uniform face samples are not a pixel-area-weighted visibility percentage.'],
    'new_render_or_saved_blend':False, 'source_native_library_opened':False,
    'only_existing_clean_scene_evaluated':True,
    'elapsed_seconds':round(time.perf_counter()-started,4)}
(QA/'stage7-eye-occlusion-diagnostic.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('EYE_OCCLUSION_READ_ONLY_COMPLETE '+json.dumps({'seconds':result['elapsed_seconds'],
    'eyes':[{'name':r['eye'],'partitions':[{k:p[k] for k in ('partition','sampled_in_frame_count','head_occluded_samples','occluded_depth_min_max_source_units')} for p in r['partitions']]} for r in results]}),flush=True)
