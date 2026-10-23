"""Static skin plan from existing JSON plus two bounded TIFF headers only."""
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import time


ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / 'qa/characters/plato/v002/einar-intake'
START = time.perf_counter()


def read_json(name):
    return json.loads((QA / name).read_text(encoding='utf-8-sig'))


def memory(header):
    return header.get('memory_estimate', header.get('memory_estimate_first_ifd'))


def budget(headers):
    return {
        'image_names': [header['name'] for header in headers],
        'native_sample_mib': sum(memory(header)['full_resolution_native_samples_mib'] for header in headers),
        'source_channel_float32_mib': sum(memory(header)['full_resolution_float32_samples_mib'] for header in headers),
        'hypothetical_all_images_expanded_to_rgba_float32_mib': sum(
            memory(header)['width'] * memory(header)['height'] * 16 / 1048576 for header in headers),
        'actual_decoder_blender_or_render_memory_measured': False,
        'excludes': ['mipmaps', 'copies', 'decoding overhead', 'geometry', 'BVH', 'render buffers'],
    }


def main():
    static = read_json('stage3-displacement-static.json')
    chain = read_json('stage3-chain-summary.json')
    catalogue = read_json('stage1-raw-meshes.json')
    old_headers = read_json('stage3-image-headers.json')
    tree = static['node_trees'][static['material']['node_tree']]
    nodes = {node['name']: node for node in tree['nodes']}
    links = [link for link in tree['links'] if link.get('is_valid', True) and not link.get('is_muted', False)]
    spec = importlib.util.spec_from_file_location('bounded_headers', Path(__file__).with_name('inspect-einar-image-headers.py'))
    parser = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(parser)
    dependencies = {entry['name']: entry for entry in catalogue['image_dependencies']}
    names = ('einar_skin.albedo', 'einar_skin.roughness')
    headers = [parser.inspect(name, dependencies[name]) for name in names]
    texture_records = []
    for image_name in names + ('shapes-E-F-DEFAULT-DETAIL',):
        node = next(node for node in nodes.values() if node.get('image', {}).get('name') == image_name)
        uv_links = [link for link in links if link['to_node'] == node['name'] and link['to_socket'] == 'Vector']
        assert len(uv_links) == 1
        uv = nodes[uv_links[0]['from_node']]
        assert uv['type'] == 'UVMAP' and uv['uv_map'] == 'UVMap'
        texture_records.append({
            'image': node['image'], 'node': node['name'], 'uv_source': uv['name'], 'uv_map': uv['uv_map'],
            'interpolation': node['interpolation'], 'projection': node['projection'], 'extension': node['extension'],
            'outgoing_links': [link for link in links if link['from_node'] == node['name']],
        })
    packed_header = next(header for header in old_headers['headers'] if header['name'] == 'shapes-E-F-DEFAULT-DETAIL')
    attribute_nodes = [node for node in tree['nodes'] if node['type'] == 'ATTRIBUTE']
    attribute_name_missing = [node['name'] for node in attribute_nodes if 'attribute_name' not in node]
    result = {
        'schema_version': 1, 'stage': '6_static_skin_plan_no_candidate',
        'created_utc': datetime.now(timezone.utc).isoformat(),
        'input_reports': ['stage3-displacement-static.json', 'stage3-chain-summary.json',
                          'stage1-raw-meshes.json', 'stage3-image-headers.json'],
        'blender_library_loaded': False, 'pixels_decoded': False,
        'material_or_candidate_created': False, 'render_started': False,
        'new_header_images_only': list(names), 'new_header_records': headers,
        'source_texture_records': texture_records,
        'independently_recoverable_layers': [
            {'image': 'einar_skin.albedo', 'colorspace': 'sRGB', 'uv_map': 'UVMap',
             'proposed_use': 'Image Color to a new simple Principled Base Color, bypassing source overlays.',
             'limits': 'This is the standalone source color layer; actual pixel appearance and full source skin reproduction are unverified.'},
            {'image': 'einar_skin.roughness', 'colorspace': 'Non-Color', 'uv_map': 'UVMap',
             'proposed_use': 'Image Color into a scalar roughness input in a new simple material, retaining color-to-value conversion.',
             'limits': 'Direct use is a simplified base-layer diagnostic, not the complete source roughness Map Range/mixing result; do not invent an R-only selection.'},
        ],
        'packed_default_detail': {
            'image': 'shapes-E-F-DEFAULT-DETAIL', 'colorspace': 'Non-Color', 'uv_map': 'UVMap',
            'channels_supported_by_existing_header': 4,
            'blue_route_evidence': 'Image Texture.016 Color -> Separate Color.001 Blue -> Reroute.024; the default branch includes Math.037 weighted by Math.109 = 1 - Math.114.',
            'blue_weight_neutral_verified': False,
            'alpha_route_evidence': 'Image Texture.016 Alpha -> Reroute.003 -> Math.070 SUBTRACT 0.5 -> Math.050 MULTIPLY 2 -> Math.043 -> Math.105 -> Math.123 -> Bump.001 Height.',
            'alpha_total_composition_or_expression_neutral_verified': False,
            'red_green_routes': 'Separate Color.001 Red -> Math.039; Green -> Math.046. Expression/control contributions must not be inferred as zero from cached linked socket values.',
            'source_bump_distance': 0.00800000037997961, 'source_bump_strength': 1.0,
            'reconstruction_status': 'Defer in the minimum closeup. Do not enable whole packed Color as a normal/vector or assume Alpha alone reproduces the source combined normal.',
            'double_counting_risk': 'The default Blue-derived form may already exist in the approved sculpted geometry. Adding that same default Bump at full strength can duplicate it.',
            'existing_route_summary': next(route for route in chain['image_routes'] if route['image']['name'] == 'shapes-E-F-DEFAULT-DETAIL'),
        },
        'neutrality_boundary': {
            'attribute_nodes_without_recorded_attribute_name': attribute_name_missing,
            'recorded_driver_counts_by_tree': {name: len(value.get('drivers', [])) for name, value in static['node_trees'].items()},
            'linked_serialized_socket_values_are_not_rig_neutral': True,
            'full_source_material_neutral_reconstruction_verified': False,
            'reason': 'Missing Attribute identifiers/provenance and unevaluated linked branches prevent a neutral claim even when recorded node-tree driver lists are empty.',
        },
        'minimum_single_closeup_proposal': {
            'required_images': list(names), 'material': 'New simplified base albedo/roughness only; no source node group import.',
            'geometry': 'Retain the separately approved default sculpt geometry; this plan does not create or modify it.',
            'exclude_initially': ['shapes-A-B-C-D', 'packed default/detail Bump', 'noise_04', 'disp_default',
                                  'dirt', 'bruises', 'distress', 'wet/coat overlays', 'expression-driven layers'],
            'eyes': 'Not included in this skin-only budget. Source head/eye saved channels may define a constraint-free candidate placement, but matching, Armature effects and resize keys remain unverified.',
            'new_render_authorized_by_this_report': False,
        },
        'texture_budgets': {
            'minimum_base_albedo_roughness': budget(headers),
            'conditional_plus_packed_default_detail_not_enabled': budget(headers + [packed_header]),
            'conditional_budget_is_not_permission_or_neutrality_proof': True,
        },
        'uncertainties': [
            'UVMap names and ordered face-index compatibility do not by themselves establish identical per-loop UV values for a reconstructed mesh.',
            'No image pixel content, values, colors, lesions, roughness distribution or actual appearance was inspected.',
            'Base Color and Roughness in the source material include remaps/overlays. The proposed two-image version deliberately does not claim complete source-material fidelity.',
            'Default sculpt and packed Bump contributions must be separated before any optional detail layer is enabled.',
            'Eye placement is a separate gate; raw near-origin meshes or unevaluated identity world matrices cannot establish alignment.',
        ],
        'elapsed_seconds': round(time.perf_counter() - START, 4),
    }
    output = QA / 'stage6-skin-static-plan.json'
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'output': str(output.relative_to(ROOT)), 'elapsed_seconds': result['elapsed_seconds'],
                      'header_summary': [{
                          'image': header['name'], 'width': memory(header)['width'], 'height': memory(header)['height'],
                          'channel_count': header['channel_count'], 'bits_per_sample': header['bits_per_sample'],
                          'native_mib': memory(header)['full_resolution_native_samples_mib'],
                          'float32_mib': memory(header)['full_resolution_float32_samples_mib'],
                          'metadata_bytes_read': header['metadata_bytes_read'],
                      } for header in headers],
                      'texture_budgets': result['texture_budgets']}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
