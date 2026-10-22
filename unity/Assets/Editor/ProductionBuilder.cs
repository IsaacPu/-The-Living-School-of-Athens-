using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Security.Cryptography;
using AthensProduction;
using AthensProduction.EditorTools;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
using UnityEngine.SceneManagement;

public static class ProductionBuilder
{
    private const string ScenePath = "Assets/Scenes/ProductionSample.unity";
    private const string Generated = "Assets/_Project/Environment/Generated";
    private static Transform architecture;
    private static Material stone, pale, trim, recess, red, joint;
    private static SceneParameters spec;
    private static readonly Dictionary<string, Mesh> meshes = new Dictionary<string, Mesh>();

    [Serializable] private sealed class Delivery
    {
        public int schema_version, triangles, skins, animations;
        public string asset_id, relative_glb_path, sha256, units, up_axis, forward_axis, technical_status, art_status;
        public long bytes;
        public bool orientation_verified;
        public float body_height_m;
    }

    [Serializable] private sealed class ImportRecord
    {
        public string schema = "athens.character-import/1", delivery, source_glb, imported_glb, sha256, art_status;
        public long bytes;
        public float body_height_m, placement_yaw_degrees;
        public bool scale_applied = false, importer_rotation_applied = false;
    }
    [Serializable] private sealed class GenerationRecord
    {
        public string phase = "P0_structure_sample", scene, parameters, character_sha256, backend = "disabled";
        public int renderer_count, mesh_assets;
        public bool all_scene_dependencies_inside_project;
        public string[] scene_dependencies;
    }

    private static string ProductionRoot => Path.GetFullPath(Path.Combine(Application.dataPath, "../.."));

