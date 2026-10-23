"""Read four approved TIFF/EXR headers; never decode or read image payloads.

Uses only the standard library. TIFF parsing reads the first IFD and selected
numeric tags, avoiding Pillow mode limitations for floating-point multichannel
TIFFs. EXR parsing stops at the header terminator, before the chunk offset table.
"""
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import struct
import time


ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / 'qa/characters/plato/v002/einar-intake'
CATALOGUE = QA / 'stage1-raw-meshes.json'
OUTPUT = QA / 'stage3-image-headers.json'
CACHE = Path('D:/AI/PROJECT/hackathon_projects/Aholo_3D_AI_Hackathon/project-management/source-cache/einar-v1/extracted').resolve()
NAMES = ('disp_default', 'shapes-A-B-C-D', 'shapes-E-F-DEFAULT-DETAIL', 'noise_04')
READ_LIMIT = 1024 * 1024
STARTED = time.perf_counter()
DEADLINE_SECONDS = 20


class HeaderReader:
    def __init__(self, handle):
        self.handle = handle
        self.bytes_read = 0
        self.read_calls = 0
        self.maximum_read_end = 0

    def read(self, size):
        if time.perf_counter() - STARTED > DEADLINE_SECONDS:
            raise TimeoutError('Header inspection exceeded 20-second internal limit')
        if size < 0 or self.bytes_read + size > READ_LIMIT:
            raise ValueError('Header byte budget exceeded or unbounded read requested')
        start = self.handle.tell()
        value = self.handle.read(size)
        self.bytes_read += len(value)
        self.read_calls += 1
        self.maximum_read_end = max(self.maximum_read_end, start + len(value))
        if len(value) != size:
            raise EOFError('Unexpected end of image metadata')
        return value

    def seek(self, offset):
        if offset < 0:
            raise ValueError('Negative metadata offset')
        self.handle.seek(offset)

    def cstring(self):
        result = bytearray()
        for _ in range(256):
            char = self.read(1)
            if char == b'\0':
                return result.decode('utf-8', errors='replace')
            result.extend(char)
        raise ValueError('EXR header string exceeds 255-byte limit')


def estimate(width, height, channel_bits):
    total_bits = width * height * sum(channel_bits)
    native_bytes = (total_bits + 7) // 8
    float32_bytes = width * height * len(channel_bits) * 4
    return {
        'width': width, 'height': height, 'pixel_count': width * height,
        'full_resolution_native_samples_bytes': native_bytes,
        'full_resolution_native_samples_mib': round(native_bytes / 1048576, 3),
        'full_resolution_float32_samples_bytes': float32_bytes,
        'full_resolution_float32_samples_mib': round(float32_bytes / 1048576, 3),
        'basis': 'One full-resolution sample per channel per pixel; excludes mipmaps, copies, renderer buffers and decode overhead.',
        'actual_decoded_or_blender_memory_measured': False,
    }


