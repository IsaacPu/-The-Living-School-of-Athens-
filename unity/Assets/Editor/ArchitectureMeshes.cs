using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Rendering;

namespace AthensProduction.EditorTools
{
    /// <summary>Closed, meter-scaled architectural meshes; no negative transform scale is required.</summary>
    public static class ArchitectureMeshes
    {
        public static Mesh BeveledBox(Vector3 size, float bevel)
        {
            RequirePositive(size.x, nameof(size));
            RequirePositive(size.y, nameof(size));
            RequirePositive(size.z, nameof(size));
            RequireNonNegative(bevel, nameof(bevel));
            Vector3 h = size * 0.5f;
            float b = Mathf.Min(bevel, Mathf.Min(h.x, Mathf.Min(h.y, h.z)) * 0.95f);
            Vector3 inset = h - Vector3.one * b;
            var data = new MeshData();

            for (int axis = 0; axis < 3; axis++)
            {
                int a = (axis + 1) % 3;
                int c = (axis + 2) % 3;
                foreach (int sign in Signs)
                {
                    Vector3 normal = Vector3.zero;
                    normal[axis] = sign;
                    var face = new Vector3[4];
                    for (int i = 0; i < 4; i++)
                    {
                        Vector3 p = Vector3.zero;
                        p[axis] = sign * h[axis];
                        p[a] = QuadSigns[i, 0] * inset[a];
                        p[c] = QuadSigns[i, 1] * inset[c];
                        face[i] = p;
                    }
                    data.AddFlatFace(face, normal);
                }
            }

            if (b > 0f)
            {
                // Twelve bevel strips between adjacent axis-aligned faces.
                for (int a = 0; a < 3; a++)
                for (int c = a + 1; c < 3; c++)
                {
                    int free = 3 - a - c;
                    foreach (int sa in Signs)
                    foreach (int sc in Signs)
                    {
                        var face = new Vector3[4];
                        for (int i = 0; i < 4; i++)
                        {
                            bool onA = i == 0 || i == 3;
                            Vector3 p = Vector3.zero;
                            p[a] = sa * (onA ? h[a] : inset[a]);
                            p[c] = sc * (onA ? inset[c] : h[c]);
                            p[free] = (i < 2 ? -1 : 1) * inset[free];
                            face[i] = p;
                        }
                        Vector3 normal = Vector3.zero;
                        normal[a] = sa;
                        normal[c] = sc;
                        data.AddFlatFace(face, normal.normalized);
                    }
                }

                // Eight triangular corners close the three adjoining bevel strips.
                foreach (int sx in Signs)
                foreach (int sy in Signs)
                foreach (int sz in Signs)
                {
                    data.AddFlatFace(new[]
                    {
                        new Vector3(sx * h.x, sy * inset.y, sz * inset.z),
                        new Vector3(sx * inset.x, sy * h.y, sz * inset.z),
                        new Vector3(sx * inset.x, sy * inset.y, sz * h.z)
                    }, new Vector3(sx, sy, sz).normalized);
                }
            }
            return data.Build("BeveledBox");
        }

        /// <summary>
        /// A closed upper semicircular ring. The springline is Y=0, center is X=Z=0,
        /// outer radius is innerRadius+thickness, and depth extends equally along +/-Z.
        /// Bevels are real geometry on all four radial/depth edges of the cross section.
        /// </summary>
        public static Mesh Arch(float innerRadius, float thickness, float depth, int segments = 48, float bevel = 0.04f)
        {
            RequirePositive(innerRadius, nameof(innerRadius));
            RequirePositive(thickness, nameof(thickness));
            RequirePositive(depth, nameof(depth));
            RequireNonNegative(bevel, nameof(bevel));
            if (segments < 3 || segments > 2048)
                throw new ArgumentOutOfRangeException(nameof(segments), "Use 3 to 2048 arc segments.");

            float r = innerRadius;
            float outer = r + thickness;
            float z = depth * 0.5f;
            float b = Mathf.Min(bevel, Mathf.Min(thickness, depth) * 0.475f);
            // Clockwise polygon in (radius, Z); each edge has outward normal (-dZ, dRadius).
            Vector2[] section = b > 0f ? new[]
            {
                new Vector2(r + b, z), new Vector2(outer - b, z),
                new Vector2(outer, z - b), new Vector2(outer, -z + b),
                new Vector2(outer - b, -z), new Vector2(r + b, -z),
                new Vector2(r, -z + b), new Vector2(r, z - b)
            } : new[]
            {
                new Vector2(r, z), new Vector2(outer, z),
                new Vector2(outer, -z), new Vector2(r, -z)
            };

            var data = new MeshData();
            float perimeter = 0f;
            for (int edge = 0; edge < section.Length; edge++)
            {
                Vector2 s0 = section[edge];
                Vector2 s1 = section[(edge + 1) % section.Length];
                Vector2 delta = s1 - s0;
                float edgeLength = delta.magnitude;
                Vector2 normalRZ = new Vector2(-delta.y, delta.x).normalized;
                float uvRadius = (s0.x + s1.x) * 0.5f;
                for (int segment = 0; segment < segments; segment++)
                {
                    float a0 = Mathf.PI * segment / segments;
                    float a1 = Mathf.PI * (segment + 1) / segments;
                    Vector3 n0 = RadialNormal(normalRZ, a0);
                    Vector3 n1 = RadialNormal(normalRZ, a1);
                    data.AddQuad(
                        new[] { Point(s0, a0), Point(s0, a1), Point(s1, a1), Point(s1, a0) },
                        new[] { n0, n1, n1, n0 },
                        new[]
                        {
                            new Vector2(a0 * uvRadius, perimeter),
                            new Vector2(a1 * uvRadius, perimeter),
                            new Vector2(a1 * uvRadius, perimeter + edgeLength),
                            new Vector2(a0 * uvRadius, perimeter + edgeLength)
                        });
                }
                perimeter += edgeLength;
            }

            // Both open arc ends lie on Y=0. Their solid-facing outward normal is -Y.
            var startCap = new Vector3[section.Length];
            var endCap = new Vector3[section.Length];
            for (int i = 0; i < section.Length; i++)
            {
                startCap[i] = Point(section[i], 0f);
                endCap[i] = Point(section[i], Mathf.PI);
            }
            data.AddFlatFace(startCap, Vector3.down);
            data.AddFlatFace(endCap, Vector3.down);
            return data.Build("SemicircularArch");
        }