    [MenuItem("Athens Production/Create P0 sample")]
    public static void CreateScene()
    {
        meshes.Clear();
        Directory.CreateDirectory(Generated + "/Meshes");
        Directory.CreateDirectory(Generated + "/Materials");
        Directory.CreateDirectory("Assets/Scenes");
        Directory.CreateDirectory("Assets/Resources");
        var parameterPath = Path.Combine(ProductionRoot, "art/environment/architecture-parameters.json");
        spec = JsonUtility.FromJson<SceneParameters>(File.ReadAllText(parameterPath));
        File.Copy(parameterPath, "Assets/Resources/scene-parameters.json", true);
        ConfigureProject();
        var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
        RenderSettings.fog = false;
        RenderSettings.ambientMode = AmbientMode.Trilight;
        RenderSettings.ambientSkyColor = new Color(.65f, .72f, .8f);
        RenderSettings.ambientEquatorColor = new Color(.53f, .50f, .43f);
        RenderSettings.ambientGroundColor = new Color(.28f, .25f, .22f);
        stone = MaterialAsset("warm limestone", new Color(.70f, .65f, .52f), .18f);
        pale = MaterialAsset("ivory plaster", new Color(.76f, .76f, .70f), .12f);
        trim = MaterialAsset("carved edge stone", new Color(.73f, .72f, .61f), .20f);
        recess = MaterialAsset("coffer recess", new Color(.46f, .48f, .40f), .08f);
        red = MaterialAsset("muted porphyry inlay", new Color(.39f, .24f, .25f), .24f);
        joint = MaterialAsset("stone joint", new Color(.37f, .36f, .30f), .10f);
        architecture = new GameObject("Central longitudinal hall - editable generated modules").transform;
        BuildFloor();
        BuildHall();
        Light("Daylight", LightType.Directional, new Vector3(0, 9, 0), Quaternion.Euler(38, -28, 0), new Color(1, .97f, .90f), 1.1f, true);
        Light("Artistic central bounce", LightType.Point, new Vector3(0, 5.8f, 8), Quaternion.identity, new Color(.98f, .94f, .82f), 12, false, 18);
        Light("Soft face fill", LightType.Point, new Vector3(-1, 3.4f, -2.5f), Quaternion.identity, new Color(.85f, .90f, 1), 5, false, 7);
        var app = new GameObject("Athens Production Sample - single entry").AddComponent<ProductionSample>();
        app.parameters = spec;
        ImportCharacter(app);
        var visitor = new GameObject("Visitor - 1.65m eye height");
        app.visitor = visitor.AddComponent<CharacterController>();
        app.visitor.height = 1.75f; app.visitor.radius = .25f;
        app.visitor.center = new Vector3(0, .875f, 0);
        app.visitor.stepOffset = .27f; app.visitor.skinWidth = .025f; app.visitor.slopeLimit = 48;
        app.visitor.enabled = false;
        var cameraObject = new GameObject("Production visitor camera");
        cameraObject.transform.SetParent(visitor.transform, false);
        app.visitorCamera = cameraObject.AddComponent<Camera>();
        app.visitorCamera.tag = "MainCamera";
        app.visitorCamera.nearClipPlane = .05f; app.visitorCamera.farClipPlane = 100;
        app.visitorCamera.clearFlags = CameraClearFlags.SolidColor;
        app.visitorCamera.backgroundColor = new Color(.52f, .66f, .80f);
        app.visitorCamera.allowHDR = true;
        app.visitorCamera.allowMSAA = true;
        cameraObject.AddComponent<AudioListener>();
        cameraObject.AddComponent<UniversalAdditionalCameraData>().renderPostProcessing = false;
        app.SetView("hero");
        // Keep the few measured source meshes individually addressable in the Player.
        // Other environment modules still use static batching; geometry/placement is unchanged.
        foreach(var anchorObject in new[]{"Front coffered barrel closed stone shell","Middle sky aperture","Far nested arch","Upper platform"})
            GameObject.Find(anchorObject).isStatic=false;
        AssetDatabase.SaveAssets();
        EditorSceneManager.SaveScene(scene, ScenePath);
        EditorBuildSettings.scenes = new[] { new EditorBuildSettingsScene(ScenePath, true) };
        var dependencies = AssetDatabase.GetDependencies(ScenePath, true);
        if (dependencies.Any(path => !path.StartsWith("Assets/", StringComparison.Ordinal) && !path.StartsWith("Packages/", StringComparison.Ordinal)))
            throw new BuildFailedException("Scene has a dependency outside production Assets/Packages.");
        var report = new GenerationRecord { scene = ScenePath, parameters = "art/environment/architecture-parameters.json", renderer_count = UnityEngine.Object.FindObjectsByType<Renderer>(FindObjectsSortMode.None).Length, mesh_assets = meshes.Count, character_sha256 = app.characterSha256, all_scene_dependencies_inside_project = true, scene_dependencies = dependencies };
        File.WriteAllText(Path.Combine(ProductionRoot, "qa/environment/scene-generation.json"), JsonUtility.ToJson(report, true));
        Debug.Log("[AthensProduction] SCENE_CREATED scene=" + ScenePath + " renderers=" + UnityEngine.Object.FindObjectsByType<Renderer>(FindObjectsSortMode.None).Length + " meshes=" + meshes.Count);
    }

