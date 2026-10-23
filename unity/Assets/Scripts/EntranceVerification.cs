using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEngine;
using UnityEngine.Rendering;

namespace AthensProduction
{
    /// <summary>Independent P1 Player probe. Requests are API-driven; movement uses the real controller.</summary>
    public sealed class EntranceVerification : MonoBehaviour
    {
        public string outputDirectory;
        public bool previewOnly;
        [Serializable] private sealed class Check { public string name, detail; public bool passed; }
        [Serializable] private sealed class PoseSample
        {
            public int cycle;
            public string phase, state;
            public float elapsed_seconds, progress, material_alpha, bridge_alpha;
            public bool controller_enabled, mural_enabled, bridge_enabled;
            public EntrancePose pose;
        }
        [Serializable] private sealed class Handoff
        {
            public string phase;
            public int cycle;
            public EntrancePose automatic, first_free;
            public float position_error_m, rotation_error_degrees, fov_error_degrees, projection_max_error;
        }
        [Serializable] private sealed class RoutePoint
        {
            public string phase;
            public Vector3 feet;
            public float elapsed_seconds;
        }
        [Serializable] private sealed class ImageInfo
        {
            public string file;
            public int width, height, quantized_colors, dark_pixels, pink_pixels;
            public EntrancePose camera;
        }
        [Serializable] private sealed class Report
        {
            public string stage = "P1_entrance_experience", started_utc, finished_utc, unity_version, graphics_device, failure = "";
            public string scope = "Independent Windows Player, three cycles of normal entry/return, skip/return, cancel/reentry/return. Actual CharacterController movement, material alpha, supporting colliders and camera projection. Requests are API-driven; no physical keyboard/mouse or window-presentation simulation. Art quality requires separate visual review.";
            public string screenshot_source = "Current Player camera via URP StandardRequest, 1200x900. Camera target, aspect, full projection and active render target restored after every capture.";
            public bool passed;
            public int completed_entries, completed_returns, cancelled_entries;
            public int blend_samples;
            public float blend_max_position_error_m, blend_max_rotation_error_degrees, blend_max_fov_error_degrees, blend_max_projection_shift_error;
            public List<Check> checks = new List<Check>();
            public List<PoseSample> poses = new List<PoseSample>();
            public List<Handoff> handoffs = new List<Handoff>();
            public List<RoutePoint> route = new List<RoutePoint>();
            public List<ImageInfo> images = new List<ImageInfo>();
            public List<string> runtime_errors = new List<string>();
        }
        private readonly Report report = new Report();
        private ProductionSample sample;
        private EntranceFlow flow;
        private float started;
        private bool finished;

        private IEnumerator Start()
        {
            started = Time.realtimeSinceStartup;
            sample = GetComponent<ProductionSample>();
            flow = GetComponent<EntranceFlow>();
            Directory.CreateDirectory(outputDirectory);
            report.started_utc = DateTime.UtcNow.ToString("o");
            report.unity_version = Application.unityVersion;
            report.graphics_device = SystemInfo.graphicsDeviceType + " / " + SystemInfo.graphicsDeviceName;
            Application.logMessageReceived += OnLog;
            // Advance nested helpers here so an exception anywhere produces a failed JSON report.
            var pending = new Stack<IEnumerator>();
            pending.Push(Verify());
            while (!finished && pending.Count > 0)
            {
                object next = null;
                bool more = false;
                string error = null;
                try { more = pending.Peek().MoveNext(); if (more) next = pending.Peek().Current; }
                catch (Exception exception) { error = exception.ToString(); }
                if (error != null) { Finish(error); yield break; }
                if (!more) { pending.Pop(); continue; }
                if (next is IEnumerator nested) { pending.Push(nested); continue; }
                yield return next;
            }
            if (!finished) Finish("");
        }

        private void Update()
        {
            if (!finished && Time.realtimeSinceStartup - started > 300) Finish("Entrance verification exceeded 300 real seconds.");
        }

