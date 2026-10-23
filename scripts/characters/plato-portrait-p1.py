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
ASSET = ROOT/'art/characters/plato/v002/portrait-p1'
QA = ROOT/'qa/characters/plato/v002/portrait-p1'
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
    spline = data.splines.new('POLY')
    spline.points.add(len(points)-1)
    for index, (p, co) in enumerate(zip(spline.points, points)):
        p.co = (*co, 1)
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
        if c.z > 1.701 or (c.y > .045 and c.z > 1.59) or (abs(c.x) > .065 and c.z > 1.635 and c.y > -.015):
            selected.append(p)
    used = sorted({i for p in selected for i in p.vertices})
    remap = {old: new for new, old in enumerate(used)}
    cap_data = bpy.data.meshes.new('P1 scalp hair mass')
    cap_data.from_pydata([mesh.vertices[i].co+mesh.vertices[i].normal*.0012 for i in used], [],
                        [[remap[i] for i in p.vertices] for p in selected])
    cap = bpy.data.objects.new('PORTRAIT_P1_Receding_gray_hair_mass', cap_data)
    scene.collection.objects.link(cap)
    cap_data.materials.append(hair_mats[1])
    for p in cap_data.polygons:
        p.use_smooth = True
    hair_count = 0
    # Surface-following waves from crown to back/temples.
    for ring, phi in enumerate((.18, .38, .58, .78, .98)):
        for column in range(25):
            theta = 2*math.pi*column/25+.08*ring
            if math.sin(theta) < -.5 and phi > .7:
                continue
            pts = []
            for index in range(11):
                t = index/10
                a = phi+.44*t
                th = theta+.08*math.sin(2*math.pi*t+theta)
                approximate = Vector((.09*math.sin(a)*math.cos(th), .055+.105*math.sin(a)*math.sin(th), 1.65+.096*math.cos(a)))
                location, normal, _, _ = tree.find_nearest(approximate)
                if location is not None:
                    pts.append(location+normal*(.0023+.0013*math.sin(math.pi*t)))
            if len(pts) > 2:
                curve(f'P1_scalp_lock_{hair_count:03}', pts, RNG.uniform(.0012,.0022), RNG.choice(hair_mats[:2]))
                hair_count += 1
                for strand in range(3):
                    offset = Vector((RNG.uniform(-.002,.002), RNG.uniform(-.001,.001), RNG.uniform(-.001,.001)))
                    curve(f'P1_scalp_fine_{hair_count:03}_{strand}', [p+offset for p in pts], .00024, RNG.choice(hair_mats))
    # Cheek/chin locks: lip line remains uncovered and readable.
    beard_count = 0
    for z in (1.485, 1.505, 1.527, 1.546):
        for column in range(-7, 8):
            x = column*.009
            if z > 1.52 and abs(x) < .029:
                continue
            hit, normal, _, _ = tree.ray_cast(Vector((x,-.4,z)), Vector((0,1,0)), .65)
            if hit is None:
                continue
            root = hit+normal*.0015
            end_z = 1.345+.75*abs(x)+RNG.uniform(-.007,.007)
            phase = RNG.uniform(0,2*math.pi)
            pts = []
            for index in range(13):
                t = index/12
                pts.append(Vector((root.x*(1-.18*t)+.0018*math.sin(3*math.pi*t+phase),
                                   root.y-.025*math.sin(math.pi*t)-.009*t+.0015*math.cos(3*math.pi*t+phase),
                                   root.z+(end_z-root.z)*t)))
            curve(f'P1_beard_lock_{beard_count:03}', pts, RNG.uniform(.0017,.0030), RNG.choice(hair_mats[:2]))
            for strand in range(6):
                offset = Vector((RNG.uniform(-.0025,.0025), RNG.uniform(-.0015,.0015), RNG.uniform(-.001,.001)))
                curve(f'P1_beard_fine_{beard_count:03}_{strand}', [p+offset for p in pts], RNG.uniform(.00020,.00038), RNG.choice(hair_mats))
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
    remove = [v for v in bm.verts if v.co.z > 1.37 and abs(v.co.x) < .082 and v.co.y < .05]
    if remove:
        bmesh.ops.delete(bm, geom=remove, context='VERTS')
    bm.to_mesh(torso.data)
    bm.free()
    torso.data.update()
    # Provisional editable garment collar bridges the bust cut for this one view.
    vertices, faces = [], []
    for ring in range(5):
        t = ring/4
        for n in range(48):
            a = 2*math.pi*n/48
            vertices.append(((.070+.19*t**.7)*math.cos(a), .075+(.045+.10*t)*math.sin(a),
                             1.46-.10*t+.006*math.sin(a)))
    for ring in range(4):
        for n in range(48):
            a=ring*48+n; b=ring*48+(n+1)%48
            faces.append((a,b,b+48,a+48))
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
    blend = ASSET/'plato-portrait-p1.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    image = QA/'plato-head-shoulders-quarter.png'
    scene.render.filepath = str(image)
    bpy.ops.render.render(write_still=True)
    assert hashlib.sha256(P0.read_bytes()).hexdigest() == baseline_hash
    result = {'schema_version':1,'created_utc':datetime.now(timezone.utc).isoformat(),
        'candidate_name':'plato-portrait-p1','art_status':'pending_single_view_review',
        'image':str(image.relative_to(ROOT)).replace('\\','/'),'blend':str(blend.relative_to(ROOT)).replace('\\','/'),
        'blend_sha256':hashlib.sha256(blend.read_bytes()).hexdigest(),'baseline_sha256':baseline_hash,
        'cpu_threads':4,'gpu_used':False,'samples':32,'denoising':False,'resolution':[768,768],
        'head_vertices':len(mesh.vertices),'head_displaced_vertices':len(displacement),
        'head_max_donor_displacement_m':max(displacement),
        'head_form_changes':['lower face elongation','jaw narrowing','cheek hollowing','less regular infraorbital rolls',
                             'brow form','nasolabial folds','nasal tip','mouth corner descent','ear lobe'],
        'surface_evaluation':'One local subdivision on the licensed quad head, supporting form editing; not claimed as refinement by itself.',
        'hair_primary_locks':hair_count,'beard_primary_locks':beard_count,
        'hair_beard_representation':'Editable actual 3D curves plus scalp mass, not image overlays.',
        'skin_material':'New procedural skin/lip material; no old face diffuse projection.',
        'eyes':'Retained anatomical eyeballs with procedural polygon iris/sclera/pupil materials.',
        'collar':'P0 clothing cropped to shoulders and provisional new collar; full neck/body connection not accepted.',
        'source_license':'CC BY 4.0 for derived head/eyes; see ../ATTRIBUTION.md. Existing clothing retains P0 source provenance.',
        'limits':['Only one three-quarter shaded preview; front/back and seam checks pending.',
                  'Hair/skin materials are procedural and not baked for runtime export.',
                  'No finished Plato likeness, full-body refinement, hand changes or animation claim.']}
    (QA/'portrait.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print('PORTRAIT_P1_ONE_FRAME_COMPLETE '+json.dumps(result))


if __name__ == '__main__':
    main()
