"""One bounded bald elderly-head form experiment; three CPU views at most.

Uses anatomical target landmarks and a smooth volumetric cage, no wrinkle noise,
old texture, hair, body or iteration loop. Reference observations are hypotheses,
not measurements recovered from a scan or proof of age/likeness.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
ASSET = ROOT/'art/characters/plato/v002/elder-gate1'
QA = ROOT/'qa/characters/plato/v002/elder-gate1'
STUDY = ROOT/'art/characters/plato/v002/work/plato-head-study.blend'
VIEWS = [('front', (0, -2, 1.595)), ('side', (2, 0, 1.595)), ('quarter', (.95, -2, 1.595))]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def material(name, gray, roughness=.55):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    node = mat.node_tree.nodes['Principled BSDF']
    node.inputs['Base Color'].default_value = (gray, gray, gray, 1)
    node.inputs['Roughness'].default_value = roughness
    return mat


def point_at(obj, target):
    obj.rotation_euler = (Vector(target)-obj.location).to_track_quat('-Z', 'Y').to_euler()


def main():
    build_only = '--build-only' in sys.argv
    assert not any((QA/(name+'.png')).exists() for name, _ in VIEWS), 'Preserve reviewed views; another revision needs a new authorized path'
    ASSET.mkdir(parents=True, exist_ok=True)
    QA.mkdir(parents=True, exist_ok=True)
    protected_paths = [STUDY,
        ROOT/'art/characters/plato/v002/portrait-p1/plato-portrait-p1.blend',
        ROOT/'qa/characters/plato/v002/portrait-p1/plato-head-shoulders-quarter.png',
        ROOT/'art/characters/plato/v002/portrait-p1b/plato-portrait-p1b.blend',
        ROOT/'qa/characters/plato/v002/portrait-p1b/plato-head-shoulders-quarter.png']
    protected = {p.relative_to(ROOT).as_posix(): digest(p) for p in protected_paths}
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system, scene.unit_settings.scale_length = 'METRIC', 1
    with bpy.data.libraries.load(str(STUDY), link=False) as (_, loaded):
        loaded.objects = ['C0_Licensed_head_proportion_control', 'C_Eyeballs_anatomy_check']
    head, eyes = loaded.objects
    for obj in (head, eyes):
        scene.collection.objects.link(obj)
        obj.hide_render = False
        obj.hide_viewport = False
        obj.hide_set(False)
    bpy.context.view_layer.update()
    head.name = 'ELDER_GATE1_Bald_anatomical_form_test'
    surface = head.modifiers.new('Supporting evaluated quad surface', 'SUBSURF')
    surface.levels = surface.render_levels = 1
    deps = bpy.context.evaluated_depsgraph_get()
    mesh = bpy.data.meshes.new_from_object(head.evaluated_get(deps), depsgraph=deps)
    head.modifiers.clear()
    head.data = mesh
    mesh.transform(head.matrix_world)
    head.matrix_world = Matrix.Identity(4)
    mesh.update()
    eyes.name = 'ELDER_GATE1_Anatomical_eyeballs_unchanged'
    eyes.data = eyes.data.copy()
    eyes.data.transform(eyes.matrix_world)
    eyes.matrix_world = Matrix.Identity(4)
    eyes.data.update()
    before = np.array([tuple(v.co) for v in mesh.vertices], dtype=np.float64)
    before_normals = [p.normal.copy() for p in mesh.polygons]
    tree = BVHTree.FromPolygons([v.co for v in mesh.vertices], [list(p.vertices) for p in mesh.polygons], all_triangles=False)
    landmarks = []

    def add(name, point, delta, method='front_surface'):
        if method == 'front_surface':
            hit, _, _, _ = tree.ray_cast(Vector((point[0], -.6, point[2])), Vector((0, 1, 0)), 1.0)
        else:
            hit, _, _, _ = tree.find_nearest(Vector(point))
        assert hit is not None, 'Missing landmark surface: '+name
        if any((hit-Vector(p['source_m'])).length < .0002 for p in landmarks):
            return
        landmarks.append({'name': name, 'source_m': list(hit), 'delta_m': list(delta),
                          'target_m': list(hit+Vector(delta)), 'surface_selection': method})

    # Unchanged crown, back and neck anchors localize this to facial tissue.
    for z in (1.46, 1.51, 1.59, 1.67, 1.727):
        for x in (-.055, 0, .055):
            add('stationary_back', (x, .20, z), (0, 0, 0), 'nearest_surface')
    for x in (-.085, -.045, 0, .045, .085):
        add('stationary_neck', (x, -.2, 1.465), (0, 0, 0))
    for x in (-.055, 0, .055):
        add('stationary_crown', (x, -.01, 1.76), (0, 0, 0), 'nearest_surface')
    # Eye rims are held while surrounding brow/cheek masses are reshaped.
    for sign in (-1, 1):
        for x_offset, z_offset in ((-.010, 0), (.010, 0), (0, .009), (0, -.009)):
            add('stationary_eye_rim', (sign*.0322+x_offset, 0, 1.622+z_offset), (0, 0, 0))
        targets = [
            # Anatomical control points, in metres; no fine-wrinkle displacement.
            ('brow_overhang', .031, 1.645, (0, -.0055, -.0020)),
            ('outer_brow_descent', .055, 1.641, (0, -.0030, -.0025)),
            ('temporal_hollow', .073, 1.661, (-.0025, .0045, 0)),
            ('malar_support', .055, 1.602, (.0035, -.0035, .0010)),
            ('submalar_volume_loss', .050, 1.572, (-.0020, .0090, -.0010)),
            ('lower_cheek_tissue_descent', .061, 1.548, (.0010, .0035, -.0050)),
            ('nasolabial_inner_plane', .018, 1.580, (-.0005, .0025, -.0010)),
            ('nasolabial_descending_mass', .025, 1.573, (.0010, -.0045, -.0030)),
            ('mouth_corner_descent', .026, 1.546, (.0005, .0010, -.0040)),
            ('perioral_tissue_descent', .034, 1.529, (.0010, -.0030, -.0045)),
            ('prejowl_recession', .041, 1.516, (-.0010, .0030, 0)),
            ('jowl_mass', .061, 1.519, (.0030, -.0035, -.0045)),
            ('nostril_wing', .014, 1.582, (.0015, -.0015, -.0010)),
            ('upper_lip_reduced_projection', .012, 1.551, (0, .0015, -.0010)),
            ('lower_lip_weight', .012, 1.541, (0, -.0015, -.0020)),
        ]
        for name, x, z, delta in targets:
            add(name, (sign*x, 0, z), (sign*delta[0], delta[1], delta[2]))
        add('ear_lobe_descent', (sign*.087, .066, 1.588), (sign*.001, 0, -.004), 'nearest_surface')
    for name, z, delta in [
        ('glabella_bony_support', 1.651, (0, -.0030, -.0005)),
        ('nose_bridge_projection', 1.616, (0, -.0020, 0)),
        ('nasal_tip_descent', 1.590, (0, -.0040, -.0030)),
        ('philtrum_length', 1.563, (0, .0010, -.0020)),
        ('upper_lip_midline', 1.552, (0, .0010, -.0010)),
        ('mouth_line_anchor', 1.546, (0, 0, 0)),
        ('lower_lip_midline', 1.539, (0, -.0010, -.0020)),
        ('chin_lower_face', 1.511, (0, -.0020, -.0030)),
    ]:
        add(name, (0, 0, z), delta)
    # Polyharmonic 3D cage interpolation (U(r)=r), with affine tail and fixed
    # boundary anchors. No Gaussian bumps, procedural skin noise or added folds.
    origin = np.array((0, .04, 1.60))
    scale = .10
    controls = (np.array([p['source_m'] for p in landmarks])-origin)/scale
    targets = np.array([p['delta_m'] for p in landmarks])
    n = len(controls)
    distances = np.linalg.norm(controls[:, None, :]-controls[None, :, :], axis=2)
    affine = np.column_stack((np.ones(n), controls))
    system = np.block([[distances+np.eye(n)*1e-9, affine], [affine.T, np.zeros((4, 4))]])
    coefficients = np.linalg.solve(system, np.vstack((targets, np.zeros((4, 3)))))
    query = (before-origin)/scale
    weights = np.linalg.norm(query[:, None, :]-controls[None, :, :], axis=2)
    deltas = weights @ coefficients[:n]+np.column_stack((np.ones(len(query)), query)) @ coefficients[n:]
    displacement = np.linalg.norm(deltas, axis=1)
    assert np.isfinite(deltas).all() and float(displacement.max()) < .020, 'Unbounded cage deformation'
    head.shape_key_add(name='C0_Evaluated_Basis')
    key = head.shape_key_add(name='Gate1_Anatomical_cage_form_hypothesis')
    for vertex, point in zip(key.data, before+deltas):
        vertex.co = point
    key.value = 1
    for p in mesh.polygons:
        p.use_smooth = True
    gray = material('Gate1 controlled neutral gray', .34)
    eye_gray = material('Gate1 controlled eyeball gray', .23, .48)
    head.data.materials.clear()
    head.data.materials.append(gray)
    eyes.data.materials.clear()
    eyes.data.materials.append(eye_gray)
    bpy.context.view_layer.update()
    evaluated = head.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh()
    normal_dots = [p.normal.dot(nrm) for p, nrm in zip(evaluated.polygons, before_normals)]
    inverted = sum(value < 0 for value in normal_dots)
    head.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh_clear()
    assert inverted == 0, f'New inverted face normals: {inverted}'
    scene.render.engine = 'CYCLES'
    scene.cycles.device, scene.cycles.samples, scene.cycles.use_denoising = 'CPU', 32, False
    scene.cycles.seed = 31
    scene.render.threads_mode, scene.render.threads = 'FIXED', 4
    scene.render.resolution_x = scene.render.resolution_y = 768
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format, scene.render.image_settings.color_mode = 'PNG', 'RGB'
    scene.view_settings.view_transform, scene.view_settings.look = 'AgX', 'AgX - Medium High Contrast'
    world = bpy.data.worlds.new('Fixed neutral gray environment')
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs['Color'].default_value = (.12, .12, .12, 1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value = .35
    for name, position, power, size in [('Key', (-.8, -1.2, 2.5), 70, .6),
                                        ('Fill', (.9, -.4, 2), 22, .75), ('Rim', (0, .8, 2), 40, .5)]:
        data = bpy.data.lights.new(name, 'AREA')
        data.energy, data.shape, data.size = power, 'DISK', size
        obj = bpy.data.objects.new(name, data)
        scene.collection.objects.link(obj)
        obj.location = position
        point_at(obj, (0, 0, 1.60))
    cam_data = bpy.data.cameras.new('Controlled_head_camera')
    camera = bpy.data.objects.new('Controlled_head_camera', cam_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    cam_data.type, cam_data.ortho_scale, cam_data.dof.use_dof = 'ORTHO', .37, False
    camera.location = VIEWS[-1][1]
    point_at(camera, (0, 0, 1.595))
    scene.render.filepath = str(QA/'quarter.png')
    scene['art_status'] = 'unreviewed_bald_age_form_test'
    scene['asset_role'] = 'elder_gate1_head_only_not_runtime'
    for obj in (head, eyes):
        obj['source_attribution'] = 'Blender Studio / Project Heist; lesson author Julien Kaspar'
        obj['source_license'] = 'CC BY 4.0'
    head['reference_role'] = 'Louvre Ma 921, single elderly structural reference; original painting governs Plato direction'
    assert not head.hide_render and not eyes.hide_render and head.visible_get() and eyes.visible_get()
    assert len([o for o in scene.objects if o.type == 'MESH']) == 2
    bpy.context.preferences.filepaths.save_version = 0
    blend = ASSET/'plato-elder-gate1.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    images = []
    if not build_only:
        for name, position in VIEWS:
            camera.location = position
            point_at(camera, (0, 0, 1.595))
            path = QA/(name+'.png')
            scene.render.filepath = str(path)
            bpy.ops.render.render(write_still=True)
            images.append({'view': name, 'path': path.relative_to(ROOT).as_posix(), 'sha256': digest(path),
                           'camera_m': list(position), 'target_m': [0, 0, 1.595], 'orthographic_span_m': .37})
    for path, expected in protected.items():
        assert digest(ROOT/path) == expected, 'Protected source changed: '+path
    result = {'schema_version': 1, 'created_utc': datetime.now(timezone.utc).isoformat(),
        'candidate': 'plato-elder-gate1', 'art_status': 'ready_for_three_view_review' if images else 'built_not_rendered',
        'source': blend.relative_to(ROOT).as_posix(), 'source_sha256': digest(blend), 'images': images,
        'render_count': len(images), 'cpu_threads': 4, 'gpu_used': False, 'samples': 32, 'denoising': False,
        'resolution': [768, 768], 'head_vertices': len(mesh.vertices), 'landmarks': landmarks,
        'method': 'Single-reference anatomical target cage with polyharmonic interpolation, editable shape key; no Gaussian/noise wrinkles',
        'max_displacement_m': float(displacement.max()), 'inverted_face_normals': inverted,
        'reference': {'object': 'Louvre Ma 921', 'catalogue': 'https://collections.louvre.fr/ark:/53355/cl010279217',
                      'views_reviewed_online': ['front', 'profile', 'three-quarter'],
                      'photo_use': 'Viewed only; copyrighted official photos not downloaded or copied into candidate',
                      'role': 'Old facial mass reference only, not Plato identity or exact scanned fitting'},
        'protected_hashes': protected, 'runtime_replacement_approved': False,
        'limits': ['Bald head and existing eyeballs only; no hair, beard, body, collar, texture or runtime export.',
                   'This is a landmark-based form hypothesis, not a professional hand-sculpted or scan-fitted elderly portrait.',
                   'Single extra surface evaluation supports the cage; subdivision/displacement counts are not acceptance criteria.',
                   'Age and identity require actual three-view review; no art acceptance from technical checks.']}
    (QA/'experiment.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print('ELDER_GATE1_'+('BUILD_ONLY' if build_only else 'THREE_VIEWS')+'_COMPLETE '+json.dumps({
        'render_count': len(images), 'landmarks': len(landmarks), 'max_displacement_m': float(displacement.max()),
        'inverted_face_normals': inverted, 'source_sha256': digest(blend)}))


if __name__ == '__main__':
    main()
