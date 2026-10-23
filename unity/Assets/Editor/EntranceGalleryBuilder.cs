using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

namespace AthensProduction.EditorTools
{
    public sealed class GalleryParts
    {
        public Transform root;
        public Renderer mural;
        public Vector3 startEye, startLookAt, triggerFeet, muralCenter;
        public float muralWidth, muralHeight;
    }

    /// <summary>
    /// Segnatura-inspired research graybox. Room dimensions and geometric ornament are
    /// design completions, not a survey or reproductions of the adjacent historic paintings.
    /// Only the caller-provided mural material can contain an image texture.
    /// </summary>
    public static class EntranceGalleryBuilder
    {
        private const string RootName = "Entrance gallery - Segnatura-inspired research graybox";
        private const string Generated = "Assets/_Project/Entrance/Generated";
        private const float HalfWidth = 5.8f;
        private const float Back = -24.5f;
        private const float Front = -14.1f;
        private const float WallZ = -14.02f;
        private const float MuralZ = -14.05f;
        private const float Spring = 6.7f;
        private const float VaultFlattening = .36f;
        private static readonly Dictionary<string, Mesh> Meshes = new Dictionary<string, Mesh>();
        private static Transform root;
        private static Material plaster, limestone, darkStone, porphyry, ochre, blue, green, wood;

        public static GalleryParts Build(Material muralMaterial)
        {
            if (muralMaterial == null) throw new ArgumentNullException(nameof(muralMaterial));
            var previous = GameObject.Find(RootName);
            if (previous != null) UnityEngine.Object.DestroyImmediate(previous);
            Directory.CreateDirectory(Generated + "/Meshes");
            Directory.CreateDirectory(Generated + "/Materials");
            AssetDatabase.Refresh();
            Meshes.Clear();
            root = new GameObject(RootName).transform;
            plaster = MaterialAsset("warm-plaster", new Color(.71f, .67f, .57f), .12f);
            limestone = MaterialAsset("ivory-limestone", new Color(.76f, .74f, .66f), .19f);
            darkStone = MaterialAsset("charcoal-inlay", new Color(.15f, .17f, .16f), .24f);
            porphyry = MaterialAsset("muted-porphyry", new Color(.32f, .18f, .16f), .25f);
            ochre = MaterialAsset("ochre-ornament", new Color(.53f, .37f, .16f), .25f);
            blue = MaterialAsset("muted-blue-panel", new Color(.18f, .29f, .34f), .12f);
            green = MaterialAsset("muted-green-panel", new Color(.30f, .34f, .26f), .12f);
            wood = MaterialAsset("dark-wood-door", new Color(.23f, .13f, .09f), .23f);

            float height = 4.4f;
            var texture=muralMaterial.mainTexture;
            var uvScale=muralMaterial.mainTextureScale;
            float width=height*(texture.width*uvScale.x)/(texture.height*uvScale.y);
            BuildEnvelope(width, height);
            BuildWallSkirts(width);
            BuildDoor();
            BuildAdjacentPanels();
            BuildCeiling();
            BuildFloor();

            var mural = MeshObject("School of Athens - dynamic mural overlay", new Vector3(0, 1.7f + height / 2, MuralZ),
                SavedMesh("mural-quad", () => MuralQuad(width, height)), muralMaterial, false);
            mural.gameObject.isStatic = false;
            mural.shadowCastingMode = ShadowCastingMode.Off;
            mural.receiveShadows = false;
            BuildMuralFrame(width, height);

            var fill = new GameObject("Gallery local warm fill - graybox lighting").AddComponent<Light>();
            fill.transform.SetParent(root, false);
            fill.transform.localPosition = new Vector3(0, 5.1f, -19.3f);
            fill.type = LightType.Point;
            fill.range = 10;
            fill.intensity = 7;
            fill.color = new Color(1, .91f, .76f);
            fill.shadows = LightShadows.None;
            AssetDatabase.SaveAssets();
            return new GalleryParts
            {
                root = root,
                mural = mural,
                startEye = new Vector3(-2.6f, 1.65f, -23),
                startLookAt = new Vector3(0, 3.3f, MuralZ),
                triggerFeet = new Vector3(0, .025f, -19),
                muralCenter = new Vector3(0, 1.7f + height / 2, MuralZ),
                muralWidth = width,
                muralHeight = height
            };
        }

