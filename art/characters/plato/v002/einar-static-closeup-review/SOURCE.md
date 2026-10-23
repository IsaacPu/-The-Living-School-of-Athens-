# Einar static closeup — provenance and limits

Einar Rig (CC-BY) Blender Foundation | studio.blender.org

Source: https://studio.blender.org/characters/einar/v1/
License: CC BY 4.0 — https://creativecommons.org/licenses/by/4.0/
Original blend SHA256: `1c6663da0a2e9d6822978467c244e9186edc76083bae2414e02f9e695e711f7b`.

Changes: reopened the independently isolated stage-5 head, retained original Catmull-Clark2/default nine-node sculpt and scale, and built two clean eye meshes with the three source static resize layers. Eye placement is `main-head basis inverse × eye basis`, using common-parent/identity-parent-inverse evidence. Source Armature constraints/deformation and driven Shrink/Grow are intentionally excluded; this is a source-channel static candidate, not an evaluated source-rig neutral pose.

Skin is a simplified Principled using the original albedo/roughness maps, IOR1.45, Subsurface0. It omits source remaps, SSS, detail/expressions/bruise controls and is not the complete source skin shader. Eyes retain the source pupil/iris/white face partitions with new near-black/muted-brown/warm-gray materials; no eye atlas, iris-depth, cornea, hair or body. No age deformation or eye-position nudging was performed.

Copied textures, unchanged bytes, referenced relative to this blend:

| File | SHA256 |
| --- | --- |
| `textures/disp_default.exr` | `782488ea8f9107c41a93465a0dcdf31894ce18885cc65c0e2e88241a7d6fe116` |
| `textures/einar_skin.albedo.tif` | `c0ec5e11fae8e516f3a0dd18e612ab4b9a9ab810bf01f63d098a401fe05af7a4` |
| `textures/einar_skin.roughness.tif` | `e35cb48cd5b62918682b9f1d8064493b587304a0efc254520991e25efd0766b7` |

Status: one actual closeup rendered. Owner rejected this round's character visual acceptance: eye boundaries remain unreadable, and source scars/red patches do not fit Plato. This prototype is `art_not_accepted`; the result does not reject the complete Einar asset. A read-only camera-ray check found partial head occlusion of sampled eye surfaces; it establishes no corrective offset or complete cause. That run checked texture files using metadata paths rather than actual saved Image paths. Before commit, actual Image references were found remapped to the older directory; only those references were repaired. A separate reopen verified the three actual relative paths/hashes, unchanged geometry/transforms and unchanged original PNG bytes (`stage7-package-verification.json`). No additional rendering or source-rig evaluation occurred. Unity/runtime compatibility remains untested. Keep this file and textures with the blend.