    private static void BuildFloor()
    {
        Box("Ground", new Vector3(0, -.16f, 7), new Vector3(24, .32f, 43), pale, .025f, true);
        var platformLength = spec.hall_back_z - spec.platform_front_z;
        Box("Upper platform", new Vector3(0, spec.platform_height / 2, spec.platform_front_z + platformLength / 2), new Vector3(20, spec.platform_height, platformLength), pale, .025f, true);
        for (var i = 0; i < 3; i++)
        {
            var height = spec.platform_height * (i + 1) / 4;
            var front = spec.platform_front_z - (3 - i) * .5f;
            Box("Stair tread " + i, new Vector3(0, height / 2, front + .25f), new Vector3(19 - i * .15f, height, .5f), pale, .025f, true);
            Box("Stair nosing " + i, new Vector3(0, height - .018f, front + .025f), new Vector3(19 - i * .15f, .04f, .07f), trim, .012f);
        }
        Box("Platform nosing", new Vector3(0, spec.platform_height - .018f, spec.platform_front_z + .03f), new Vector3(20, .04f, .08f), trim, .01f);
        for (int x = -4; x <= 4; x++)
            for (int z = -3; z <= 11; z++)
            {
                float centerZ = z * 2.4f + .8f;
                if (centerZ > -3.1f && centerZ < .9f) continue;
                float y = centerZ < spec.platform_front_z ? .006f : spec.platform_height + .006f;
                var center = new Vector3(x * 2.15f, y, centerZ);
                Box("Porphyry frame", center, new Vector3(1.87f, .012f, 1.94f), red, .002f);
                Box("Ivory inset", center + Vector3.up * .008f, new Vector3(1.48f, .014f, 1.56f), pale, .002f);
                Box("Inner stone panel", center + Vector3.up * .017f, new Vector3(1.19f, .01f, 1.27f), stone, .002f);
            }
        for (int side = -1; side <= 1; side += 2)
        {
            Box("Side boundary wall", new Vector3(side * 11.5f, 3.7f, 9), new Vector3(.4f, 7.4f, 36), stone, .04f, true);
            Box("Boundary base molding", new Vector3(side * 11.17f, .3f, 9), new Vector3(.25f, .4f, 36), trim, .035f);
            Box("Entry side boundary continuation",new Vector3(side*11.5f,2.8f,-11.4f),new Vector3(.4f,5.6f,6),stone,.03f,true);
        }
        Box("Front visitor boundary balustrade",new Vector3(0,.72f,-13.7f),new Vector3(23.4f,1.44f,.38f),stone,.04f,true);
        Box("Front boundary cap",new Vector3(0,1.46f,-13.7f),new Vector3(23.6f,.12f,.55f),trim,.025f);
        Box("Rear boundary", new Vector3(0, 3.4f, 30.1f), new Vector3(24, 5.2f, .35f), pale, .03f, true);
        // The far sky is a distant unlit plane. It is outside the reachable hall, not the original photo.
        var skyShader = Shader.Find("Universal Render Pipeline/Unlit");
        var skyMat = new Material(skyShader) { name = "original plain sky color" };
        skyMat.SetColor("_BaseColor", new Color(.48f, .64f, .84f));
        var skyPath = Generated + "/Materials/plain-sky.mat";
        var existing = AssetDatabase.LoadAssetAtPath<Material>(skyPath);
        if (existing == null) AssetDatabase.CreateAsset(skyMat, skyPath); else { EditorUtility.CopySerialized(skyMat, existing); UnityEngine.Object.DestroyImmediate(skyMat); skyMat = existing; }
        Box("Distant blue sky opening", new Vector3(0, 7, 29.8f), new Vector3(12, 12, .04f), skyMat, 0);
    }

