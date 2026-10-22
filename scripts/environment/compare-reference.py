"""Local-only QA comparison, not a game texture or public artwork deliverable."""
from pathlib import Path
import argparse
import json
from PIL import Image, ImageDraw

parser = argparse.ArgumentParser()
parser.add_argument("run", type=Path)
args = parser.parse_args()
production = Path(__file__).resolve().parents[2]
run = args.run.resolve()
run.relative_to(production / "qa" / "environment")
params = json.loads((production / "art/environment/architecture-parameters.json").read_text(encoding="utf-8-sig"))
report = json.loads((run / "verification.json").read_text(encoding="utf-8-sig"))
x, y, width, height = params["reference_crop_pixels"]
original = Image.open(production / "references/original/school-of-athens.jpg").convert("RGB")
reference = original.crop((x, y, x + width, y + height)).resize((800, 600))
render = Image.open(run / "hero.png").convert("RGB").resize((800, 600))
pair = Image.new("RGB", (1600, 650), "#22252a")
pair.paste(reference, (0, 50))
pair.paste(render, (800, 50))
draw = ImageDraw.Draw(pair)
draw.text((16, 18), "REFERENCE: fixed crop [128,128,1024,768] / local QA only", fill="white")
draw.text((816, 18), "ACTUAL WINDOWS PLAYER: P0 structure / baseline diagnostic figure", fill="white")
overlay = Image.blend(reference, render, .5)
overlay_draw = ImageDraw.Draw(overlay)
for i, anchor in enumerate(report["anchors"], 1):
    ref_uv = anchor["reference_uv_top"]
    act_uv = anchor["actual_uv_top"]
    rx, ry = ref_uv["x"] * 800, ref_uv["y"] * 600
    ax, ay = act_uv["x"] * 800, act_uv["y"] * 600
    for px, py, color, offset in ((rx, ry, "#35edac", 0), (ax, ay, "#ff6381", 800)):
        draw.ellipse((offset + px - 4, py + 46, offset + px + 4, py + 54), outline=color, width=2)
        draw.text((offset + px + 6, py + 43), str(i), fill=color)
    overlay_draw.line((rx, ry, ax, ay), fill="#ffed8a", width=2)
    overlay_draw.ellipse((rx - 4, ry - 4, rx + 4, ry + 4), outline="#35edac", width=2)
    overlay_draw.ellipse((ax - 3, ay - 3, ax + 3, ay + 3), outline="#ff6381", width=2)
    overlay_draw.text((rx + 6, ry - 8), str(i), fill="white")
pair.save(run / "reference-comparison.png")
overlay.save(run / "reference-overlay.png")
summary = {
    "reference_crop_pixels": [x, y, width, height],
    "method": "Manual painting annotations versus projected actual saved mesh vertices/edge and actual Renderer bounds; source objects and vertex indices are in anchors. Color overlay is visual QA only.",
    "reference_annotation_uncertainty_px": 8,
    "max_error_percent_width": max(a["error_fraction_of_width"] for a in report["anchors"]) * 100,
    "mean_error_percent_width": sum(a["error_fraction_of_width"] for a in report["anchors"]) / len(report["anchors"]) * 100,
    "anchors": report["anchors"],
    "not_covered": ["outer decorated fresco frame", "full philosopher crowd", "architectural statues and figurative reliefs", "final surface texture detail", "finished character face/hands/gesture"],
}
(run / "composition-comparison.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"comparison": str(run / "reference-comparison.png"), "max_error_percent_width": summary["max_error_percent_width"]}, ensure_ascii=False))
