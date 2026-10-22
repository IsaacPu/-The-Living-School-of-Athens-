"""Recheck substantive test files against the pre-isolation SHA-256 snapshot."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

production = Path(__file__).resolve().parents[1]
workspace = production.parent
baseline_file = workspace / "project-management/isolation-20261022/baseline-before-move.json"
baseline = json.loads(baseline_file.read_text(encoding="utf-8-sig"))
test_root = workspace / "test-project"
failures = []
for entry in baseline["baselineFiles"]:
    path = (test_root / entry["path"]).resolve()
    if not path.is_relative_to(test_root):
        raise ValueError("Baseline path escapes test-project")
    if not path.is_file():
        failures.append({"path": entry["path"], "reason": "missing"})
        continue
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    if path.stat().st_size != entry["bytes"] or digest != entry["sha256"]:
        failures.append({"path": entry["path"], "reason": "changed", "actual_sha256": digest})
report = {"schema_version": 1, "utc": datetime.now(timezone.utc).isoformat(),
          "passed": not failures, "checked_files": len(baseline["baselineFiles"]),
          "baseline": "project-management/isolation-20261022/baseline-before-move.json",
          "scope": "Only files in the original substantive-file snapshot; excluded caches/runtime logs and new files are outside this check.",
          "failures": failures}
output = production / "qa/integration/test-preservation.json"
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
print(json.dumps({"passed": report["passed"], "checked_files": report["checked_files"], "failures": failures}))
raise SystemExit(0 if report["passed"] else 1)
