#!/usr/bin/env python3
"""Generates the n8n workflows of the AI Act Transparency Kit.

  transparency-kit.json  the kit: two entries (own form, or called by another workflow) → Art. 50 classification
                         → label → manifest → Wait-form human gate → approval log → instance-wide AI-systems registry
                         with path analysis (generator → exit: disclosed / editorial / verify / uncovered / likeness)
  audit-view.json        GET /webhook/audit → the auditor's page
  host-line.json         a real production line: notice text → Kokoro, three voices → AI Act gate → publish
  sample-line.json       (hand-written) a marketing line without any gate, for the registry to flag

Run:  python3 workflows/build.py
"""
import json, uuid, pathlib

HERE = pathlib.Path(__file__).parent
DATA = "/data"
KIT_ID = "AiActTransparenc"
AUDIT_ID = "AiActAuditView00"
HOST_ID = "RecyclingVoices1"
# Credential "n8n API" created by hand in the UI (Settings → n8n API → key; Credentials → n8n API). Needs workflow:list.
# The id is local to this instance; on another instance attach the credential in the editor instead.
N8N_API_CREDENTIAL_ID = "57qykOiFfUipk1bM"
N8N_API_CREDENTIAL_NAME = "n8n ruslan"
KOKORO_URL = "http://host.docker.internal:8880/tts"


def nid():
    return str(uuid.uuid4())


def node(name, type_, version, params, x, y, **extra):
    n = {"id": nid(), "name": name, "type": type_, "typeVersion": version, "position": [x, y], "parameters": params}
    n.update(extra)
    return n


def cond(left, right, op="equals", kind="string"):
    return {"options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict", "version": 2},
            "conditions": [{"id": nid(), "leftValue": left, "rightValue": right, "operator": {"type": kind, "operation": op}}],
            "combinator": "and"}


def wire(*pairs):
    c = {}
    for src, dst, *idx in pairs:
        out = idx[0] if idx else 0
        c.setdefault(src, {"main": []})
        while len(c[src]["main"]) <= out:
            c[src]["main"].append([])
        c[src]["main"][out].append({"node": dst, "type": "main", "index": 0})
    return c


def X(step):
    return 240 * step


# ============================================================================ kit: JavaScript
CLASSIFY_JS = r"""
// Article 50 classification for a deployer. One item in, one item out.
// Accepts the form's field labels or snake_case fields from a calling workflow.
const it = $input.first();
const f = it.json || {};
const g = (label, key) => (f[label] !== undefined && f[label] !== '' ? f[label] : f[key]);
const now = new Date();
const id = now.toISOString().slice(0,23).replace(/[:T.]/g,'-') + '-' + String(f.prompt_sha256 || '').slice(0,6) + Math.random().toString(36).slice(2,6);
const type = String(g('Asset type', 'asset_type') || '').toLowerCase();
const yes = (v) => ['yes', 'true', '1'].includes(String(v ?? 'no').toLowerCase());
const realPerson = yes(g('Depicts a real person (face or voice)?', 'depicts_real_person'));
const publicInfo = yes(g('Published to inform the public on a matter of public interest?', 'public_information') ?? g('Published to inform the public?', 'public_information'));
const lang = String(g('Language of the asset', 'language') || 'en').slice(0, 2).toLowerCase();
const model = String(g('Model', 'model') || '');
const binary_key = it.binary && it.binary.File ? 'File' : (it.binary && it.binary.data ? 'data' : null);
const file = binary_key ? it.binary[binary_key] : null;
const ALLOWED = { image: ['png','jpg','jpeg','webp'], video: ['mp4','mov','webm'], audio: ['wav','mp3','m4a','ogg'] };
const rawExt = file && file.fileName && file.fileName.includes('.') ? file.fileName.split('.').pop().toLowerCase() : '';
const ext = (ALLOWED[type] || []).includes(rawExt) ? '.' + rawExt : ((ALLOWED[type] || [''])[0] ? '.' + ALLOWED[type][0] : '');
const shellSafe = (v) => String(v ?? '').replace(/[^\p{L}\p{N} .,;:()\-_/§·]/gu, '').slice(0, 160);   // nothing from a user reaches the shell unfiltered

// Approved disclosure wording per language. Legal text is fixed, not generated: change it here, with counsel, not per asset.
const DISCLOSURE = {
  en: (m) => `This ${type} was created with an AI system (${m}).`,
  bg: (m) => `Този ${({text:'текст',image:'образ',video:'видеоклип',audio:'аудиозапис'})[type] || 'материал'} е създаден с помощта на изкуствен интелект (${m}).`,
  ru: (m) => `${({text:'Этот текст создан',image:'Это изображение создано',video:'Это видео создано',audio:'Эта аудиозапись создана'})[type] || 'Этот материал создан'} с помощью системы искусственного интеллекта (${m}).`,
  de: (m) => `${({text:'Dieser Text wurde',image:'Dieses Bild wurde',video:'Dieses Video wurde',audio:'Diese Aufnahme wurde'})[type] || 'Dieses Material wurde'} mit einem KI-System erstellt (${m}).`,
};
const disclosure_sentence = (DISCLOSURE[lang] || DISCLOSURE.en)(model || 'AI system');

let category, label_required = false, label_basis = 'none';
const obligations = [], other_law = [];
if (type === 'text') {
  if (publicInfo) {
    category = 'generated_public_text'; label_required = true; label_basis = 'law';
    obligations.push('Art. 50(4) §2 — text published to inform the public on matters of public interest must be disclosed as AI-generated, unless a human exercised editorial control and a person holds editorial responsibility.');
  } else {
    category = 'internal_text';
    obligations.push('No Art. 50 duty: not published to inform the public. Provenance is recorded anyway.');
  }
} else {
  if (realPerson) {
    category = 'deepfake'; label_required = true; label_basis = 'law';
    obligations.push('Art. 50(4) §1 — image, audio or video resembling a real person must carry a disclosure that it is artificially generated or manipulated (deep fake, Art. 3(60)). Artistic or satirical works: disclosure may be limited so it does not hamper the work.');
    other_law.push('Consent or another legal basis for using the person\'s likeness or voice: GDPR and personality rights, not the AI Act (consent reference below).');
  } else {
    category = 'synthetic_media';
    label_required = (type === 'image' || type === 'video' || (type === 'audio' && publicInfo));
    label_basis = label_required ? 'house policy' : 'none';
    obligations.push('Art. 50(2) machine-readable marking is the provider\'s duty; as deployer we keep a provenance manifest and apply a disclosure by house policy.');
  }
}

const label_text = 'AI-generated · EU AI Act Art. 50';
const inPath  = `/data/incoming/${id}${ext}`;
const outPath = `/data/labelled/${id}${ext}`;
const font = '/usr/share/fonts/DejaVuSans.ttf';
const draw = `drawtext=fontfile=${font}:text='${label_text}':fontcolor=white:fontsize=h/28:box=1:boxcolor=black@0.55:boxborderw=10:x=20:y=h-th-20`;
const meta = `-metadata comment="${label_text}; manifest ${id}" -metadata title="${shellSafe(disclosure_sentence)}"`;
let ffmpeg_cmd = '';
if (type === 'image')      ffmpeg_cmd = `ffmpeg -y -loglevel error -i "${inPath}" -vf "${draw}" ${meta} "${outPath}"`;
else if (type === 'video') ffmpeg_cmd = `ffmpeg -y -loglevel error -i "${inPath}" -vf "${draw}" -c:a copy ${meta} "${outPath}"`;
else if (type === 'audio') ffmpeg_cmd = `ffmpeg -y -loglevel error -i "${inPath}" -c copy ${meta} "${outPath}"`;

const manifest = {
  id, created_at: now.toISOString(),
  line: String(g('Calling workflow', 'caller_workflow') || 'manual intake'),
  asset_type: type, category, label_required, label_basis, label_text: label_required ? label_text : null,
  obligations, other_law,
  model, model_version: String(g('Model version', 'model_version') || ''),
  prompt_sha256: f.prompt_sha256 || '',
  operator: String(g('Operator', 'operator') || ''),
  depicts_real_person: realPerson, consent_reference: String(g('Consent reference', 'consent_reference') || ''),
  public_information: publicInfo,
  source_file: file ? file.fileName : null,
  incoming_path: file ? inPath : null, labelled_path: (file && ffmpeg_cmd) ? outPath : null,
  text_content: type === 'text' ? String(g('Text content', 'text_content') || '') : null,
  language: lang, disclosure_sentence,
  status: 'pending_review',
};
return [{ json: { ...manifest, ext, ffmpeg_cmd, binary_key }, binary: it.binary }];
"""