        private static void BuildEnvelope(float muralWidth, float muralHeight)
        {
            float half = muralWidth / 2;
            float top = 1.7f + muralHeight;
            Box("Gallery structural floor", new Vector3(0, -.12f, (Front + Back) / 2), new Vector3(HalfWidth * 2, .24f, Front - Back), limestone, .01f, true);
            Box("Gallery rear enclosing wall", new Vector3(0, 4.5f, Back - .13f), new Vector3(12.12f, 9, .26f), plaster, .02f, true);
            for (int side = -1; side <= 1; side += 2)
                Box("Gallery side enclosing wall", new Vector3(side * (HalfWidth + .13f), Spring / 2, (Front + Back) / 2), new Vector3(.26f, Spring, Front - Back + .26f), plaster, .02f, true);

            // The mural aperture is genuinely empty: no opaque wall/collider sits behind its rectangle.
            Box("Mural wall below actual opening", new Vector3(0, .85f, WallZ), new Vector3(muralWidth, 1.7f, .26f), plaster, .02f, true);
            Box("Mural wall above actual opening", new Vector3(0, (top + 9) / 2, WallZ), new Vector3(muralWidth, 9 - top, .26f), plaster, .02f, true);
            Box("Mural right enclosing pier", new Vector3((half + HalfWidth) / 2, 4.5f, WallZ), new Vector3(HalfWidth - half, 9, .26f), plaster, .02f, true);

            // A second real opening, at the lower left, contains a closed ornamental door.
            const float doorLeft = -5.20f, doorRight = -3.90f, doorTop = 2.45f;
            Box("Door left masonry jamb", new Vector3((-HalfWidth + doorLeft) / 2, 4.5f, WallZ), new Vector3(doorLeft + HalfWidth, 9, .26f), plaster, .02f, true);
            Box("Door right masonry jamb", new Vector3((doorRight - half) / 2, 4.5f, WallZ), new Vector3(-half - doorRight, 9, .26f), plaster, .02f, true);
            Box("Masonry above lower door", new Vector3((doorLeft + doorRight) / 2, (doorTop + 9) / 2, WallZ), new Vector3(doorRight - doorLeft, 9 - doorTop, .26f), plaster, .02f, true);
        }

        private static void BuildWallSkirts(float muralWidth)
        {
            Box("Wall skirt under mural", new Vector3(0, .78f, -14.19f), new Vector3(muralWidth, 1.5f, .08f), limestone, .015f);
            Box("Wall skirt upper molding", new Vector3(0, 1.54f, -14.24f), new Vector3(muralWidth + .08f, .12f, .16f), limestone, .025f);
            for (int i = -2; i <= 2; i++)
            {
                float x = i * 1.22f;
                Box("Lower wall polychrome panel", new Vector3(x, .79f, -14.245f), new Vector3(1.02f, .99f, .035f), porphyry, .01f);
                Box("Lower wall inset medallion", new Vector3(x, .79f, -14.27f), new Vector3(.62f, .62f, .025f), ochre, .01f, false, Quaternion.Euler(0, 0, 45));
                for (int side = -1; side <= 1; side += 2)
                    Box("Lower wall panel upright", new Vector3(x + side * .54f, .79f, -14.275f), new Vector3(.055f, 1.1f, .055f), limestone, .012f);
            }
            for (int side = -1; side <= 1; side += 2)
            {
                Box("Adjacent wall skirt", new Vector3(side * 5.73f, .76f, -19.3f), new Vector3(.11f, 1.52f, 10.4f), limestone, .015f);
                Box("Adjacent skirt top molding", new Vector3(side * 5.66f, 1.54f, -19.3f), new Vector3(.18f, .12f, 10.4f), limestone, .025f);
                for (int p = 0; p < 7; p++)
                {
                    float z = -23.65f + p * 1.42f;
                    Box("Adjacent lower polychrome inset", new Vector3(side * 5.655f, .78f, z), new Vector3(.035f, 1.0f, 1.15f), p % 2 == 0 ? porphyry : green, .01f);
                    Box("Adjacent lower panel division", new Vector3(side * 5.615f, .78f, z - .64f), new Vector3(.07f, 1.12f, .065f), ochre, .01f);
                }
            }
        }

