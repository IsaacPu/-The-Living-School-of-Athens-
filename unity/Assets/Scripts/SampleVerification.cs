using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEngine;
using UnityEngine.Rendering;

namespace AthensProduction
{
    public sealed class SampleVerification : MonoBehaviour
    {
        public string outputDirectory;
        [Serializable] private sealed class Check { public string name, detail; public bool passed; }
        [Serializable] private sealed class Anchor
        {
            public string id;
            public string source_object, source_mesh, feature, sampling;
            public int vertex_index = -1, second_vertex_index = -1, vertex_count;
            public Vector3 local_vertex, second_local_vertex;
            public Bounds actual_renderer_bounds;
            public Vector3 world;
            public Vector2 reference_uv_top, actual_uv_top;
            public float error_fraction_of_width;
        }
        [Serializable] private sealed class ImageInfo { public string file; public int width, height, dark_pixels, pink_pixels, quantized_colors; }
        [Serializable] private sealed class RoutePoint { public Vector3 target, actual; public float horizontal_error, vertical_error; public bool passed; }
        [Serializable] private sealed class Report
        {
            public string stage = "P0_structure_and_integration", started_utc, finished_utc, unity_version, graphics_device, character_sha256, character_art_status, failure = "";
            public string scope = "Independent Windows Player. Actual saved meshes/materials, GPU camera renders, projected reference anchors and CharacterController collision route. No real mouse/keyboard simulation, no finished art/LLM/animation claim.";
            public string screenshot_source = "Same Player camera rendered through URP StandardRequest; GPU offscreen images do not prove physical window presentation.";
            public string reference_measurement = "Manual annotation of original reference, approximately +/-8 pixels; crop [128,128,1024,768] fixed before first build. Outer decorated frame is outside P0.";
            public bool passed;
            public List<Check> checks = new List<Check>();
            public List<Anchor> anchors = new List<Anchor>();
            public List<ImageInfo> images = new List<ImageInfo>();
            public List<RoutePoint> route = new List<RoutePoint>();
            public List<string> runtime_errors = new List<string>();
            public float route_max_ground_error, average_fps, p95_frame_ms;
            public int frame_count;
            public Vector3 return_reference_eye, return_reached_eye;
            public float return_eye_error;
        }
        private readonly Report report = new Report();
        private readonly List<float> frameTimes = new List<float>();
        private ProductionSample sample;
        private float started;
        private bool finished, sampling;

