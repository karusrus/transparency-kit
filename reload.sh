#!/bin/sh
# First run, or a clean slate: builds the workflow JSON, wipes the local stack (n8n + Postgres), starts both,
# imports the database credential and all workflows, publishes them. Local demo only — it deletes the owner account too.
set -e
cd "$(dirname "$0")"
[ -f .env ] || { echo "KIT_DB_PASSWORD=$(openssl rand -hex 16)" > .env; }
. ./.env
[ -f secrets/postgres-credential.json ] || { mkdir -p secrets; printf '[{"id":"KitPostgresCred01","name":"kit-db","type":"postgres","data":{"host":"kit-db","database":"kit","user":"kit","password":"%s","port":5432,"ssl":"disable","allowUnauthorizedCerts":false}}]\n' "$KIT_DB_PASSWORD" > secrets/postgres-credential.json; }
python3 workflows/build.py
docker rm -f n8n kit-db >/dev/null 2>&1 || true
docker volume rm n8n_data kit_db >/dev/null 2>&1 || true
docker network create kit-net >/dev/null 2>&1 || true
docker run -d --name kit-db --network kit-net \
  -e POSTGRES_DB=kit -e POSTGRES_USER=kit -e POSTGRES_PASSWORD="$KIT_DB_PASSWORD" \
  -v kit_db:/var/lib/postgresql/data -v "$PWD/db/schema.sql":/docker-entrypoint-initdb.d/01-schema.sql:ro \
  postgres:16-alpine >/dev/null
until docker exec kit-db pg_isready -U kit -d kit >/dev/null 2>&1; do sleep 1; done
docker build -q -t kit-media-label tools/media-label >/dev/null
docker rm -f kit-media-label >/dev/null 2>&1 || true
docker network create kit-net >/dev/null 2>&1 || true
docker run -d --name kit-media-label --network kit-net kit-media-label >/dev/null
docker run -d --name n8n --network kit-net -p 5678:5678 --add-host host.docker.internal:host-gateway \
  -v n8n_data:/home/node/.n8n -v "$PWD/data":/data -v "$PWD/workflows":/workflows:ro -v "$PWD/secrets":/secrets:ro \
  -e N8N_SECURE_COOKIE=false -e GENERIC_TIMEZONE=Europe/Sofia -e TZ=Europe/Sofia \
  -e N8N_RUNNERS_ENABLED=true -e N8N_DIAGNOSTICS_ENABLED=false -e 'NODES_EXCLUDE=[]' -e N8N_RESTRICT_FILE_ACCESS_TO=/data \
  n8n-ffmpeg >/dev/null
sleep 16
docker exec n8n n8n import:credentials --input=/secrets/postgres-credential.json | tail -1
for f in transparency-kit audit-view sample-line sample-50-3 sample-chatbot host-line; do docker exec n8n n8n import:workflow --input=/workflows/$f.json | tail -1; done
for id in AiActTransparenc AiActAuditView00 RecyclingVoices1; do docker exec n8n n8n publish:workflow --id=$id >/dev/null; done
docker restart n8n >/dev/null
sleep 22
for u in form/ai-act-intake form/notice webhook/audit; do printf '%s ' "$u"; curl -s -o /dev/null -w '%{http_code}\n' "http://localhost:5678/$u"; done
