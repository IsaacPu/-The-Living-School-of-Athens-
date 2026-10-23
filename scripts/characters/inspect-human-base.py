"""Read official CC BY base mesh without executing its embedded scripts."""
import argparse
import json
from pathlib import Path
import bpy

parser = argparse.ArgumentParser()
parser.add_argument('--source', required=True)
parser.add_argument('--report', required=True)
args = parser.parse_args(__import__('sys').argv[__import__('sys').argv.index('--') + 1:])
project = Path(__file__).resolve().parents[2]
source = (project / args.source).resolve()
report = (project / args.report).resolve()
bpy.ops.wm.read_factory_settings(use_empty=True)
with bpy.data.libraries.load(str(source), link=False) as (available, loaded):
    names = list(available.objects)
    text_names = list(available.texts)
    loaded.objects = names
    loaded.texts = text_names
for obj in loaded.objects:
    if obj:
        bpy.context.scene.collection.objects.link(obj)
bpy.context.view_layer.update()
objects = []
for obj in loaded.objects:
    if obj is None:
        continue
    item = {'name': obj.name, 'type': obj.type, 'matrix_world': [list(row) for row in obj.matrix_world],
            'location': list(obj.location), 'parent': obj.parent.name if obj.parent else None}
    if obj.type == 'MESH':
        points = [obj.matrix_world @ v.co for v in obj.data.vertices]
        item.update(vertices=len(points), polygons=len(obj.data.polygons),
                    bounds_blender={'min': [min(p[k] for p in points) for k in range(3)],
                                    'max': [max(p[k] for p in points) for k in range(3)]},
                    modifiers=[{'type': m.type, 'name': m.name, 'levels': getattr(m, 'levels', None),
                                'total_levels': getattr(m, 'total_levels', None)} for m in obj.modifiers],
                    uv_layers=list(obj.data.uv_layers.keys()))
        if obj.name == 'GEO-body':
            item['front_head_profile'] = []
            for z in [1.50 + .01 * i for i in range(30)]:
                band = [p for p in points if abs(p.x) < .025 and abs(p.z - z) < .007]
                if band:
                    front = min(band, key=lambda p: p.y)
                    item['front_head_profile'].append({'z_band': round(z, 3), 'front_vertex': list(front)})
    objects.append(item)
texts = [{'name': t.name, 'text': t.as_string()[:16000]} for t in loaded.texts if t]
result = {'blender_version': bpy.app.version_string, 'objects': objects, 'texts': texts,
          'scripts_executed': False, 'loaded_as_library': True}
prior = set(bpy.context.scene.objects)
bpy.ops.import_scene.gltf(filepath=str(project / 'art/characters/plato/v001/export/plato-baseline-diagnostic.glb'))
target_points = [o.matrix_world @ v.co for o in set(bpy.context.scene.objects) - prior if o.type == 'MESH' for v in o.data.vertices]
result['plato_front_head_profile'] = []
for z in [1.40 + .01 * i for i in range(36)]:
    band = [p for p in target_points if abs(p.x) < .025 and abs(p.z - z) < .007]
    if band:
        front = min(band, key=lambda p: p.y)
        result['plato_front_head_profile'].append({'z_band': round(z, 3), 'front_vertex': list(front)})
report.write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps(result))