        private IEnumerator Verify()
        {
            if (previewOnly)
            {
                report.stage = "visual_preview";
                report.scope = "Single normal entry and return visual preview. Actual controller and camera checks are included, but this report is not the final three-cycle P1 acceptance. Requests are API-driven; no physical keyboard/mouse or window-presentation simulation. Art quality requires separate visual review.";
            }
            yield return null;
            yield return null;
            Require(sample != null && flow != null, "ProductionSample and EntranceFlow must share the verification object.");
            CheckResult("single_sample_and_flow", FindObjectsByType<ProductionSample>(FindObjectsSortMode.None).Length == 1 && FindObjectsByType<EntranceFlow>(FindObjectsSortMode.None).Length == 1, "One sample and one entrance state machine in the loaded scene.");
            CheckResult("verification_input_suppressed", sample.verifying && sample.hideInterface, "Player probe suppresses user input and UI; EntranceFlow.Update still advances normally.");
            CheckResult("real_time_duration_configuration", Mathf.Abs(Time.timeScale - 1) < .0001f && flow.durationSeconds >= 6 && flow.durationSeconds <= 8, "timeScale=" + Time.timeScale + " entry_duration=" + flow.durationSeconds);
            CheckResult("urp", GraphicsSettings.currentRenderPipeline != null && GraphicsSettings.currentRenderPipeline.GetType().Name.Contains("UniversalRenderPipelineAsset"), "Actual active rendering pipeline.");
            CheckResult("mural_texture_and_shader", flow.mural != null && flow.mural.sharedMaterial != null && flow.mural.sharedMaterial.mainTexture != null && flow.mural.sharedMaterial.mainTexture.width >= 2048 && flow.mural.sharedMaterial.shader.isSupported, "Runtime mural has an actual high resolution texture and supported shader.");
            CheckResult("initial_gallery_idle", flow.State == EntranceState.GalleryIdle && !sample.visitor.enabled && AlphaNear(1), "Initial observation pose is controlled and mural is visible.");
            CheckResult("idle_rejects_actions", !flow.RequestEnter() && !flow.RequestSkip() && !flow.RequestCancel() && !flow.RequestReturn(), "No automatic transition starts outside its allowed state.");
            Record(0, "initial_gallery");
            Capture("gallery-initial.png");
            flow.StartGalleryRoaming();
            CheckResult("gallery_control_enabled", flow.State == EntranceState.GalleryRoaming && sample.visitor.enabled, "Starting gallery roaming adopts the initial view.");
            yield return WalkToTrigger();
            CheckResult("trigger_reached_by_controller", flow.CanEnter && sample.visitor.enabled, "Continuous movement reached trigger; feet=" + sample.visitor.transform.position);
            Record(0, "trigger_reached");
            Capture("gallery-before-entry.png");

            for (int cycle = 1; cycle <= 3; cycle++)
            {
                int entryBefore = flow.CompletedEntries, returnBefore = flow.CompletedReturns, cancelBefore = flow.CancelledEntries;
                float requested = Time.realtimeSinceStartup;
                Require(flow.RequestEnter(), "Normal entry was rejected in cycle " + cycle);
                CheckResult(Key(cycle, "normal_duplicate_guard"), !flow.RequestEnter() && !flow.RequestReturn(), "Repeated entry and premature return rejected while entering.");
                yield return WaitFor(EntranceState.AcademyRoaming, cycle, "normal", 12, cycle == 1);
                float elapsed = Time.realtimeSinceStartup - requested;
                CheckResult(Key(cycle, "normal_real_duration"), elapsed >= 6 && elapsed <= 8.5f, "Actual wall-clock seconds=" + elapsed + "; no shortened verification animation.");
                yield return CheckHandoff(cycle, "normal");
                if (cycle == 1) Capture("academy-after-entry.png");
                yield return ReturnToGallery(cycle, "normal_return");
                if (cycle == 1) Capture("gallery-returned.png");
                if (previewOnly)
                {
                    report.completed_entries = flow.CompletedEntries;
                    report.completed_returns = flow.CompletedReturns;
                    report.cancelled_entries = flow.CancelledEntries;
                    CheckResult("visual_preview_complete", flow.State == EntranceState.GalleryRoaming && flow.CanEnter && sample.visitor.enabled && flow.CompletedEntries == 1 && flow.CompletedReturns == 1 && flow.CancelledEntries == 0, "One normal entry and return only; final three-cycle acceptance has not run.");
                    CheckBlend();
                    CheckResult("runtime_errors", report.runtime_errors.Count == 0, "Error/Exception/Assert count=" + report.runtime_errors.Count);
                    yield break;
                }

                Require(flow.RequestEnter(), "Skip entry was rejected in cycle " + cycle);
                yield return UntilProgress(.13f, cycle, "skip_lead_in");
                CheckResult(Key(cycle, "skip_accepted"), flow.RequestSkip(), "Skip uses the real entering state.");
                yield return CheckHandoff(cycle, "skip");
                CheckResult(Key(cycle, "skip_duplicate_guard"), !flow.RequestSkip() && !flow.RequestEnter() && !flow.RequestCancel(), "Completed entry rejects another skip/entry/cancel.");
                yield return ReturnToGallery(cycle, "skip_return");

                var beforeCancel = flow.ReadPose();
                Require(flow.RequestEnter(), "Cancelable entry was rejected in cycle " + cycle);
                yield return UntilProgress(cycle == 1 ? .24f : cycle == 2 ? .42f : .62f, cycle, "cancel_lead_in");
                CheckResult(Key(cycle, "cancel_accepted"), flow.RequestCancel(), "Cancel reverses the active entry.");
                CheckResult(Key(cycle, "cancel_duplicate_guard"), !flow.RequestCancel() && !flow.RequestSkip() && !flow.RequestEnter(), "Cancel/skip/reentry rejected during reversal.");
                yield return WaitFor(EntranceState.GalleryRoaming, cycle, "cancel_return", 8, false);
                yield return null;
                var cancelledPose = flow.ReadPose();
                CheckPose(Key(cycle, "cancel_restores_pose"), beforeCancel, cancelledPose);
                CheckResult(Key(cycle, "cancel_restores_gallery"), sample.visitor.enabled && AlphaNear(1) && flow.CanEnter, "Controller, actual mural material and trigger restored after cancel.");
                CheckFloor(Key(cycle, "cancel_floor"));
                Require(flow.RequestEnter(), "Reentry after cancel was rejected in cycle " + cycle);
                requested = Time.realtimeSinceStartup;
                yield return WaitFor(EntranceState.AcademyRoaming, cycle, "cancel_reentry", 12, false);
                elapsed = Time.realtimeSinceStartup - requested;
                CheckResult(Key(cycle, "reentry_real_duration"), elapsed >= 6 && elapsed <= 8.5f, "Actual wall-clock seconds=" + elapsed);
                yield return CheckHandoff(cycle, "cancel_reentry");
                yield return ReturnToGallery(cycle, "reentry_return");
                CheckResult(Key(cycle, "counters"), flow.CompletedEntries == entryBefore + 3 && flow.CompletedReturns == returnBefore + 3 && flow.CancelledEntries == cancelBefore + 1, "Actual completions entries=" + flow.CompletedEntries + " returns=" + flow.CompletedReturns + " cancellations=" + flow.CancelledEntries);
            }
            report.completed_entries = flow.CompletedEntries;
            report.completed_returns = flow.CompletedReturns;
            report.cancelled_entries = flow.CancelledEntries;
            CheckResult("three_cycles_complete", flow.State == EntranceState.GalleryRoaming && flow.CanEnter && sample.visitor.enabled && flow.CompletedEntries == 9 && flow.CompletedReturns == 9 && flow.CancelledEntries == 3, "Three independent cycles end in usable gallery roaming.");
            CheckBlend();
            CheckResult("runtime_errors", report.runtime_errors.Count == 0, "Error/Exception/Assert count=" + report.runtime_errors.Count);
        }