TEXT_JS = r"""
// Text branch: prepare the disclosed version. The gate may later replace it with an editorial exception.
const m = $('Classify (Art. 50)').first().json;
const footer = '\n\n— ' + m.disclosure_sentence;
return [{ json: { ...m, disclosed_text: m.label_required ? m.text_content + footer : m.text_content } }];
"""

MANIFEST_JS = r"""
// Collect everything into the manifest, add the gate link, encode files for shell-safe writes.
const m = { ...$('Classify (Art. 50)').first().json };
delete m.ext; delete m.ffmpeg_cmd; delete m.binary_key;
const src = $input.first().json;
if (src.disclosed_text !== undefined) m.disclosed_text = src.disclosed_text;
if (src.exitCode !== undefined) { m.label_exit_code = src.exitCode; if (src.stderr) m.label_stderr = String(src.stderr).slice(0, 500); }
m.gate_url = $execution.resumeFormUrl;
const inbox = { id: m.id, line: m.line, asset_type: m.asset_type, category: m.category, model: m.model, operator: m.operator,
                created_at: m.created_at, gate_url: m.gate_url, execution_id: $execution.id };
const b64 = (o) => Buffer.from(JSON.stringify(o, null, 2)).toString('base64');
const cmd = `mkdir -p /data/manifests /data/approvals /data/labelled /data/incoming /data/inbox`
  + ` && printf %s ${b64(m)} | base64 -d > /data/manifests/${m.id}.json`
  + ` && printf %s ${b64(inbox)} | base64 -d > /data/inbox/${m.id}.json`;
return [{ json: { ...m, write_cmd: cmd } }];
"""

