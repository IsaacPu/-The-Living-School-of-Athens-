"""One bounded, actually shaded Plato-direction portrait; no external services.

The geometry-study stays immutable. This separate candidate develops age/long
face, editable gray-white hair/beard curves, eyes and a provisional collar.
"""
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import random

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
ASSET = ROOT/'art/characters/plato/v002/portrait-p1b'
QA = ROOT/'qa/characters/plato/v002/portrait-p1b'
STUDY = ROOT/'art/characters/plato/v002/work/plato-head-study.blend'
P0 = ROOT/'art/characters/plato/v001/export/plato-baseline-diagnostic.glb'
RNG = random.Random(231023)


def smooth(a, b, value):
    t = max(0, min(1, (value-a)/(b-a)))
    return t*t*(3-2*t)


def g(value, center, width):
    return math.exp(-((value-center)/width)**2)


def material(name, color, roughness=.6):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    node = mat.node_tree.nodes['Principled BSDF']
    node.inputs['Base Color'].default_value = (*color, 1)
    node.inputs['Roughness'].default_value = roughness
    return mat


def point_at(obj, target):
    obj.rotation_euler = (Vector(target)-obj.location).to_track_quat('-Z', 'Y').to_euler()


def curve(name, points, radius, mat):
    data = bpy.data.curves.new(name, 'CURVE')
    data.dimensions = '3D'
    data.resolution_u = 2
    data.bevel_depth = radius
    data.bevel_resolution = 1
    spline = data.splines.new('BEZIER')
    spline.bezier_points.add(len(points)-1)
    for index, (p, co) in enumerate(zip(spline.bezier_points, points)):
        p.co = co
        p.handle_left_type = p.handle_right_type = 'AUTO'
        t = index/(len(points)-1)
        p.radius = .12 + .88*((1-t)**.55)
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    data.materials.append(mat)
    return obj


def older_form(point):
    x, y, z = point
    ax = abs(x)
    front = 1-smooth(-.075, -.005, y)
    sign = 1 if x >= 0 else -1
    # Long lower face and less square jaw; neck cut and eye centres unchanged.
    lower = g(z, 1.565, .043)*smooth(1.505, 1.54, z)
    x *= 1-.10*lower*smooth(.022, .060, ax)
    z -= .010*lower
    y += .0062*front*g(ax, .048, .020)*g(z, 1.628, .027)
    y -= .0030*front*g(ax, .027, .022)*g(z, 1.696, .009)
    # Less regular infraorbital roll than C1, and a broad cheek transition.
    roll_center = 1.659 + .10*(ax-.030)
    y -= .0014*front*g(ax, .031, .023)*g(z, roll_center, .0055)
    y += .0011*front*g(ax, .033, .023)*g(z, roll_center-.007, .0035)
    fold_x = .017+.37*(1.642-z)
    fold_window = smooth(1.588, 1.601, z)*(1-smooth(1.644, 1.653, z))
    y += .0022*front*g(ax, fold_x, .0028)*fold_window
    y -= .0010*front*g(ax, fold_x+.0045, .004)*fold_window
    y += .0010*front*g(ax, .006, .0020)*g(z, 1.707, .017)
    y -= .0018*front*g(x, 0, .014)*g(z, 1.65, .009)
    z -= .0018*front*g(ax, .025, .008)*g(z, 1.603, .008)
    # Small ear-lobe change; avoids changing the complete head by a global scale.
    z -= .002*g(ax, .077, .010)*g(z, 1.636, .014)
    return Vector((x, y, z))


