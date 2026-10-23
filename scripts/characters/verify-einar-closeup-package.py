"""Repair only derived texture references, then reopen without rendering/evaluation."""
import hashlib
import json
from pathlib import Path
import struct
import sys

import bpy

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / 'qa/characters/plato/v002/einar-intake'
BLEND = ROOT / 'art/characters/plato/v002/einar-static-closeup-review/einar-static-rest-skin-closeup.blend'
REPORT = QA / 'stage7-package-verification.json'
METADATA = QA / 'stage7-static-closeup.json'
assert not REPORT.exists(), 'Preserve existing verification; no implicit retry'
metadata = json.loads(METADATA.read_text(encoding='utf-8'))
image = Path(metadata['image'])


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def open_clean():
    bpy.ops.wm.open_mainfile(filepath=str(BLEND), load_ui=False, use_scripts=False)
    for kind in ('armatures', 'actions', 'lattices', 'texts', 'libraries', 'shape_keys'):
        assert len(getattr(bpy.data, kind)) == 0, kind
    assert all(obj.animation_data is None and not obj.constraints for obj in bpy.context.scene.objects)


def geometry_fingerprint():
    result = []
    for obj in sorted(bpy.context.scene.objects, key=lambda obj: obj.name):
        record = {'name': obj.name, 'type': obj.type,
                  'matrix': [list(row) for row in obj.matrix_world]}
        if obj.type == 'MESH':
            mesh = obj.data
            payload = b''.join(struct.pack('<3f', *vertex.co) for vertex in mesh.vertices)
            payload += b''.join(struct.pack('<I', index) for poly in mesh.polygons for index in poly.vertices)
            payload += b''.join(struct.pack('<I?', poly.material_index, poly.use_smooth) for poly in mesh.polygons)
            for layer in mesh.uv_layers:
                payload += layer.name.encode('utf-8')
                payload += b''.join(struct.pack('<2f', *loop.uv) for loop in layer.data)
            record.update(mesh_sha256=hashlib.sha256(payload).hexdigest(),
                          vertices=len(mesh.vertices), polygons=len(mesh.polygons),
                          material_names=[mat.name for mat in mesh.materials],
                          modifiers=[(mod.name, mod.type, mod.show_render, mod.show_viewport)
                                     for mod in obj.modifiers])
        result.append(record)
    return result


blend_sha_before = sha(BLEND)
image_sha_before = sha(image)
open_clean()
geometry_before = geometry_fingerprint()
records = []
file_images = [item for item in bpy.data.images if item.source == 'FILE']
print('ACTUAL_FILE_IMAGES '+json.dumps([{'name': item.name, 'filepath': item.filepath,
      'resolved': bpy.path.abspath(item.filepath)} for item in file_images]), flush=True)
if '--inspect-only' in sys.argv:
    print('INSPECTION_ONLY_NO_SAVE_OR_RENDER', flush=True)
    raise SystemExit(0)
assert len(file_images) == len(metadata['textures']) == 3
for record in metadata['textures']:
    target = BLEND.parent / 'textures' / Path(record['local_copy']).name
    assert target.is_file() and sha(target) == record['sha256']
    matches = [item for item in file_images if item.filepath.replace('\\', '/').rsplit('/', 1)[-1] == target.name]
    assert len(matches) == 1
    item = matches[0]
    records.append({'image': item.name, 'before_filepath': item.filepath,
                    'before_resolved_file_exists': Path(bpy.path.abspath(item.filepath)).is_file(),
                    'expected_relative_path': record['final_relative_path'],
                    'expected_sha256': record['sha256']})
    item.filepath = record['final_relative_path']

# These paths already refer to the destination folder, so Blender must not
# remap them from the previously opened file's location when saving.
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND), check_existing=False, relative_remap=False)
open_clean()
assert geometry_fingerprint() == geometry_before
assert sha(image) == image_sha_before
for record in records:
    item = bpy.data.images[record['image']]
    assert item.filepath.replace('\\', '/') == record['expected_relative_path'].replace('\\', '/'), (item.filepath, record['expected_relative_path'])
    resolved = Path(bpy.path.abspath(item.filepath)).resolve()
    assert resolved.parent == (BLEND.parent / 'textures').resolve()
    assert sha(resolved) == record['expected_sha256']
    record.update(after_filepath=item.filepath, actual_resolved_path=str(resolved),
                  actual_image_path_reopened_and_sha256_verified=True)

result = {'stage': '7_derived_package_texture_reference_repair',
          'blend': str(BLEND), 'blend_sha256_before': blend_sha_before,
          'blend_sha256_after': sha(BLEND), 'blend_bytes_after': BLEND.stat().st_size,
          'textures': records, 'geometry_and_object_transforms_unchanged': True,
          'geometry_fingerprint': geometry_before,
          'single_image_sha256_before_and_after': image_sha_before,
          'single_image_bytes_unchanged': True, 'render_performed': False,
          'source_library_opened': False, 'depsgraph_evaluated': False,
          'scope': 'Only derived texture references repaired; original failed image preserved. No source rig or eye movement. Art remains not accepted.',
          'historical_occlusion_path_check_limit': 'The original occlusion run verified files using metadata paths, not actual bpy image filepaths. This separate reopen verifies actual saved image paths.'}
REPORT.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
metadata['original_saved_texture_paths_before_package_repair'] = metadata['all_texture_paths_relative_to_new_blend']
metadata['all_texture_paths_relative_to_new_blend'] = [record['after_filepath'] for record in records]
metadata['package_verification'] = 'qa/characters/plato/v002/einar-intake/stage7-package-verification.json'
metadata['package_repair_no_new_render_image_unchanged'] = True
METADATA.write_text(json.dumps(metadata, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print('CLOSEUP_PACKAGE_VERIFIED '+json.dumps({'textures': len(records), 'render_performed': False,
      'geometry_unchanged': True, 'image_unchanged': True, 'blend_bytes': BLEND.stat().st_size}), flush=True)