        private static void BuildDoor()
        {
            const float x = -4.55f;
            Box("Left lower closed timber door", new Vector3(x, 1.225f, -14.06f), new Vector3(1.30f, 2.45f, .12f), wood, .025f, true);
            for (int side = -1; side <= 1; side += 2)
            {
                Box("Door stone frame jamb", new Vector3(x + side * .72f, 1.31f, -14.24f), new Vector3(.15f, 2.62f, .25f), limestone, .025f);
                for (int row = 0; row < 2; row++)
                {
                    Box("Timber inset panel", new Vector3(x + side * .30f, .64f + row * 1.12f, -14.135f), new Vector3(.48f, .88f, .045f), porphyry, .018f);
                    Box("Timber inner panel", new Vector3(x + side * .30f, .64f + row * 1.12f, -14.165f), new Vector3(.35f, .72f, .022f), wood, .014f);
                }
            }
            Box("Door frame lintel", new Vector3(x, 2.61f, -14.24f), new Vector3(1.61f, .19f, .30f), limestone, .03f);
            Box("Door frame upper lip", new Vector3(x, 2.77f, -14.25f), new Vector3(1.78f, .12f, .34f), ochre, .02f);
            Box("Timber central stile", new Vector3(x, 1.23f, -14.16f), new Vector3(.065f, 2.35f, .05f), ochre, .01f);
        }

        private static void BuildAdjacentPanels()
        {
            for (int side = -1; side <= 1; side += 2)
            {
                for (int panel = 0; panel < 3; panel++)
                {
                    float z = -22.55f + panel * 3.23f;
                    // Geometric placeholders indicate the neighbouring painted wall zones; no photo is copied.
                    Box("Adjacent painted-zone placeholder - geometric only", new Vector3(side * 5.62f, 3.9f, z), new Vector3(.09f, 3.9f, 2.75f), panel % 2 == 0 ? blue : green, .025f);
                    for (int edge = -1; edge <= 1; edge += 2)
                    {
                        Box("Adjacent panel vertical frame", new Vector3(side * 5.54f, 3.9f, z + edge * 1.43f), new Vector3(.12f, 4.08f, .11f), ochre, .02f);
                        Box("Adjacent panel horizontal frame", new Vector3(side * 5.54f, 3.9f + edge * 2.02f, z), new Vector3(.12f, .11f, 2.96f), limestone, .02f);
                    }
                    Box("Adjacent geometric medallion", new Vector3(side * 5.53f, 3.9f, z), new Vector3(.06f, 1.45f, 1.45f), ochre, .025f, false, Quaternion.Euler(45, 0, 0));
                }
                for (int end = 0; end < 2; end++)
                    Box("Gallery corner pilaster", new Vector3(side * 5.58f, 3.35f, end == 0 ? -24.22f : -14.38f), new Vector3(.28f, 6.7f, .28f), limestone, .035f);
            }
            Box("Rear wall skirt", new Vector3(0, .78f, -24.44f), new Vector3(11.6f, 1.55f, .10f), limestone, .02f);
            for (int i = -2; i <= 2; i++)
                Box("Rear polychrome wall panel", new Vector3(i * 2.05f, 3.7f, -24.40f), new Vector3(1.75f, 3.65f, .08f), i % 2 == 0 ? green : blue, .025f);
        }