        private IEnumerator WalkToTrigger()
        {
            float began = Time.realtimeSinceStartup, nextRecord = 0;
            float maxHorizontalExcess = 0;
            report.route.Add(new RoutePoint { phase = "gallery_route_start", feet = sample.visitor.transform.position, elapsed_seconds = 0 });
            while (Time.realtimeSinceStartup - began < 10)
            {
                var delta = flow.triggerFeet - sample.visitor.transform.position;
                delta.y = 0;
                if (delta.magnitude <= .04f) break;
                float dt = Mathf.Clamp(Time.unscaledDeltaTime, .001f, .1f);
                var velocity = delta.normalized * Mathf.Min(1.8f, delta.magnitude / dt);
                var before = sample.visitor.transform.position;
                sample.Drive(velocity, dt);
                var moved = sample.visitor.transform.position - before;
                moved.y = 0;
                maxHorizontalExcess = Mathf.Max(maxHorizontalExcess, moved.magnitude - velocity.magnitude * dt);
                if (Time.realtimeSinceStartup >= nextRecord)
                {
                    report.route.Add(new RoutePoint { phase = "gallery_approach", feet = sample.visitor.transform.position, elapsed_seconds = Time.realtimeSinceStartup - began });
                    nextRecord = Time.realtimeSinceStartup + .2f;
                }
                yield return null;
            }
            var remainder = flow.triggerFeet - sample.visitor.transform.position;
            remainder.y = 0;
            CheckResult("gallery_route_continuous", remainder.magnitude <= .05f && maxHorizontalExcess <= .005f, "Endpoint horizontal error=" + remainder.magnitude + " maximum excess over commanded movement=" + maxHorizontalExcess + "; no route teleports.");
            CheckFloor("gallery_route_floor");
        }