RESOLVE_JS = r"""
// Turn the reviewer's decision into a disclosure status and an approval record.
const m = { ...$('Build manifest').first().json };
delete m.write_cmd;
const g = $input.first().json;
const decision = String(g.Decision || '');
const reviewer = String(g.Reviewer || '');
const reason = String(g['Reason / note'] || '');
let status, disclosure, responsible = null, note = '';
if (decision.startsWith('Approve')) {
  status = 'approved';
  disclosure = m.label_required ? 'disclosed' : 'not_required';
} else if (decision.startsWith('Editorial')) {
  status = 'approved';
  if (m.category === 'generated_public_text') { disclosure = 'editorial_exception'; responsible = reviewer; m.disclosed_text = m.text_content; }
  else { disclosure = m.label_required ? 'disclosed' : 'not_required'; note = 'Editorial exception applies to text only (Art. 50(4) §2); label kept.'; }
} else {
  status = 'returned'; disclosure = 'returned';
}
m.status = status; m.disclosure_status = disclosure; m.responsible_person = responsible;
m.decided_at = new Date().toISOString(); m.reviewer = reviewer;
const approval = {
  id: m.id, line: m.line, decided_at: m.decided_at, reviewer, decision, reason, note,
  category: m.category, asset_type: m.asset_type, model: m.model,
  disclosure_status: disclosure, responsible_person: responsible,
  artefact: m.labelled_path || m.incoming_path || 'text',
  execution_id: $execution.id, workflow_id: $workflow.id,
};
const b64 = (o) => Buffer.from(JSON.stringify(o, null, 2)).toString('base64');
const cmd = `printf %s ${b64(approval)} | base64 -d > /data/approvals/${m.id}.json`
          + ` && printf %s ${b64(m)} | base64 -d > /data/manifests/${m.id}.json`
          + ` && rm -f /data/inbox/${m.id}.json`;
return [{ json: { ...m, approval, write_cmd: cmd } }];
"""

