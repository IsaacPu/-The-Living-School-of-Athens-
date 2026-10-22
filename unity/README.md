# A-P0 independent Unity structure sample

This is the formal project's first structure/integration sample, not finished art.

## Rebuild and run

From `production/`, use PowerShell 7:

```powershell
./scripts/environment/build.ps1
./scripts/environment/verify.ps1
```

The build defaults to the installed Unity 6000.0.85f1 at `D:\A-3D\Unity Editors\Editor\Unity.exe`; pass `-UnityEditor` to use another compatible installation. `-SceneOnly` regenerates the editable saved scene without building. Close this project's Editor before a batch rebuild.

Run `unity/start-sample.cmd`. Keep the executable and its entire `Builds/P0/` directory together.
The launcher explicitly writes `qa/environment/manual/player-latest.log` inside production. Starting it again replaces this clearly named latest manual log; timestamped automated runs remain separate.

Enter: start roaming. WASD: move. Right mouse: capture/look. Escape: release. 1/R: fixed reference view, 2: close, 3: side, 4: look back, H: hide interface. This phase has no network or backend dependency.

## Ownership and provenance

- Runtime and Editor scene code are new production implementations. No old scene, prototype Bootstrap, Library, Builds, or historical QA report was copied.
- Initial `ProjectVersion.txt`, legacy `InputManager.asset`, package version declarations, and Noto Sans SC/OFL font files were independently copied from the accepted test project. `com.unity.pipeline` was omitted because it is unnecessary for this sample. Unity created its own cache and remaining settings.
- `Assets/_Project/Characters/plato-v001.glb` is a hash-checked independent copy of B's `art/characters/plato/v001/delivery.json` asset. The imported prefab is serialized into the saved scene; there is no runtime access to the test project or B's working directory.
- Character geometry is not scaled. Canonical +Z is verified by B; a single scene-placement yaw turns the character toward the front visitor. No importer yaw is added. Character art status remains `baseline_diagnostic`.
- Generated architecture comes from `Assets/Editor/ArchitectureMeshes.cs`, `ProductionBuilder.cs`, and `art/environment/architecture-parameters.json`. The scene and mesh assets remain editable in Unity. Mesh source has metric UVs; material surfaces are still plain P0 values, not a completed PBR texture pass.
- The official reference photo is local research material outside Assets. It is never used as a scene texture or included in the Player. Local QA comparison images must not be published as cleared museum-image assets.

## Evidence boundaries

`qa/environment/` contains new production reports only. The opt-in verifier renders the actual Player camera through URP StandardRequest, projects the original seven manually annotated painting anchors plus three additional near-vault anchors, checks actual imported materials/textures, measured height and ground contact, and drives the actual CharacterController through a collision route. Anchor world coordinates come from actual saved mesh vertices/edge midpoints and actual character Renderer bounds; reports include source objects and vertex indices, not merely parameter-derived coordinates. Every route endpoint checks vertical and horizontal error; step-transition support error and final descent have separate gates. The route continuously reaches the return camera at Z=8, records the real eye position against the preset and captures `return-reached.png` there before walking back. Other temporary camera presets do not prove that a human walked to those exact poses. No physical mouse/keyboard automation or final art verdict is claimed.

Fixed reference crop: `[128,128,1024,768]` from the 1280x1000 source. This central study excludes the decorative outer fresco arch and bottom wall panels, which remain explicit P0 gaps. Reference annotations have about +/-8px uncertainty. An anchor gate does not validate the whole composition, crowd, silhouettes, face, hands, carved ornament, lighting or surface detail.

The architecture is a longitudinal nested hall with coffered barrels, beveled piers, stair risers, side aisles and a distant sky aperture. Off-picture connections and stair depth are design completions. No extra generated asset, paid service, LLM, animation or backend was used.