        private IEnumerator UntilProgress(float progress, int cycle, string phase)
        {
            float began = Time.realtimeSinceStartup;
            bool disabledThroughout = true;
            while (flow.State == EntranceState.Entering && flow.Progress < progress && Time.realtimeSinceStartup - began < 10)
            {
                disabledThroughout &= !sample.visitor.enabled;
                ObserveBlend();
                yield return null;
            }
            Record(cycle, phase);
            CheckResult(Key(cycle, phase + "_automatic"), flow.State == EntranceState.Entering && flow.Progress >= progress && disabledThroughout && !sample.visitor.enabled, "Actual progress=" + flow.Progress + " controller disabled during automatic segment.");
        }

        private IEnumerator WaitFor(EntranceState target, int cycle, string phase, float timeout, bool screenshots)
        {
            float began = Time.realtimeSinceStartup, nextRecord = 0;
            bool disabledThroughout = true, alignmentCaptured = false, bridgeCaptured = false, matchCaptured = false, midpointCaptured = false, crossingCaptured = false;
            while (flow.State != target && Time.realtimeSinceStartup - began < timeout)
            {
                disabledThroughout &= flow.IsAutomatic && !sample.visitor.enabled;
                ObserveBlend();
                if (Time.realtimeSinceStartup >= nextRecord)
                {
                    Record(cycle, phase);
                    nextRecord = Time.realtimeSinceStartup + .25f;
                }
                if (screenshots && !alignmentCaptured && flow.Progress >= .30f)
                {
                    Capture("entry-alignment.png");
                    alignmentCaptured = true;
                }
                if (screenshots && !bridgeCaptured && flow.Progress >= .42f)
                {
                    Capture("entry-bridge.png");
                    bridgeCaptured = true;
                }
                if (screenshots && !matchCaptured && flow.Progress >= .50f)
                {
                    Capture("entry-match.png");
                    matchCaptured = true;
                }
                if (screenshots && !midpointCaptured && flow.Progress >= .61f)
                {
                    Capture("entry-middle.png");
                    midpointCaptured = true;
                }
                if (screenshots && !crossingCaptured && flow.Progress >= .80f)
                {
                    Capture("entry-crossed.png");
                    crossingCaptured = true;
                }
                yield return null;
            }
            Record(cycle, phase + "_complete");
            CheckResult(Key(cycle, phase + "_state"), flow.State == target, "Expected=" + target + " actual=" + flow.State + " elapsed=" + (Time.realtimeSinceStartup - began));
            CheckResult(Key(cycle, phase + "_automatic_controller"), disabledThroughout, "All sampled automatic frames used a disabled CharacterController.");
            Require(flow.State == target, "Timed out waiting for " + target + " during " + phase);
        }