REGISTRY_JS = r"""
// AI-systems registry for the whole n8n instance, with path analysis per generator.
// Source 1: every workflow on the instance (n8n API). For each node that calls a model, walk every path forward
//           to every node that reaches people and check what stands in between.
// Source 2: models declared in manifests (generation often happens outside n8n).
const KIT_ID = '__KIT_ID__';
const wfs = $input.all().map(i => i.json).filter(w => w && Array.isArray(w.nodes));

const AI_TYPE = /langchain|openai|anthropic|ollama|gemini|mistral|huggingface|groq|cohere|deepseek|perplexity|xai|elevenlabs|replicate|stability|bedrock|vertex|azureopenai|heygen|midjourney|runway|bannerbear|kokoro/i;
const AI_HOST = /api\.openai\.com|api\.anthropic\.com|:11434|:8880|kokoro|api\.elevenlabs\.io|api\.replicate\.com|api\.stability\.ai|generativelanguage\.googleapis|api\.mistral\.ai|api\.heygen\.com|api\.bannerbear\.com|api\.groq\.com|api\.cohere|api\.deepseek\.com|api\.x\.ai|openrouter\.ai|api\.d-id\.com|api\.synthesia\.io/i;
const LIKENESS = /elevenlabs|heygen|d-id|synthesia|voice.?clone|clone/i;             // can reproduce a real face or voice
const EXIT_TYPE = /linkedIn|twitter|facebook|instagram|youTube|tiktok|wordpress|ghost|webflow|contentful|mailchimp|brevo|sendinblue|sendgrid|mailgun|emailSend|gmail|microsoftOutlook|telegram|whatsApp|twilio|messageBird|discord|reddit|medium|hubspot|activeCampaign|klaviyo/i;
const GATE_TYPE = /n8n-nodes-base\.form$|n8n-nodes-base\.wait$/;
const GATE_OP = /sendAndWait|approval/i;
const NAME_EXIT = /\[exit\]/i;               // convention: tag your own publishing nodes
const NAME_DISCLOSE = /\[ai disclosure\]/i;  // convention: tag your own disclosure/label nodes

function classify(n) {
  const p = n.parameters || {};
  const url = typeof p.url === 'string' ? p.url : '';
  const isKit = /executeWorkflow$/.test(n.type) && JSON.stringify(p.workflowId || '').includes(KIT_ID);
  const gen = AI_TYPE.test(n.type) || AI_HOST.test(url);
  const waitsForPerson = /n8n-nodes-base\.wait$/.test(n.type) ? ['form', 'webhook'].includes(String(p.resume || '')) : true;   // a timer is not a human
  const gate = isKit || (GATE_TYPE.test(n.type) && waitsForPerson) || GATE_OP.test(String(p.operation || '')) || GATE_OP.test(String(p.resource || ''));
  const disclose = isKit || NAME_DISCLOSE.test(n.name);
  const exit = EXIT_TYPE.test(n.type) || NAME_EXIT.test(n.name);
  const maybeExit = !exit && !gen && ((/httpRequest$/.test(n.type) && url && !AI_HOST.test(url) && !/host\.docker\.internal|localhost|127\.0\.0\.1/.test(url))
                    || /slack|notion|googleSheets|airtable|microsoftTeams|mattermost/i.test(n.type));
  return { gen, gate, disclose, exit, maybeExit, isKit, likeness: gen && (LIKENESS.test(n.type) || LIKENESS.test(n.name) || LIKENESS.test(url)) };
}

function modelOf(n) {
  const p = n.parameters || {};
  let model = (p.model && (p.model.value || p.model)) || (p.modelId && (p.modelId.value || p.modelId)) || '';
  if (!model && typeof p.jsonBody === 'string') { const mm = p.jsonBody.match(/model['"]?\s*:\s*['"]([^'"]+)['"]/); if (mm) model = mm[1]; }
  if (!model && typeof p.url === 'string' && p.url) model = p.url.replace(/^https?:\/\//, '').split('/')[0];
  return String(model);
}

function analyse(w) {
  const nodes = w.nodes.filter(n => !/stickyNote$/.test(n.type));
  const byName = Object.fromEntries(nodes.map(n => [n.name, n]));
  const cls = Object.fromEntries(nodes.map(n => [n.name, classify(n)]));
  const outs = (name) => {
    const c = (w.connections || {})[name];
    if (!c || !Array.isArray(c.main)) return [];
    return c.main.map((edges, idx) => (edges || []).map(e => e && e.node).filter(t => t && byName[t]).map(t => ({ t, idx })));
  };
  const next = (name) => outs(name).flat().map(o => o.t);
  const isLoop = (name) => /splitInBatches$/.test(byName[name].type);
  // what the loop body (output 1, back to the loop node) passes through
  const bodyFlags = (loop) => {
    let gate = false, disc = false; const seen = new Set([loop]);
    const stack = (outs(loop)[1] || []).map(o => o.t);
    while (stack.length) {
      const x = stack.pop(); if (seen.has(x)) continue; seen.add(x);
      if (!byName[x].disabled) { gate = gate || cls[x].gate; disc = disc || cls[x].disclose; }
      for (const y of next(x)) if (!seen.has(y)) stack.push(y);
    }
    return { gate, disc };
  };
  const rows = [];
  for (const n of nodes) {
    const c = cls[n.name];
    if (!c.gen || n.disabled) continue;
    // enumerate paths forward (capped), remembering what each path passed through
    const paths = [];
    const walk = (name, seen, gate, disc, trail) => {
      if (paths.length > 300) return;
      const loopBody = isLoop(name) ? bodyFlags(name) : null;
      for (const { t, idx } of outs(name).flat()) {
        if (seen.has(t)) continue;
        const tc = cls[t]; const dn = byName[t].disabled;
        let g2 = gate || (!dn && tc.gate), d2 = disc || (!dn && tc.disclose);
        if (loopBody && idx === 0) { g2 = g2 || loopBody.gate; d2 = d2 || loopBody.disc; }   // "done" output: items went through the body
        const trail2 = trail.concat(t);
        if (tc.exit || tc.maybeExit) paths.push({ exit: t, kind: tc.exit ? 'exit' : 'maybe', gate: g2, disc: d2, trail: trail2 });
        walk(t, new Set([...seen, t]), g2, d2, trail2);
      }
    };
    walk(n.name, new Set([n.name]), false, false, [n.name]);
    const real = paths.filter(p => p.kind === 'exit'), maybe = paths.filter(p => p.kind === 'maybe');
    let status, evidence;
    const fmt = (p) => p.trail.join(' → ');
    if (!real.length && !maybe.length) { status = 'internal'; evidence = 'no path from this node reaches a publishing node'; }
    else if (real.some(p => !p.disc && !p.gate)) { const p = real.find(p => !p.disc && !p.gate); status = 'uncovered'; evidence = fmt(p) + ' — no disclosure, no human gate on this path'; }
    else if (c.likeness && real.some(p => !p.disc)) { const p = real.find(p => !p.disc); status = 'likeness'; evidence = fmt(p) + ' — face/voice generator reaches people without a disclosure step (gate alone is not enough for Art. 50(4) §1)'; }
    else if (real.length && real.every(p => p.disc)) { status = 'disclosed'; evidence = fmt(real[0]); }
    else if (real.length && real.every(p => p.disc || p.gate)) { const p = real.find(p => !p.disc); status = 'editorial'; evidence = fmt(p) + ' — human gate but no disclosure step: allowed for text only, with a named responsible person'; }
    else { status = 'verify'; evidence = fmt(maybe[0]) + ' — destination may or may not reach people; mark the node [exit] or leave it'; }
    if (status === 'disclosed' && maybe.some(p => !p.disc && !p.gate)) { status = 'verify'; evidence = fmt(maybe.find(p => !p.disc && !p.gate)) + ' — destination may or may not reach people; mark the node [exit] or leave it'; }
    rows.push({ system: n.name, source: 'workflow node', workflow: w.name, workflow_id: w.id, workflow_active: !!w.active,
                node_type: n.type.replace('@n8n/n8n-nodes-langchain.', 'langchain.').replace('n8n-nodes-base.', ''), model: modelOf(n),
                role: 'deployer', likeness: c.likeness, exits: real.map(p => p.exit).filter((v, i, a) => a.indexOf(v) === i),
                path_status: status, evidence, first_seen: new Date().toISOString().slice(0,10) });
  }
  return rows;
}

const rows = [];
for (const w of wfs) rows.push(...analyse(w));

const raw = String($('Read manifests').first().json.stdout || '');
const seen = new Map();
for (const line of raw.split('\n')) {
  const t = line.trim(); if (!t.startsWith('{')) continue;
  try {
    const m = JSON.parse(t);
    const key = (m.model || '') + '|' + (m.model_version || '');
    if (!m.model) continue;
    if (seen.has(key)) { seen.get(key).assets += 1; continue; }
    seen.set(key, { system: m.model + (m.model_version ? ' ' + m.model_version : ''), source: 'declared in manifest', workflow: m.line || 'outside n8n', workflow_active: null,
                    node_type: 'external generator', model: m.model, role: 'deployer', exits: [],
                    path_status: m.status === 'pending_review' ? 'verify' : (m.disclosure_status === 'disclosed' || m.disclosure_status === 'editorial_exception' || m.disclosure_status === 'not_required') ? 'disclosed' : m.disclosure_status === 'returned' ? 'internal' : 'verify',
                    evidence: 'declared at intake, passed through this kit (' + m.asset_type + '), decision: ' + (m.disclosure_status || m.status),
                    first_seen: String(m.created_at || '').slice(0,10), assets: 1 });
  } catch (e) {}
}
rows.push(...seen.values());
const order = { uncovered: 0, likeness: 1, editorial: 2, verify: 3, disclosed: 4, internal: 5 };
rows.sort((a, b) => (order[a.path_status] ?? 9) - (order[b.path_status] ?? 9));
const registry = { generated_at: new Date().toISOString(), instance_workflows: wfs.length, registry_partial: wfs.length === 0,
                   workflows_scanned: wfs.map(w => ({ id: w.id, name: w.name, active: !!w.active })),
                   rules: 'internal: no path to a publishing node · disclosed: every path passes a disclosure step (this kit or a node tagged [AI disclosure]) · editorial: human gate only, text with a named responsible person · verify: destination unclear, tag it [exit] · uncovered: a path reaches people with neither · likeness: face/voice generator reaches people without disclosure',
                   systems: rows };
const cmd = `printf %s ${Buffer.from(JSON.stringify(registry, null, 2)).toString('base64')} | base64 -d > /data/registry.json`;
return [{ json: { systems: rows.length, workflows: wfs.length, write_cmd: cmd } }];
""".replace('__KIT_ID__', KIT_ID)

