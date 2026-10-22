"""Package actual diagnostic outputs and the explicitly reviewed limitations."""
import hashlib
import json
import os
from pathlib import Path

production = Path(__file__).resolve().parents[2]
asset = production / 'art/characters/plato/v001'
qa = production / 'qa/characters/plato/v001'
report = json.loads((qa / 'blender-inspection.json').read_text(encoding='utf-8'))


def rel(p):
    return os.path.relpath(p, asset).replace('\\', '/')


def defect(code, description, image, region, next_step):
    return {'id': code, 'description': description, 'qa_image': rel(qa / image),
            'region_normalized_xywh': region, 'status': 'open', 'next_step': next_step}


defects = [
    defect('D01_FACE', '鼻梁、额头、发须的多边形棱面与模糊底色在近景明显；眼睑与嘴部缺乏可信体积，未达到主角近景标准。',
           'face_front.png', [.22, .14, .53, .76], '按统一角色设定重建头脸、眼睑和发须体积，重拓扑与重做贴图；不能靠全局平滑解决。'),
    defect('D02_HAND_BOOK', '手指细节和指节不清，手与书接触处有尖角、狭缝及薄片感；书脊和封面边缘变形。',
           'hands_book_front.png', [.24, .17, .53, .53], '保留中性手部母版，局部重建手/书的独立结构，再安排真实握持。'),
    defect('D03_GESTURE', '双手抱书，与原画柏拉图向上指点的标志手势不一致；书上也没有可确认的《蒂迈欧篇》标识。',
           'axis_plus_z_candidate_front.png', [.30, .26, .42, .24], '统一原画姿态与书籍设计后重建手臂和持书关系。'),
    defect('D04_CLOTH_FRONT', '披衣存在大块尖锐三角折片，内袍臂部有黑色裂隙外观；不能用底色掩盖。裂隙的拓扑成因尚需局部检查。',
           'hands_book_front.png', [.02, .06, .94, .94], '围绕肩、肘、腰受力点重建衣褶，逐处检查开口与穿插。'),
    defect('D05_CLOTH_BACK', '背面披衣有不连续的凹槽/黑缝外观和尖锐折面，后背近距离不可验收。',
           'axis_minus_z_candidate_back.png', [.30, .23, .43, .56], '补足背面参考和真实厚度，局部重建披衣而非仅细分。'),
    defect('D06_FEET', '脚趾与足部贴图模糊、脚跟轮廓粗糙；地面接触已技术落地，但不等于足部解剖通过。',
           'feet_front.png', [.12, .10, .77, .77], '局部重建足部或统一鞋履方案，并复查袍摆与地面关系。'),
    defect('D07_MATERIAL', '单材质同时覆盖皮肤、衣料和书籍；原件金属度贴图含非零值，没有法线细节贴图。候选金属度归零仅供同条件对照，未采用。',
           'material_before.png', [.18, .12, .64, .78], '先制作材质分区与有效金属遮罩；结合近景和最终场景照明决定局部修正。'),
    defect('D08_STRUCTURE', '一个静态网格，无骨骼、动画、形变目标；可编辑源不代表具备可换装或可动画母版。',
           'hands_book_side.png', [.10, .08, .82, .83], '后续重建中性姿态身体、服装、手和道具，并单独验收蒙皮与动作。'),
    defect('D09_TOPOLOGY', '以 1 微米位置量化合并后的诊断统计为 0 条边界边、579 条被超过两个三角形共享的边；接触或重合也可能产生此结果，尚未逐处定位，不能认定所有黑缝都是开口。',
           'axis_minus_z_candidate_back.png', [.18, .19, .64, .70], '按局部区域检查重复面、穿插与高连接边，先保留证据，不执行自动焊接或全局修复。'),
]
images = [i['path'] for i in report['qa_images']]
for name in ('front_metric_ruler.png', 'source_before_same_conditions.png', 'delivery_after_same_conditions.png'):
    if (qa / name).exists():
        images.append(rel(qa / name))