def tiff_header(reader):
    reader.seek(0)
    byte_order = reader.read(2)
    endian = {'little': '<', 'big': '>'}
    order_name = {b'II': 'little', b'MM': 'big'}.get(byte_order)
    if order_name is None:
        raise ValueError('Invalid TIFF byte-order marker')
    order = endian[order_name]
    version = struct.unpack(order + 'H', reader.read(2))[0]
    if version == 42:
        first_ifd = struct.unpack(order + 'I', reader.read(4))[0]
        count_format, count_size, entry_size, inline_size, offset_format = 'H', 2, 12, 4, 'I'
    elif version == 43:
        offset_size, reserved = struct.unpack(order + 'HH', reader.read(4))
        if offset_size != 8 or reserved != 0:
            raise ValueError('Unsupported BigTIFF offset layout')
        first_ifd = struct.unpack(order + 'Q', reader.read(8))[0]
        count_format, count_size, entry_size, inline_size, offset_format = 'Q', 8, 20, 8, 'Q'
    else:
        raise ValueError('Unsupported TIFF version: ' + str(version))
    if not first_ifd:
        raise ValueError('TIFF has no first image directory')
    reader.seek(first_ifd)
    entry_count = struct.unpack(order + count_format, reader.read(count_size))[0]
    if entry_count > 8192:
        raise ValueError('TIFF metadata directory exceeds bounded entry count')
    entries = reader.read(entry_count * entry_size)
    next_ifd = struct.unpack(order + offset_format, reader.read(inline_size))[0]
    wanted = {256, 257, 258, 259, 262, 277, 284, 339}
    numeric_types = {1: ('B', 1), 3: ('H', 2), 4: ('I', 4), 6: ('b', 1),
                     8: ('h', 2), 9: ('i', 4), 16: ('Q', 8), 17: ('q', 8), 18: ('Q', 8)}
    values = {}
    for index in range(entry_count):
        entry = entries[index * entry_size:(index + 1) * entry_size]
        tag, field_type = struct.unpack(order + 'HH', entry[:4])
        if tag not in wanted:
            continue
        if field_type not in numeric_types:
            raise ValueError('Unsupported numeric type in TIFF tag ' + str(tag))
        value_count = struct.unpack(order + offset_format, entry[4:4 + inline_size])[0]
        if not 1 <= value_count <= 512:
            raise ValueError('TIFF numeric tag count exceeds bounded limit')
        code, size = numeric_types[field_type]
        size *= value_count
        inline = entry[4 + inline_size:]
        if size <= inline_size:
            data = inline[:size]
        else:
            reader.seek(struct.unpack(order + offset_format, inline)[0])
            data = reader.read(size)
        values[tag] = list(struct.unpack(order + str(value_count) + code, data))
    width, height = values[256][0], values[257][0]
    channels = values.get(277, [1])[0]
    bits = values.get(258, [1])
    formats = values.get(339, [1])
    if len(bits) == 1:
        bits = bits * channels
    if len(formats) == 1:
        formats = formats * channels
    if min(width, height, channels) < 1 or len(bits) != channels or len(formats) != channels:
        raise ValueError('Inconsistent TIFF dimensions/channel tags')
    compression = values.get(259, [1])[0]
    compression_names = {1: 'NONE', 2: 'CCITT_RLE', 3: 'CCITT_T4', 4: 'CCITT_T6',
                         5: 'LZW', 6: 'OLD_JPEG', 7: 'JPEG', 8: 'ADOBE_DEFLATE',
                         32773: 'PACKBITS', 32946: 'DEFLATE', 50000: 'ZSTD'}
    sample_names = {1: 'unsigned_integer', 2: 'signed_integer', 3: 'IEEE_floating_point',
                    4: 'undefined', 5: 'complex_integer', 6: 'complex_floating_point'}
    return {
        'format': 'BigTIFF' if version == 43 else 'TIFF', 'byte_order': order_name,
        'ifd_entry_count': entry_count, 'inspected_ifd_index': 0,
        'next_ifd_offset': next_ifd, 'additional_ifds_inspected': False,
        'channel_count': channels, 'bits_per_sample': bits,
        'sample_format_codes': formats,
        'sample_formats': [sample_names.get(value, 'unknown') for value in formats],
        'compression': {'code': compression, 'name': compression_names.get(compression, 'unknown')},
        'photometric_interpretation_code': values.get(262, [None])[0],
        'planar_configuration_code': values.get(284, [1])[0],
        'channel_names_available_in_selected_header_tags': False,
        'memory_estimate_first_ifd': estimate(width, height, bits),
    }


