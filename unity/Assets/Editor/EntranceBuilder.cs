using System;
using System.IO;
using System.Linq;
using AthensProduction;
using AthensProduction.EditorTools;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.SceneManagement;

public static class EntranceBuilder
{
    private const string ScenePath = "Assets/Scenes/EntranceSample.unity";
    private const string TexturePath = "Assets/_Project/Entrance/Textures/raphael-school-of-athens-pd.jpg";
    private const string Generated = "Assets/_Project/Entrance/Generated";
    private static string Root => Path.GetFullPath(Path.Combine(Application.dataPath, "../.."));
    [Serializable] private sealed class Generation
    {
        public string phase = "A-P1_entrance_graybox", scene = ScenePath, character_sha256;
        public string source = "art/environment/entrance/source/source.json";
        public string scope = "One research gallery and P0 academy. No measured museum replica or seamless crowd reconstruction claim.";
        public string[] dependencies;
        public float mural_width, mural_height, duration_seconds;
    }
    [Serializable] private sealed class BuildRecord
    {
        public string result, executable, unity_version;
        public int errors, warnings;
        public ulong bytes;
    }

    [MenuItem("Athens Production/Create P1 entrance")]
    public static void CreateScene()
    {
        Directory.CreateDirectory(Path.Combine(Root, "qa/environment/entrance"));
        var sample = ProductionBuilder.CreateArchitectureForEntrance();
        Directory.CreateDirectory(Generated + "/Materials");
        AssetDatabase.Refresh();
        var importer = AssetImporter.GetAtPath(TexturePath) as TextureImporter;
        if (importer == null) throw new BuildFailedException("Public-domain mural texture is missing.");
        importer.textureType = TextureImporterType.Default;
        importer.npotScale = TextureImporterNPOTScale.None;
        importer.maxTextureSize = 4096;
        importer.wrapMode = TextureWrapMode.Clamp;
        importer.filterMode = FilterMode.Trilinear;
        importer.mipmapEnabled = true;
        importer.SaveAndReimport();
        var texture = AssetDatabase.LoadAssetAtPath<Texture2D>(TexturePath);
        var material = AssetDatabase.LoadAssetAtPath<Material>(Generated + "/Materials/public-domain-mural.mat");
        if (material == null)
        {
            material = new Material(Shader.Find("Universal Render Pipeline/Unlit"));
            AssetDatabase.CreateAsset(material, Generated + "/Materials/public-domain-mural.mat");
        }
        material.SetTexture("_BaseMap", texture);
        material.SetTextureScale("_BaseMap", new Vector2(1, 2388f / 2964));
        material.SetTextureOffset("_BaseMap", new Vector2(0, 1 - 2388f / 2964));
        material.SetColor("_BaseColor", Color.white);
        material.SetFloat("_Surface", 1);
        material.SetFloat("_Blend", 0);
        material.SetFloat("_SrcBlend", (float)BlendMode.SrcAlpha);
        material.SetFloat("_DstBlend", (float)BlendMode.OneMinusSrcAlpha);
        material.SetFloat("_SrcBlendAlpha", (float)BlendMode.One);
        material.SetFloat("_DstBlendAlpha", (float)BlendMode.OneMinusSrcAlpha);
        material.SetFloat("_ZWrite", 0);
        material.SetOverrideTag("RenderType", "Transparent");
        material.EnableKeyword("_SURFACE_TYPE_TRANSPARENT");
        material.DisableKeyword("_ALPHAPREMULTIPLY_ON");
        material.renderQueue = (int)RenderQueue.Transparent;
        EditorUtility.SetDirty(material);
        var gallery = EntranceGalleryBuilder.Build(material);
        var flow = sample.gameObject.AddComponent<EntranceFlow>();
        flow.mural = gallery.mural; flow.galleryRoot = gallery.root;
        flow.galleryStartEye = gallery.startEye; flow.galleryStartLookAt = gallery.startLookAt;
        flow.triggerFeet = gallery.triggerFeet; flow.muralCenter = gallery.muralCenter;
        flow.muralWidth = gallery.muralWidth; flow.muralHeight = gallery.muralHeight;
        flow.durationSeconds = 7;
        var bridge = AssetDatabase.LoadAssetAtPath<Material>(Generated + "/Materials/painting-bridge.mat");
        if (bridge == null)
        {
            bridge = new Material(Shader.Find("Athens/Entrance Painting Bridge"));
            AssetDatabase.CreateAsset(bridge, Generated + "/Materials/painting-bridge.mat");
        }
        bridge.mainTexture = texture;
        flow.paintingBridgeTemplate = bridge;
        BuildReturnMarker();
        flow.Initialize(sample);
        PlayerSettings.productName = "The Academy - Entrance Study";
        AssetDatabase.SaveAssets();
        EditorSceneManager.SaveScene(SceneManager.GetActiveScene(), ScenePath);
        EditorBuildSettings.scenes = new[] { new EditorBuildSettingsScene(ScenePath, true) };
        var dependencies = AssetDatabase.GetDependencies(ScenePath, true);
        if (dependencies.Any(path => !path.StartsWith("Assets/", StringComparison.Ordinal) && !path.StartsWith("Packages/", StringComparison.Ordinal)))
            throw new BuildFailedException("Entrance dependency is outside project Assets/Packages.");
        if (dependencies.Any(path => path.Contains("segnatura-official") || path.Contains("references/")))
            throw new BuildFailedException("Museum research imagery cannot ship in the entrance.");
        File.WriteAllText(Path.Combine(Root, "qa/environment/entrance/scene-generation.json"), JsonUtility.ToJson(new Generation
        {
            character_sha256 = sample.characterSha256, dependencies = dependencies,
            mural_width = gallery.muralWidth, mural_height = gallery.muralHeight, duration_seconds = flow.durationSeconds
        }, true));
        Debug.Log("[Entrance] SCENE_CREATED " + ScenePath + " mural=" + gallery.muralWidth + "x" + gallery.muralHeight);
    }