    private static void BuildHall()
    {
        var p = spec;
        Vault("Front coffered barrel", p.front_vault_radius, p.front_vault_spring_y, p.front_vault_start_z, p.front_vault_end_z, p.coffer_angle_count, p.coffer_depth_count);
        Vault("Entry continuation", p.front_vault_radius, p.front_vault_spring_y, -3.8f, p.front_vault_start_z, p.coffer_angle_count, 6);
        Vault("Middle coffered barrel", p.middle_arch_radius, p.middle_arch_spring_y, p.front_vault_end_z + .4f, p.middle_arch_z, 11, 5);
        PortalWall("Cross hall transition", 5.9f, p.platform_height, p.middle_arch_spring_y, p.middle_arch_radius + .05f, 1, 11.8f, p.front_vault_end_z + .42f, .65f);
        PortalWall("Rear aperture wall", 5.8f, p.platform_height, p.far_arch_spring_y, p.far_arch_radius, p.far_arch_x_scale, 5.8f, p.far_arch_z + .28f, .65f);
        PortalWall("Entry return structure - design completion", 11.2f, 0, 4.8f, 4.8f, 1, 10.7f, -3.9f, .7f);
        Arch("Middle sky aperture", new Vector3(0, p.middle_arch_spring_y, p.middle_arch_z), p.middle_arch_radius, .36f, .65f, pale);
        var far = Arch("Far nested arch", new Vector3(0, p.far_arch_spring_y, p.far_arch_z), p.far_arch_radius, .35f, .8f, pale);
        far.transform.localScale = new Vector3(p.far_arch_x_scale, 1, 1);
        for (int side = -1; side <= 1; side += 2)
        {
            foreach (var z in new[] {p.front_vault_start_z, p.front_vault_end_z})
                Pier(new Vector3(side * (p.front_vault_radius + .68f), p.platform_height, z), p.front_vault_spring_y - p.platform_height, 1.35f, 1.6f, side);
            Pier(new Vector3(side * (p.middle_arch_radius + .5f), p.platform_height, p.middle_arch_z), p.middle_arch_spring_y - p.platform_height, 1f, 1.2f, side);
            Pier(new Vector3(side * (p.far_arch_radius * p.far_arch_x_scale + .35f), p.platform_height, p.far_arch_z), p.far_arch_spring_y - p.platform_height, .7f, .9f, side);
            Box("Side nave upper wall", new Vector3(side * 5.5f, 9.1f, 8), new Vector3(2.3f, 4.6f, 11), pale, .06f);
            Box("Longitudinal cornice", new Vector3(side * 4.13f, p.front_vault_spring_y -.06f, 8), new Vector3(.43f, .32f, 11.0f), trim, .035f);
            Box("Cornice fine bead", new Vector3(side * 3.99f, p.front_vault_spring_y -.26f, 8), new Vector3(.16f, .08f, 11.0f), pale, .02f);
            Niche(side);
            Box("Side aisle roof - design completion",new Vector3(side*7.8f,5.85f,10),new Vector3(4.4f,.35f,28),pale,.035f);
            // Side aisle has overhead lintels and visible back surfaces, with a clear walking strip.
            for (int z = 2; z <= 22; z += 5)
            {
                Pier(new Vector3(side * 9.9f, p.platform_height, z), 4.5f, .7f, .7f, side);
                Box("Side aisle ceiling lintel", new Vector3(side * 7.3f, 5.5f, z), new Vector3(4.7f, .4f, .8f), pale, .045f);
            }
        }
        // Cross-hall connector is intentionally open above the middle sky aperture.
        Box("Middle arch crown wall", new Vector3(0, p.middle_arch_spring_y + p.middle_arch_radius + .6f, p.middle_arch_z), new Vector3(7.4f, .85f, .65f), pale, .04f);
    }

    private static void PortalWall(string name, float halfWidth, float floor, float spring, float radius, float xScale, float top, float z, float depth)
    {
        float inner = radius * xScale;
        for(int side=-1;side<=1;side+=2)
            Box(name+" side masonry",new Vector3(side*(halfWidth+inner)/2,(floor+top)/2,z),new Vector3(halfWidth-inner,top-floor,depth),pale,.025f,true);
        string key="spandrel_"+radius+"_"+xScale+"_"+spring+"_"+top+"_"+depth;
        var mesh=CachedMesh(key,()=>Spandrel(radius,xScale,spring,top,depth));
        MeshObject(name+" arched masonry",new Vector3(0,0,z),mesh,pale,false,null);
        Box(name+" cornice",new Vector3(0,top+.08f,z-.15f),new Vector3(halfWidth*2+.1f,.18f,depth+.24f),trim,.025f);
    }

    private static Mesh Spandrel(float radius,float xScale,float spring,float top,float depth)
    {
        var vertices=new List<Vector3>();var triangles=new List<int>();var uv=new List<Vector2>();
        Action<Vector3,Vector3,Vector3,Vector3,Vector3> quad=(a,b,c,d,normal)=>
        {
            if(Vector3.Dot(Vector3.Cross(b-a,c-a),normal)<0){var temp=b;b=d;d=temp;}
            int index=vertices.Count;vertices.AddRange(new[]{a,b,c,d});
            foreach(var v in new[]{a,b,c,d})uv.Add(new Vector2(v.x,v.y));
            triangles.AddRange(new[]{index,index+1,index+2,index,index+2,index+3});
        };
        const int count=64;
        for(int i=0;i<count;i++)
        {
            float a=i*Mathf.PI/count,b=(i+1)*Mathf.PI/count;
            var loA=new Vector3(radius*xScale*Mathf.Cos(a),spring+radius*Mathf.Sin(a),-depth/2);
            var loB=new Vector3(radius*xScale*Mathf.Cos(b),spring+radius*Mathf.Sin(b),-depth/2);
            var hiA=new Vector3(loA.x,top,-depth/2);var hiB=new Vector3(loB.x,top,-depth/2);
            var dz=Vector3.forward*depth;
            quad(loA,loB,hiB,hiA,Vector3.back);quad(loB+dz,loA+dz,hiA+dz,hiB+dz,Vector3.forward);
            quad(loB,loA,loA+dz,loB+dz,new Vector3(-Mathf.Cos((a+b)/2),-Mathf.Sin((a+b)/2),0));
            quad(hiA,hiB,hiB+dz,hiA+dz,Vector3.up);
        }
        var mesh=new Mesh();mesh.SetVertices(vertices);mesh.SetTriangles(triangles,0);mesh.SetUVs(0,uv);mesh.RecalculateNormals();mesh.RecalculateBounds();return mesh;
    }

