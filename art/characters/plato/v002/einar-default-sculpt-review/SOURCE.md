# Source and changes

Einar Rig (CC-BY) Blender Foundation | studio.blender.org

Source: https://studio.blender.org/characters/einar/v1/
License: CC BY 4.0 — https://creativecommons.org/licenses/by/4.0/

Derived from `DATA_GEO-einar_head.base` in `einar_release_v1.blend` (source SHA256 `1c6663da0a2e9d6822978467c244e9186edc76083bae2414e02f9e695e711f7b`). Raw vertices/faces, UVMap, edge crease and sharp flags preserved. Recreated source Catmull-Clark render level 2 and the verified nine-node default scalar normal displacement with original midlevel 0.5 and scale 0.00800000038. Added only clean gray review material, camera and lights; no artistic shape edits, rig, facial expression layer, hair or eyes.

Copied original `textures/displacement/face/disp_default.exr` into `textures/disp_default.exr` byte-for-byte, SHA256 `782488ea8f9107c41a93465a0dcdf31894ce18885cc65c0e2e88241a7d6fe116`. The editable blend uses `//textures/disp_default.exr`; keep the texture folder alongside it. The original cache is not a final dependency.

Status: source-default restoration A/B review only; not accepted Plato art. Detailed execution and image evidence: `qa/characters/plato/v002/einar-intake/STAGE5.md` in this worktree. Saved blend round-trip and Unity/runtime compatibility have not been tested.