        private static readonly int[] Signs = { -1, 1 };
        private static readonly int[,] QuadSigns = { { -1, -1 }, { 1, -1 }, { 1, 1 }, { -1, 1 } };

        private static Vector3 Point(Vector2 radialZ, float angle)
        {
            // Clamp the two springline ends exactly to the same plane as the caps/piers.
            float y = angle <= 0f || angle >= Mathf.PI ? 0f : radialZ.x * Mathf.Sin(angle);
            return new Vector3(radialZ.x * Mathf.Cos(angle), y, radialZ.y);
        }

        private static Vector3 RadialNormal(Vector2 radialZ, float angle)
        {
            return new Vector3(radialZ.x * Mathf.Cos(angle), radialZ.x * Mathf.Sin(angle), radialZ.y).normalized;
        }

        private static void RequirePositive(float value, string name)
        {
            if (float.IsNaN(value) || float.IsInfinity(value) || value <= 0f)
                throw new ArgumentOutOfRangeException(name, "Dimensions must be finite and greater than zero.");
        }

        private static void RequireNonNegative(float value, string name)
        {
            if (float.IsNaN(value) || float.IsInfinity(value) || value < 0f)
                throw new ArgumentOutOfRangeException(name, "Bevel must be finite and non-negative.");
        }

        private sealed class MeshData
        {
            private readonly List<Vector3> vertices = new List<Vector3>();
            private readonly List<Vector3> normals = new List<Vector3>();
            private readonly List<Vector2> uv = new List<Vector2>();
            private readonly List<int> triangles = new List<int>();

            public void AddFlatFace(Vector3[] points, Vector3 outward)
            {
                int count = points.Length;
                int first = vertices.Count;
                bool reverse = Vector3.Dot(Vector3.Cross(points[1] - points[0], points[2] - points[0]), outward) < 0f;
                Vector3 absolute = new Vector3(Mathf.Abs(outward.x), Mathf.Abs(outward.y), Mathf.Abs(outward.z));
                for (int i = 0; i < count; i++)
                {
                    Vector3 p = points[i];
                    vertices.Add(p);
                    normals.Add(outward.normalized);
                    uv.Add(absolute.x >= absolute.y && absolute.x >= absolute.z ? new Vector2(p.z, p.y)
                        : absolute.y >= absolute.z ? new Vector2(p.x, p.z) : new Vector2(p.x, p.y));
                }
                for (int i = 1; i < count - 1; i++)
                {
                    triangles.Add(first);
                    triangles.Add(first + (reverse ? i + 1 : i));
                    triangles.Add(first + (reverse ? i : i + 1));
                }
            }

            public void AddQuad(Vector3[] points, Vector3[] outward, Vector2[] coordinates)
            {
                int first = vertices.Count;
                vertices.AddRange(points);
                normals.AddRange(outward);
                uv.AddRange(coordinates);
                bool reverse = Vector3.Dot(Vector3.Cross(points[1] - points[0], points[2] - points[0]), outward[0] + outward[1]) < 0f;
                if (reverse)
                    triangles.AddRange(new[] { first, first + 2, first + 1, first, first + 3, first + 2 });
                else
                    triangles.AddRange(new[] { first, first + 1, first + 2, first, first + 2, first + 3 });
            }

            public Mesh Build(string name)
            {
                var mesh = new Mesh { name = name };
                if (vertices.Count > 65535) mesh.indexFormat = IndexFormat.UInt32;
                mesh.SetVertices(vertices);
                mesh.SetNormals(normals);
                mesh.SetUVs(0, uv);
                mesh.SetTriangles(triangles, 0);
                mesh.RecalculateBounds();
                mesh.RecalculateTangents();
                return mesh;
            }
        }
    }
}