RETURN_JS = r"""
// What a calling workflow gets back, one item per asset.
const m = $('Resolve decision').first().json;
return [{ json: { id: m.id, approved: m.status === 'approved', status: m.status, disclosure_status: m.disclosure_status,
                  responsible_person: m.responsible_person, reviewer: m.reviewer, disclosure_sentence: m.disclosure_sentence,
                  labelled_path: m.labelled_path, disclosed_text: m.disclosed_text || null, manifest: '/data/manifests/' + m.id + '.json',
                  audit_view: 'http://localhost:5678/webhook/audit' } }];
"""

READ_MANIFESTS_SH = "for f in /data/manifests/*.json; do [ -f \"$f\" ] && node -e 'process.stdout.write(JSON.stringify(JSON.parse(require(\"fs\").readFileSync(process.argv[1],\"utf8\")))+\"\\n\")' \"$f\"; done; true"

GATE_HTML = ("={{ (() => { const m = $('Build manifest').first().json; const esc = (v) => String(v ?? '').replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));"
             " return '<div style=\"font:14px/1.5 -apple-system,Inter,sans-serif;color:#14171c\">'"
             " + '<h3 style=\"margin:0 0 6px\">Human approval gate</h3>'"
             " + '<p style=\"margin:0 0 8px;color:#6b7280\">Line: ' + esc(m.line) + ' · asset <code>' + esc(m.id) + '</code> · ' + esc(m.asset_type) + ' · <b>' + esc(m.category) + '</b> · model ' + esc(m.model) + (m.model_version ? ' ' + esc(m.model_version) : '') + ' · operator ' + esc(m.operator) + '</p>'"
             " + '<p style=\"margin:0 0 8px\"><b>Disclosure sentence</b> (' + esc(m.language) + '): ' + esc(m.disclosure_sentence) + '</p>'"
             " + '<p style=\"margin:0 0 4px\"><b>Obligations under the AI Act</b></p><ul style=\"margin:0 0 8px 18px;padding:0\">' + m.obligations.map(o => '<li>' + esc(o) + '</li>').join('') + '</ul>'"
             " + ((m.other_law || []).length ? '<p style=\"margin:0 0 4px\"><b>Other law</b></p><ul style=\"margin:0 0 8px 18px;padding:0\">' + m.other_law.map(o => '<li>' + esc(o) + '</li>').join('') + '</ul>' : '')"
             " + (m.depicts_real_person ? '<p style=\"margin:0 0 8px\">Real person depicted · consent: <code>' + esc(m.consent_reference || 'MISSING') + '</code></p>' : '')"
             " + (m.labelled_path ? '<p style=\"margin:0 0 8px\">Labelled file: <code>' + esc(m.labelled_path) + '</code>' + (m.label_exit_code ? ' · <span style=\"color:#b91c1c\">ffmpeg exit ' + esc(m.label_exit_code) + '</span>' : ' · label applied') + '</p>' : '')"
             " + (m.disclosed_text ? '<p style=\"margin:0 0 4px\"><b>Text as it would be published</b></p><pre style=\"white-space:pre-wrap;background:#f6f7f9;padding:10px;border-radius:8px;margin:0\">' + esc(m.disclosed_text) + '</pre>' : '')"
             " + '</div>'; })() }}")

GATE_FIELDS = {"values": [
    {"fieldLabel": "Context", "fieldType": "html", "elementName": "context", "html": GATE_HTML},
    {"fieldLabel": "Decision", "fieldType": "dropdown", "fieldOptions": {"values": [
        {"option": "Approve — publish with the disclosure"},
        {"option": "Editorial exception — I edited this text and take editorial responsibility (text only)"},
        {"option": "Return — needs changes"}]}, "requiredField": True},
    {"fieldLabel": "Reviewer", "requiredField": True},
    {"fieldLabel": "Reason / note", "fieldType": "textarea"},
]}