        private IEnumerator CheckHandoff(int cycle, string phase)
        {
            var automatic = flow.LastAutomaticPose;
            Require(automatic != null, "Entry completed without a recorded automatic camera pose.");
            // One complete input-free frame after the automatic writer has handed control back.
            yield return null;
            sample.Drive(Vector3.zero, 1f / 60);
            var free = flow.ReadPose();
            var evidence = new Handoff
            {
                cycle = cycle, phase = phase, automatic = automatic, first_free = free,
                position_error_m = Vector3.Distance(automatic.eye, free.eye),
                rotation_error_degrees = Quaternion.Angle(automatic.rotation, free.rotation),
                fov_error_degrees = Mathf.Abs(automatic.fov - free.fov),
                projection_max_error = MatrixError(automatic.projection, free.projection)
            };
            report.handoffs.Add(evidence);
            CheckPose(Key(cycle, phase + "_handoff"), automatic, free);
            CheckResult(Key(cycle, phase + "_roaming_state"), flow.State == EntranceState.AcademyRoaming && sample.visitor.enabled && AlphaNear(0), "Academy controller enabled and actual mural transparent/disabled.");
            CheckFloor(Key(cycle, phase + "_landing_floor"));
            var before = sample.visitorCamera.transform.position;
            const float dt = 1f / 30;
            var velocity = Vector3.right * 1.2f;
            sample.Drive(velocity, dt);
            var displacement = sample.visitorCamera.transform.position - before;
            var horizontal = new Vector3(displacement.x, 0, displacement.z);
            CheckResult(Key(cycle, phase + "_first_move"), Vector3.Distance(horizontal, velocity * dt) <= .003f && Mathf.Abs(displacement.y) <= .05f, "Actual eye delta=" + displacement + " expected horizontal=" + velocity * dt + "; no call to the old fixed roaming spawn.");
            Record(cycle, phase + "_first_move");
        }

        private IEnumerator ReturnToGallery(int cycle, string phase)
        {
            var expected = flow.LastPreEntryPose;
            float requested = Time.realtimeSinceStartup;
            Require(flow.RequestReturn(), "Return was rejected during " + phase);
            CheckResult(Key(cycle, phase + "_guard"), !flow.RequestReturn() && !flow.RequestEnter() && !flow.RequestSkip() && !flow.RequestCancel(), "Duplicate and incompatible requests rejected while returning.");
            yield return WaitFor(EntranceState.GalleryRoaming, cycle, phase, 10, false);
            float elapsed = Time.realtimeSinceStartup - requested;
            CheckResult(Key(cycle, phase + "_real_duration"), elapsed >= 5.8f && elapsed <= 7.5f, "Actual wall-clock seconds=" + elapsed + "; return path runs at configured duration.");
            yield return null;
            CheckPose(Key(cycle, phase + "_restored_pose"), expected, flow.ReadPose());
            CheckResult(Key(cycle, phase + "_ready"), sample.visitor.enabled && flow.CanEnter && AlphaNear(1), "Actual mural restored, controller enabled and reentry available.");
            CheckFloor(Key(cycle, phase + "_floor"));
        }

        private void CheckFloor(string name)
        {
            Physics.SyncTransforms();
            var feet = sample.visitor.transform.position;
            var supports = Physics.RaycastAll(feet + Vector3.up * .2f, Vector3.down, .5f, ~0, QueryTriggerInteraction.Ignore)
                .Where(hit => hit.collider != sample.visitor && Vector3.Dot(hit.normal, Vector3.up) > .9f)
                .OrderBy(hit => hit.distance).ToArray();
            bool supported = supports.Length > 0 && Mathf.Abs(feet.y - supports[0].point.y) <= .08f;
            float radius = Mathf.Max(.01f, sample.visitor.radius - sample.visitor.skinWidth - .005f);
            var center = sample.visitor.transform.TransformPoint(sample.visitor.center);
            float halfSegment = sample.visitor.height / 2 - sample.visitor.radius;
            var overlaps = Physics.OverlapCapsule(center - Vector3.up * halfSegment, center + Vector3.up * halfSegment, radius, ~0, QueryTriggerInteraction.Ignore)
                .Where(collider => collider != sample.visitor).ToArray();
            CheckResult(name, supported && overlaps.Length == 0, "feet=" + feet + " support=" + (supports.Length > 0 ? supports[0].collider.name + " at " + supports[0].point : "none") + " inner-capsule overlaps=" + string.Join(",", overlaps.Select(collider => collider.name)));
        }