        private IEnumerator Start()
        {
            started = Time.realtimeSinceStartup;
            sample = GetComponent<ProductionSample>();
            Directory.CreateDirectory(outputDirectory);
            report.started_utc = DateTime.UtcNow.ToString("o");
            report.unity_version = Application.unityVersion;
            report.graphics_device = SystemInfo.graphicsDeviceType + " / " + SystemInfo.graphicsDeviceName;
            report.character_sha256 = sample.characterSha256; report.character_art_status = sample.characterStatus;
            Application.logMessageReceived += OnLog;
            var iterator = Verify();
            while (!finished)
            {
                object next = null; bool more = false; string error = null;
                try { more = iterator.MoveNext(); if (more) next = iterator.Current; }
                catch (Exception exception) { error = exception.ToString(); }
                if (error != null) { Finish(error); yield break; }
                if (!more) { Finish(""); yield break; }
                yield return next;
            }
        }
        private void Update()
        {
            if (sampling && Time.unscaledDeltaTime > 0) frameTimes.Add(Time.unscaledDeltaTime);
            if (!finished && Time.realtimeSinceStartup - started > 150) Finish("Verification timed out.");
        }
        private IEnumerator Verify()
        {
            yield return null; yield return null;
            CheckResult("single_entry", FindObjectsByType<ProductionSample>(FindObjectsSortMode.None).Length == 1, "Exactly one explicit production sample; no test Bootstrap.");
            CheckResult("urp", GraphicsSettings.currentRenderPipeline != null && GraphicsSettings.currentRenderPipeline.GetType().Name.Contains("UniversalRenderPipelineAsset"), "Actual rendering pipeline.");
            CheckResult("production_identity", Application.companyName == "Athens Studio" && Application.productName == "The Academy - Production Sample", Application.companyName + " / " + Application.productName);
            CheckResult("actual_character", sample.character != null && !string.IsNullOrEmpty(sample.characterSha256), sample.characterStatus + " / " + sample.characterSha256);
            var renderers = sample.character.GetComponentsInChildren<Renderer>();
            CheckResult("character_materials", renderers.Length > 0 && renderers.All(r => r.sharedMaterials.Length > 0 && r.sharedMaterials.All(m => m != null && m.shader != null && m.shader.isSupported && m.shader.name != "Hidden/InternalErrorShader")), "Every actual character material has a supported shader.");
            var textures = renderers.SelectMany(r=>r.sharedMaterials).SelectMany(m=>m.GetTexturePropertyNames().Select(name=>m.GetTexture(name))).Where(t=>t!=null).Distinct().ToArray();
            CheckResult("character_embedded_textures", textures.Length >= 2 && textures.All(t=>t.width>=1024 && t.height>=1024), "Actual character texture count="+textures.Length+" sizes="+string.Join(",",textures.Select(t=>t.width+"x"+t.height)));
            var bounds = renderers[0].bounds; foreach (var renderer in renderers) bounds.Encapsulate(renderer.bounds);
            CheckResult("feet_on_platform", Mathf.Abs(bounds.min.y - sample.parameters.platform_height) < .025f, "mesh_min_y=" + bounds.min.y + " platform=" + sample.parameters.platform_height);
            CheckResult("no_import_rescale", Vector3.Distance(sample.character.localScale,Vector3.one)<.0001f && Mathf.Abs(bounds.size.y-sample.characterBodyHeight)<.005f, "Actual renderer height="+bounds.size.y+" delivery="+sample.characterBodyHeight+"; P0 source has no raised arm.");
            var importedRoot=sample.character.GetChild(0);
            CheckResult("imported_root_transform",Vector3.Distance(importedRoot.localScale,Vector3.one)<.0001f && Quaternion.Angle(importedRoot.localRotation,Quaternion.identity)<.01f,"Imported prefab root scale="+importedRoot.localScale+" rotation="+importedRoot.localRotation.eulerAngles+"; visual front/side/back review also required.");
            CheckResult("facing_viewer", Vector3.Dot(sample.character.forward, Vector3.back) > .999f, "One scene yaw maps canonical +Z to world -Z; importer applies none.");
            var front=GameObject.Find("Front coffered barrel closed stone shell");var middle=GameObject.Find("Middle coffered barrel closed stone shell");var far=GameObject.Find("Far nested arch");
            CheckResult("longitudinal_geometry",front!=null&&middle!=null&&far!=null&&front.GetComponent<MeshFilter>().sharedMesh.vertexCount>0&&middle.GetComponent<MeshFilter>().sharedMesh.vertexCount>0&&far.GetComponent<MeshFilter>().sharedMesh.vertexCount>0&&front.transform.position.z<middle.transform.position.z&&middle.transform.position.z<far.transform.position.z,"Actual saved mesh objects exist in increasing Z order.");
            sample.SetView("hero"); sample.SetHeroProjection(4f/3f);
            var p = sample.parameters;
            AddArchAnchor("middle_sky_apex","Middle sky aperture","crown",false,new Vector2(.5098f,.3359f));
            AddArchAnchor("far_arch_apex","Far nested arch","crown",false,new Vector2(.5117f,.4570f));
            AddArchAnchor("far_spring_left","Far nested arch","left",false,new Vector2(.4541f,.5247f));
            AddArchAnchor("far_spring_right","Far nested arch","right",false,new Vector2(.5684f,.5247f));
            AddPlatformAnchor(new Vector2(.5440f,.7526f));
            AddBoundsAnchor("plato_crown",renderers,bounds,true,new Vector2(.4775f,.5273f));
            AddBoundsAnchor("plato_support",renderers,bounds,false,new Vector2(.4795f,.7422f));
            AddArchAnchor("front_vault_rear_crown","Front coffered barrel closed stone shell","crown",true,new Vector2(.5000f,.1211f));
            AddArchAnchor("front_vault_rear_spring_left","Front coffered barrel closed stone shell","left",true,new Vector2(.3428f,.3073f));
            AddArchAnchor("front_vault_rear_spring_right","Front coffered barrel closed stone shell","right",true,new Vector2(.6563f,.3073f));
            CheckResult("anchors_bound_to_actual_geometry",report.anchors.All(a=>!string.IsNullOrEmpty(a.source_object)&&(a.vertex_index>=0||a.sampling=="actual Renderer bounds")),"Every point is derived from an actual saved mesh vertex/edge or actual imported Renderer bounds, with object/mesh identity.");
            CheckResult("anchor_projection_within_3pct_width", report.anchors.All(a=>a.error_fraction_of_width <= .03f), "Projected world features vs manually annotated painting crop; geometric gate only, not an art verdict.");
            yield return null;
            Capture("hero.png",1600,1200);
            foreach(var view in new[]{"close","side","return"})
            {
                sample.SetView(view); yield return null;
                Capture(view+".png",1600,1200);
            }
            sample.SetView("return");
            report.return_reference_eye=sample.visitorCamera.transform.position;
            var returnRotation=sample.visitorCamera.transform.rotation;
            // First-hit rays test actual geometry occlusion; no through-wall target selection.
            sample.SetView("close"); Physics.SyncTransforms();
            var center = sample.character.position + Vector3.up * (sample.characterBodyHeight*.55f);
            var ray = new Ray(sample.visitorCamera.transform.position, (center-sample.visitorCamera.transform.position).normalized);
            bool hit = Physics.Raycast(ray,out var result,4);
            CheckResult("near_character_first_hit", hit && result.collider.GetComponentInParent<CharacterMarker>()!=null, hit ? result.collider.name : "no hit");
            bool rangeHit = Physics.Raycast(new Ray(center+Vector3.back*6,Vector3.forward),out var farHit,4);
            CheckResult("range_limit", !rangeHit || farHit.collider.GetComponentInParent<CharacterMarker>()==null,"Target beyond four meters is not picked.");
            sample.BeginRoaming();
            for(int f=0;f<30;f++){sample.Drive(Vector3.zero,1f/60); yield return null;}
            sampling = true;
            var targets = new[]{new Vector3(0,0,-2.8f),new Vector3(0,.2f,-1.7f),new Vector3(0,.6f,-.7f),new Vector3(0,.8f,.8f),new Vector3(1.8f,.8f,1.2f),new Vector3(1.8f,.8f,5.5f),new Vector3(0,.8f,8),new Vector3(-2.4f,.8f,5.5f),new Vector3(-2.4f,.8f,1),new Vector3(0,.8f,.6f),new Vector3(0,0,-3.2f)};
            foreach(var target in targets)
            {
                int frames=0;
                while(frames++<400)
                {
                    var delta=target-sample.visitor.transform.position; delta.y=0;
                    if(delta.magnitude<(target.z==8?.015f:.09f)) break;
                    sample.Drive(delta.normalized*Mathf.Min(1.8f,delta.magnitude*12),1f/60);
                    float floor=FloorHeight(sample.visitor.transform.position.z);
                    report.route_max_ground_error=Mathf.Max(report.route_max_ground_error,Mathf.Abs(sample.visitor.transform.position.y-floor));
                    yield return null;
                }
                var actual=sample.visitor.transform.position; var difference=actual-target; difference.y=0;
                var verticalError=Mathf.Abs(actual.y-target.y);
                var point=new RoutePoint{target=target,actual=actual,horizontal_error=difference.magnitude,vertical_error=verticalError,passed=difference.magnitude<.15f && verticalError<.08f};
                report.route.Add(point);
                CheckResult("route_"+report.route.Count,point.passed,"target="+target+" actual="+actual+" error="+difference.magnitude);
                if(target.z==8)
                {
                    for(int f=0;f<15;f++){sample.Drive(Vector3.zero,1f/60);yield return null;}
                    report.return_reached_eye=sample.visitorCamera.transform.position;
                    report.return_eye_error=Vector3.Distance(report.return_reached_eye,report.return_reference_eye);
                    CheckResult("return_camera_reached_continuously",report.return_eye_error<.05f,"Actual controller eye="+report.return_reached_eye+" preset="+report.return_reference_eye+" delta_m="+report.return_eye_error+"; no teleport in route.");
                    sample.visitorCamera.transform.rotation=returnRotation;
                    sample.visitorCamera.fieldOfView=55;
                    Capture("return-reached.png",1600,1200);
                    sample.visitorCamera.fieldOfView=57;
                }
            }
            CheckResult("stairs_reached_upper_platform",report.route.Count>3 && report.route[3].actual.y>.70f,"CharacterController moved continuously from ground through actual stair colliders.");
            CheckResult("continuous_ground_height",report.route_max_ground_error<.28f,"Maximum stair-transition support delta="+report.route_max_ground_error+"m; step rise is 0.20m and capsule skin is 0.025m.");
            CheckResult("descending_returns_to_ground",report.route.Count==targets.Length&&Mathf.Abs(report.route[report.route.Count-1].actual.y)<.08f,"Actual descent endpoint is near ground level.");
            // Adversarial wall test: continuously push toward the outer wall, do not teleport through it.
            sample.visitor.enabled=false; sample.visitor.transform.position=new Vector3(10.6f,.82f,8); sample.visitor.enabled=true; Physics.SyncTransforms();
            for(int f=0;f<70;f++){sample.Drive(Vector3.right*2,1f/60);yield return null;}
            CheckResult("wall_blocks_motion",sample.visitor.transform.position.x<11.1f,"After continuous push x="+sample.visitor.transform.position.x+"; teleport before this separate wall test is not part of route evidence.");
            sampling=false;
            if(frameTimes.Count>0)
            {
                frameTimes.Sort(); report.frame_count=frameTimes.Count; report.average_fps=frameTimes.Count/frameTimes.Sum(); report.p95_frame_ms=frameTimes[Mathf.Min(frameTimes.Count-1,(int)(frameTimes.Count*.95f))]*1000;
            }
            CheckResult("runtime_errors",report.runtime_errors.Count==0,"Error/Exception/Assert count="+report.runtime_errors.Count);
        }
        private float FloorHeight(float z)
        {
            float front=sample.parameters.platform_front_z;
            if(z>=front)return .8f;
            if(z>=front-.5f)return .6f;
            if(z>=front-1)return .4f;
            if(z>=front-1.5f)return .2f;
            return 0;
        }
        private void AddArchAnchor(string id,string objectName,string feature,bool rear,Vector2 reference)
        {
            var source=GameObject.Find(objectName);var mesh=source.GetComponent<MeshFilter>().sharedMesh;
            if(!mesh.isReadable)throw new InvalidOperationException("Measured mesh must retain readable vertices: "+objectName);
            var vertices=mesh.vertices;
            var candidates=Enumerable.Range(0,vertices.Length).Where(i=>feature=="crown"?Mathf.Abs(vertices[i].x)<.0001f:Mathf.Abs(vertices[i].y)<.0001f&&(feature=="left"?vertices[i].x<0:vertices[i].x>0)).ToArray();
            if(candidates.Length==0)throw new InvalidOperationException("No actual mesh feature: "+objectName+" "+feature);
            float inner=candidates.Min(i=>feature=="crown"?vertices[i].y:Mathf.Abs(vertices[i].x));
            candidates=candidates.Where(i=>Mathf.Abs((feature=="crown"?vertices[i].y:Mathf.Abs(vertices[i].x))-inner)<.0001f).ToArray();
            int index=rear?candidates.OrderByDescending(i=>vertices[i].z).First():candidates.OrderBy(i=>vertices[i].z).First();
            AddAnchor(new Anchor{id=id,world=source.transform.TransformPoint(vertices[index]),source_object=Hierarchy(source.transform),source_mesh=mesh.name,feature=feature,sampling=rear?"actual inner edge vertex at rear bevel":"actual inner edge vertex at front bevel",vertex_index=index,vertex_count=vertices.Length,local_vertex=vertices[index]},reference);
        }
        private void AddPlatformAnchor(Vector2 reference)
        {
            var source=GameObject.Find("Upper platform");var mesh=source.GetComponent<MeshFilter>().sharedMesh;var vertices=mesh.vertices;
            float frontZ=vertices.Min(v=>v.z);
            var candidates=Enumerable.Range(0,vertices.Length).Where(i=>Mathf.Abs(vertices[i].z-frontZ)<.0001f).ToArray();
            float top=candidates.Max(i=>vertices[i].y);candidates=candidates.Where(i=>Mathf.Abs(vertices[i].y-top)<.0001f).ToArray();
            int left=candidates.OrderBy(i=>vertices[i].x).First(),right=candidates.OrderByDescending(i=>vertices[i].x).First();
            AddAnchor(new Anchor{id="platform_front",world=source.transform.TransformPoint((vertices[left]+vertices[right])/2),source_object=Hierarchy(source.transform),source_mesh=mesh.name,feature="front face upper edge midpoint",sampling="midpoint of two actual beveled mesh edge vertices",vertex_index=left,second_vertex_index=right,vertex_count=vertices.Length,local_vertex=vertices[left],second_local_vertex=vertices[right]},reference);
        }
        private void AddBoundsAnchor(string id,Renderer[] renderers,Bounds bounds,bool top,Vector2 reference)
        {
            AddAnchor(new Anchor{id=id,world=new Vector3(bounds.center.x,top?bounds.max.y:bounds.min.y,bounds.center.z),source_object=string.Join(";",renderers.Select(r=>Hierarchy(r.transform))),source_mesh="actual imported renderer union",feature=top?"actual bounds top center":"actual bounds bottom center",sampling="actual Renderer bounds",actual_renderer_bounds=bounds},reference);
        }
        private static string Hierarchy(Transform target){return target.parent==null?target.name:Hierarchy(target.parent)+"/"+target.name;}
        private void AddAnchor(Anchor anchor,Vector2 reference)
        {
            var v=sample.visitorCamera.WorldToViewportPoint(anchor.world);var actual=new Vector2(v.x,1-v.y);var d=actual-reference;
            anchor.reference_uv_top=reference;anchor.actual_uv_top=actual;anchor.error_fraction_of_width=Mathf.Sqrt(d.x*d.x+d.y*d.y*.75f*.75f);
            report.anchors.Add(anchor);
        }
        private void Capture(string file,int width,int height)
        {
            var camera=sample.visitorCamera;var previous=RenderTexture.active;var oldTarget=camera.targetTexture;float aspect=camera.aspect;
            var target=new RenderTexture(width,height,24,RenderTextureFormat.ARGB32,RenderTextureReadWrite.sRGB);target.Create();
            Texture2D texture=null;
            try
            {
                camera.aspect=(float)width/height;
                if(sample.currentView=="hero")sample.SetHeroProjection(camera.aspect);
                var request=new RenderPipeline.StandardRequest{destination=target};
                if(!RenderPipeline.SupportsRenderRequest(camera,request))throw new InvalidOperationException("URP StandardRequest is unsupported.");
                RenderPipeline.SubmitRenderRequest(camera,request);RenderTexture.active=target;
                texture=new Texture2D(width,height,TextureFormat.RGB24,false);
                texture.ReadPixels(new Rect(0,0,width,height),0,0,false);texture.Apply(false);
                File.WriteAllBytes(Path.Combine(outputDirectory,file),texture.EncodeToPNG());
                var colors=texture.GetPixels32();var bins=new HashSet<int>();int dark=0,pink=0;
                foreach(var c in colors){if(c.r+c.g+c.b<18)dark++;if(c.r>180&&c.b>180&&c.g<80)pink++;bins.Add(((c.r>>3)<<10)|((c.g>>3)<<5)|(c.b>>3));}
                report.images.Add(new ImageInfo{file=file,width=width,height=height,dark_pixels=dark,pink_pixels=pink,quantized_colors=bins.Count});
                CheckResult("image_"+file,dark<colors.Length*.95f&&pink<colors.Length*.01f&&bins.Count>100,"GPU pixels colors="+bins.Count+" dark="+dark+" pink="+pink+"; requires visual review.");
            }
            finally{RenderTexture.active=previous;camera.targetTexture=oldTarget;camera.aspect=aspect;target.Release();Destroy(target);if(texture!=null)Destroy(texture);}
        }
        private void CheckResult(string name,bool passed,string detail){report.checks.Add(new Check{name=name,passed=passed,detail=detail});Debug.Log("[ProductionQA] "+name+" passed="+passed+" "+detail);}
        private void OnLog(string message,string stack,LogType type){if(type==LogType.Error||type==LogType.Exception||type==LogType.Assert)report.runtime_errors.Add(message);}
        private void Finish(string failure)
        {
            if(finished)return;finished=true;Application.logMessageReceived-=OnLog;
            report.failure=failure;report.finished_utc=DateTime.UtcNow.ToString("o");report.passed=string.IsNullOrEmpty(failure)&&report.checks.All(c=>c.passed)&&report.runtime_errors.Count==0;
            File.WriteAllText(Path.Combine(outputDirectory,"verification.json"),JsonUtility.ToJson(report,true));
            Debug.Log("[ProductionQA] FINISHED passed="+report.passed+" checks="+report.checks.Count+" failure="+failure);
            Application.Quit(report.passed?0:1);
        }
    }
}