glb = asset / report['relative_glb_path']
delivery = {
    'schema_version': 1, 'asset_id': 'plato-v001', 'relative_glb_path': report['relative_glb_path'],
    'sha256': hashlib.sha256(glb.read_bytes()).hexdigest(), 'bytes': glb.stat().st_size,
    'source': {'provider': 'Aholo Lux3D', 'region': 'international', 'task_id': '4277623',
               'relative_original_path': 'source/plato-lux3d-task-4277623.glb',
               'sha256': report['source_sha256'], 'provenance': 'source/provenance.json',
               'new_generation': False, 'license_status': 'not_verified'},
    'units': 'meters', 'up_axis': '+Y', 'forward_axis': '+Z', 'orientation_verified': True,
    'orientation_evidence': {'front': images[0], 'back': images[1], 'source_to_canonical_yaw_degrees': 0,
                             'note': 'Actual front/back local Blender renders reviewed; glTF +Z maps to Blender -Y. Do not add a default 180-degree turn.'},
    'body_height_m': report['body_height_m'], 'body_height_method': 'Lowest foot vertex to top of hair/head; actual images confirm no raised hand extends above head. Not a historical height claim.',
    'bounds_m': report['canonical_bounds_m'], 'overall_bounds_m': report['canonical_bounds_m'],
    'triangles': report['triangles'],
    'materials': {'count': 1, 'policy': 'preserve_source', 'textures': [
        {'role': 'base_color', 'width': 2048, 'height': 2048, 'embedded': True},
        {'role': 'metallic_roughness', 'width': 2048, 'height': 2048, 'embedded': True}],
        'normal_map': False, 'nonmetal_candidate_adopted': False},
    'skins': 0, 'animations': 0, 'relative_blend_path': report['relative_blend_path'],
    'qa_images': images, 'geometry_changed': False,
    'changes': [
        {'type': 'source_isolation', 'description': 'Independent read-only source copy, exact SHA-256 preserved.'},
        {'type': 'rigid_root_rebase', 'translation_gltf_m': [0, .875, 0], 'scale': [1, 1, 1], 'yaw_degrees': 0,
         'description': 'Feet-centred empty root at origin. No rescale, smoothing, subdivision or topology edit.'},
        {'type': 'serialization', 'description': 'Blender GLB roundtrip; corner/UV splits can change vertex count while all triangle positions are preserved.'},
        {'type': 'editable_source', 'description': 'Packed-texture Blender source with QA cameras, lights and preserved source/candidate materials. Helpers are excluded from GLB.'}],
    'rollback': {'relative_source_path': 'source/plato-lux3d-task-4277623.glb',
                 'undo_rebase_translation_gltf_m': [0, -.875, 0], 'material_changes_in_export': False},
    'known_defects': defects, 'technical_status': 'local_export_verified_unity_pending',
    'art_status': 'baseline_diagnostic',
    'qa_report': rel(qa / 'REPORT.md'), 'verification_report': rel(qa / 'verification.json'),
    'roundtrip_report': rel(qa / 'roundtrip.json'), 'reference_sources': 'source/references.json',
    'reproduction': '../../../../scripts/characters/run-plato-diagnostic.ps1',
    'integration_notes': ['Copy GLB and required metadata into A-owned Unity project; no runtime reference to test-project.',
                           'Place root at intended ground point with localScale=1; orientation is +Z. Scene-specific yaw belongs to the placement transform.',
                           'Use a separate simple interaction collider; GLB intentionally contains no collision mesh.',
                           'Unity material/load/performance validation belongs to integration; old test reports do not validate this GLB.'],
    'verification_scope': 'Local source isolation, export and actual renders; final art, formal Unity integration, animation and commercial rights remain unaccepted.'}
(asset / 'delivery.json').write_text(json.dumps(delivery, ensure_ascii=False, indent=2), encoding='utf-8')
(qa / 'visual-review.json').write_text(json.dumps({
    'schema_version': 1, 'reviewer': 'B', 'method': 'Actual local Blender renders visually inspected',
    'orientation_verified': True, 'front_axis_gltf': '+Z', 'body_top_is_head': True,
    'geometry_finishing_claimed': False, 'material_candidate_adopted': False, 'known_defects': defects,
    'art_status': 'baseline_diagnostic'}, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'delivery': str(asset / 'delivery.json'), 'status': delivery['technical_status'],
                  'art_status': delivery['art_status'], 'defects': len(defects)}, ensure_ascii=False))
