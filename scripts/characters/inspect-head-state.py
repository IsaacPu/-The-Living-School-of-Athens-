"""Lightweight saved-candidate checks; never renders or saves the blend."""
import json
from pathlib import Path
import bpy

root = Path(__file__).resolve().parents[2]
path = root/'art/characters/plato/v002/work/plato-head-study.blend'
bpy.ops.wm.open_mainfile(filepath=str(path), load_ui=False, use_scripts=False)
result = {}
for obj in bpy.context.scene.objects:
    if obj.type != 'MESH':
        continue
    mesh = obj.data
    aligned, total = 0, 0
    for p in mesh.polygons:
        for index in p.loop_indices:
            total += 1
            aligned += mesh.corner_normals[index].vector.dot(p.normal) > .9999
    result[obj.name] = {'vertices': len(mesh.vertices), 'polygons': len(mesh.polygons),
        'custom_normals': mesh.has_custom_normals, 'smooth_polygons': sum(p.use_smooth for p in mesh.polygons),
        'corner_normals_aligned_to_face_pct': 100*aligned/total,
        'modifiers': [m.type for m in obj.modifiers]}
print(json.dumps(result))
(root/'qa/characters/plato/v002/saved-mesh-state.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