    private static void Pier(Vector3 bottom, float height, float width, float depth, int side)
    {
        Box("Pier structural core", bottom + Vector3.up * height / 2, new Vector3(width, height, depth), pale, .045f, true);
        Box("Pier plinth lower", bottom + Vector3.up * .12f, new Vector3(width + .3f, .24f, depth + .24f), stone, .035f);
        Box("Pier plinth upper", bottom + Vector3.up * .29f, new Vector3(width + .17f, .12f, depth + .1f), trim, .025f);
        Box("Capital lower neck", bottom + Vector3.up * (height - .22f), new Vector3(width + .12f, .13f, depth + .14f), trim, .025f);
        Box("Capital crown", bottom + Vector3.up * height, new Vector3(width + .43f, .22f, depth + .35f), pale, .045f);
        Box("Capital lip", bottom + Vector3.up * (height + .13f), new Vector3(width + .49f, .08f, depth + .42f), trim, .018f);
        // Shallow pilaster subdivisions add tangible profile detail without a unique texture.
        for (int strip = -1; strip <= 1; strip++)
            Box("Pilaster recessed flute", bottom + new Vector3(strip * width * .23f, height * .5f, -depth / 2 - .009f), new Vector3(width * .06f, height - .9f, .035f), stone, .015f);
    }

    private static void Niche(int side)
    {
        var x = side * 7.8f; var z = 4.2f;
        Box("Niche backing", new Vector3(x, 3.45f, z + .45f), new Vector3(3, 5.3f, .35f), stone, .04f, true);
        Box("Niche recessed panel", new Vector3(x, 3.7f, z + .23f), new Vector3(1.7f, 3.6f, .13f), recess, .03f);
        Box("Niche pedestal", new Vector3(x, 1.18f, z - .03f), new Vector3(2.1f, .7f, 1.05f), pale, .045f, true);
        for (int s = -1; s <= 1; s += 2)
            Box("Niche upright molding", new Vector3(x + s * 1.03f, 3.45f, z), new Vector3(.26f, 5.1f, .32f), trim, .03f);
        Arch("Niche crowning arch", new Vector3(x, 5.4f, z), .9f, .22f, .32f, trim);
        // Sculpture is deliberately absent in P0; no extra background figures are passed off as finished.
        for (int row = 0; row < 3; row++)
            Box("Pedestal panel division", new Vector3(x, 1.0f + row * .14f, z - .565f), new Vector3(1.72f, .025f, .035f), stone, .005f);
    }

    private static void Vault(string name, float radius, float spring, float startZ, float endZ, int angleCount, int depthCount)
    {
        Arch(name + " closed stone shell", new Vector3(0, spring, (startZ + endZ) / 2), radius, .35f, endZ - startZ, pale);
        Arch(name + " front profiled rib", new Vector3(0, spring, startZ), radius - .055f, .24f, .28f, trim);
        Arch(name + " rear profiled rib", new Vector3(0, spring, endZ), radius - .055f, .24f, .28f, trim);
        float step = Mathf.PI / angleCount, pitch = (endZ - startZ) / depthCount;
        float width = 2 * radius * Mathf.Sin(step / 2) * .84f;
        for (int a = 0; a < angleCount; a++)
            for (int d = 0; d < depthCount; d++)
            {
                float theta = (a + .5f) * step;
                var radial = new Vector3(Mathf.Cos(theta), Mathf.Sin(theta), 0);
                var tangent = new Vector3(-Mathf.Sin(theta), Mathf.Cos(theta), 0);
                var center = new Vector3(0, spring, startZ + (d + .5f) * pitch) + radial * (radius - .045f);
                var rotation = Quaternion.Euler(0, 0, theta * Mathf.Rad2Deg - 90);
                Box("Coffer recessed face", center, new Vector3(width, .035f, pitch * .79f), recess, .015f, false, rotation);
                var frameCenter = center - radial * .065f;
                for (int s = -1; s <= 1; s += 2)
                {
                    Box("Coffer side bevel", frameCenter + tangent * (s * width / 2), new Vector3(.075f, .1f, pitch * .88f), trim, .02f, false, rotation);
                    Box("Coffer end bevel", frameCenter + Vector3.forward * (s * pitch * .42f), new Vector3(width + .075f, .1f, .075f), trim, .02f, false, rotation);
                }
            }
    }

