# B-P1 v002 geometry study

**Decision: visible head-structure improvement; Plato/elderly-character art not accepted.** This independent study does not replace A's frozen runtime v001. It contains no new paid generation, model API calls, quotes, purchases or installed software.

## Diagnosis and actual experiments

1. **A, original:** clean import of the exact P0 canonical GLB. Neutral gray removes the distracting old skin/beard colors and exposes broad mask-like planes; the eye, lip and nasal structures are not adequately represented. [Front](A_front_gray.png), [side](A_side_gray.png), [three-quarter](A_quarter_gray.png).
2. **B, normals only:** detect 12 head edges where geometric dihedral is below 15 degrees but stored corner-normal discontinuity exceeds 30 degrees. Change 135 corner normals around those locations, preserving all vertex positions, topology, UVs and textures. [Same-condition result](B_front_normals_only_gray.png). The mean image-channel difference is about 0.041/255 and only about 0.42% of image pixels differ by more than 3/255. This is not a quality score. The result is visually insufficient and **rejected as a refinement solution**. No global smoothing is performed.
3. **C0, licensed anatomical control:** extract a full head/upper-neck region from Blender Studio's CC BY 4.0 base, preserving its authored eyelid, nasal, lip, ear and eyeball forms. [Front control](C0_front_licensed_base_control_gray.png).
4. **C1, local form candidate:** retain C0's topology and shared placement, then make explicit brow/infraorbital/cheek/nasolabial/glabella/nasal-tip/mouth-corner vertex displacements. 3,332 vertices move; maximum displacement is 3.865mm and mean displacement among moved vertices is 0.464mm, before shared placement. [Front](C1_front_reshaped_head_gray.png), [side](C1_side_reshaped_head_gray.png), [three-quarter](C1_quarter_reshaped_head_gray.png).

The large **A→C** improvement comes primarily from anatomy already authored in the licensed base. **C0→C1** is a small procedural form adjustment, not a claim that all of C1's anatomy was newly sculpted. The complete head is not merely a scaled old mask, but it also is not yet an elderly Plato likeness.

## Geometry, normals, texture and lighting separated

- The reproducible [diagnosis script result](diagnosis.json) uses a conservative head ROI: all three triangle vertices above 1.42m. It counts 1,874 triangles; 1.92% have three identical corner normals, so the entire issue cannot be called flat shading. The initial read-only estimate used triangle-centroid inclusion (2,046 triangles); that broader ROI explains the different preliminary number.
- The conservative head ROI occupies about 127,985 summed UV texels on the shared 2048² color image, equivalent to the area of roughly 358² pixels. This is not an actual rectangular head texture resolution, and overlapping UVs can affect the sum. Initial centroid inclusion gave about 375². Enlarging or sharpening this image cannot supply missing anatomy.
- [Original base-color-only Emission](A_front_original_albedo_only.png) shows blurry, painted-in facial/hair information even without scene lighting. [Original complete material](A_front_original_full_material.png) retains the geometric and color limitations.
- All geometric before/after views share the same camera, target, orthographic span, resolution, light scene, gray material and 32-sample Cycles settings. CPU uses four threads, no GPU, no denoising, no depth of field, fixed exposure/color management. The images retain sampling noise; no enhancement filter was applied.
- C1 uses untextured gray. No old diffuse texture is projected onto it. No new skin texture, UV layout, normal-map baking or skin material completion is claimed.

## Retained and rejected quality

Retain the full-head foundation: eyelids actually surround eyeballs, nasal ala/nostril forms, lip separation and ear volumes can be inspected in more than one view. The source study must remain recoverable.

Do not accept the current identity: the head remains generic and bald; under-eye rolls are overly regular, cheek/jaw forms still read young, and the present adjustments do not establish an elderly long face. Hair/beard, real skin treatment and connection to the original collar/body are absent. The neck/upper-torso cut is capped but not integrated with that body. The head retains broad base-mesh transitions and is not a completed production retopology.

Next bounded step authorized by the owner: preserve this geometry study, then develop a separate head-and-shoulders portrait candidate in the same branch. Explicitly work on elderly long-face proportions and gray-white hair/beard without hiding eyelid and mouth structure, followed by collar connection. First request is one actual shaded three-quarter image; new render operations wait for the owner's resource window.

## Files, license and rollback

- [Candidate manifest](../../../../art/characters/plato/v002/delivery.json)
- [Attribution](../../../../art/characters/plato/v002/ATTRIBUTION.md), [download provenance/license](../../../../art/characters/plato/v002/source/base-mesh-license.json)
- [Research and applied-method boundaries](RESEARCH.md), [actual experiment](experiment.json), [saved mesh inspection](saved-mesh-state.json)
- [Actual blend reopen / clean GLB reimport](roundtrip.json), [technical verification](verification.json), [all 27 frozen v001 files](v001-preservation-after.json)

The original CC BY file's actual SHA-256 is `1d9d2a6070acd6a3d0d9b676af816001310fb0f6128d07a3ab3e0318c7fdd981`. Source-file text was inspected for attribution, not executed. The derived head and eyeballs carry attribution/license as glTF extras as well as the accompanying attribution file. The normals-diagnostic GLB derives from the separate P0/Lux3D file and is not relabeled CC BY.

Reproduction commands are in the manifest. The source C0 control and changed C1 are both retained in the editable `.blend`; exact original v001 bytes remain available and unchanged. `art_status=art_not_accepted`, `asset_role=standalone_head_geometry_study`, `runtime_replacement_approved=false`.