def exr_header(reader):
    reader.seek(0)
    magic, version_flags = struct.unpack('<II', reader.read(8))
    if magic != 20000630:
        raise ValueError('Invalid OpenEXR magic')
    if version_flags & (0x800 | 0x1000):
        raise ValueError('Deep/multipart EXR is outside this bounded single-image parser')
    attributes = {}
    for _ in range(256):
        name = reader.cstring()
        if not name:
            break
        attribute_type = reader.cstring()
        payload_size = struct.unpack('<I', reader.read(4))[0]
        if name in ('dataWindow', 'displayWindow', 'channels', 'compression', 'lineOrder'):
            attributes[name] = (attribute_type, reader.read(payload_size))
        else:
            # An EXR preview can itself contain pixel data inside an attribute.
            # Skip all unneeded payloads, including previews, without reading.
            reader.seek(reader.handle.tell() + payload_size)
    else:
        raise ValueError('EXR attribute count exceeds bounded limit')
    if attributes['dataWindow'][0] != 'box2i' or len(attributes['dataWindow'][1]) != 16:
        raise ValueError('Unexpected EXR dataWindow type')
    xmin, ymin, xmax, ymax = struct.unpack('<4i', attributes['dataWindow'][1])
    width, height = xmax - xmin + 1, ymax - ymin + 1
    if min(width, height) < 1:
        raise ValueError('Invalid EXR data window')
    if attributes['channels'][0] != 'chlist':
        raise ValueError('Unexpected EXR channel list type')
    payload = attributes['channels'][1]
    offset, channels = 0, []
    channel_types = {0: ('UINT', 32), 1: ('HALF', 16), 2: ('FLOAT', 32)}
    while offset < len(payload) and payload[offset] != 0:
        end = payload.index(0, offset)
        name = payload[offset:end].decode('utf-8', errors='replace')
        offset = end + 1
        if offset + 16 > len(payload):
            raise ValueError('Truncated EXR channel descriptor')
        pixel_type, linear, xs, ys = struct.unpack('<iB3xii', payload[offset:offset + 16])
        offset += 16
        if pixel_type not in channel_types or min(xs, ys) < 1:
            raise ValueError('Unsupported EXR channel type/sampling')
        typename, bits = channel_types[pixel_type]
        nx = max(0, xmax // xs - math.ceil(xmin / xs) + 1)
        ny = max(0, ymax // ys - math.ceil(ymin / ys) + 1)
        channels.append({'name': name, 'pixel_type': typename, 'bits': bits,
                         'p_linear': bool(linear), 'x_sampling': xs, 'y_sampling': ys,
                         'native_sample_bytes': nx * ny * (bits // 8)})
    if not channels or offset >= len(payload) or payload[offset] != 0:
        raise ValueError('Invalid EXR channel list terminator')
    compression = attributes['compression'][1]
    if len(compression) != 1:
        raise ValueError('Invalid EXR compression attribute')
    compression_code = compression[0]
    compression_names = {0: 'NONE', 1: 'RLE', 2: 'ZIPS', 3: 'ZIP', 4: 'PIZ',
                         5: 'PXR24', 6: 'B44', 7: 'B44A', 8: 'DWAA', 9: 'DWAB'}
    memory = estimate(width, height, [channel['bits'] for channel in channels])
    memory['native_samples_accounting_for_channel_subsampling_bytes'] = sum(channel['native_sample_bytes'] for channel in channels)
    return {
        'format': 'OpenEXR', 'version': version_flags & 255,
        'flags_hex': hex(version_flags & ~255), 'tiled': bool(version_flags & 0x200),
        'data_window': {'min': [xmin, ymin], 'max': [xmax, ymax]},
        'channel_count': len(channels), 'channels': channels,
        'bits_per_sample': [channel['bits'] for channel in channels],
        'compression': {'code': compression_code, 'name': compression_names.get(compression_code, 'unknown')},
        'memory_estimate': memory,
    }


def inspect(name, entry):
    if entry.get('source') != 'FILE' or not entry.get('resolved_path'):
        raise ValueError('Expected cache-local file dependency for ' + name)
    candidate = Path(entry['resolved_path'])
    if os.path.commonpath([str(CACHE), str(candidate)]) != str(CACHE):
        raise ValueError('Path is outside the approved cache')
    path = candidate.resolve(strict=True)
    if not path.is_relative_to(CACHE):
        raise ValueError('Resolved path is outside the approved cache')
    before = path.stat()
    with path.open('rb', buffering=0) as handle:
        reader = HeaderReader(handle)
        result = exr_header(reader) if path.suffix.lower() == '.exr' else tiff_header(reader)
    after = path.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise ValueError('Source file size/mtime changed during header inspection')
    return {
        'name': name, 'cache_path_provenance_only': str(path), 'file_bytes': before.st_size,
        'metadata_bytes_read': reader.bytes_read, 'metadata_read_calls': reader.read_calls,
        'maximum_metadata_read_end_offset': reader.maximum_read_end,
        'metadata_read_limit_bytes': READ_LIMIT, 'source_size_mtime_unchanged': True,
        'pixel_payload_decoded': False, 'channel_semantics_inferred': False,
        **result,
    }


def main():
    catalogue = json.loads(CATALOGUE.read_text(encoding='utf-8-sig'))
    dependencies = catalogue['image_dependencies']
    headers, errors = [], []
    for name in NAMES:
        matches = [entry for entry in dependencies if entry['name'] == name]
        try:
            if len(matches) != 1:
                raise ValueError('Expected exactly one catalogue entry')
            headers.append(inspect(name, matches[0]))
        except Exception as error:
            errors.append({'name': name, 'error_type': type(error).__name__, 'message': str(error)})
    result = {
        'schema_version': 1, 'stage': '3_header_only_four_images',
        'created_utc': datetime.now(timezone.utc).isoformat(),
        'requested_images': list(NAMES), 'parser': 'Python standard-library struct; no image decoding libraries',
        'all_headers_read': len(headers) == len(NAMES) and not errors,
        'elapsed_seconds': round(time.perf_counter() - STARTED, 4),
        'per_image_read_limit_bytes': READ_LIMIT, 'internal_deadline_seconds': DEADLINE_SECONDS,
        'blender_started': False, 'pixel_payload_decoded': False, 'source_files_written': False,
        'headers': headers, 'errors': errors,
        'limits': [
            'Header metadata establishes format/type capacity, not actual sample values, ranges or vector/displacement semantics.',
            'TIFF reads only the first IFD and selected numeric tags; EXR stops before the chunk offset table.',
            'Memory figures are theoretical sample-buffer sizes, not measured decoding or Blender allocations.',
            'No image payload decoding, pixel arrays, thumbnails, previews or cache modifications.',
            'Size/mtime invariance is checked; no full-file hash was computed because that would read image payloads.',
        ],
    }
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('EINAR_IMAGE_HEADERS_COMPLETE ' + json.dumps({
        'all_headers_read': result['all_headers_read'], 'elapsed_seconds': result['elapsed_seconds'],
        'total_metadata_bytes_read': sum(item['metadata_bytes_read'] for item in headers),
        'errors': errors,
    }), flush=True)
    return 0 if result['all_headers_read'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