    private static GameObject Box(string name, Vector3 position, Vector3 size, Material material, float bevel, bool collision = false, Quaternion? rotation = null)
    {
        var key = "box_" + size.ToString("F4") + "_" + bevel.ToString("F4");
        return MeshObject(name, position, CachedMesh(key, () => ArchitectureMeshes.BeveledBox(size, bevel)), material, collision, rotation);
    }

    private static GameObject Arch(string name, Vector3 position, float radius, float thickness, float depth, Material material)
    {
        var key = "arch_" + radius.ToString("F4") + "_" + thickness.ToString("F4") + "_" + depth.ToString("F4");
        return MeshObject(name, position, CachedMesh(key, () => ArchitectureMeshes.Arch(radius, thickness, depth)), material, false, null);
    }

    private static GameObject MeshObject(string name, Vector3 position, Mesh mesh, Material material, bool collision, Quaternion? rotation)
    {
        var go = new GameObject(name, typeof(MeshFilter), typeof(MeshRenderer));
        go.transform.SetParent(architecture, false); go.transform.localPosition = position;
        if (rotation.HasValue) go.transform.localRotation = rotation.Value;
        go.GetComponent<MeshFilter>().sharedMesh = mesh;
        go.GetComponent<MeshRenderer>().sharedMaterial = material;
        go.isStatic = true;
        if (collision)
        {
            var box = go.AddComponent<BoxCollider>(); box.center = mesh.bounds.center; box.size = mesh.bounds.size;
        }
        return go;
    }

    private static Mesh CachedMesh(string key, Func<Mesh> create)
    {
        if (meshes.TryGetValue(key, out var mesh)) return mesh;
        var safe = key.Replace("(", "").Replace(")", "").Replace(",", "_").Replace(" ", "");
        var path = Generated + "/Meshes/" + safe + ".asset";
        var candidate = create(); candidate.name = safe;
        mesh = AssetDatabase.LoadAssetAtPath<Mesh>(path);
        if (mesh == null) { AssetDatabase.CreateAsset(candidate, path); mesh = candidate; }
        else { EditorUtility.CopySerialized(candidate, mesh); UnityEngine.Object.DestroyImmediate(candidate); }
        meshes[key] = mesh; return mesh;
    }

    private static Material MaterialAsset(string name, Color color, float smoothness)
    {
        var path = Generated + "/Materials/" + name.Replace(" ", "-") + ".mat";
        var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
        if (mat == null) { mat = new Material(Shader.Find("Universal Render Pipeline/Lit")); AssetDatabase.CreateAsset(mat, path); }
        mat.SetColor("_BaseColor", color); mat.SetFloat("_Metallic", 0); mat.SetFloat("_Smoothness", smoothness);
        mat.enableInstancing = true; EditorUtility.SetDirty(mat); return mat;
    }

    private static void Light(string name, LightType type, Vector3 position, Quaternion rotation, Color color, float intensity, bool shadows, float range = 10)
    {
        var light = new GameObject(name).AddComponent<Light>();
        light.type = type; light.transform.SetPositionAndRotation(position, rotation);
        light.color = color; light.intensity = intensity; light.range = range;
        light.shadows = shadows ? LightShadows.Soft : LightShadows.None;
        if (type == LightType.Directional) RenderSettings.sun = light;
    }

