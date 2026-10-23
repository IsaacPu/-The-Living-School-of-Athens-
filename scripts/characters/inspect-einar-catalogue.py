"""Stage 0: names only from an approved read-only Blender library.

Never assign any data_to member, open the scene, evaluate objects, execute Text,
access drivers or read image pixels. Native source files remain untouched.
"""
from datetime import datetime, timezone
import ctypes
from ctypes import wintypes
import json
from pathlib import Path
import time

import bpy

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT/'qa/characters/plato/v002/einar-intake'
SOURCE = Path('D:/AI/PROJECT/hackathon_projects/Aholo_3D_AI_Hackathon/project-management/source-cache/einar-v1/extracted/einar_release_v1.blend')
EXPECTED_BYTES = 91323760
OWNER_SOURCE_SHA256 = '1c6663da0a2e9d6822978467c244e9186edc76083bae2414e02f9e695e711f7b'
KINDS = ('objects', 'meshes', 'materials', 'images', 'collections', 'armatures',
         'actions', 'node_groups', 'texts', 'curves', 'lattices', 'cameras', 'lights',
         'scenes', 'shape_keys')


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
            'peak_working_set_mib': round(counters.PeakWorkingSetSize/1048576, 2),
            'pagefile_usage_mib': round(counters.PagefileUsage/1048576, 2)}


def resident_counts():
    return {kind: len(getattr(bpy.data, kind)) for kind in KINDS if hasattr(bpy.data, kind)}


started = time.perf_counter()
assert SOURCE.is_file() and SOURCE.stat().st_size == EXPECTED_BYTES
before_counts, before_memory = resident_counts(), process_memory()
catalogue = {}
unavailable = []
with bpy.data.libraries.load(str(SOURCE), link=False) as (data_from, data_to):
    # data_to is deliberately never assigned or dereferenced.
    for kind in KINDS:
        if not hasattr(data_from, kind):
            unavailable.append(kind)
            continue
        names = getattr(data_from, kind)
        assert all(isinstance(name, str) for name in names), 'Expected names only: '+kind
        catalogue[kind] = sorted(names)
after_counts, after_memory = resident_counts(), process_memory()
assert before_counts == after_counts, 'Unexpected native data appended during names-only read'
assert SOURCE.stat().st_size == EXPECTED_BYTES
elapsed = time.perf_counter()-started
QA.mkdir(parents=True, exist_ok=True)
summary = {'schema_version': 1, 'stage': '0_library_catalogue_only',
    'created_utc': datetime.now(timezone.utc).isoformat(), 'blender_version': bpy.app.version_string,
    'source_cache_read_only': str(SOURCE), 'source_bytes': EXPECTED_BYTES,
    'source_sha256_reported_by_owner': OWNER_SOURCE_SHA256,
    'catalogue_read_succeeded': True, 'data_to_members_assigned': False,
    'full_source_scene_opened': False, 'object_or_modifier_evaluation_performed': False,
    'text_or_driver_code_executed': False, 'image_pixels_loaded': False, 'render_started': False,
    'requested_cli_threads': 4, 'catalogue_elapsed_seconds': round(elapsed, 4),
    'process_memory_before': before_memory, 'process_memory_after': after_memory,
    'resident_counts_before': before_counts, 'resident_counts_after': after_counts,
    'catalogue_counts': {kind: len(names) for kind, names in catalogue.items()},
    'catalogue': catalogue, 'catalogue_kinds_not_exposed': unavailable,
    'head_eye_name_hits_unverified': [name for name in catalogue.get('objects', [])
        if any(term in name.lower() for term in ('head', 'eye', 'face', 'body'))],
    'limits': ['Names only: object type, topology, parenting, transforms, dependencies and image paths not inspected.',
               'Text/armature/action names do not establish code safety or rig compatibility.',
               'No head/eye objects appended; no head geometry or elderly form verified.',
               'Metadata-read memory is not a complete-scene or render memory estimate.',
               'Cache paths are provenance only; no Unity dependency or deliverable absolute asset reference created.']}
(QA/'stage0-metadata.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print('EINAR_STAGE0_COMPLETE '+json.dumps({key: summary[key] for key in (
    'catalogue_read_succeeded', 'catalogue_elapsed_seconds', 'process_memory_after',
    'catalogue_counts', 'head_eye_name_hits_unverified', 'resident_counts_before', 'resident_counts_after')}))
