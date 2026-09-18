#!/bin/sh
# What the ledger claims, checked instead of asserted. Runs against a throwaway database in the
# running kit-db container, so the real ledger is never touched.
#
#   sh db/test-chain.sh
#
# Checks: append-only (UPDATE, DELETE, TRUNCATE all refused) · a tampered row is caught ·
# the chain verifies identically from another time zone (the v1 bug, fixed 2026-09-18).
set -e
cd "$(dirname "$0")/.."
DB=kit_chain_test
PSQL="docker exec -i kit-db psql -U kit -v ON_ERROR_STOP=1 -Atq"

fail() { echo "FAIL · $1"; exit 1; }
ok()   { echo "  ok · $1"; }

docker exec kit-db psql -U kit -d postgres -Atqc "drop database if exists $DB" >/dev/null
docker exec kit-db psql -U kit -d postgres -Atqc "create database $DB" >/dev/null
$PSQL -d $DB < db/schema.sql >/dev/null

$PSQL -d $DB >/dev/null <<'SQL'
insert into assets (id, line, asset_type, category, manifest) values
  ('t1','test line','image','synthetic_media','{}'::jsonb),
  ('t2','test line','text','generated_text','{}'::jsonb),
  ('t3','test line','audio','synthetic_media','{}'::jsonb);
insert into decisions (asset_id, reviewer, decision, disclosure_status, responsible_person) values
  ('t1','anna','approved','disclosed','anna'),
  ('t2','boris','returned','returned','boris'),
  ('t3','anna','approved','disclosed','anna');
SQL

echo "chain"
[ "$($PSQL -d $DB -c "select count(*) from verify_chain() where not ok")" = "0" ] || fail "свежая цепочка не проходит проверку"
ok "три решения, цепочка верна"
[ "$($PSQL -d $DB -c "select count(*) from verify_chain() where alg <> 'v2'")" = "0" ] || fail "новые записи посчитаны не форматом v2"
ok "все записи в формате v2"

echo "append-only"
$PSQL -d $DB -c "update decisions set reviewer='mallory' where seq=1" >/dev/null 2>&1 && fail "UPDATE прошёл" || ok "UPDATE отбит"
$PSQL -d $DB -c "delete from decisions where seq=1" >/dev/null 2>&1 && fail "DELETE прошёл" || ok "DELETE отбит"
$PSQL -d $DB -c "truncate decisions" >/dev/null 2>&1 && fail "TRUNCATE прошёл" || ok "TRUNCATE отбит"

echo "tamper"
# подмена в обход триггера: снимаем его, как это сделал бы владелец базы, и правим строку
$PSQL -d $DB >/dev/null <<'SQL'
alter table decisions disable trigger decisions_immutable_trg;
update decisions set reviewer = 'mallory' where seq = 2;
alter table decisions enable trigger decisions_immutable_trg;
SQL
BROKEN=$($PSQL -d $DB -c "select count(*) from verify_chain() where not ok")
[ "$BROKEN" -ge 1 ] || fail "подмена строки не обнаружена"
ok "подменённая строка поймана ($BROKEN из 3)"

echo "time zone"
A=$($PSQL -d $DB -c "set timezone='UTC'; select count(*) from verify_chain() where not ok")
B=$($PSQL -d $DB -c "set timezone='America/Los_Angeles'; select count(*) from verify_chain() where not ok")
C=$($PSQL -d $DB -c "set timezone='Asia/Tokyo'; set datestyle='SQL, DMY'; select count(*) from verify_chain() where not ok")
[ "$A" = "$B" ] && [ "$A" = "$C" ] || fail "результат зависит от таймзоны: UTC=$A LA=$B Tokyo=$C"
ok "одинаково в UTC, Лос-Анджелесе и Токио ($A нарушений)"

docker exec kit-db psql -U kit -d postgres -Atqc "drop database $DB" >/dev/null
echo "все проверки пройдены"