        private bool AlphaNear(float expected)
        {
            var material = flow.mural.sharedMaterial;
            return material != null && material.HasProperty("_BaseColor") && Mathf.Abs(material.GetColor("_BaseColor").a - expected) <= .001f && flow.mural.enabled == (expected > 0) && Mathf.Abs(flow.MuralAlpha - expected) <= .001f;
        }

        private void Record(int cycle, string phase)
        {
            report.poses.Add(new PoseSample { cycle = cycle, phase = phase, state = flow.State.ToString(), elapsed_seconds = Time.realtimeSinceStartup - started, progress = flow.Progress, material_alpha = flow.mural.sharedMaterial.GetColor("_BaseColor").a, bridge_alpha = flow.BridgeAlpha, bridge_enabled = flow.BridgeEnabled, controller_enabled = sample.visitor.enabled, mural_enabled = flow.mural.enabled, pose = flow.ReadPose() });
        }

        private void ObserveBlend()
        {
            if (!flow.BridgeEnabled || flow.BridgeAlpha <= .001f || flow.BridgeAlpha >= .999f) return;
            var pose = flow.ReadPose();
            float expectedShift = 2 * (sample.parameters.hero_vanishing_y_top - .5f);
            report.blend_samples++;
            report.blend_max_position_error_m = Mathf.Max(report.blend_max_position_error_m, Vector3.Distance(pose.eye, sample.parameters.hero_position));
            report.blend_max_rotation_error_degrees = Mathf.Max(report.blend_max_rotation_error_degrees, Quaternion.Angle(pose.rotation, Quaternion.identity));
            report.blend_max_fov_error_degrees = Mathf.Max(report.blend_max_fov_error_degrees, Mathf.Abs(pose.fov - sample.parameters.hero_vertical_fov));
            report.blend_max_projection_shift_error = Mathf.Max(report.blend_max_projection_shift_error, Mathf.Abs(pose.projectionShift - expectedShift));
        }

        private void CheckBlend()
        {
            CheckResult("translucent_bridge_locks_hero_camera", report.blend_samples > 0 && report.blend_max_position_error_m <= .001f && report.blend_max_rotation_error_degrees <= .1f && report.blend_max_fov_error_degrees <= .05f && report.blend_max_projection_shift_error <= .0001f,
                "Actual translucent bridge frames=" + report.blend_samples + " maximum position_m=" + report.blend_max_position_error_m + " rotation_degrees=" + report.blend_max_rotation_error_degrees + " fov_degrees=" + report.blend_max_fov_error_degrees + " projection_shift=" + report.blend_max_projection_shift_error + "; entry, return and cancellation samples aggregated.");
        }

        private void CheckPose(string name, EntrancePose expected, EntrancePose actual)
        {
            float position = Vector3.Distance(expected.eye, actual.eye), rotation = Quaternion.Angle(expected.rotation, actual.rotation);
            float fov = Mathf.Abs(expected.fov - actual.fov), projection = MatrixError(expected.projection, actual.projection);
            CheckResult(name, position <= .001f && rotation <= .1f && fov <= .05f && projection <= .0001f && Mathf.Abs(expected.aspect - actual.aspect) <= .0001f, "position_m=" + position + " rotation_degrees=" + rotation + " fov_degrees=" + fov + " projection_max=" + projection + " aspect_error=" + Mathf.Abs(expected.aspect - actual.aspect));
        }