def main():
    build_only = '--build-only' in __import__('sys').argv
    assert not (QA/'plato-head-shoulders-quarter.png').exists(), 'Preserve the rendered candidate and source; further revisions need a separate review window/path'
    ASSET.mkdir(parents=True, exist_ok=True)
    QA.mkdir(parents=True, exist_ok=True)
    baseline_hash = hashlib.sha256(P0.read_bytes()).hexdigest()
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
    head.name = 'PORTRAIT_P1_Elder_long_face'
    # One local surface-evaluation step on the licensed quad head is supporting
    # geometry only, not the claim of refinement. Deliberate form edits follow.
    surface = head.modifiers.new('Local head surface evaluation', 'SUBSURF')
    surface.levels = surface.render_levels = 1
    deps = bpy.context.evaluated_depsgraph_get()
    mesh = bpy.data.meshes.new_from_object(head.evaluated_get(deps), depsgraph=deps)
    head.modifiers.clear()
    head.data = mesh
    displacement = []
    for v in mesh.vertices:
        before = v.co.copy()
        v.co = older_form(before)
        d = (v.co-before).length
        if d > .000001:
            displacement.append(d)
    mesh.transform(head.matrix_world)
    head.matrix_world = Matrix.Identity(4)
    mesh.update()
    for p in mesh.polygons:
        p.use_smooth = True
    eyes.name = 'PORTRAIT_P1_Eyeballs'
    eyes.data = eyes.data.copy()
    eyes.data.transform(eyes.matrix_world)
    eyes.matrix_world = Matrix.Identity(4)
    eyes.data.update()
    # A new procedural skin material; the old diffuse is never used on this head.
    skin = material('P1 procedural weathered warm skin', (.40, .255, .19), .58)
    shader = skin.node_tree.nodes['Principled BSDF']
    shader.inputs['Subsurface Weight'].default_value = .025
    noise = skin.node_tree.nodes.new('ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value = 170
    noise.inputs['Detail'].default_value = 2
    bump = skin.node_tree.nodes.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value = .13
    bump.inputs['Distance'].default_value = .00018
    skin.node_tree.links.new(noise.outputs['Fac'], bump.inputs['Height'])
    skin.node_tree.links.new(bump.outputs['Normal'], shader.inputs['Normal'])
    lips = material('P1 restrained lip color', (.29, .13, .105), .62)
    mesh.materials.clear()
    mesh.materials.append(skin)
    mesh.materials.append(lips)
    for p in mesh.polygons:
        c = p.center
        if 1.532 < c.z < 1.553 and abs(c.x) < .030 and c.y < -.035:
            p.material_index = 1
    eye_white = material('P1 muted sclera', (.56, .53, .46), .24)
    iris = material('P1 brown iris', (.055, .029, .013), .3)
    pupil = material('P1 pupil', (.003, .002, .002), .25)
    eyes.data.materials.clear()
    for mat in (eye_white, iris, pupil):
        eyes.data.materials.append(mat)
    centres = [Vector((sign*.029815087*1.08, -.112483576+.085, 1.677055717-.055)) for sign in (-1, 1)]
    for p in eyes.data.polygons:
        c = p.center
        centre = min(centres, key=lambda x: (c-x).length_squared)
        r = math.hypot((c.x-centre.x)/1.08, c.z-centre.z)
        if c.y < centre.y-.0095:
            p.material_index = 2 if r < .0027 else 1 if r < .0058 else 0
        else:
            p.material_index = 0
    # World-space head BVH is used for actual hair roots, not floating face decals.
    points = [v.co.copy() for v in mesh.vertices]
    tree = BVHTree.FromPolygons(points, [list(p.vertices) for p in mesh.polygons], all_triangles=False)
    hair_mats = [material('P1 hair white', (.70, .70, .66), .78),
                 material('P1 hair silver', (.43, .45, .44), .8),
                 material('P1 hair dark roots', (.22, .245, .24), .82)]
    # Thin scalp volume, with a receding frontal line. Separate editable object.
    selected = []
    for p in mesh.polygons:
        c = p.center
        frontal_line = 1.713+.020*g(abs(c.x), .050, .022)
        if c.z > frontal_line or (c.y > .045 and c.z > 1.59) or (abs(c.x) > .065 and c.z > 1.635 and c.y > .005):
            selected.append(p)
    used = sorted({i for p in selected for i in p.vertices})
    remap = {old: new for new, old in enumerate(used)}
    cap_data = bpy.data.meshes.new('P1 scalp hair mass')
    cap_data.from_pydata([mesh.vertices[i].co+mesh.vertices[i].normal*.0012 for i in used], [],
                        [[remap[i] for i in p.vertices] for p in selected])
    cap = bpy.data.objects.new('PORTRAIT_P1_Receding_gray_hair_mass', cap_data)
    scene.collection.objects.link(cap)
    cap_data.materials.append(hair_mats[2])
    for p in cap_data.polygons:
        p.use_smooth = True
    scalp_tree = BVHTree.FromPolygons(points, [list(p.vertices) for p in selected], all_triangles=False)
    hair_count = 0
    # Surface-following waves from crown to back/temples.
    for ring, phi in enumerate((.18, .38, .58, .78, .98)):
        for column in range(25):
            theta = 2*math.pi*(column+RNG.uniform(-.35,.35))/25+.08*ring
            root_phi = phi+RNG.uniform(-.045,.045)
            growth = RNG.uniform(.33,.58)
            if math.sin(theta) < -.5 and phi > .7:
                continue
            pts = []
            for index in range(11):
                t = index/10
                a = root_phi+growth*t
                th = theta+.08*math.sin(2*math.pi*t+theta)
                approximate = Vector((.09*math.sin(a)*math.cos(th), .055+.105*math.sin(a)*math.sin(th), 1.65+.096*math.cos(a)))
                location, normal, _, distance = scalp_tree.find_nearest(approximate)
                if location is not None and distance < .018:
                    pts.append(location+normal*(.0023+.0013*math.sin(math.pi*t)))
            if len(pts) > 2:
                curve(f'P1_scalp_lock_{hair_count:03}', pts, RNG.uniform(.0007,.0012), RNG.choice(hair_mats[:2]))
                hair_count += 1
                for strand in range(3):
                    offset = Vector((RNG.uniform(-.002,.002), RNG.uniform(-.001,.001), RNG.uniform(-.001,.001)))
                    curve(f'P1_scalp_fine_{hair_count:03}_{strand}', [p+offset for p in pts], .00024, RNG.choice(hair_mats))
    # Connected beard mass precedes a limited number of surface-following guides.
    # The upper contour rises at the cheeks, keeping the central lip line open.
    def beard_surface(t, angle):
        side = abs(math.sin(angle))
        root_z, end_z = 1.515+.034*side+.0015*math.sin(2.7*angle)*side, 1.337+.035*side+.002*math.sin(4.3*angle)
        radius_x = .065*(1-.66*t)+.006*math.sin(math.pi*t)
        radius_y = .018+.013*math.sin(math.pi*t)
        ridge = (.0013*math.sin(8.7*angle+2.4*math.pi*t)+.0008*math.sin(13.1*angle-1.3*math.pi*t+.43))*math.sin(math.pi*t)
        x0 = .065*math.sin(angle)
        hit, _, _, _ = tree.ray_cast(Vector((x0,-.30,root_z)), Vector((0,1,0)), .55)
        y0 = -.034-.018*math.cos(angle)
        correction = 0 if hit is None else hit.y+(-.0015 if math.cos(angle)>=0 else .004)-y0
        return Vector(((radius_x+ridge)*math.sin(angle),
                       -.034-.010*math.sin(math.pi*t)-(radius_y+ridge)*math.cos(angle)+correction*(1-t)**2,
                       root_z+(end_z-root_z)*t))
    beard_vertices = [beard_surface(ring/10, 2*math.pi*n/64) for ring in range(11) for n in range(64)]
    beard_faces = []
    for ring in range(10):
        for n in range(64):
            a=ring*64+n; b=ring*64+(n+1)%64
            beard_faces.append((a,a+64,b+64,b))
    beard_faces.append(tuple(10*64+n for n in reversed(range(64))))
    beard_data = bpy.data.meshes.new('P1r1 connected layered beard mass')
    beard_data.from_pydata(beard_vertices, [], beard_faces)
    beard_obj = bpy.data.objects.new('PORTRAIT_P1R1_Beard_volume', beard_data)
    scene.collection.objects.link(beard_obj)
    beard_data.materials.append(hair_mats[1])
    for p in beard_data.polygons:
        p.use_smooth = True
    beard_count = 0
    for column in range(39):
        angle = -1.58+3.16*column/38+RNG.uniform(-.015,.015)
        pts = [beard_surface(t, angle+.025*math.sin(2*math.pi*t+angle))+Vector((0,-.0009,0)) for t in [j/16 for j in range(17)]]
        curve(f'P1r1_beard_surface_guide_{column:03}', pts, RNG.uniform(.00038,.00065), RNG.choice(hair_mats[:2]))
        for strand in range(2):
            offset = Vector((RNG.uniform(-.0012,.0012), -.0007, 0))
            curve(f'P1r1_beard_surface_fine_{column:03}_{strand}', [p+offset for p in pts], .00020, RNG.choice(hair_mats))
        beard_count += 1
    # Short moustache branches around, rather than across, the mouth opening.
    for side in (-1, 1):
        for n in range(11):
            x = side*(.005+.0014*n)
            z = 1.563-.001*abs(n-4)
            hit, normal, _, _ = tree.ray_cast(Vector((x,-.4,z)), Vector((0,1,0)), .65)
            if hit is None:
                continue
            root = hit+normal*.001
            pts = [root+Vector((side*.014*t, -.003*math.sin(math.pi*t), -.006*t)) for t in [j/8 for j in range(9)]]
            curve(f'P1_moustache_{side}_{n}', pts, .00065, RNG.choice(hair_mats[:2]))
        for n in range(15):
            x = side*(.012+.0024*n)
            z = 1.645-.12*(abs(x)-.025)
            hit, normal, _, _ = tree.ray_cast(Vector((x,-.4,z)), Vector((0,1,0)), .65)
            if hit is None:
                continue
            root = hit+normal*.0008
            pts = [root+Vector((side*.006*t, -.0015*math.sin(math.pi*t), .0015*math.sin(math.pi*t))) for t in [j/6 for j in range(7)]]
            curve(f'P1_brow_{side}_{n}', pts, .00052, RNG.choice(hair_mats))
    # Read-only source body, cropped to shoulders only; no old facial texture on new head.
    before = set(scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(P0))
    imported = list(set(scene.objects)-before)
    torso = next(o for o in imported if o.type == 'MESH')
    torso.name = 'PORTRAIT_P1_Existing_clothing_crop'
    torso.data.transform(torso.matrix_world)
    torso.matrix_world = Matrix.Identity(4)
    torso.parent = None
    bm = bmesh.new()
    bm.from_mesh(torso.data)
    bmesh.ops.bisect_plane(bm, geom=list(bm.verts)+list(bm.edges)+list(bm.faces), plane_co=(0,0,1.43), plane_no=(0,0,1), clear_outer=True)
    bmesh.ops.bisect_plane(bm, geom=list(bm.verts)+list(bm.edges)+list(bm.faces), plane_co=(0,0,1.18), plane_no=(0,0,1), clear_inner=True)
    remove = [v for v in bm.verts if (v.co.z > 1.37 and abs(v.co.x) < .082 and v.co.y < .05) or v.co.y < -.13]
    if remove:
        bmesh.ops.delete(bm, geom=remove, context='VERTS')
    # Repair the cropped clothing's actual cut boundaries, not just hide them.
    # This is limited to the independent shoulder crop; P0 data stays unchanged.
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=.000001)
    bm.verts.index_update()
    torso_tree = BVHTree.FromPolygons([v.co.copy() for v in bm.verts],
        [[v.index for v in face.verts] for face in bm.faces], all_triangles=False)
    boundary_before = [e for e in bm.edges if len(e.link_faces)==1]
    cap_result = bmesh.ops.holes_fill(bm, edges=boundary_before, sides=0) if boundary_before else {'faces': []}
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    boundary_after = sum(len(e.link_faces)==1 for e in bm.edges)
    nonmanifold_after = sum(len(e.link_faces)>2 for e in bm.edges)
    bm.to_mesh(torso.data)
    bm.free()
    torso.data.update()
    torso_top = max(v.co.z for v in torso.data.vertices)
    assert torso_top <= 1.43001, 'Old P0 head was not fully excluded from clothing crop'
    # A surface-anchored collar bridges the head cut and provisional clothing crop.
    # The pieces are still separate; this is not a welded production integration.
    inner_ring, outer_ring = [], []
    for n in range(48):
        a = 2*math.pi*n/48
        radial = Vector((math.cos(a), math.sin(a), 0))
        location, normal, _, _ = tree.ray_cast(Vector((0,.075,1.465))+radial*.35, -radial, .70)
        if location is None:
            location, normal, _, _ = tree.find_nearest(Vector((.072*math.cos(a), .075+.05*math.sin(a), 1.465)))
        inner_ring.append(location+normal*.0015)
        location, _, _, _ = torso_tree.find_nearest(Vector((.21*math.cos(a), .035+.13*math.sin(a), 1.405)))
        outer_ring.append(location)
    vertices, faces = [], []
    for ring in range(5):
        t = ring/4
        for n in range(48):
            co = inner_ring[n].lerp(outer_ring[n], t)
            co.z -= .004*math.sin(math.pi*t)
            vertices.append(co)
    for ring in range(4):
        for n in range(48):
            a=ring*48+n; b=ring*48+(n+1)%48
            faces.append((a,a+48,b+48,b))
    cloth = bpy.data.meshes.new('P1 collar rings')
    cloth.from_pydata(vertices, [], faces)
    collar = bpy.data.objects.new('PORTRAIT_P1_Provisional_purple_collar', cloth)
    scene.collection.objects.link(collar)
    cloth.materials.append(material('P1 collar muted purple', (.17,.115,.19), .9))
    for p in cloth.polygons:
        p.use_smooth = True
    solid = collar.modifiers.new('Actual collar thickness', 'SOLIDIFY')
    solid.thickness = .002
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 32
    scene.cycles.use_denoising = False
    scene.cycles.seed = 231
    scene.render.threads_mode, scene.render.threads = 'FIXED', 4
    scene.render.resolution_x = scene.render.resolution_y = 768
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - Medium High Contrast'
    world = bpy.data.worlds.new('P1 neutral portrait world')
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs['Color'].default_value = (.11,.12,.13,1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value = .3
    for name, position, power, size in [('Key',(-.7,-1,2.3),30,.65),('Fill',(.8,-.3,1.9),8,.8),('Rim',(0,.8,2.1),18,.6)]:
        light = bpy.data.lights.new('P1 '+name, 'AREA')
        light.energy, light.shape, light.size = power, 'DISK', size
        obj = bpy.data.objects.new('P1 '+name, light)
        scene.collection.objects.link(obj)
        obj.location = position
        point_at(obj,(0,.03,1.54))
    camera_data = bpy.data.cameras.new('P1 one-quarter portrait camera')
    camera = bpy.data.objects.new('P1 one-quarter portrait camera',camera_data)
    scene.collection.objects.link(camera)
    camera.location = (.70,-1.4,1.60)
    point_at(camera,(0,.02,1.50))
    camera_data.type, camera_data.ortho_scale = 'ORTHO', .62
    camera_data.dof.use_dof = False
    scene.camera = camera
    scene['asset_role'] = 'elderly_Plato_direction_head_shoulders_candidate'
    scene['art_status'] = 'pending_single_view_review'
    bpy.context.preferences.filepaths.save_version = 0
    blend = ASSET/'plato-portrait-p1b.blend'
    image = QA/'plato-head-shoulders-quarter.png'
    scene.render.filepath = str(image)
    assert not head.hide_render and not eyes.hide_render and head.visible_get() and eyes.visible_get(), 'Head or eyes hidden before render'
    assert max(v.co.z for v in mesh.vertices) > 1.73 and min(v.co.z for v in mesh.vertices) < 1.46, 'New head/neck extent is incomplete'
    scene['portrait_head_visibility_preflight_passed'] = True
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    if not build_only:
        bpy.ops.render.render(write_still=True)
    assert hashlib.sha256(P0.read_bytes()).hexdigest() == baseline_hash
    result = {'schema_version':1,'created_utc':datetime.now(timezone.utc).isoformat(),
        'candidate_name':'plato-portrait-p1b','art_status':'ready_for_render_review' if build_only else 'pending_single_view_review',
        'rendered':not build_only,
        'image':str(image.relative_to(ROOT)).replace('\\','/'),'blend':str(blend.relative_to(ROOT)).replace('\\','/'),
        'blend_sha256':hashlib.sha256(blend.read_bytes()).hexdigest(),'baseline_sha256':baseline_hash,
        'cpu_threads':4,'gpu_used':False,'samples':32,'denoising':False,'resolution':[768,768],
        'head_vertices':len(mesh.vertices),'head_displaced_vertices':len(displacement),
        'head_max_donor_displacement_m':max(displacement),
        'head_form_changes':['lower face elongation','jaw narrowing','cheek hollowing','less regular infraorbital rolls',
                             'brow form','nasolabial folds','nasal tip','mouth corner descent','ear lobe'],
        'surface_evaluation':'One local subdivision on the licensed quad head, supporting form editing; not claimed as refinement by itself.',
        'hair_primary_locks':hair_count,'beard_primary_locks':beard_count,
        'hair_beard_representation':'Connected scalp/beard masses plus limited surface-following editable curves; no face overlays.',
        'visibility_preflight':{'head_hide_render':head.hide_render,'eyes_hide_render':eyes.hide_render,'head_visible':head.visible_get()},
        'old_clothing_max_z_m':torso_top,
        'clothing_boundary_repair':{'boundary_edges_before':len(boundary_before),'cap_faces_created':len(cap_result.get('faces',[])),
                                    'boundary_edges_after':boundary_after,'edges_with_more_than_two_faces':nonmanifold_after,
                                    'status':'incomplete_nonmanifold_crop','scope':'Independent cropped clothing only; remaining boundaries/nonmanifold edges are unresolved. No watertight or welded integration claim.'},
        'collar_attachment':'Inner ring anchored to head/neck surface with 1.5mm thickness allowance; outer ring anchored to retained clothing surface before new cap faces were created. Separate meshes, full multi-view integration pending.',
        'skin_material':'New procedural skin/lip material; no old face diffuse projection.',
        'eyes':'Retained anatomical eyeballs with procedural polygon iris/sclera/pupil materials.',
        'collar':'P0 clothing cropped to shoulders and provisional new collar; full neck/body connection not accepted.',
        'source_license':'CC BY 4.0 for derived head/eyes; see ../ATTRIBUTION.md. Existing clothing retains P0 source provenance.',
        'limits':['Only one three-quarter shaded preview; front/back and seam checks pending.',
                  'Clothing crop still has open boundaries and edges with more than two faces; collar/head/body integration is not accepted.',
                  'Hair/skin materials are procedural and not baked for runtime export.',
                  'No finished Plato likeness, full-body refinement, hand changes or animation claim.']}
    (QA/'portrait.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(('PORTRAIT_P1B_BUILD_ONLY_COMPLETE ' if build_only else 'PORTRAIT_P1B_ONE_FRAME_COMPLETE ')+json.dumps(result))


if __name__ == '__main__':
    main()
