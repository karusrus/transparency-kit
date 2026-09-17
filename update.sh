#!/bin/sh
# Rebuild the JSON and push it into the running n8n WITHOUT wiping anything (keeps owner, API key, credentials, the database).
set -e
cd "$(dirname "$0")"
python3 workflows/build.py
for f in transparency-kit audit-view sample-line sample-50-3 sample-chatbot host-line; do docker exec n8n n8n import:workflow --input=/workflows/$f.json | tail -1; done
for id in AiActTransparenc AiActAuditView00 RecyclingVoices1; do docker exec n8n n8n publish:workflow --id=$id >/dev/null; done
docker restart n8n >/dev/null
sleep 22
for u in form/ai-act-intake form/notice webhook/audit; do printf '%s ' "$u"; curl -s -o /dev/null -w '%{http_code}\n' "http://localhost:5678/$u"; done