# ============================================================================ kit: nodes
kit_nodes = [
    node("Asset produced", "n8n-nodes-base.formTrigger", 2.2, {
        "formTitle": "AI Act Transparency Kit · asset intake",
        "formDescription": "Register one AI-generated asset before it goes anywhere. The kit classifies it under Article 50, labels it, writes a provenance manifest and sends it to a human gate. The gate link appears on the audit view under “awaiting a human”.",
        "formFields": {"values": [
            {"fieldLabel": "Asset type", "fieldType": "dropdown", "fieldOptions": {"values": [{"option": "image"}, {"option": "video"}, {"option": "audio"}, {"option": "text"}]}, "requiredField": True},
            {"fieldLabel": "Language of the asset", "fieldType": "dropdown", "fieldOptions": {"values": [{"option": "en"}, {"option": "bg"}, {"option": "ru"}, {"option": "de"}]}, "requiredField": True},
            {"fieldLabel": "Model", "placeholder": "Midjourney v7 · ElevenLabs Multilingual v2 · gpt-4o · Kokoro-82M", "requiredField": True},
            {"fieldLabel": "Model version", "placeholder": "optional"},
            {"fieldLabel": "Prompt", "fieldType": "textarea", "requiredField": True},
            {"fieldLabel": "Operator", "placeholder": "who ran the generation", "requiredField": True},
            {"fieldLabel": "Depicts a real person (face or voice)?", "fieldType": "dropdown", "fieldOptions": {"values": [{"option": "no"}, {"option": "yes"}]}, "requiredField": True},
            {"fieldLabel": "Consent reference", "placeholder": "link or id of the person's consent, if a real person is depicted"},
            {"fieldLabel": "Published to inform the public on a matter of public interest?", "fieldType": "dropdown", "fieldOptions": {"values": [{"option": "no"}, {"option": "yes"}]}, "requiredField": True},
            {"fieldLabel": "Text content", "fieldType": "textarea", "placeholder": "for text assets"},
            {"fieldLabel": "File", "fieldType": "file", "multipleFiles": False},
        ]},
        "options": {"path": "ai-act-intake"}}, X(0), 200, webhookId="a1b2c3d4-0001-4000-8000-aiactintake01"),
    node("Called by another workflow", "n8n-nodes-base.executeWorkflowTrigger", 1.1, {"inputSource": "passthrough"}, X(0), 420),
    node("Prompt hash", "n8n-nodes-base.crypto", 1, {
        "action": "hash", "type": "SHA256", "value": "={{ $json.Prompt || $json.prompt || '' }}", "dataPropertyName": "prompt_sha256"}, X(1), 300),
    node("Classify (Art. 50)", "n8n-nodes-base.code", 2, {"jsCode": CLASSIFY_JS.strip()}, X(2), 300),
    node("Is text?", "n8n-nodes-base.if", 2.2, {"conditions": cond("={{ $json.asset_type }}", "text"), "options": {}}, X(3), 300),
    node("Text disclosure", "n8n-nodes-base.code", 2, {"jsCode": TEXT_JS.strip()}, X(4), 160),
    node("Save incoming file", "n8n-nodes-base.readWriteFile", 1, {
        "operation": "write", "fileName": "={{ $json.incoming_path }}", "dataPropertyName": "={{ $json.binary_key || 'File' }}", "options": {}}, X(4), 440),
    node("Label with ffmpeg", "n8n-nodes-base.executeCommand", 1, {
        "command": "={{ $('Classify (Art. 50)').first().json.ffmpeg_cmd || 'true' }}"}, X(5), 440),
    node("Build manifest", "n8n-nodes-base.code", 2, {"jsCode": MANIFEST_JS.strip()}, X(6), 300),
    node("Write manifest + inbox", "n8n-nodes-base.executeCommand", 1, {"command": "={{ $json.write_cmd }}"}, X(7), 300),
    node("Notify reviewer (Slack)", "n8n-nodes-base.slack", 2.3, {
        "resource": "message", "operation": "post", "select": "channel",
        "channelId": {"__rl": True, "mode": "name", "value": "#ai-act-gate"},
        "text": "={{ ':vertical_traffic_light: *AI Act gate* · ' + $('Build manifest').first().json.line + ' · ' + $('Build manifest').first().json.asset_type + ' · ' + $('Build manifest').first().json.category + ' · model ' + $('Build manifest').first().json.model + '\\n' + $('Build manifest').first().json.disclosure_sentence + '\\nDecide here: ' + $('Build manifest').first().json.gate_url }}",
        "otherOptions": {}}, X(8), 160, onError="continueRegularOutput", notes="The human is told where the gate is. Attach a Slack credential and pick the channel; swap for Gmail or Telegram if that is where your reviewers live. Without a credential the node is skipped and the link still shows on the audit view."),
    node("Review & approve", "n8n-nodes-base.wait", 1.1, {
        "resume": "form", "formTitle": "Human approval gate",
        "formDescription": "One asset, one decision. Everything below was filled by the line.",
        "formFields": GATE_FIELDS, "options": {}}, X(9), 300, webhookId="a1b2c3d4-0002-4000-8000-aiactgate0001"),
    node("Resolve decision", "n8n-nodes-base.code", 2, {"jsCode": RESOLVE_JS.strip()}, X(10), 300),
    node("Write approval + manifest", "n8n-nodes-base.executeCommand", 1, {"command": "={{ $json.write_cmd }}"}, X(11), 300),
    node("Read manifests", "n8n-nodes-base.executeCommand", 1, {"command": READ_MANIFESTS_SH}, X(12), 300),
    node("Read all workflows", "n8n-nodes-base.n8n", 1, {"resource": "workflow", "operation": "getAll", "returnAll": True, "filters": {}},
         X(13), 300, onError="continueRegularOutput", credentials={"n8nApi": {"id": N8N_API_CREDENTIAL_ID, "name": N8N_API_CREDENTIAL_NAME}}),
    node("Registry rows", "n8n-nodes-base.code", 2, {"jsCode": REGISTRY_JS.strip()}, X(14), 300),
    node("Write registry", "n8n-nodes-base.executeCommand", 1, {"command": "={{ $json.write_cmd }}"}, X(15), 300),
    node("Return to caller", "n8n-nodes-base.code", 2, {"jsCode": RETURN_JS.strip()}, X(16), 300),
    node("How it works", "n8n-nodes-base.stickyNote", 1, {"width": 1950, "height": 130, "content":
        "## AI Act Transparency Kit — deployer side of Article 50, as a module\n"
        "Two entries: its own intake form, or **Execute Sub-workflow** from any production line (pass asset_type, language, model, prompt, operator, depicts_real_person, public_information, caller_workflow and the file as binary `data`). "
        "classify → label + manifest → **Wait-form human gate** (link on the audit view) → approval log → registry of every AI system on this instance with **path analysis**: generator → publishing node, what stands in between. "
        "Returns `approved`, `disclosure_status`, `labelled_path`, `disclosed_text` to the caller."}, X(1), 0),
]
kit_conn = wire(
    ("Asset produced", "Prompt hash"), ("Called by another workflow", "Prompt hash"),
    ("Prompt hash", "Classify (Art. 50)"), ("Classify (Art. 50)", "Is text?"),
    ("Is text?", "Text disclosure", 0), ("Is text?", "Save incoming file", 1),
    ("Text disclosure", "Build manifest"), ("Save incoming file", "Label with ffmpeg"), ("Label with ffmpeg", "Build manifest"),
    ("Build manifest", "Write manifest + inbox"), ("Write manifest + inbox", "Notify reviewer (Slack)"), ("Notify reviewer (Slack)", "Review & approve"),
    ("Review & approve", "Resolve decision"), ("Resolve decision", "Write approval + manifest"),
    ("Write approval + manifest", "Read manifests"), ("Read manifests", "Read all workflows"),
    ("Read all workflows", "Registry rows"), ("Registry rows", "Write registry"), ("Write registry", "Return to caller"),
)
kit = {"id": KIT_ID, "name": "AI Act Transparency Kit", "nodes": kit_nodes, "connections": kit_conn, "active": False,
       "settings": {"executionOrder": "v1", "saveManualExecutions": True}, "meta": {"templateCredsSetupCompleted": True}}