    private static void ImportCharacter(ProductionSample app)
    {
        var deliveryPath = Path.Combine(ProductionRoot, "art/characters/plato/v001/delivery.json");
        if (!File.Exists(deliveryPath)) throw new BuildFailedException("B delivery is not ready: " + deliveryPath);
        var delivery = JsonUtility.FromJson<Delivery>(File.ReadAllText(deliveryPath));
        if (delivery.schema_version != 1 || !delivery.orientation_verified || delivery.units != "meters" || delivery.up_axis != "+Y" || delivery.forward_axis != "+Z")
            throw new BuildFailedException("Character delivery coordinate contract is not verified.");
        var source = Path.GetFullPath(Path.Combine(Path.GetDirectoryName(deliveryPath), delivery.relative_glb_path));
        var characterRoot = Path.GetFullPath(Path.Combine(ProductionRoot, "art/characters")) + Path.DirectorySeparatorChar;
        if (!source.StartsWith(characterRoot, StringComparison.OrdinalIgnoreCase)) throw new BuildFailedException("Character path escapes production art/characters.");
        string digest;
        using (var algorithm = SHA256.Create()) using (var stream = File.OpenRead(source)) digest = BitConverter.ToString(algorithm.ComputeHash(stream)).Replace("-", "").ToLowerInvariant();
        if (new FileInfo(source).Length != delivery.bytes || digest != delivery.sha256.ToLowerInvariant()) throw new BuildFailedException("B delivery bytes/hash do not match.");
        const string target = "Assets/_Project/Characters/plato-v001.glb";
        File.Copy(source, target, true);
        AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
        AssetDatabase.ImportAsset(target, ImportAssetOptions.ForceUpdate | ImportAssetOptions.ForceSynchronousImport);
        var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(target);
        if (prefab == null) throw new BuildFailedException("glTFast did not produce a character prefab.");
        var instance = (GameObject)PrefabUtility.InstantiatePrefab(prefab);
        instance.name = "Plato v001 - " + delivery.art_status;
        var root = new GameObject("Plato placement - one scene yaw only");
        instance.transform.SetParent(root.transform, false);
        root.transform.SetPositionAndRotation(spec.plato_position, Quaternion.Euler(0, spec.plato_yaw, 0));
        root.AddComponent<CharacterMarker>();
        var collider = root.AddComponent<CapsuleCollider>(); collider.height = delivery.body_height_m; collider.radius = .29f;
        collider.center = Vector3.up * delivery.body_height_m / 2;
        var renderers = instance.GetComponentsInChildren<Renderer>();
        if (renderers.Length == 0 || renderers.Any(r => r.sharedMaterials.Any(m => m == null || m.shader == null || !m.shader.isSupported))) throw new BuildFailedException("Imported character renderer/material is invalid.");
        app.character = root.transform; app.characterBodyHeight = delivery.body_height_m;
        app.characterSha256 = digest; app.characterStatus = delivery.art_status;
        app.characterAssetPath = target;
        var record = new ImportRecord { delivery = "art/characters/plato/v001/delivery.json", source_glb = Path.GetRelativePath(ProductionRoot, source).Replace('\\', '/'), imported_glb = target, sha256 = digest, bytes = delivery.bytes, body_height_m = delivery.body_height_m, placement_yaw_degrees = spec.plato_yaw, art_status = delivery.art_status };
        File.WriteAllText(Path.Combine(ProductionRoot, "qa/environment/character-import.json"), JsonUtility.ToJson(record, true));
        Debug.Log("[AthensProduction] CHARACTER_IMPORTED hash=" + digest + " rotation=scene_only scale=unchanged art=" + delivery.art_status);
    }

