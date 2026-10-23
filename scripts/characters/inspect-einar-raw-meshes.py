"""Stage 1: append only five approved raw Mesh IDs, without scene links/eval."""
from datetime import datetime, timezone
import ctypes
from ctypes import wintypes
import glob
import json
import os
from pathlib import Path
import time

import bpy

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT/'qa/characters/plato/v002/einar-intake'
SOURCE = Path('D:/AI/PROJECT/hackathon_projects/Aholo_3D_AI_Hackathon/project-management/source-cache/einar-v1/extracted/einar_release_v1.blend')
NAMES = ('DATA_GEO-einar_head', 'DATA_GEO-einar_head.base', 'DATA_GEO-einar_head.base.001',
         'DATA_GEO-eye.L', 'DATA_GEO-eye.R')
KINDS = ('objects', 'meshes', 'materials', 'images', 'collections', 'armatures', 'actions',
         'node_groups', 'texts', 'curves', 'lattices', 'cameras', 'lights', 'scenes', 'shape_keys', 'libraries')


def process_memory():
    class Counters(ctypes.Structure):
        _fields_ = [('cb', wintypes.DWORD), ('PageFaultCount', wintypes.DWORD)] + [
            (name, ctypes.c_size_t) for name in ('PeakWorkingSetSize', 'WorkingSetSize',
            'QuotaPeakPagedPoolUsage', 'QuotaPagedPoolUsage', 'QuotaPeakNonPagedPoolUsage',
            'QuotaNonPagedPoolUsage', 'PagefileUsage', 'PeakPagefileUsage')]
    current = ctypes.windll.kernel32.GetCurrentProcess
    current.restype = wintypes.HANDLE
    query = ctypes.windll.psapi.GetProcessMemoryInfo
    query.argtypes = (wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD)
    query.restype = wintypes.BOOL
    counters = Counters()
    counters.cb = ctypes.sizeof(counters)
    if not query(current(), ctypes.byref(counters), counters.cb):
        raise ctypes.WinError()
    return {'working_set_mib': round(counters.WorkingSetSize/1048576, 2),
            'peak_working_set_mib': round(counters.PeakWorkingSetSize/1048576, 2)}


def resident_names():
    return {kind: sorted(item.name for item in getattr(bpy.data, kind))
            for kind in KINDS if hasattr(bpy.data, kind)}


def driver_count(data):
    animation = getattr(data, 'animation_data', None)
    return len(animation.drivers) if animation else 0


def material_images(tree, visited=None):
    if tree is None:
        return set()
    visited = set() if visited is None else visited
    pointer = tree.as_pointer()
    if pointer in visited:
        return set()
    visited.add(pointer)
    names = set()
    for node in tree.nodes:
        if node.type == 'TEX_IMAGE' and node.image:
            names.add(node.image.name)
        elif node.type == 'GROUP':
            names.update(material_images(node.node_tree, visited))
    return names


def image_dependency(image):
    # These are path/storage metadata only. Never read size, pixels, packed bytes,
    # reload or renderer handles, any of which could request image decoding.
    path = image.filepath
    packed_count = len(image.packed_files)
    entry = {'name': image.name, 'source': image.source, 'filepath': path,
             'packed_file_count': packed_count, 'resolved_path': None,
             'path_exists': None, 'udim_matches': [], 'pixels_accessed': False}
    if image.source not in ('FILE', 'TILED', 'SEQUENCE', 'MOVIE') or not path:
        entry['path_status'] = 'no_external_file_path'
        return entry
    resolved = os.path.normpath(bpy.path.abspath(path, start=str(SOURCE.parent), library=image.library))
    entry['resolved_path'] = resolved
    # Do not follow original artist/network locations outside the approved cache.
    try:
        inside = os.path.commonpath([os.path.normcase(str(SOURCE.parent)), os.path.normcase(resolved)]) == os.path.normcase(str(SOURCE.parent))
    except ValueError:
        inside = False
    if not inside:
        entry['path_status'] = 'outside_approved_cache_not_followed'
        return entry
    if '<UDIM>' in resolved or '<UVTILE>' in resolved:
        pattern = glob.escape(resolved).replace('<UDIM>', '[0-9][0-9][0-9][0-9]').replace('<UVTILE>', 'u[0-9]*_v[0-9]*')
        matches = sorted(p for p in glob.glob(pattern) if os.path.isfile(p))
        entry['udim_matches'], entry['path_exists'] = matches, bool(matches)
        entry['path_status'] = 'tile_files_found' if matches else 'tile_files_not_found'
    else:
        entry['path_exists'] = Path(resolved).is_file()
        entry['path_status'] = 'file_found' if entry['path_exists'] else 'file_not_found'
    if packed_count:
        entry['external_path_optional_because_packed'] = True
    return entry