# ============================================================================ audit view
COLLECT_SH = ("echo '###REGISTRY'; [ -f /data/registry.json ] && cat /data/registry.json; echo; "
              "for s in MANIFESTS:manifests APPROVALS:approvals INBOX:inbox; do echo \"###${s%%:*}\"; "
              "for f in /data/${s#*:}/*.json; do [ -f \"$f\" ] && node -e 'process.stdout.write(JSON.stringify(JSON.parse(require(\"fs\").readFileSync(process.argv[1],\"utf8\")))+\"\\n\")' \"$f\"; done; done; true")
RENDER_JS = (HERE / "audit_render.js").read_text()
audit_nodes = [
    node("Audit request (GET)", "n8n-nodes-base.webhook", 2, {"path": "audit", "httpMethod": "GET", "responseMode": "responseNode", "options": {}},
         0, 300, webhookId="a1b2c3d4-0004-4000-8000-aiactaudit001"),
    node("Collect files", "n8n-nodes-base.executeCommand", 1, {"command": COLLECT_SH}, 240, 300),
    node("Render audit view", "n8n-nodes-base.code", 2, {"jsCode": RENDER_JS.strip()}, 480, 300),
    node("Respond HTML", "n8n-nodes-base.respondToWebhook", 1.1, {
        "respondWith": "text", "responseBody": "={{ $json.html }}",
        "options": {"responseHeaders": {"entries": [{"name": "Content-Type", "value": "text/html; charset=utf-8"}]}}}, 720, 300),
    node("What this is", "n8n-nodes-base.stickyNote", 1, {"width": 900, "height": 100, "content":
        "## Audit view — what an auditor reads instead of the pipeline\nAwaiting a human (gate links) · AI-systems registry with path analysis (Art. 4) · synthetic media & deepfakes (Art. 50(2), 50(4)) · generated public text (Art. 50(4) §2) · approval log (Art. 14, Art. 12 voluntary). Filled from files the kit writes; nothing here is typed by hand."}, 0, 120),
]
audit = {"id": AUDIT_ID, "name": "AI Act Transparency Kit — Audit view", "nodes": audit_nodes,
         "connections": wire(("Audit request (GET)", "Collect files"), ("Collect files", "Render audit view"), ("Render audit view", "Respond HTML")),
         "active": False, "settings": {"executionOrder": "v1"}}

