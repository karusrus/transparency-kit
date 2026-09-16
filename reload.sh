#!/bin/sh
# Rebuild the workflow JSON, wipe the local n8n and load the kit fresh. Local demo only.
set -e
cd "$(dirname "$0")"
python3 workflows/build.py
docker rm -f n8n >/dev/null 2>&1 || true
docker volume rm n8n_data >/dev/null 2>&1 || true
docker run -d --name n8n -p 5678:5678 \
  -v n8n_data:/home/node/.n8n \
  -v "$PWD/data":/data \
  -v "$PWD/workflows":/workflows:ro \
  -e N8N_SECURE_COOKIE=false -e GENERIC_TIMEZONE=Europe/Sofia -e TZ=Europe/Sofia \
  -e N8N_RUNNERS_ENABLED=true -e N8N_DIAGNOSTICS_ENABLED=false -e 'NODES_EXCLUDE=[]' -e N8N_RESTRICT_FILE_ACCESS_TO=/data \
  n8n-ffmpeg >/dev/null
sleep 16
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