    private static void BuildReturnMarker()
    {
        var material = AssetDatabase.LoadAssetAtPath<Material>(Generated + "/Materials/return-marker.mat");
        if (material == null)
        {
            material = new Material(Shader.Find("Universal Render Pipeline/Lit"));
            AssetDatabase.CreateAsset(material, Generated + "/Materials/return-marker.mat");
        }
        material.SetColor("_BaseColor", new Color(.66f, .45f, .16f));
        var path = Generated + "/return-marker-strip.asset";
        var mesh = AssetDatabase.LoadAssetAtPath<Mesh>(path);
        if (mesh == null)
        {
            mesh = ArchitectureMeshes.BeveledBox(new Vector3(4, .008f, .06f), .002f);
            AssetDatabase.CreateAsset(mesh, path);
        }
        var root = new GameObject("Return to gallery - safe forecourt marker").transform;
        for (int i = 0; i < 4; i++)
        {
            var strip = new GameObject("Golden return boundary", typeof(MeshFilter), typeof(MeshRenderer));
            strip.transform.SetParent(root, false);
            strip.transform.position = new Vector3(i < 2 ? 0 : (i == 2 ? -2 : 2), .01f, i < 2 ? (i == 0 ? -7 : -3) : -5);
            strip.transform.rotation = Quaternion.Euler(0, i < 2 ? 0 : 90, 0);
            strip.GetComponent<MeshFilter>().sharedMesh = mesh;
            strip.GetComponent<MeshRenderer>().sharedMaterial = material;
        }
    }

    [MenuItem("Athens Production/Build Windows P1 entrance")]
    public static void BuildWindows()
    {
        CreateScene();
        var output = Environment.GetEnvironmentVariable("ATHENS_ENTRANCE_BUILD");
        if (string.IsNullOrEmpty(output)) output = Path.GetFullPath("Builds/Entrance");
        Directory.CreateDirectory(output);
        var executable = Path.Combine(output, "AthensEntrance.exe");
        var build = BuildPipeline.BuildPlayer(new BuildPlayerOptions { scenes = new[] { ScenePath }, locationPathName = executable, target = BuildTarget.StandaloneWindows64, options = BuildOptions.None });
        var summary = build.summary;
        File.WriteAllText(Path.Combine(Root, "qa/environment/entrance/build-result.json"), JsonUtility.ToJson(new BuildRecord { result = summary.result.ToString(), executable = Path.GetRelativePath(Root, executable), errors = (int)summary.totalErrors, warnings = (int)summary.totalWarnings, bytes = summary.totalSize, unity_version = Application.unityVersion }, true));
        if (summary.result != BuildResult.Succeeded) throw new BuildFailedException("Entrance build failed.");
        Debug.Log("[Entrance] BUILD_SUCCEEDED " + executable);
    }

    // Build the unchanged saved P0 scene with the shared runtime code, without
    // regenerating its scene or overwriting any historical P0 report.
    public static void BuildP0Regression()
    {
        var previousProduct = PlayerSettings.productName;
        var output = Path.GetFullPath("Builds/P0");
        Directory.CreateDirectory(output);
        var reportDirectory = Path.Combine(Root, "qa/environment/entrance/p0-regression");
        Directory.CreateDirectory(reportDirectory);
        try
        {
            PlayerSettings.productName = "The Academy - Production Sample";
            var build = BuildPipeline.BuildPlayer(new BuildPlayerOptions { scenes = new[] { "Assets/Scenes/ProductionSample.unity" }, locationPathName = Path.Combine(output, "AthensProduction.exe"), target = BuildTarget.StandaloneWindows64, options = BuildOptions.None });
            var summary = build.summary;
            File.WriteAllText(Path.Combine(reportDirectory, "build-result.json"), JsonUtility.ToJson(new BuildRecord { result = summary.result.ToString(), executable = "unity/Builds/P0/AthensProduction.exe", errors = (int)summary.totalErrors, warnings = (int)summary.totalWarnings, bytes = summary.totalSize, unity_version = Application.unityVersion }, true));
            if (summary.result != BuildResult.Succeeded) throw new BuildFailedException("P0 shared-runtime regression build failed.");
        }
        finally { PlayerSettings.productName = previousProduct; }
    }
}
