"""Independent file/provenance gate. This does not award visual art acceptance."""
import argparse
import hashlib
import json
import struct
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--environment-report", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "qa/integration/file-contract.json")
    args = parser.parse_args()
    checks = []

    def check(name, passed, detail):
        checks.append({"name": name, "passed": bool(passed), "detail": detail})

    def resolve(base, value):
        path = (base / value).resolve()
        if not path.is_relative_to(ROOT):
            raise ValueError(f"Path escapes production: {value}")
        return path

    manifest_path = ROOT / "art/characters/plato/v001/delivery.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    base = manifest_path.parent
    required = ["schema_version", "asset_id", "relative_glb_path", "sha256", "bytes",
                "source", "units", "up_axis", "forward_axis", "orientation_verified",
                "body_height_m", "bounds_m", "triangles", "materials", "skins",
                "animations", "relative_blend_path", "qa_images", "changes",
                "known_defects", "technical_status", "art_status"]
    check("manifest_fields", all(key in manifest for key in required),
          [key for key in required if key not in manifest])
    check("coordinate_contract", manifest["schema_version"] == 1 and
          manifest["units"] == "meters" and manifest["up_axis"] == "+Y" and
          manifest["forward_axis"] == "+Z" and manifest["orientation_verified"],
          "Orientation image judgment remains a separate visual review.")
    glb = resolve(base, manifest["relative_glb_path"])
    raw = glb.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    check("delivered_bytes_hash", len(raw) == manifest["bytes"] and digest == manifest["sha256"],
          {"sha256": digest, "bytes": len(raw)})
    magic, version, total = struct.unpack_from("<4sII", raw, 0)
    chunk_len, chunk_type = struct.unpack_from("<II", raw, 12)
    check("glb_container", magic == b"glTF" and version == 2 and total == len(raw)
          and chunk_type == 0x4E4F534A, {"version": version, "length": total})
    gltf = json.loads(raw[20:20+chunk_len])
    external = [obj["uri"] for group in ("buffers", "images") for obj in gltf.get(group, [])
                if "uri" in obj and not obj["uri"].startswith("data:")]
    check("self_contained_glb", not external, external)
    triangles = sum(gltf["accessors"][primitive["indices"]]["count"] // 3
                    for mesh in gltf.get("meshes", []) for primitive in mesh["primitives"]
                    if primitive.get("mode", 4) == 4 and "indices" in primitive)
    check("geometry_metadata", triangles == manifest["triangles"] and
          len(gltf.get("skins", [])) == manifest["skins"] and
          len(gltf.get("animations", [])) == manifest["animations"],
          {"triangles": triangles, "skins": len(gltf.get("skins", [])),
           "animations": len(gltf.get("animations", []))})
    original = resolve(base, manifest["source"]["relative_original_path"])
    check("independent_source_hash", hashlib.sha256(original.read_bytes()).hexdigest()
          == manifest["source"]["sha256"], original.relative_to(ROOT).as_posix())
    evidence = {"blend": manifest["relative_blend_path"],
                "provenance": manifest["source"]["provenance"]}
    evidence.update({key: manifest[key] for key in
                     ("qa_report", "verification_report", "roundtrip_report", "reference_sources", "reproduction")
                     if key in manifest})
    evidence.update({f"image_{i}": value for i, value in enumerate(manifest["qa_images"])})
    missing = [value for value in evidence.values() if not resolve(base, value).is_file()]
    check("all_declared_delivery_evidence", not missing, missing)
    check("art_status_is_honest", manifest["art_status"] == "baseline_diagnostic" and
          manifest["geometry_changed"] is False and len(manifest["known_defects"]) >= 3,
          "An unchanged diagnostic mesh is not a refined/rigged character.")

    imported = ROOT / "unity/Assets/_Project/Characters/plato-v001.glb"
    check("unity_physical_copy", imported.is_file() and
          hashlib.sha256(imported.read_bytes()).hexdigest() == digest,
          imported.relative_to(ROOT).as_posix())
    runtime_findings = []
    for path in (ROOT / "unity/Assets").rglob("*.cs"):
        for i, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
            # Comments are not dependencies. Flag actual forbidden path/port literals.
            code = line.strip()
            if code.startswith("//"):
                continue
            if "test-project" in code.lower() or "8787" in code:
                runtime_findings.append({"file": path.relative_to(ROOT).as_posix(), "line": i})
    check("no_test_runtime_literals", not runtime_findings, runtime_findings)
    reparse_points = [str(p.relative_to(ROOT)) for folder in ("art", "unity/Assets")
                      for p in (ROOT / folder).rglob("*")
                      if p.is_symlink() or (hasattr(p, "is_junction") and p.is_junction())]
    check("no_art_asset_links", not reparse_points, reparse_points)
    dependencies = json.loads((ROOT / "unity/Packages/manifest.json").read_text(encoding="utf-8-sig"))
    package_paths = {k: v for k, v in dependencies.get("dependencies", {}).items()
                     if isinstance(v, str) and "test-project" in v.lower()}
    check("no_test_package_dependencies", not package_paths, package_paths)
    if args.environment_report:
        report_path = args.environment_report.resolve()
        report = json.loads(report_path.read_text(encoding="utf-8-sig"))
        check("fresh_player_gate", report.get("passed") and not report.get("runtime_errors"),
              str(report_path.relative_to(ROOT)))
        check("player_character_matches_delivery", report.get("character_sha256") == digest,
              report.get("character_sha256"))
        check("player_carries_diagnostic_status", report.get("character_art_status") == "baseline_diagnostic",
              report.get("character_art_status"))
        for info in report.get("images", []):
            capture = resolve(report_path.parent, info["file"])
            check("capture_"+info["file"], capture.is_file() and capture.stat().st_size > 1024,
                  {"width": info.get("width"), "height": info.get("height")})
    else:
        check("fresh_player_gate", False, "Supply --environment-report after Player validation.")

    result = {"schema_version": 1, "utc": datetime.now(timezone.utc).isoformat(),
              "passed": all(c["passed"] for c in checks), "checks": checks,
              "scope": "Independent manifest/file/dependency inspection plus supplied fresh Player report. "
                       "No aesthetic, physical input, historical likeness or commercial-rights verdict."}
    output = args.output.resolve()
    if not output.is_relative_to(ROOT / "qa/integration"):
        raise ValueError("Output must stay in qa/integration")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({"passed": result["passed"], "checks": len(checks), "output": str(output),
                      "failures": [c["name"] for c in checks if not c["passed"]]}))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