        private static void BuildCeiling()
        {
            var shell = MeshObject("Palace flattened vault - design completion", new Vector3(0, Spring, -19.3f),
                SavedMesh("gallery-vault", () => ArchitectureMeshes.Arch(HalfWidth, .24f, Front - Back, 48, .025f)), plaster, false);
            shell.transform.localScale = new Vector3(1, VaultFlattening, 1);
            var roofCollider = shell.gameObject.AddComponent<MeshCollider>();
            roofCollider.sharedMesh = shell.GetComponent<MeshFilter>().sharedMesh;
            for (int i = 0; i < 5; i++)
            {
                var rib = MeshObject("Ceiling ornamental cross rib", new Vector3(0, Spring, -24.3f + i * 2.5f),
                    SavedMesh("gallery-vault-rib", () => ArchitectureMeshes.Arch(5.73f, .095f, .12f, 48, .018f)), ochre, false);
                rib.transform.localScale = new Vector3(1, VaultFlattening, 1);
            }
            for (int a = 0; a < 5; a++)
                for (int d = 0; d < 3; d++)
                {
                    float angle = (a + .5f) * Mathf.PI / 5;
                    var tangent = new Vector3(-Mathf.Sin(angle), VaultFlattening * Mathf.Cos(angle), 0).normalized;
                    float rotation = Mathf.Atan2(tangent.y, tangent.x) * Mathf.Rad2Deg;
                    var position = new Vector3(5.67f * Mathf.Cos(angle), Spring + 5.67f * VaultFlattening * Mathf.Sin(angle), -22.6f + d * 3.25f);
                    Box("Ceiling polychrome geometric field", position, new Vector3(1.2f, .045f, 1.82f), (a + d) % 2 == 0 ? blue : green, .018f, false, Quaternion.Euler(0, 0, rotation));
                }
            for (int side = -1; side <= 1; side += 2)
            {
                Box("Long gallery cornice", new Vector3(side * 5.63f, 6.44f, -19.3f), new Vector3(.36f, .22f, 10.4f), limestone, .035f);
                Box("Gallery cornice ochre bead", new Vector3(side * 5.51f, 6.29f, -19.3f), new Vector3(.12f, .08f, 10.4f), ochre, .015f);
            }
            Box("Mural wall crown cornice", new Vector3(0, 6.45f, -14.25f), new Vector3(11.6f, .22f, .34f), limestone, .035f);
            Box("Rear wall crown cornice", new Vector3(0, 6.45f, -24.35f), new Vector3(11.6f, .22f, .34f), limestone, .035f);
        }

        private static void BuildFloor()
        {
            for (int x = -4; x <= 4; x++)
                for (int z = 0; z < 8; z++)
                {
                    var center = new Vector3(x * 1.12f, .0025f, -23.65f + z * 1.2f);
                    Box("Geometric mosaic field", center, new Vector3(1.01f, .005f, 1.07f), (x + z) % 2 == 0 ? green : limestone, .001f);
                    Box("Mosaic field inset diamond", center + Vector3.up * .003f, new Vector3(.35f, .003f, .35f), (x + z) % 2 == 0 ? limestone : darkStone, .001f, false, Quaternion.Euler(0, 45, 0));
                }
            for (int side = -1; side <= 1; side += 2)
            {
                Box("Floor long perimeter inlay", new Vector3(side * 5.4f, .006f, -19.3f), new Vector3(.13f, .008f, 9.7f), darkStone, .002f);
                Box("Floor long ivory border", new Vector3(side * 5.18f, .006f, -19.3f), new Vector3(.13f, .008f, 9.7f), limestone, .002f);
                Box("Floor short perimeter inlay", new Vector3(0, .006f, -19.3f + side * 4.85f), new Vector3(10.93f, .008f, .13f), darkStone, .002f);
            }
            // Low polygonal rings and four lobes recall the official overview's inlaid floor relations.
            var centerRose = new Vector3(0, .012f, -19.1f);
            Ring("Central rosette outer dark band", centerRose, 1.86f, .09f, darkStone);
            Ring("Central rosette ivory band", centerRose, 1.73f, .07f, limestone);
            for (int i = 0; i < 4; i++)
            {
                float angle = i * Mathf.PI / 2;
                Ring("Rosette quatrefoil lobe", centerRose + new Vector3(Mathf.Cos(angle) * .81f, .003f, Mathf.Sin(angle) * .81f), .73f, .065f, ochre);
            }
            Ring("Rosette central circle", centerRose + Vector3.up * .006f, .53f, .07f, darkStone);
            Box("Rosette central inset diamond", centerRose + Vector3.up * .003f, new Vector3(.61f, .008f, .61f), porphyry, .002f, false, Quaternion.Euler(0, 45, 0));
        }

        private static void Ring(string name, Vector3 position, float radius, float width, Material material)
        {
            string key = string.Format(CultureInfo.InvariantCulture, "floor-ring-{0:F4}-{1:F4}", radius, width);
            var mesh = SavedMesh(key, () => ArchitectureMeshes.Arch(radius, width, .005f, 48, .001f));
            for (int half = 0; half < 2; half++)
            {
                var renderer = MeshObject(name, position, mesh, material, false);
                renderer.transform.localRotation = Quaternion.AngleAxis(half * 180, Vector3.up) * Quaternion.AngleAxis(90, Vector3.right);
                renderer.shadowCastingMode = ShadowCastingMode.Off;
            }
        }

