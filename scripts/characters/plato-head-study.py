"""B-P1 controlled diagnostics + licensed, locally reshaped head study.

No generated anatomy, sharpened textures or global source smoothing. The donor
is explicitly CC BY 4.0. The head is a local study, not a finished Plato.
"""
import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import bmesh
import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[2]
ASSET = ROOT / 'art/characters/plato/v002'
QA = ROOT / 'qa/characters/plato/v002'
SOURCE = ROOT / 'art/characters/plato/v001/export/plato-baseline-diagnostic.glb'
BASE = ASSET / 'source/realistic_human_base.blend'


def hash_file(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def smooth(a, b, x):
    t = min(1., max(0., (x-a)/(b-a)))
    return t*t*(3.-2.*t)


def gauss(value, center, width):
    return math.exp(-((value-center)/width)**2)


def point_at(obj, target):
    obj.rotation_euler = (Vector(target)-obj.location).to_track_quat('-Z', 'Y').to_euler()


def triangle_count(mesh):
    mesh.calc_loop_triangles()
    return len(mesh.loop_triangles)


def geometry_hash(mesh):
    import struct
    data = b''.join(struct.pack('<3f', *v.co) for v in mesh.vertices)
    data += b''.join(struct.pack('<I', i) for p in mesh.polygons for i in p.vertices)
    return hashlib.sha256(data).hexdigest()


def source_normals_variant(obj):
    """Change only corner normals around gentle but discontinuous head edges."""
    mesh = obj.data
    mesh.calc_loop_triangles()
    normals = [n.vector.copy() for n in mesh.corner_normals]
    key = lambda co: tuple(round(x*1e6) for x in co)
    edges = defaultdict(list)
    incident = defaultdict(list)
    for poly in mesh.polygons:
        ids = list(poly.loop_indices)
        world = [obj.matrix_world @ mesh.vertices[mesh.loops[i].vertex_index].co for i in ids]
        if not all(p.z > 1.42 for p in world):
            continue
        for i in ids:
            co = mesh.vertices[mesh.loops[i].vertex_index].co
            incident[key(co)].append((i, poly.normal.copy(), poly.area))
        for a, b in zip(ids, ids[1:]+ids[:1]):
            ka = key(mesh.vertices[mesh.loops[a].vertex_index].co)
            kb = key(mesh.vertices[mesh.loops[b].vertex_index].co)
            corners = (a, b) if ka < kb else (b, a)
            edges[tuple(sorted((ka, kb)))].append((poly.normal.copy(), corners))
    affected = set()
    flagged = []
    for edge, faces in edges.items():
        if len(faces) != 2:
            continue
        dihedral = math.degrees(faces[0][0].angle(faces[1][0]))
        jump = max(math.degrees(normals[faces[0][1][k]].angle(normals[faces[1][1][k]])) for k in (0, 1))
        if dihedral < 15 and jump > 30:
            affected.update(edge)
            flagged.append({'vertex_position_keys': edge, 'geometric_dihedral_degrees': dihedral,
                            'stored_normal_jump_degrees': jump})
    changed = []
    for position in affected:
        entries = incident[position]
        average = sum((n*area for _, n, area in entries), Vector()).normalized()
        for index, _, _ in entries:
            angle = math.degrees(normals[index].angle(average))
            if angle > .01:
                changed.append({'loop': index, 'angle_degrees': angle})
                normals[index] = average.copy()
    mesh.normals_split_custom_set(normals)
    mesh.update()
    return {'flagged_edges': flagged, 'changed_corner_normals': changed,
            'vertices_moved': 0, 'topology_changed': False, 'uv_changed': False,
            'texture_changed': False, 'scope': 'Only identified head corner normals; no source vertex welding or subdivision.'}


def make_material(name, color, roughness=.55):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    node = mat.node_tree.nodes.get('Principled BSDF')
    node.inputs['Base Color'].default_value = (*color, 1)
    node.inputs['Roughness'].default_value = roughness
    return mat


def age_warp(point):
    """Small explicit form edits, in donor metres before final placement.

    These are design hypotheses, not recovered historical anatomy.
    """
    x, y, z = point
    frontal = 1.-smooth(-.075, -.015, y)
    side = 1 if x >= 0 else -1
    ax = abs(x)
    brow = .0028*gauss(ax, .030, .022)*gauss(z, 1.694, .010)
    under_eye_roll = .0025*gauss(ax, .031, .019)*gauss(z, 1.659, .006)
    under_eye_groove = -.0014*gauss(ax, .031, .021)*gauss(z, 1.652, .0035)
    cheek_hollow = -.0040*gauss(ax, .049, .016)*gauss(z, 1.625, .025)
    # Naso-labial crease/adjacent roll follows an explicit diagonal from ala.
    fold_x = .017 + .36*(1.642-z)
    fold_window = smooth(1.592, 1.605, z)*(1.-smooth(1.641, 1.651, z))
    fold = -.0018*gauss(ax, fold_x, .0027)*fold_window
    fold_roll = .0012*gauss(ax, fold_x+.0045, .0035)*fold_window
    glabella = -.0009*gauss(ax, .006, .0018)*gauss(z, 1.704, .016)
    nose_tip = .0018*gauss(x, 0, .013)*gauss(z, 1.650, .008)
    delta_y = -frontal*(brow+under_eye_roll+under_eye_groove+cheek_hollow+fold+fold_roll+glabella+nose_tip)
    # Broad cheek form and slightly descending corners; no eye-centre shift.
    delta_x = side*.0018*frontal*gauss(ax, .055, .018)*gauss(z, 1.655, .017)
    delta_z = -.0012*frontal*gauss(ax, .025, .007)*gauss(z, 1.604, .007)
    return Vector((x+delta_x, y+delta_y, z+delta_z))


def build_head():
    with bpy.data.libraries.load(str(BASE), link=False) as (_, loaded):
        loaded.objects = ['GEO-body', 'GEO-eye.R']
    body, eyes = loaded.objects
    for obj in loaded.objects:
        bpy.context.scene.collection.objects.link(obj)
    bpy.context.view_layer.update()
    # Existing authored multires has two levels. Evaluate it, then discard body.
    for modifier in body.modifiers:
        if modifier.type == 'MULTIRES':
            modifier.levels = 2
    depsgraph = bpy.context.evaluated_depsgraph_get()
    mesh = bpy.data.meshes.new_from_object(body.evaluated_get(depsgraph), depsgraph=depsgraph)
    mesh.name = 'Licensed_head_authored_surface'
    bm = bmesh.new()
    bm.from_mesh(mesh)
    cut = bmesh.ops.bisect_plane(bm, geom=list(bm.verts)+list(bm.edges)+list(bm.faces),
                                plane_co=(0, 0, 1.50), plane_no=(0, 0, 1), clear_inner=True)
    rim = [e for e in bm.edges if len(e.link_faces) == 1 and all(abs(v.co.z-1.5) < .00001 for v in e.verts)]
    if rim:
        bmesh.ops.holes_fill(bm, edges=rim, sides=0)
    bm.normal_update()
    bm.to_mesh(mesh)
    bm.free()
    for polygon in mesh.polygons:
        polygon.use_smooth = True
    bpy.data.objects.remove(body, do_unlink=True)
    neutral = bpy.data.objects.new('C0_Licensed_head_proportion_control', mesh)
    bpy.context.scene.collection.objects.link(neutral)
    aged = neutral.copy()
    aged.data = neutral.data.copy()
    aged.name = 'C1_Local_head_form_candidate'
    bpy.context.scene.collection.objects.link(aged)
    # Explicit shape edits occur before the shared placement transform.
    displacements = []
    for vertex in aged.data.vertices:
        before = vertex.co.copy()
        vertex.co = age_warp(before)
        distance = (vertex.co-before).length
        if distance > .000001:
            displacements.append(distance)
    # Fit head width/position to the existing character frame; does not establish likeness.
    placement = Matrix.Translation((0, .085, -.055)) @ Matrix.Diagonal((1.08, 1, 1, 1))
    neutral.matrix_world = placement
    aged.matrix_world = placement
    # Eyeballs already have correct location and mirror around the file's Center.
    # Evaluate the mirror before applying the shared head placement.
    eye_mesh = bpy.data.meshes.new_from_object(eyes.evaluated_get(depsgraph), depsgraph=depsgraph)
    eye_obj = bpy.data.objects.new('C_Eyeballs_anatomy_check', eye_mesh)
    bpy.context.scene.collection.objects.link(eye_obj)
    eye_obj.matrix_world = placement @ eyes.matrix_world
    bpy.data.objects.remove(eyes, do_unlink=True)
    for p in eye_mesh.polygons:
        p.use_smooth = True
    for obj in (neutral, aged, eye_obj):
        obj['source_attribution'] = 'Blender Studio / Project Heist; lesson author Julien Kaspar'
        obj['source_license'] = 'CC BY 4.0'
        obj['source_license_url'] = 'https://creativecommons.org/licenses/by/4.0/'
        obj['source_page'] = 'https://studio.blender.org/training/realistic-human-research/use-of-base-meshes/'
        obj['modifications'] = 'Head extraction, proportion placement and localized form edits; see accompanying experiment.json.'
    return neutral, aged, eye_obj, {'derived_from': 'Blender Studio / Project Heist realistic_human_base.blend, CC BY 4.0',
        'authored_multires_levels_evaluated': 2, 'head_cut_plane_donor_z_m': 1.50, 'neck_cut_capped': bool(rim),
        'placement_blender_translation_m': [0, .085, -.055], 'placement_scale': [1.08, 1, 1],
        'sculpt_form_changes': ['brow projection', 'infraorbital roll and groove', 'cheek hollow', 'nasolabial crease and roll',
                                'glabella crease', 'nasal tip projection', 'cheek width form', 'mouth corner descent'],
        'vertices_actually_displaced': len(displacements), 'max_displacement_donor_m': max(displacements),
        'mean_displacement_donor_m': sum(displacements)/len(displacements),
        'texture_changes': 'No old diffuse projection, no invented skin texture; neutral gray shape study.',
        'identity_status': 'Generic licensed head locally reshaped; aged Plato likeness NOT accepted.',
        'topology_status': 'Derived authored subdivision surface, not a new production retopology.',
        'high_to_low_bake_performed': False}


def export(objects, path):
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.export_scene.gltf(filepath=str(path), export_format='GLB', use_selection=True,
                              export_yup=True, export_animations=False, export_skins=False,
                              export_cameras=False, export_lights=False, export_extras=True)
    return {'file': str(path.relative_to(ASSET)).replace('\\', '/'), 'sha256': hash_file(path), 'bytes': path.stat().st_size}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--no-render', action='store_true')
    parser.add_argument('--samples', type=int, default=32)
    args = parser.parse_args(__import__('sys').argv[__import__('sys').argv.index('--')+1:] if '--' in __import__('sys').argv else [])
    for sub in ('work', 'export'):
        (ASSET/sub).mkdir(parents=True, exist_ok=True)
    QA.mkdir(parents=True, exist_ok=True)
    source_hash = hash_file(SOURCE)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.scale_length = 1
    bpy.ops.import_scene.gltf(filepath=str(SOURCE))
    original = next(o for o in scene.objects if o.type == 'MESH')
    original.name = 'A_P0_unchanged'
    normal_variant = original.copy()
    normal_variant.data = original.data.copy()
    scene.collection.objects.link(normal_variant)
    normal_variant.name = 'B_Targeted_normal_diagnostic'
    baseline_geometry_hash = geometry_hash(original.data)
    baseline_uv = [tuple(loop.uv) for loop in original.data.uv_layers.active.data]
    normal_report = source_normals_variant(normal_variant)
    assert baseline_geometry_hash == geometry_hash(normal_variant.data)
    assert baseline_uv == [tuple(loop.uv) for loop in normal_variant.data.uv_layers.active.data]
    neutral, aged, eyes, shape_report = build_head()
    gray = make_material('QA neutral gray, no textures', (.34, .34, .34))
    eye_gray = make_material('QA eyeball gray', (.23, .23, .23), .48)
    for obj in (neutral, aged):
        obj.data.materials.clear()
        obj.data.materials.append(gray)
    eyes.data.materials.clear()
    eyes.data.materials.append(eye_gray)
    source_materials = list(original.data.materials)
    source_image = next(n.image for m in source_materials for n in m.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image.colorspace_settings.name == 'sRGB')
    albedo = bpy.data.materials.new('QA original base color only, emission')
    albedo.use_nodes = True
    nodes = albedo.node_tree.nodes
    nodes.clear()
    output = nodes.new('ShaderNodeOutputMaterial')
    emission = nodes.new('ShaderNodeEmission')
    image_node = nodes.new('ShaderNodeTexImage')
    image_node.image = source_image
    albedo.node_tree.links.new(image_node.outputs['Color'], emission.inputs['Color'])
    albedo.node_tree.links.new(emission.outputs['Emission'], output.inputs['Surface'])
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = args.samples
    scene.cycles.use_denoising = False
    scene.cycles.seed = 31
    scene.render.threads_mode = 'FIXED'
    scene.render.threads = 4
    scene.render.resolution_x = scene.render.resolution_y = 768
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - Medium High Contrast'
    scene.view_settings.exposure = 0
    world = bpy.data.worlds.new('Fixed neutral gray environment')
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs['Color'].default_value = (.12, .12, .12, 1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value = .35
    for name, position, power, size in [('Key', (-.8, -1.2, 2.5), 70, .6), ('Fill', (.9, -.4, 2), 22, .75), ('Rim', (0, .8, 2), 40, .5)]:
        data = bpy.data.lights.new(name, 'AREA')
        data.energy, data.shape, data.size = power, 'DISK', size
        obj = bpy.data.objects.new(name, data)
        scene.collection.objects.link(obj)
        obj.location = position
        point_at(obj, (0, 0, 1.60))
    camdata = bpy.data.cameras.new('Controlled_head_camera')
    camera = bpy.data.objects.new('Controlled_head_camera', camdata)
    scene.collection.objects.link(camera)
    scene.camera = camera
    camdata.type, camdata.ortho_scale = 'ORTHO', .37
    camdata.dof.use_dof = False
    variants = [original, normal_variant, neutral, aged, eyes]
    images = []

    def render(name, visible, position, mode='gray'):
        for obj in variants:
            obj.hide_render = obj not in visible
            obj.hide_set(obj not in visible)
        for obj in (original, normal_variant):
            obj.data.materials.clear()
            for material in (source_materials if mode == 'full' else [albedo] if mode == 'albedo' else [gray]):
                obj.data.materials.append(material)
        camera.location = position
        point_at(camera, (0, 0, 1.595))
        scene.render.filepath = str(QA/(name+'.png'))
        if not args.no_render:
            bpy.ops.render.render(write_still=True)
        images.append({'file': name+'.png', 'visible_objects': [o.name for o in visible], 'mode': mode,
                       'camera_blender_m': list(position), 'target_blender_m': [0, 0, 1.595],
                       'orthographic_span_m': .37, 'resolution': [768, 768], 'samples': args.samples,
                       'denoising': False, 'classification': 'actual_local_mesh_render'})

    front, side, quarter = (0, -2, 1.595), (2, 0, 1.595), (.95, -2, 1.595)
    render('A_front_gray', [original], front)
    render('B_front_normals_only_gray', [normal_variant], front)
    render('A_front_original_albedo_only', [original], front, 'albedo')
    render('A_front_original_full_material', [original], front, 'full')
    render('A_side_gray', [original], side)
    render('A_quarter_gray', [original], quarter)
    render('C0_front_licensed_base_control_gray', [neutral, eyes], front)
    render('C1_front_reshaped_head_gray', [aged, eyes], front)
    render('C1_side_reshaped_head_gray', [aged, eyes], side)
    render('C1_quarter_reshaped_head_gray', [aged, eyes], quarter)
    # Restore exported baseline materials; candidate remains untextured gray.
    for obj in (original, normal_variant):
        obj.data.materials.clear()
        for material in source_materials:
            obj.data.materials.append(material)
    for obj in variants:
        obj.hide_set(False)
    outputs = {}
    outputs['normals_diagnostic'] = export([normal_variant], ASSET/'export/plato-normal-diagnostic.glb')
    outputs['head_study'] = export([aged, eyes], ASSET/'export/plato-head-geometry-study.glb')
    for obj in variants:
        obj.hide_render = obj not in (aged, eyes)
        obj.hide_set(obj not in (aged, eyes))
    for image in bpy.data.images:
        if image.source == 'FILE' and not image.packed_file:
            image.pack()
    camera.location = quarter
    point_at(camera, (0, 0, 1.595))
    bpy.context.preferences.filepaths.save_version = 0
    work = ASSET/'work/plato-head-study.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(work))
    report = {'schema_version': 1, 'executed_utc': datetime.now(timezone.utc).isoformat(),
              'blender_version': bpy.app.version_string, 'baseline_sha256': source_hash,
              'baseline_hash_after': hash_file(SOURCE), 'donor_sha256': hash_file(BASE),
              'normals_experiment': normal_report, 'geometry_experiment': shape_report,
              'mesh_stats': {o.name: {'vertices': len(o.data.vertices), 'triangles': triangle_count(o.data),
                                     'geometry_hash_local': geometry_hash(o.data)} for o in variants},
              'baseline_geometry_hash': baseline_geometry_hash, 'baseline_uv_preserved_in_B': True,
              'images': images, 'outputs': outputs, 'relative_blend_path': str(work.relative_to(ASSET)).replace('\\', '/'),
              'technical_status': 'local_candidate_exported', 'art_status': 'unreviewed_head_study_not_final_plato',
              'limits': ['Head study only; no body/neck integration, beard/hair, skin texture, baking or animation claim.',
                         'C1 uses real licensed anatomy and small explicit form changes, not recovered face information.',
                         'No source P0 mesh position/UV/texture changes; B has identified corner-normal changes only.']}
    (QA/'experiment.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print('HEAD_STUDY_COMPLETE '+json.dumps({'images': len(images), 'outputs': outputs, 'shape_changes': shape_report}))


if __name__ == '__main__':
    main()
