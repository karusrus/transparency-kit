#!/bin/sh
# The three numbers an operations lead is asked for, straight from the ledger.
docker exec kit-db psql -U kit -d kit -At -F ' | ' -c "
select 'assets through the gate' as metric, count(*)::text from assets where status <> 'pending_review'
union all select 'returned (%)', round(100.0 * count(*) filter (where status = 'returned') / nullif(count(*) filter (where status <> 'pending_review'), 0), 1)::text from assets
union all select 'median decision time', to_char(percentile_cont(0.5) within group (order by decided_at - created_at), 'HH24:MI:SS') from assets where decided_at is not null
union all select 'p90 decision time', to_char(percentile_cont(0.9) within group (order by decided_at - created_at), 'HH24:MI:SS') from assets where decided_at is not null
union all select 'reviewers', count(distinct reviewer)::text from decisions
union all select 'runs (distinct days)', count(distinct created_at::date)::text from assets
union all select 'decisions in the ledger', count(*)::text from decisions
union all select 'chain verified', (count(*) filter (where not ok) = 0)::text from verify_chain()
union all (select 'AI systems on the instance (last snapshot)', systems::text from registry_snapshots order by seq desc limit 1);
"
