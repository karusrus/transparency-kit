#!/bin/sh
# Rebuild the JSON and push it into the running n8n WITHOUT wiping the database (keeps owner, API key, credentials).
set -e
cd "$(dirname "$0")"
python3 workflows/build.py
docker exec n8n n8n import:workflow --input=/workflows/transparency-kit.json | tail -1
docker exec n8n n8n import:workflow --input=/workflows/audit-view.json | tail -1
docker exec n8n n8n import:workflow --input=/workflows/sample-line.json | tail -1
docker exec n8n n8n import:workflow --input=/workflows/host-line.json | tail -1
docker exec n8n n8n publish:workflow --id=AiActTransparenc >/dev/null
docker exec n8n n8n publish:workflow --id=AiActAuditView00 >/dev/null
docker exec n8n n8n publish:workflow --id=RecyclingVoices1 >/dev/null
docker restart n8n >/dev/null
sleep 22
for u in form/ai-act-intake webhook/audit; do printf '%s ' "$u"; curl -s -o /dev/null -w '%{http_code}\n' "http://localhost:5678/$u"; done
