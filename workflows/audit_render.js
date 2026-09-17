// Renders the auditor's page from the files the kit writes. Input: stdout of "Collect files".
const raw = String($input.first().json.stdout || '');
const sec = { REGISTRY: '', MANIFESTS: '', APPROVALS: '', INBOX: '' };
let cur = null;
for (const line of raw.split('\n')) {
  const m = line.match(/^###(REGISTRY|MANIFESTS|APPROVALS|INBOX)\s*$/);
  if (m) { cur = m[1]; continue; }
  if (cur) sec[cur] += line + '\n';
}
const parseLines = (s) => s.split('\n').map(l => l.trim()).filter(l => l.startsWith('{')).map(l => { try { return JSON.parse(l); } catch (e) { return null; } }).filter(Boolean);
let registry = null; try { registry = JSON.parse(sec.REGISTRY.trim()); } catch (e) {}
const manifests = parseLines(sec.MANIFESTS).sort((a, b) => String(b.created_at).localeCompare(String(a.created_at)));
const inbox = parseLines(sec.INBOX).sort((a, b) => String(b.created_at).localeCompare(String(a.created_at)));
const approvals = parseLines(sec.APPROVALS).sort((a, b) => String(b.decided_at).localeCompare(String(a.decided_at)));

const esc = (v) => String(v === null || v === undefined ? '' : v).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const dt = (v) => v ? esc(String(v).replace('T', ' ').slice(0, 16)) : '';
const pill = (v) => {
  const map = { approved: 'ok', disclosed: 'ok', editorial_exception: 'warn', not_required: 'muted', pending_review: 'warn', returned: 'bad', 'n/a': 'muted', internal: 'muted', editorial: 'warn', verify: 'warn', uncovered: 'bad', likeness: 'bad' };
  return `<span class="pill ${map[v] || 'muted'}">${esc(v)}</span>`;
};
const table = (cols, rows) => rows.length
  ? `<table><thead><tr>${cols.map(c => `<th>${esc(c[0])}</th>`).join('')}</tr></thead><tbody>${rows.map(r => `<tr>${cols.map(c => `<td>${c[1](r)}</td>`).join('')}</tr>`).join('')}</tbody></table>`
  : `<p class="empty">Nothing recorded yet.</p>`;

const media = manifests.filter(m => m.asset_type !== 'text');
const texts = manifests.filter(m => m.asset_type === 'text');
const systems = registry && Array.isArray(registry.systems) ? registry.systems : [];

const blocks = [
  {
    n: 1, title: 'AI-systems registry', art: 'voluntary · supports Art. 4 literacy',
    what: 'Every AI system on this n8n instance, with path analysis: from each node that calls a model, every path forward to a node that reaches people, and what stands in between. Plus every external generator declared at intake. Read from the instance, not typed by hand.',
    body: table([
      ['Status', r => pill(r.path_status)],
      ['Workflow / line', r => esc(r.workflow) + (r.workflow_active === true ? ' <span class="pill ok">active</span>' : r.workflow_active === false ? ' <span class="pill muted">inactive</span>' : '')],
      ['System (node)', r => esc(r.system) + (r.likeness ? ' <span class="pill warn">face/voice</span>' : '')], ['Node type', r => `<code>${esc(r.node_type)}</code>`], ['Model', r => esc(r.model)],
      ['Reaches people via', r => esc((r.exits || []).join(', '))],
      ['Evidence (path)', r => `<span class="ev">${esc(r.evidence)}</span>`],
      ['Source', r => esc(r.source)], ['Assets', r => esc(r.assets || '')],
    ], systems),
    foot: registry ? `${registry.registry_partial ? '<b style="color:var(--bad)">Partial: the instance could not be read (n8n API credential missing); only declared generators are listed.</b><br>' : ''}Generated ${dt(registry.generated_at)} · ${registry.instance_workflows || 0} workflows scanned: ${(registry.workflows_scanned || []).map(w => esc(w.name)).join(' · ')}<br>Rules: ${esc(registry.rules || '')}` : 'Registry file not written yet.',
  },
  {
    n: 2, title: 'Synthetic media and deep fakes', art: 'Art. 50(4) §1 · Art. 50(2)',
    what: 'Images, video and audio. A real person depicted means deep fake: visible disclosure plus consent on file. Provenance manifest for all of them.',
    body: table([
      ['ID', r => `<code>${esc(r.id)}</code>`], ['Type', r => esc(r.asset_type)], ['Category', r => pill(r.category)],
      ['Real person', r => r.depicts_real_person ? 'yes' : 'no'], ['Consent', r => esc(r.consent_reference)],
      ['Disclosure', r => !r.label_required ? 'none' : r.asset_type === 'audio' ? `metadata + sentence at publication (${esc(r.label_basis)})` : `burnt-in label (${esc(r.label_basis)})`], ['Model', r => esc(r.model + (r.model_version ? ' ' + r.model_version : ''))],
      ['Prompt hash', r => `<code>${esc(String(r.prompt_sha256).slice(0, 12))}</code>`], ['Operator', r => esc(r.operator)],
      ['Status', r => pill(r.disclosure_status || r.status)], ['Artefact', r => esc(r.labelled_path || r.incoming_path || '')],
    ], media),
  },
  {
    n: 3, title: 'Generated text', art: 'Art. 50(4) §2',
    what: 'Text published to inform the public must say it is AI-generated, unless a named person exercised editorial control and holds responsibility. The gate records which of the two applies.',
    body: table([
      ['ID', r => `<code>${esc(r.id)}</code>`], ['Public information', r => r.public_information ? 'yes' : 'no'],
      ['Disclosure', r => pill(r.disclosure_status || r.status)], ['Responsible person', r => esc(r.responsible_person || '')],
      ['Model', r => esc(r.model)], ['Operator', r => esc(r.operator)], ['Decided', r => dt(r.decided_at)],
      ['Text', r => `<details><summary>${esc(String(r.text_content || '').slice(0, 60))}…</summary><pre>${esc(r.disclosed_text || r.text_content)}</pre></details>`],
    ], texts),
  },
  {
    n: 4, title: 'Approval log', art: 'voluntary · Art. 26(6)-style record',
    what: 'Who approved or returned what, when, and why. Human oversight as a property of the line. Record-keeping is mandatory only for high-risk systems (Art. 26(6)); this kit keeps it anyway. Reviewer identity is self-declared unless the gate is behind an authenticated channel.',
    body: table([
      ['Decided', r => dt(r.decided_at)], ['ID', r => `<code>${esc(r.id)}</code>`], ['Reviewer', r => esc(r.reviewer)],
      ['Decision', r => esc(r.decision)], ['Outcome', r => pill(r.disclosure_status)], ['Reason', r => esc(r.reason || r.note || '')],
      ['Artefact', r => esc(r.artefact)], ['Execution', r => `<code>${esc(r.execution_id)}</code>`],
    ], approvals),
  },
];

const stat = (n, l) => `<div class="stat"><b>${n}</b><span>${l}</span></div>`;
const html = `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Audit view · AI Act Transparency Kit</title>
<style>
:root{--bg:#f6f7f9;--card:#fff;--ink:#14171c;--mut:#6b7280;--line:#e5e7eb;--acc:#1d4ed8;--ok:#0f766e;--warn:#b45309;--bad:#b91c1c}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.45 -apple-system,Inter,Segoe UI,Roboto,sans-serif}
header{padding:28px 32px 12px}h1{margin:0 0 4px;font-size:22px}header p{margin:0;color:var(--mut)}
.stats{display:flex;gap:12px;padding:8px 32px 20px;flex-wrap:wrap}.stat{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px 16px;min-width:130px}
.stat b{display:block;font-size:22px}.stat span{color:var(--mut);font-size:12px}
main{display:grid;gap:18px;padding:0 32px 40px}
section{background:var(--card);border:1px solid var(--line);border-radius:12px;overflow:hidden}
section>.hd{display:flex;align-items:baseline;gap:12px;padding:14px 18px;border-bottom:1px solid var(--line)}
.hd .n{width:28px;height:28px;border-radius:50%;background:var(--acc);color:#fff;display:inline-flex;align-items:center;justify-content:center;font-weight:600;flex:none}
.hd h2{margin:0;font-size:16px}.hd .art{margin-left:auto;color:var(--acc);font-weight:600;white-space:nowrap}
.what{padding:10px 18px;color:var(--mut);border-bottom:1px solid var(--line)}
.wrap{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:13px}th,td{padding:8px 12px;text-align:left;vertical-align:top;border-bottom:1px solid var(--line)}
th{font-weight:600;color:var(--mut);font-size:12px;text-transform:uppercase;letter-spacing:.03em;white-space:nowrap}
code{font:12px ui-monospace,SFMono-Regular,Menlo,monospace}pre{white-space:pre-wrap;margin:6px 0 0;font:12px ui-monospace,Menlo,monospace}
.pill{display:inline-block;padding:2px 8px;border-radius:999px;font-size:12px;font-weight:600}.pill.ok{background:#ccfbf1;color:var(--ok)}.pill.warn{background:#fef3c7;color:var(--warn)}.pill.bad{background:#fee2e2;color:var(--bad)}.pill.muted{background:#f3f4f6;color:var(--mut)}
.empty{padding:14px 18px;color:var(--mut);margin:0}.ev{font-size:12px;color:var(--mut)}a{color:var(--acc)}.foot{padding:8px 18px;color:var(--mut);font-size:12px}
footer{padding:0 32px 40px;color:var(--mut);font-size:12px}
</style></head><body>
<header><h1>Audit view · AI Act Transparency Kit</h1><p>What the auditor reads instead of the pipeline. Deployer obligations under the EU AI Act, filled automatically by the line. Generated ${dt(new Date().toISOString())}.</p></header>
<div class="stats">${stat(systems.length, 'AI systems on the instance')}${stat(systems.filter(r => r.path_status === 'uncovered' || r.path_status === 'likeness').length, 'reach people uncovered')}${stat(systems.filter(r => r.path_status === 'editorial' || r.path_status === 'verify').length, 'need a decision')}${stat(media.length, 'synthetic media assets')}${stat(texts.length, 'generated texts')}${stat(approvals.length, 'decisions logged')}${stat(inbox.length, 'awaiting a human')}</div>
<main>${inbox.length ? `<section><div class="hd"><span class="n">!</span><h2>Awaiting a human</h2><span class="art">the gate · a named person decides</span></div><p class="what">Assets stopped at the gate. Open the link, decide, and the row moves to the approval log.</p><div class="wrap">${table([['Since', r => dt(r.created_at)], ['Line', r => esc(r.line)], ['Asset', r => `<code>${esc(r.id)}</code>`], ['Type', r => esc(r.asset_type)], ['Category', r => pill(r.category)], ['Model', r => esc(r.model)], ['Operator', r => esc(r.operator)], ['Gate', r => `<a href="${esc(r.gate_url)}">open the gate →</a>`]], inbox)}</div></section>` : ''}${blocks.map(b => `<section><div class="hd"><span class="n">${b.n}</span><h2>${esc(b.title)}</h2><span class="art">${esc(b.art)}</span></div><p class="what">${esc(b.what)}</p><div class="wrap">${b.body}</div>${b.foot ? `<p class="foot">${b.foot}</p>` : ''}</section>`).join('')}</main>
<footer>Scope: deployer duties under Article 50 (in force 2 Aug 2026) and Article 4. High-risk obligations (Annex III) are out of scope and not claimed. Sources: files under /data written by the “AI Act Transparency Kit” workflow.</footer>
</body></html>`;
return [{ json: { html, systems: systems.length, manifests: manifests.length, approvals: approvals.length } }];
