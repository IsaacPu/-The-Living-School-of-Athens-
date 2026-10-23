# B-P1: research applied to this model

The following public pages were actually read on 2026-10-23. Sources describe capabilities and methods; they do not certify the local result.

| Source | Relevant method | Applied locally / limits |
| --- | --- | --- |
| [Blender 4.5 Editing Normals](https://docs.blender.org/manual/en/4.5/modeling/meshes/editing/mesh/normals.html) | Distinguish face orientation, split/custom corner normals and vector edits | B identifies gentle head edges with excessive stored-normal jumps. Only 135 corner normals changed; no vertex/UV/texture edits. Visually insufficient, rejected as a refinement solution. |
| [Blender Studio: Use of Base Meshes](https://studio.blender.org/training/realistic-human-research/use-of-base-meshes/) | A properly designed quad base, real scale, UVs and sculpt-friendly topology support deliberate form editing | Downloaded this specific CC BY 4.0 asset, extracted a complete head, retained existing eyelid/nose/lip/ear structure and made explicit local form edits. Its sculpting topology is not automatically animation-ready. |
| [Blender Studio: Reprojection & Sculpt Layers](https://studio.blender.org/training/realistic-human-research/reprojection-sculpt-layers/) | Transfer detail that was actually sculpted, then refine and bake; control projection errors | Method reference only. No Sculpt Layers add-on installed; no missing detail inferred from blurry pixels; no reprojection claimed. |
| [Blender 4.5 Normal Map node](https://docs.blender.org/manual/en/4.5/render/shader_nodes/vector/normal_map.html) | Texture-driven shading normal, correct UV and Non-Color data | No normal map is present in the P0 asset. Normal maps cannot supply real silhouette/occlusion changes; no high-to-low normal bake is claimed for C1. |
| [Blender 4.5 Cycles Baking](https://docs.blender.org/manual/en/4.5/render/cycles/baking.html) | Selected-to-Active, cage/ray distance and selected channels | Future low-poly transfer must use actual high-poly detail and verify cage errors. The current head is a geometry study, not an optimized/baked runtime character. |

Professional sequence adopted: inspect references → establish complete anatomical forms → make explicit local changes → judge front/side/three-quarter in controlled gray → decide identity/proportion changes → only then production topology/UV/material baking. The head study reaches the structural inspection step only.

The original low-resolution painting and previously inspected museum sculpture support character direction, not pore-level or exact historical facial reconstruction. The next portrait must explicitly develop an elderly long face and gray-white hair/beard; a generic bald head is not accepted as Plato.
