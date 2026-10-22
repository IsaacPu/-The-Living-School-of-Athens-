"""Reproducible, local-only Plato diagnostic. Run with Blender 4.5 LTS.

Preserves source mesh shape; only rebases the character to a feet-centred root.
No smoothing, subdivision, remeshing, generation or external requests.
"""
import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import bpy
from mathutils import Matrix, Vector


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def bounds(objects):
    points = [o.matrix_world @ v.co for o in objects for v in o.data.vertices]
    return [min(p[k] for p in points) for k in range(3)], [max(p[k] for p in points) for k in range(3)]


def gltf_bounds(low, high):
    # Blender (X,Y,Z) to glTF (X,Z,-Y).
    return {"min": [low[0], low[2], -high[1]], "max": [high[0], high[2], -low[1]],
            "size": [high[k] - low[k] for k in (0, 2, 1)]}


def point_at(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat('-Z', 'Y').to_euler()


def area_light(name, xyz, energy, size, target=(0, 0, .9)):
    data = bpy.data.lights.new(name, 'AREA')
    data.energy, data.shape, data.size = energy, 'DISK', size
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = xyz
    point_at(obj, target)


def material_summary(material):
    principled = next((n for n in material.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    images = []
    for n in material.node_tree.nodes:
        if n.type == 'TEX_IMAGE' and n.image:
            images.append({"name": n.image.name, "size": list(n.image.size), "colorspace": n.image.colorspace_settings.name})
    return {"name": material.name, "images": images,
            "metallic_linked": bool(principled and principled.inputs['Metallic'].is_linked),
            "normal_linked": bool(principled and principled.inputs['Normal'].is_linked),
            "roughness_linked": bool(principled and principled.inputs['Roughness'].is_linked)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--asset-dir', required=True)
    parser.add_argument('--qa-dir', required=True)
    parser.add_argument('--canonical-yaw', type=float, default=0)
    parser.add_argument('--material-policy', choices=('preserve', 'nonmetal'), default='preserve')
    parser.add_argument('--no-render', action='store_true')
    args = parser.parse_args(__import__('sys').argv[__import__('sys').argv.index('--') + 1:])
    asset_dir, qa_dir = Path(args.asset_dir).resolve(), Path(args.qa_dir).resolve()
    qa_dir.mkdir(parents=True, exist_ok=True)
    source = asset_dir / 'source/plato-lux3d-task-4277623.glb'
    original_hash = digest(source)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.scale_length = 1.0
    bpy.ops.import_scene.gltf(filepath=str(source))
    meshes = [o for o in scene.objects if o.type == 'MESH']
    if not meshes:
        raise RuntimeError('Source contains no mesh')
    for obj in meshes:
        obj.data.calc_loop_triangles()
    triangles = sum(len(o.data.loop_triangles) for o in meshes)
    initial_low, initial_high = bounds(meshes)
    root = bpy.data.objects.new('Plato_CANONICAL_FEET_ROOT', None)
    scene.collection.objects.link(root)
    root.empty_display_type, root.empty_display_size = 'ARROWS', .25
    rotation = Matrix.Rotation(math.radians(args.canonical_yaw), 4, 'Z')
    for obj in meshes:
        obj.matrix_world = rotation @ obj.matrix_world
    bpy.context.view_layer.update()
    low, high = bounds(meshes)
    translation = Vector((-(low[0] + high[0]) / 2, -(low[1] + high[1]) / 2, -low[2]))
    for obj in meshes:
        world = Matrix.Translation(translation) @ obj.matrix_world
        obj.parent = root
        obj.matrix_world = world
    bpy.context.view_layer.update()
    low, high = bounds(meshes)
    height = high[2] - low[2]
    if abs(low[2]) > 1e-5 or abs(height - (initial_high[2] - initial_low[2])) > 1e-5:
        raise RuntimeError('Rebase changed height or failed to ground feet')
    original_materials = [m for o in meshes for m in o.data.materials]
    material_info = [material_summary(m) for m in original_materials]
    nonmetal = {}
    for mat in original_materials:
        mat.use_fake_user = True
        candidate = mat.copy()
        candidate.name = mat.name + '_NONMETAL_CANDIDATE'
        candidate.use_fake_user = True
        shader = next(n for n in candidate.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
        for link in list(shader.inputs['Metallic'].links):
            candidate.node_tree.links.remove(link)
        shader.inputs['Metallic'].default_value = 0.0
        nonmetal[mat.name] = candidate

    def set_materials(policy):
        cursor = 0
        for obj in meshes:
            for index in range(len(obj.data.materials)):
                mat = original_materials[cursor]
                obj.data.materials[index] = nonmetal[mat.name] if policy == 'nonmetal' else mat
                cursor += 1

    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 12
    scene.cycles.use_denoising = True
    scene.render.threads_mode = 'FIXED'
    scene.render.threads = 6
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.render.resolution_percentage = 100
    scene.view_settings.view_transform = 'AgX'
    scene.world = bpy.data.worlds.new('Neutral diagnostic world')
    scene.world.use_nodes = True
    scene.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.18, .18, .18, 1)
    scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .4
    area_light('Key neutral', (-2.5, -3.5, 4), 350, 3)
    area_light('Fill neutral', (2.5, -1, 2.4), 170, 2.5)
    area_light('Rim neutral', (0, 3, 3), 220, 2.5)
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -.012))
    ground = bpy.context.object
    ground.name = 'QA_GROUND_NOT_EXPORTED'
    ground_mat = bpy.data.materials.new('QA matte gray')
    ground_mat.diffuse_color = (.12, .12, .12, 1)
    ground.data.materials.append(ground_mat)
    camera_data = bpy.data.cameras.new('QA_Camera')
    camera = bpy.data.objects.new('QA_Camera', camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera_data.type = 'ORTHO'
    images = []

    def render(name, position, target, ortho, width=768, height_px=1024, policy='preserve'):
        set_materials(policy)
        camera.location = position
        point_at(camera, target)
        camera_data.ortho_scale = ortho
        scene.render.resolution_x, scene.render.resolution_y = width, height_px
        scene.render.filepath = str(qa_dir / (name + '.png'))
        if not args.no_render:
            bpy.ops.render.render(write_still=True)
            images.append({"path": str(Path(__import__('os').path.relpath(scene.render.filepath, asset_dir))).replace('\\', '/'),
                           "view": name, "material_policy": policy, "camera_blender": list(position),
                           "target_blender": list(target), "orthographic_span_m": ortho,
                           "resolution": [width, height_px], "samples": scene.cycles.samples,
                           "classification": "actual_mesh_render"})

    # Source +Z is Blender -Y. Until visual review these are axis-labelled candidates.
    full = height * 1.17
    render('axis_plus_z_candidate_front', (0, -4, height / 2), (0, 0, height / 2), full)
    render('axis_minus_z_candidate_back', (0, 4, height / 2), (0, 0, height / 2), full)
    render('axis_plus_x_subject_left', (4, 0, height / 2), (0, 0, height / 2), full)
    render('axis_minus_x_subject_right', (-4, 0, height / 2), (0, 0, height / 2), full)
    render('front_three_quarter', (2.7, -4, height / 2), (0, 0, height / 2), full)
    render('face_front', (0, -4, height - .16), (0, 0, height - .16), .44, 1024, 1024)
    render('face_three_quarter', (2.1, -4, height - .16), (0, 0, height - .16), .44, 1024, 1024)
    render('hands_book_front', (0, -4, height * .61), (0, 0, height * .61), .76, 1024, 1024)
    render('hands_book_side', (2.7, -4, height * .61), (0, 0, height * .61), .76, 1024, 1024)
    render('feet_front', (0, -4, .12), (0, 0, .12), .48, 1024, 768)
    render('material_before', (2.7, -4, height / 2), (0, 0, height / 2), full)
    render('material_nonmetal_candidate', (2.7, -4, height / 2), (0, 0, height / 2), full, policy='nonmetal')
    set_materials(args.material_policy)
    for image in bpy.data.images:
        if image.source == 'FILE' and not image.packed_file:
            image.pack()
    export = asset_dir / 'export/plato-baseline-diagnostic.glb'
    export.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action='DESELECT')
    root.select_set(True)
    for obj in meshes:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = root
    bpy.ops.export_scene.gltf(filepath=str(export), export_format='GLB', use_selection=True,
                              export_yup=True, export_animations=False, export_skins=False,
                              export_cameras=False, export_lights=False)
    camera.location = (2.7, -4, height / 2)
    point_at(camera, (0, 0, height / 2))
    camera_data.ortho_scale = full
    blend = asset_dir / 'work/plato-baseline-diagnostic.blend'
    blend.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    report = {"schema_version": 1, "executed_at": datetime.now(timezone.utc).isoformat(),
              "blender_version": bpy.app.version_string, "source_sha256": original_hash,
              "source_hash_after": digest(source), "source_bounds_blender_m": {"min": initial_low, "max": initial_high},
              "canonical_bounds_m": gltf_bounds(low, high), "body_height_m": height,
              "top_is_head_requires_visual_review": True, "source_axis_front_candidate": '+Z',
              "canonical_yaw_degrees": args.canonical_yaw, "rebase_blender_m": list(translation),
              "geometry_changed": False, "geometry_note": 'Mesh vertex data and topology preserved; rigid object transforms only; no rescale.',
              "triangles": triangles, "materials_source": material_info, "material_policy": args.material_policy,
              "mesh_objects": [{"name": o.name, "vertices": len(o.data.vertices), "polygons": len(o.data.polygons),
                                "modifiers": len(o.modifiers)} for o in meshes],
              "skins": 0, "animations": 0, "qa_images": images,
              "relative_glb_path": str(export.relative_to(asset_dir)).replace('\\', '/'),
              "export_sha256": digest(export), "export_bytes": export.stat().st_size,
              "relative_blend_path": str(blend.relative_to(asset_dir)).replace('\\', '/'),
              "art_status": 'baseline_diagnostic', "orientation_verified": False}
    (qa_dir / 'blender-inspection.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print('CHARACTER_DIAGNOSTIC_COMPLETE ' + json.dumps({"glb": str(export), "blend": str(blend), "images": len(images)}))


if __name__ == '__main__':
    main()