started = time.perf_counter()
QA.mkdir(parents=True, exist_ok=True)
before = resident_names()
scene_object_names_before = sorted(obj.name for obj in bpy.context.scene.objects)
before_memory = process_memory()
print('EINAR_STAGE1_START_RAW_MESHES_ONLY '+json.dumps({'requested_meshes': NAMES, 'pid': os.getpid()}), flush=True)
with bpy.data.libraries.load(str(SOURCE), link=False) as (data_from, data_to):
    assert all(name in data_from.meshes for name in NAMES), 'Approved mesh catalogue mismatch'
    data_to.meshes = list(NAMES)
loaded_meshes = list(data_to.meshes)
assert len(loaded_meshes) == 5 and all(mesh is not None for mesh in loaded_meshes)
print('EINAR_STAGE1_RAW_IDS_READ '+json.dumps({'memory': process_memory(), 'mesh_names': [m.name for m in loaded_meshes]}), flush=True)
meshes = []
for requested, mesh in zip(NAMES, loaded_meshes):
    vertex_count, polygon_count, loop_count = len(mesh.vertices), len(mesh.polygons), len(mesh.loops)
    # Populates raw tessellation cache only; no depsgraph or geometry edits.
    mesh.calc_loop_triangles()
    key = mesh.shape_keys
    materials = []
    for mat in mesh.materials:
        if mat is None:
            materials.append(None)
            continue
        materials.append({'name': mat.name, 'uses_nodes': mat.use_nodes,
                          'image_ids_in_static_node_graph': sorted(material_images(mat.node_tree)) if mat.use_nodes else []})
    bounds = {'min': [min(v.co[axis] for v in mesh.vertices) for axis in range(3)],
              'max': [max(v.co[axis] for v in mesh.vertices) for axis in range(3)]} if vertex_count else None
    entry = {'requested_name': requested, 'loaded_name': mesh.name, 'vertices': vertex_count,
             'edges': len(mesh.edges), 'polygons': polygon_count, 'loop_triangles': len(mesh.loop_triangles),
             'bounds': bounds, 'bounds_space': 'raw mesh local; object transforms and world placement not inspected',
             'uv_layer_names': [layer.name for layer in mesh.uv_layers],
             'shape_key_id_name': key.name if key else None,
             'shape_key_names': [block.name for block in key.key_blocks] if key else [],
             'mesh_static_driver_count': driver_count(mesh), 'shape_key_static_driver_count': driver_count(key) if key else 0,
             'materials': materials}
    assert (len(mesh.vertices), len(mesh.polygons), len(mesh.loops)) == (vertex_count, polygon_count, loop_count)
    meshes.append(entry)
after = resident_names()
added = {kind: sorted(set(names)-set(before.get(kind, []))) for kind, names in after.items()}
scene_object_names_after = sorted(obj.name for obj in bpy.context.scene.objects)
assert scene_object_names_before == scene_object_names_after, 'Unexpected source object linked into factory scene'
images = [image_dependency(image) for image in bpy.data.images if image.name in added.get('images', [])]
result = {'schema_version': 1, 'stage': '1_five_raw_mesh_ids_only',
    'created_utc': datetime.now(timezone.utc).isoformat(), 'blender_version': bpy.app.version_string,
    'pid': os.getpid(), 'source_cache_read_only': str(SOURCE), 'requested_meshes': list(NAMES),
    'data_to_assigned_members': ['meshes'], 'full_scene_opened': False, 'source_objects_linked_into_scene': False,
    'depsgraph_modifier_rig_or_displacement_evaluation': False, 'geometry_edited': False,
    'raw_mesh_tessellation_cache_computed': True, 'text_or_driver_code_executed': False,
    'image_pixels_accessed': False, 'render_started': False, 'blend_saved': False,
    'inspection_elapsed_seconds': round(time.perf_counter()-started, 4),
    'process_memory_before': before_memory, 'process_memory_after': process_memory(),
    'resident_names_before': before, 'resident_names_after': after, 'new_data_blocks': added,
    'new_data_block_counts': {kind: len(names) for kind, names in added.items()},
    'scene_object_names_before': scene_object_names_before, 'scene_object_names_after': scene_object_names_after,
    'raw_meshes': meshes, 'image_dependencies': images,
    'limits': ['Raw local-space data only; no object transforms, hierarchy, active shape key values, expressions or rig behavior evaluated.',
               'Dependency IDs may be loaded implicitly; their presence is reported, never evaluated or linked to the scene.',
               'Image metadata and cache-local file existence only; no pixel/size queries or reads outside approved cache.',
               'Geometry availability and material paths do not establish elderly form or production/runtime compatibility.',
               'No new candidate or blend source saved; next step requires project owner decision.']}
(QA/'stage1-raw-meshes.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print('EINAR_STAGE1_COMPLETE '+json.dumps({key: result[key] for key in (
    'inspection_elapsed_seconds', 'process_memory_after', 'new_data_block_counts')}), flush=True)