# ============================================================================ host line: notice → three Kokoro voices → gate → publish
VOICES_JS = r"""
// One item per voice. Fields the AI Act gate expects travel with the item (snake_case).
const f = $input.first().json;
const text = String(f['Notice text'] || '').trim();
const operator = String(f['Operator'] || 'unknown');
const stamp = new Date().toISOString().slice(0,16).replace(/[:T]/g,'-');
return ['af_bella', 'am_adam', 'bf_emma'].map(voice => ({ json: {
  voice, text, notice_id: stamp,
  asset_type: 'audio', language: 'en', model: 'Kokoro-82M', model_version: voice, prompt: text, operator,
  depicts_real_person: 'no', consent_reference: '', public_information: 'yes',
  caller_workflow: $workflow.name,
} }));
"""
ATTACH_JS = r"""
// The HTTP node returns only the audio; put the item's fields back next to it, in order.
const src = $('Three voices').all();
return $input.all().map((it, i) => {
  const b = it.binary && it.binary.data ? it.binary.data : null;
  if (b) b.fileName = `${src[i].json.notice_id}-${src[i].json.voice}.wav`;
  return { json: { ...src[i].json }, binary: it.binary };
});
"""
PREPARE_PUBLISH_JS = r"""
// One shell command that publishes every approved item (Buffer is not available in expressions, so this lives in Code).
const cmds = ['mkdir -p /data/published'];
const ids = [];
for (const it of $input.all()) {
  const j = it.json;
  if (!j.labelled_path) continue;
  const rec = { id: j.id, published_at: new Date().toISOString(), file: '/data/published/' + String(j.labelled_path).split('/').pop(),
                disclosure: j.disclosure_sentence, reviewer: j.reviewer, disclosure_status: j.disclosure_status };
  const b64 = Buffer.from(JSON.stringify(rec, null, 2)).toString('base64');
  cmds.push(`cp "${j.labelled_path}" /data/published/`, `printf %s ${b64} | base64 -d > /data/published/${j.id}.json`);
  ids.push(j.id);
}
return [{ json: { published_ids: ids, publish_cmd: cmds.join(' && ') } }];
"""
host_nodes = [
    node("Notice text", "n8n-nodes-base.formTrigger", 2.2, {
        "formTitle": "Recycling notice · three voices",
        "formDescription": "Type the public notice. Kokoro reads it in three voices; every voice passes the AI Act gate before it is published.",
        "formFields": {"values": [
            {"fieldLabel": "Notice text", "fieldType": "textarea", "requiredField": True},
            {"fieldLabel": "Operator", "requiredField": True}]},
        "options": {"path": "notice"}}, X(0), 300, webhookId="a1b2c3d4-0201-4000-8000-hostnotice001"),
    node("Three voices", "n8n-nodes-base.code", 2, {"jsCode": VOICES_JS.strip()}, X(1), 300),
    node("Kokoro TTS (local)", "n8n-nodes-base.httpRequest", 4.2, {
        "method": "POST", "url": KOKORO_URL, "sendBody": True, "specifyBody": "json",
        "jsonBody": "={{ JSON.stringify({ text: $json.text, voice: $json.voice, lang: 'en-us' }) }}",
        "options": {"response": {"response": {"responseFormat": "file", "outputPropertyName": "data"}}, "timeout": 120000}}, X(2), 300),
    node("Attach fields", "n8n-nodes-base.code", 2, {"jsCode": ATTACH_JS.strip()}, X(3), 300),
    node("One voice at a time", "n8n-nodes-base.splitInBatches", 3, {"batchSize": 1, "options": {}}, X(4), 300),
    node("AI Act gate", "n8n-nodes-base.executeWorkflow", 1.2, {
        "workflowId": {"__rl": True, "mode": "id", "value": KIT_ID}, "mode": "once", "options": {"waitForSubWorkflow": True}}, X(5), 460),
    node("Human approved?", "n8n-nodes-base.if", 2.2, {"conditions": {"options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict", "version": 2},
        "conditions": [{"id": nid(), "leftValue": "={{ $json.approved }}", "rightValue": "", "operator": {"type": "boolean", "operation": "true", "singleValue": True}}],
        "combinator": "and"}, "options": {}}, X(6), 200),
    node("Prepare publish", "n8n-nodes-base.code", 2, {"jsCode": PREPARE_PUBLISH_JS.strip()}, X(7), 100),
    node("Publish to site [exit]", "n8n-nodes-base.executeCommand", 1, {"command": "={{ $json.publish_cmd }}"}, X(8), 100),
    node("Returned, not published", "n8n-nodes-base.noOp", 1, {}, X(7), 300),
    node("What this line is", "n8n-nodes-base.stickyNote", 1, {"width": 1500, "height": 110, "content":
        "## A real production line with the kit as a module\nnotice → **Kokoro-82M**, three stock voices (local, no cloned person) → **AI Act gate** (Loop Over Items → Execute Sub-workflow, the parent waits for the human) → publish only what was approved. "
        "The publishing node is tagged `[exit]` so the registry knows it reaches people. Voices are stock, so this is `synthetic_media`, not a deep fake."}, X(0), 100),
]
host = {"id": HOST_ID, "name": "Recycling notice · three voices", "nodes": host_nodes,
        "connections": wire(("Notice text", "Three voices"), ("Three voices", "Kokoro TTS (local)"), ("Kokoro TTS (local)", "Attach fields"),
                            ("Attach fields", "One voice at a time"), ("One voice at a time", "Human approved?", 0), ("One voice at a time", "AI Act gate", 1),
                            ("AI Act gate", "One voice at a time"),
                            ("Human approved?", "Prepare publish", 0), ("Prepare publish", "Publish to site [exit]"), ("Human approved?", "Returned, not published", 1)),
        "active": False, "settings": {"executionOrder": "v1", "saveManualExecutions": True}}

for name, wf in (("transparency-kit.json", kit), ("audit-view.json", audit), ("host-line.json", host)):
    (HERE / name).write_text(json.dumps(wf, indent=2, ensure_ascii=False))
    print("wrote", name, len(wf["nodes"]), "nodes")
