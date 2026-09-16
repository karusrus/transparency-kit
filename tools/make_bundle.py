#!/usr/bin/env python3
"""Bundles the kit's workflows and the current registry into one JSON for Pipeline Map's n8n importer.

  python3 tools/make_bundle.py            → docs/transparency-kit.bundle.json (+ a copy into ../pipeline-map/docs/)

Order matters for the picture: the production line first, the kit second, the unsafe sample third, the audit view last.
"""
import json, pathlib, glob

HERE = pathlib.Path(__file__).resolve().parent.parent
WF = HERE / "workflows"
ORDER = ["host-line.json", "transparency-kit.json", "sample-line.json", "audit-view.json"]
ACTIVE = {"host-line.json": True, "transparency-kit.json": True, "sample-line.json": False, "audit-view.json": True}

workflows = []
for name in ORDER:
    wf = json.loads((WF / name).read_text())
    wf["active"] = ACTIVE[name]
    workflows.append(wf)

registry = None
reg_path = HERE / "data" / "registry.json"
if reg_path.exists():
    registry = json.loads(reg_path.read_text())
    manifests = [json.loads(pathlib.Path(p).read_text()) for p in glob.glob(str(HERE / "data/manifests/*.json"))] if (HERE / "data/manifests").exists() else []
    registry["audit"] = {
        "media": sum(1 for m in manifests if m.get("asset_type") != "text"),
        "texts": sum(1 for m in manifests if m.get("asset_type") == "text"),
        "approvals": len(glob.glob(str(HERE / "data/approvals/*.json"))),
        "awaiting": len(glob.glob(str(HERE / "data/inbox/*.json"))),
    }

bundle = {"workflows": workflows, "registry": registry, "note": "AI Act Transparency Kit · n8n workflows + registry with path analysis, for Pipeline Map (Import n8n)"}
out = HERE / "docs" / "transparency-kit.bundle.json"
out.write_text(json.dumps(bundle, ensure_ascii=False))
print("wrote", out, f"({len(workflows)} workflows, registry: {'yes' if registry else 'no'})")
pm = HERE.parent / "pipeline-map" / "docs"
if pm.exists():
    (pm / "transparency-kit.bundle.json").write_text(json.dumps(bundle, ensure_ascii=False))
    print("copied to", pm / "transparency-kit.bundle.json")