        private static void BuildMuralFrame(float width, float height)
        {
            float centerY = 1.7f + height / 2;
            for (int side = -1; side <= 1; side += 2)
            {
                Box("Mural opening stone jamb", new Vector3(side * (width / 2 + .08f), centerY, -14.19f), new Vector3(.16f, height + .25f, .19f), limestone, .025f);
                Box("Mural opening fine ochre edge", new Vector3(side * (width / 2 + .024f), centerY, -14.22f), new Vector3(.048f, height, .08f), ochre, .009f);
                Box("Mural opening horizontal frame", new Vector3(0, centerY + side * (height / 2 + .07f), -14.19f), new Vector3(width + .32f, .14f, .19f), limestone, .025f);
            }
        }

        private static Mesh MuralQuad(float width, float height)
        {
            var mesh = new Mesh { name = "mural-quad-facing-minus-Z" };
            mesh.vertices = new[] { new Vector3(-width / 2, -height / 2, 0), new Vector3(-width / 2, height / 2, 0), new Vector3(width / 2, height / 2, 0), new Vector3(width / 2, -height / 2, 0) };
            mesh.normals = new[] { Vector3.back, Vector3.back, Vector3.back, Vector3.back };
            mesh.uv = new[] { new Vector2(0, 0), new Vector2(0, 1), new Vector2(1, 1), new Vector2(1, 0) };
            mesh.triangles = new[] { 0, 1, 2, 0, 2, 3 };
            mesh.RecalculateBounds(); mesh.RecalculateTangents();
            return mesh;
        }

        private static Renderer Box(string name, Vector3 position, Vector3 size, Material material, float bevel, bool collision = false, Quaternion? rotation = null)
        {
            string key = string.Format(CultureInfo.InvariantCulture, "box-{0:F4}-{1:F4}-{2:F4}-{3:F4}", size.x, size.y, size.z, bevel);
            var renderer = MeshObject(name, position, SavedMesh(key, () => ArchitectureMeshes.BeveledBox(size, bevel)), material, collision);
            if (rotation.HasValue) renderer.transform.localRotation = rotation.Value;
            return renderer;
        }

        private static Renderer MeshObject(string name, Vector3 position, Mesh mesh, Material material, bool collision)
        {
            var go = new GameObject(name, typeof(MeshFilter), typeof(MeshRenderer));
            go.transform.SetParent(root, false);
            go.transform.localPosition = position;
            go.GetComponent<MeshFilter>().sharedMesh = mesh;
            var renderer = go.GetComponent<MeshRenderer>(); renderer.sharedMaterial = material;
            go.isStatic = true;
            if (collision)
            {
                var collider = go.AddComponent<BoxCollider>(); collider.center = mesh.bounds.center; collider.size = mesh.bounds.size;
            }
            return renderer;
        }

        private static Mesh SavedMesh(string key, Func<Mesh> create)
        {
            if (Meshes.TryGetValue(key, out var saved)) return saved;
            string path = Generated + "/Meshes/" + key + ".asset";
            var candidate = create(); candidate.name = key;
            saved = AssetDatabase.LoadAssetAtPath<Mesh>(path);
            if (saved == null) { AssetDatabase.CreateAsset(candidate, path); saved = candidate; }
            else { EditorUtility.CopySerialized(candidate, saved); UnityEngine.Object.DestroyImmediate(candidate); EditorUtility.SetDirty(saved); }
            Meshes.Add(key, saved);
            return saved;
        }

        private static Material MaterialAsset(string name, Color color, float smoothness)
        {
            string path = Generated + "/Materials/" + name + ".mat";
            var material = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (material == null)
            {
                var shader = Shader.Find("Universal Render Pipeline/Lit");
                if (shader == null) throw new InvalidOperationException("URP/Lit shader is unavailable.");
                material = new Material(shader); AssetDatabase.CreateAsset(material, path);
            }
            material.SetColor("_BaseColor", color); material.SetFloat("_Metallic", 0); material.SetFloat("_Smoothness", smoothness);
            material.enableInstancing = true; EditorUtility.SetDirty(material);
            return material;
        }
    }
}