    private static void ConfigureProject()
    {
        PlayerSettings.companyName = "Athens Studio";
        PlayerSettings.productName = "The Academy - Production Sample";
        PlayerSettings.defaultScreenWidth = 1440; PlayerSettings.defaultScreenHeight = 1080;
        PlayerSettings.fullScreenMode = FullScreenMode.Windowed; PlayerSettings.runInBackground = true;
        PlayerSettings.resizableWindow = true; PlayerSettings.colorSpace = ColorSpace.Linear;
        PlayerSettings.insecureHttpOption = InsecureHttpOption.NotAllowed;
        PlayerSettings.strictShaderVariantMatching = true;
        PlayerSettings.SetScriptingBackend(NamedBuildTarget.Standalone, ScriptingImplementation.Mono2x);
        PlayerSettings.SetUseDefaultGraphicsAPIs(BuildTarget.StandaloneWindows64, false);
        PlayerSettings.SetGraphicsAPIs(BuildTarget.StandaloneWindows64, new[] {GraphicsDeviceType.Direct3D11});
        var playerSettings = new SerializedObject(AssetDatabase.LoadAllAssetsAtPath("ProjectSettings/ProjectSettings.asset")[0]);
        var input = playerSettings.FindProperty("activeInputHandler"); if (input != null) { input.intValue = 0; playerSettings.ApplyModifiedPropertiesWithoutUndo(); }
        Directory.CreateDirectory("Assets/Settings");
        var renderer = AssetDatabase.LoadAssetAtPath<UniversalRendererData>("Assets/Settings/ProductionRenderer.asset");
        if (renderer == null) { renderer = ScriptableObject.CreateInstance<UniversalRendererData>(); AssetDatabase.CreateAsset(renderer, "Assets/Settings/ProductionRenderer.asset"); }
        var pipeline = AssetDatabase.LoadAssetAtPath<UniversalRenderPipelineAsset>("Assets/Settings/ProductionURP.asset");
        if (pipeline == null) { pipeline = UniversalRenderPipelineAsset.Create(renderer); AssetDatabase.CreateAsset(pipeline, "Assets/Settings/ProductionURP.asset"); }
        pipeline.renderScale = 1; pipeline.msaaSampleCount = 2; pipeline.shadowDistance = 35;
        var pipelineSettings = new SerializedObject(pipeline);
        var softShadows = pipelineSettings.FindProperty("m_SoftShadowsSupported");
        if (softShadows != null) { softShadows.boolValue = true; pipelineSettings.ApplyModifiedPropertiesWithoutUndo(); }
        pipeline.mainLightShadowmapResolution = 2048;
        GraphicsSettings.defaultRenderPipeline = pipeline; QualitySettings.renderPipeline = pipeline;
        QualitySettings.vSyncCount = 0; QualitySettings.shadows = UnityEngine.ShadowQuality.All;
        var globalType = AppDomain.CurrentDomain.GetAssemblies().Select(a => a.GetType("UnityEngine.Rendering.Universal.UniversalRenderPipelineGlobalSettings")).FirstOrDefault(t => t != null);
        var ensure = globalType?.GetMethod("Ensure", System.Reflection.BindingFlags.Static | System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.NonPublic, null, new[] {typeof(bool)}, null);
        ensure?.Invoke(null, new object[] {true});
        AssetDatabase.SaveAssets();
    }

    [MenuItem("Athens Production/Build Windows P0")]
    public static void BuildWindows()
    {
        CreateScene();
        var output = Environment.GetEnvironmentVariable("ATHENS_PRODUCTION_BUILD");
        if (string.IsNullOrEmpty(output)) output = Path.GetFullPath("Builds/P0");
        Directory.CreateDirectory(output);
        var build = BuildPipeline.BuildPlayer(new BuildPlayerOptions { scenes = new[] {ScenePath}, locationPathName = Path.Combine(output, "AthensProduction.exe"), target = BuildTarget.StandaloneWindows64, options = BuildOptions.None });
        var summary = build.summary;
        Debug.Log("[AthensProduction] BUILD_RESULT result=" + summary.result + " errors=" + summary.totalErrors + " warnings=" + summary.totalWarnings + " bytes=" + summary.totalSize);
        File.WriteAllText(Path.Combine(ProductionRoot, "qa/environment/build-result.json"), "{\"result\":\"" + summary.result + "\",\"errors\":" + summary.totalErrors + ",\"warnings\":" + summary.totalWarnings + ",\"bytes\":" + summary.totalSize + "}");
        if (summary.result != BuildResult.Succeeded) throw new BuildFailedException("Production build failed.");
    }
}