        private void Capture(string file)
        {
            const int width = 1200, height = 900;
            var camera = sample.visitorCamera;
            var oldActive = RenderTexture.active;
            var oldTarget = camera.targetTexture;
            var oldProjection = camera.projectionMatrix;
            float oldAspect = camera.aspect;
            var pose = flow.ReadPose();
            var target = new RenderTexture(width, height, 24, RenderTextureFormat.ARGB32, RenderTextureReadWrite.sRGB);
            Texture2D texture = null;
            target.Create();
            try
            {
                camera.aspect = (float)width / height;
                // The entrance camera is 4:3. Preserve its current asymmetric/cinematic projection verbatim.
                camera.projectionMatrix = oldProjection;
                var request = new RenderPipeline.StandardRequest { destination = target };
                if (!RenderPipeline.SupportsRenderRequest(camera, request)) throw new InvalidOperationException("URP StandardRequest is unsupported.");
                RenderPipeline.SubmitRenderRequest(camera, request);
                RenderTexture.active = target;
                texture = new Texture2D(width, height, TextureFormat.RGB24, false);
                texture.ReadPixels(new Rect(0, 0, width, height), 0, 0, false);
                texture.Apply(false);
                File.WriteAllBytes(Path.Combine(outputDirectory, file), texture.EncodeToPNG());
                var colors = texture.GetPixels32();
                var bins = new HashSet<int>();
                int dark = 0, pink = 0;
                foreach (var color in colors)
                {
                    if (color.r + color.g + color.b < 18) dark++;
                    if (color.r > 180 && color.b > 180 && color.g < 80) pink++;
                    bins.Add(((color.r >> 3) << 10) | ((color.g >> 3) << 5) | (color.b >> 3));
                }
                report.images.Add(new ImageInfo { file = file, width = width, height = height, camera = pose, quantized_colors = bins.Count, dark_pixels = dark, pink_pixels = pink });
                CheckResult("image_" + file, dark < colors.Length * .95f && pink < colors.Length * .01f && bins.Count > 100, "GPU colors=" + bins.Count + " dark=" + dark + " pink=" + pink + "; separate visual review required.");
            }
            finally
            {
                camera.targetTexture = oldTarget;
                camera.aspect = oldAspect;
                camera.projectionMatrix = oldProjection;
                RenderTexture.active = oldActive;
                target.Release();
                Destroy(target);
                if (texture != null) Destroy(texture);
            }
            CheckPose("capture_preserves_camera_" + file, pose, flow.ReadPose());
            CheckResult("capture_preserves_targets_" + file, camera.targetTexture == oldTarget && RenderTexture.active == oldActive, "Original camera targetTexture and RenderTexture.active restored.");
        }

        private static float MatrixError(Matrix4x4 a, Matrix4x4 b)
        {
            float maximum = 0;
            for (int row = 0; row < 4; row++) for (int column = 0; column < 4; column++) maximum = Mathf.Max(maximum, Mathf.Abs(a[row, column] - b[row, column]));
            return maximum;
        }
        private static string Key(int cycle, string name) { return "cycle_" + cycle + "_" + name; }
        private static void Require(bool condition, string message) { if (!condition) throw new InvalidOperationException(message); }
        private void CheckResult(string name, bool passed, string detail)
        {
            report.checks.Add(new Check { name = name, passed = passed, detail = detail });
            Debug.Log("[EntranceQA] " + name + " passed=" + passed + " " + detail);
        }
        private void OnLog(string message, string stack, LogType type)
        {
            if (type == LogType.Error || type == LogType.Exception || type == LogType.Assert) report.runtime_errors.Add(message);
        }
        private void Finish(string failure)
        {
            if (finished) return;
            finished = true;
            Application.logMessageReceived -= OnLog;
            report.failure = failure;
            report.finished_utc = DateTime.UtcNow.ToString("o");
            report.passed = string.IsNullOrEmpty(failure) && report.checks.Count > 0 && report.checks.All(check => check.passed) && report.runtime_errors.Count == 0;
            File.WriteAllText(Path.Combine(outputDirectory, "report.json"), JsonUtility.ToJson(report, true));
            Debug.Log("[EntranceQA] FINISHED passed=" + report.passed + " checks=" + report.checks.Count + " failure=" + failure);
            Application.Quit(report.passed ? 0 : 1);
        }
    }
}
