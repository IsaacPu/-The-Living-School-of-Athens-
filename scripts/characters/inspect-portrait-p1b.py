"""Read-only Blender inspection of the independent portrait candidate; no render."""
import json
import hashlib
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT/'art/characters/plato/v002/portrait-p1b/plato-portrait-p1b.blend'
QA = ROOT/'qa/characters/plato/v002/portrait-p1b'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))


def bounds(points):
    return {'min': [min(p[i] for p in points) for i in range(3)],
            'max': [max(p[i] for p in points) for i in range(3)]} if points else None


objects = []
for obj in bpy.context.scene.objects:
    if obj.type != 'MESH':
        continue
    points = [obj.matrix_world @ v.co for v in obj.data.vertices]
    entry = {'name': obj.name, 'bounds': bounds(points),
             'hide_render': obj.hide_render, 'visible': obj.visible_get(),
             'matrix': [list(row) for row in obj.matrix_world]}
    if 'clothing' in obj.name:
        counts = {}
        for polygon in obj.data.polygons:
            for edge in polygon.edge_keys:
                counts[edge] = counts.get(edge, 0)+1
        edges = [e for e, count in counts.items() if count == 1]
        adjacency = {}
        for a, b in edges:
            adjacency.setdefault(a, set()).add(b)
            adjacency.setdefault(b, set()).add(a)
        pending = set(adjacency)
        components = []
        while pending:
            stack = [pending.pop()]
            component = set(stack)
            while stack:
                for other in adjacency[stack.pop()]:
                    if other in pending:
                        pending.remove(other)
                        component.add(other)
                        stack.append(other)
            components.append({'vertices': len(component), 'bounds': bounds([points[i] for i in component]),
                               'edge_length_m': sum((points[a]-points[b]).length for a, b in edges if a in component),
                               'degree_counts': {str(n): sum(len(adjacency[i]) == n for i in component)
                                                 for n in set(len(adjacency[i]) for i in component)}})
        entry.update(boundary_edges=len(edges), boundary_components=components,
                     nonmanifold_edges=sum(n > 2 for n in counts.values()))
    if 'Elder_long_face' in obj.name:
        lip_vertices = {i for p in obj.data.polygons if p.material_index == 1 for i in p.vertices}
        entry['lip_bounds'] = bounds([points[i] for i in lip_vertices])
        entry['image_texture_nodes'] = sum(node.type == 'TEX_IMAGE' for mat in obj.data.materials
                                           if mat and mat.use_nodes for node in mat.node_tree.nodes)
    objects.append(entry)
scene = bpy.context.scene
report = {'inspection_rendered': False, 'source': SOURCE.relative_to(ROOT).as_posix(),
          'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(), 'objects': objects,
          'image_path': scene.render.filepath, 'cpu_threads': scene.render.threads,
          'device': scene.cycles.device, 'camera': scene.camera.name}
(QA/'static-inspection.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('PORTRAIT_STATIC_INSPECTION '+json.dumps(report))
