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
# the registry lives in Postgres now: latest snapshot, plus counts for the Auditor block
import subprocess
def psql(sql):
    try:
        return subprocess.run(["docker", "exec", "kit-db", "psql", "-U", "kit", "-d", "kit", "-At", "-c", sql], capture_output=True, text=True, timeout=30).stdout.strip()
    except Exception:
        return ""
raw = psql("select registry::text from registry_snapshots order by seq desc limit 1")
if raw:
    registry = json.loads(raw)
    registry["audit"] = {
        "media": int(psql("select count(*) from assets where asset_type <> 'text'") or 0),
        "texts": int(psql("select count(*) from assets where asset_type = 'text'") or 0),
        "approvals": int(psql("select count(*) from decisions") or 0),
        "awaiting": int(psql("select count(*) from assets where status = 'pending_review'") or 0),
        "chain_ok": psql("select count(*) filter (where not ok) = 0 from verify_chain()") == "t",
    }

bundle = {"workflows": workflows, "registry": registry, "note": "AI Act Transparency Kit · n8n workflows + registry with path analysis, for Pipeline Map (Import n8n)"}
out = HERE / "docs" / "transparency-kit.bundle.json"
out.write_text(json.dumps(bundle, ensure_ascii=False))
print("wrote", out, f"({len(workflows)} workflows, registry: {'yes' if registry else 'no'})")
pm = HERE.parent / "pipeline-map" / "docs"
if pm.exists():
    (pm / "transparency-kit.bundle.json").write_text(json.dumps(bundle, ensure_ascii=False))
    print("copied to", pm / "transparency-kit.bundle.json")
