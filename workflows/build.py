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
N8N_API_CREDENTIAL_ID = "0O4IFf0UeEqYcj74"
N8N_API_CREDENTIAL_NAME = "n8n account"
KOKORO_URL = "http://host.docker.internal:8880/tts"
MEDIA_LABEL_URL = "http://kit-media-label:8881/label"   # ffmpeg label service in its own container; if unreachable, images fall back to Edit Image, media to "disclosure at publication"
# Postgres credential imported by reload.sh from secrets/postgres-credential.json (id is fixed so the JSON can reference it)
PG = {"postgres": {"id": "KitPostgresCred01", "name": "kit-db"}}
GATE_MODE = "slack"          # "form": Wait node with a form (works everywhere) · "slack": Slack Send-and-Wait with the same form, channel members only
SLACK_CHANNEL = "#ai-act-gate"
SLACK = {"slackApi": {"id": "yqaUQ2SkfGomOHLf", "name": "Slack_pipeline_approval"}}   # created by hand in the editor; id is instance-local
SLACK_POLL_SECONDS = 20
SLACK_MAX_POLLS = 4320          # 24 h at 20 s


def pg(name, query, values_expr, x, y, **extra):
    """Postgres · Execute Query with $1..$n bound from an expression that returns an array."""
    return node(name, "n8n-nodes-base.postgres", 2.7, {"operation": "executeQuery", "query": query,
                "options": {"queryReplacement": values_expr}}, x, y, credentials=PG, **extra)


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
const shows = String(g('What does it show?', 'shows') || (yes(g('Depicts a real person (face or voice)?', 'depicts_real_person')) ? 'a real person (face or voice)' : 'nothing real')).toLowerCase();
const realPerson = /person|face|voice/.test(shows);
const realThing = /object|place|event|entity/.test(shows);
const manipulated = /manipulat/.test(String(g('Generated or manipulated?', 'origin') || 'generated').toLowerCase());
const artistic = yes(g('Artistic, creative or satirical work?', 'artistic'));
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
  en: (m) => manipulated ? `This ${type} was altered with an AI system (${m}).` : `This ${type} was created with an AI system (${m}).`,
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
  if (realPerson || realThing) {
    // Art. 3(60): content resembling existing persons, objects, places, entities or events that would falsely appear authentic
    category = 'deepfake'; label_required = true; label_basis = artistic ? 'law (limited: artistic work)' : 'law';
    obligations.push('Art. 3(60) deep fake: ' + (manipulated ? 'manipulated' : 'generated') + ' content resembling ' + (realPerson ? 'a real person' : 'a real object, place or event') + ' that would appear authentic.');
    obligations.push('Art. 50(4) §1 — disclose that the content is artificially ' + (manipulated ? 'manipulated' : 'generated') + '.' + (artistic ? ' Artistic, creative or satirical work: the disclosure may be limited so it does not hamper the work — still present, in an appropriate form.' : ''));
    if (realPerson) other_law.push('Consent or another legal basis for using the person\'s likeness or voice: GDPR and personality rights, not the AI Act (consent reference below).');
  } else {
    category = 'synthetic_media';
    label_required = (type === 'image' || type === 'video' || (type === 'audio' && publicInfo));
    label_basis = label_required ? 'house policy' : 'none';
    obligations.push('Art. 50(2) machine-readable marking is the provider\'s duty; as deployer we keep a provenance manifest and apply a disclosure by house policy.');
  }
}

const label_text = (manipulated ? 'AI-manipulated' : 'AI-generated') + ' - EU AI Act Art. 50';   // ASCII only: some ffmpeg builds drop the last glyph after a multibyte character
const inPath  = `/data/incoming/${id}${ext}`;
const outPath = `/data/labelled/${id}${ext}`;
const wants_burn_in = (type === 'image' || type === 'video') && label_required;
const manifest = {
  id, created_at: now.toISOString(),
  line: String(g('Calling workflow', 'caller_workflow') || 'manual intake'),
  asset_type: type, category, label_required, label_basis, label_text: label_required ? label_text : null,
  obligations, other_law,
  model, model_version: String(g('Model version', 'model_version') || ''),
  prompt_sha256: f.prompt_sha256 || '',
  operator: String(g('Operator', 'operator') || ''),
  depicts_real_person: realPerson, shows, manipulated, artistic, consent_reference: String(g('Consent reference', 'consent_reference') || ''),
  public_information: publicInfo,
  source_file: file ? file.fileName : null,
  incoming_path: file ? inPath : null, labelled_path: file ? outPath : null, label_small: artistic, wants_burn_in,
  text_content: type === 'text' ? String(g('Text content', 'text_content') || '') : null,
  language: lang, disclosure_sentence,
  status: 'pending_review',
};
return [{ json: { ...manifest, ext, binary_key }, binary: it.binary }];
"""

TEXT_JS = r"""
// Text branch: prepare the disclosed version. The gate may later replace it with an editorial exception.
const m = $('Classify (Art. 50)').first().json;
const footer = '\n\n— ' + m.disclosure_sentence;
return [{ json: { ...m, disclosed_text: m.label_required ? m.text_content + footer : m.text_content } }];
"""

MANIFEST_JS = r"""
// Collect everything into the manifest and add the gate link. The next node stores it in Postgres.
const m = { ...$('Classify (Art. 50)').first().json };
delete m.ext; delete m.binary_key;
const src = $input.first().json;
if (src.disclosed_text !== undefined) m.disclosed_text = src.disclosed_text;
if (src.label_note !== undefined) { m.label_note = src.label_note; }
if (src.burned_in !== undefined) { m.burned_in = src.burned_in; if (!src.burned_in) { m.labelled_path = m.incoming_path; } }
m.gate_url = $execution.resumeFormUrl;
m.execution_id = $execution.id;
return [{ json: m }];
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
return [{ json: { ...m, approval } }];
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
const EMOTION = /emotion|sentiment.?of.?face|facial|face.?analy|biometric|hume\.ai|api\.hume|affectiva|rekognition|azure.*face|face\+\+|faceplusplus|detect.?face|age.?gender/i;   // Art. 50(3): emotion recognition / biometric categorisation
const CHATBOT = /chatTrigger|chat.?trigger|n8n-nodes-langchain\.agent|conversational|chatbot|assistant/i;   // Art. 50(1): interacts with natural persons (provider duty, checked for awareness)
const INFORMED = /\[persons informed\]|\[ai disclosed\]/i;   // convention: tag the node that informs people
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
  const emotion = EMOTION.test(n.type) || EMOTION.test(n.name) || EMOTION.test(url);
  const chatbot = CHATBOT.test(n.type) || (CHATBOT.test(n.name) && gen);
  return { gen: gen || emotion || chatbot, gate, disclose, exit, maybeExit, isKit, emotion, chatbot, informed: INFORMED.test(n.name),
           likeness: gen && (LIKENESS.test(n.type) || LIKENESS.test(n.name) || LIKENESS.test(url)) };
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
    const informedInWf = nodes.some(x => cls[x.name].informed && !x.disabled);
    if (c.emotion) {
      // Art. 50(3): the duty exists whenever the system runs on people, publishing or not
      status = informedInWf ? 'informed' : 'inform';
      evidence = informedInWf ? 'emotion/biometric system; a node tagged [persons informed] exists in this workflow' : 'emotion recognition or biometric categorisation runs on people — they must be informed (Art. 50(3)); no node tagged [persons informed] in this workflow';
    } else if (c.chatbot) {
      status = informedInWf ? 'informed' : 'chatbot';
      evidence = informedInWf ? 'people are told they talk to an AI (node tagged [ai disclosed])' : 'interacts with natural persons — the provider must make the AI nature clear unless obvious (Art. 50(1)); no node tagged [ai disclosed] in this workflow';
    } else if (!real.length && !maybe.length) { status = 'internal'; evidence = 'no path from this node reaches a publishing node'; }
    else if (real.some(p => !p.disc && !p.gate)) { const p = real.find(p => !p.disc && !p.gate); status = 'uncovered'; evidence = fmt(p) + ' — no disclosure, no human gate on this path'; }
    else if (c.likeness && real.some(p => !p.disc)) { const p = real.find(p => !p.disc); status = 'likeness'; evidence = fmt(p) + ' — face/voice generator reaches people without a disclosure step (gate alone is not enough for Art. 50(4) §1)'; }
    else if (real.length && real.every(p => p.disc)) { status = 'disclosed'; evidence = fmt(real[0]); }
    else if (real.length && real.every(p => p.disc || p.gate)) { const p = real.find(p => !p.disc); status = 'editorial'; evidence = fmt(p) + ' — human gate but no disclosure step: allowed for text only, with a named responsible person'; }
    else { status = 'verify'; evidence = fmt(maybe[0]) + ' — destination may or may not reach people; mark the node [exit] or leave it'; }
    if (status === 'disclosed' && maybe.some(p => !p.disc && !p.gate)) { status = 'verify'; evidence = fmt(maybe.find(p => !p.disc && !p.gate)) + ' — destination may or may not reach people; mark the node [exit] or leave it'; }
    rows.push({ system: n.name, source: 'workflow node', workflow: w.name, workflow_id: w.id, workflow_active: !!w.active,
                node_type: n.type.replace('@n8n/n8n-nodes-langchain.', 'langchain.').replace('n8n-nodes-base.', ''), model: modelOf(n),
                role: 'deployer', likeness: c.likeness, emotion: c.emotion, chatbot: c.chatbot, exits: real.map(p => p.exit).filter((v, i, a) => a.indexOf(v) === i),
                path_status: status, evidence, first_seen: new Date().toISOString().slice(0,10) });
  }
  return rows;
}

const rows = [];
for (const w of wfs) rows.push(...analyse(w));

const seen = new Map();
for (const row of $('Read assets').all()) {
  try {
    const m = typeof row.json.manifest === 'string' ? JSON.parse(row.json.manifest) : (row.json.manifest || {});
    m.status = row.json.status || m.status; m.disclosure_status = row.json.disclosure_status || m.disclosure_status;
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
const order = { uncovered: 0, likeness: 1, inform: 2, editorial: 3, chatbot: 4, verify: 5, disclosed: 6, informed: 7, internal: 8 };
rows.sort((a, b) => (order[a.path_status] ?? 9) - (order[b.path_status] ?? 9));
const registry = { generated_at: new Date().toISOString(), instance_workflows: wfs.length, registry_partial: wfs.length === 0,
                   workflows_scanned: wfs.map(w => ({ id: w.id, name: w.name, active: !!w.active })),
                   rules: 'internal: no path to a publishing node · disclosed: every path passes a disclosure step (this kit or a node tagged [AI disclosure]) · editorial: human gate only, text with a named responsible person · verify: destination unclear, tag it [exit] · uncovered: a path reaches people with neither · likeness: face/voice generator reaches people without disclosure · inform: emotion/biometric system runs on people who are not told (Art. 50(3)), tag the node that tells them [persons informed] · chatbot: talks to people without saying it is an AI (Art. 50(1)), tag [ai disclosed]',
                   systems: rows };
return [{ json: { systems: rows.length, workflows: wfs.length, partial: wfs.length === 0, registry } }];
""".replace('__KIT_ID__', KIT_ID)

SLACK_PARSE_JS = r"""
// Look through the thread replies for the first decision by a channel member. Returns decided=false to keep polling.
const root = $('Post to the review thread').first().json;
const rootTs = root.ts || (root.message && root.message.ts);
const replies = $input.all().map(i => i.json).filter(m => m.ts !== rootTs && !m.bot_id && m.user);
let decided = false, decision = '', reason = '', user = '', ts = '';
for (const m of replies) {
  const t = String(m.text || '').trim(); const low = t.toLowerCase();
  if (/^(:white_check_mark:|✅|approve)/.test(low)) { decided = true; decision = 'Approve — publish with the disclosure'; }
  else if (/^(:writing_hand:|✍️|editorial)/.test(low)) { decided = true; decision = 'Editorial exception — I edited this text and take editorial responsibility (text only)'; }
  else if (/^(:x:|❌|return|reject)/.test(low)) { decided = true; decision = 'Return — needs changes'; }
  if (decided) { reason = t.replace(/^(:[a-z_]+:|✅|✍️|❌|approve|editorial|return|reject)\s*[:\-–—]?\s*/i, '').trim(); user = m.user; ts = m.ts; break; }
}
const polls = $runIndex + 1;
if (!decided && polls >= __MAX__) { decided = true; decision = 'Return — needs changes'; reason = 'No decision in the thread within the wait limit; returned automatically.'; user = ''; }
return [{ json: { decided, Decision: decision, 'Reason / note': reason, slack_user: user, slack_ts: ts, polls } }];
""".replace('__MAX__', str(SLACK_MAX_POLLS))

SLACK_RESOLVE_JS = r"""
// The reviewer's identity comes from Slack, not from a text field.
const d = $('Decided in the thread?').first().json;
const u = $input.first().json || {};
const name = (u.real_name || (u.profile && u.profile.real_name) || u.name || '').trim();
const reviewer = name ? `${name} (Slack ${d.slack_user})` : (d.slack_user ? `Slack ${d.slack_user}` : 'gate timeout');
return [{ json: { Decision: d.Decision, Reviewer: reviewer, 'Reason / note': d['Reason / note'], slack_user: d.slack_user, slack_ts: d.slack_ts } }];
"""

RETURN_JS = r"""
// What a calling workflow gets back, one item per asset.
const m = $('Resolve decision').first().json;
return [{ json: { id: m.id, approved: m.status === 'approved', status: m.status, disclosure_status: m.disclosure_status,
                  responsible_person: m.responsible_person, reviewer: m.reviewer, disclosure_sentence: m.disclosure_sentence,
                  labelled_path: m.labelled_path, disclosed_text: m.disclosed_text || null, manifest: 'assets/' + m.id + ' (Postgres)',
                  audit_view: 'http://localhost:5678/webhook/audit' } }];
"""


GATE_HTML = ("={{ (() => { const m = $('Build manifest').first().json; const esc = (v) => String(v ?? '').replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));"
             " return '<div style=\"font:14px/1.5 -apple-system,Inter,sans-serif;color:#14171c\">'"
             " + '<h3 style=\"margin:0 0 6px\">Human approval gate</h3>'"
             " + '<p style=\"margin:0 0 8px;color:#6b7280\">Line: ' + esc(m.line) + ' · asset <code>' + esc(m.id) + '</code> · ' + esc(m.asset_type) + ' · <b>' + esc(m.category) + '</b> · model ' + esc(m.model) + (m.model_version ? ' ' + esc(m.model_version) : '') + ' · operator ' + esc(m.operator) + '</p>'"
             " + '<p style=\"margin:0 0 8px\"><b>Disclosure sentence</b> (' + esc(m.language) + '): ' + esc(m.disclosure_sentence) + '</p>'"
             " + '<p style=\"margin:0 0 4px\"><b>Obligations under the AI Act</b></p><ul style=\"margin:0 0 8px 18px;padding:0\">' + m.obligations.map(o => '<li>' + esc(o) + '</li>').join('') + '</ul>'"
             " + ((m.other_law || []).length ? '<p style=\"margin:0 0 4px\"><b>Other law</b></p><ul style=\"margin:0 0 8px 18px;padding:0\">' + m.other_law.map(o => '<li>' + esc(o) + '</li>').join('') + '</ul>' : '')"
             " + '<p style=\"margin:0 0 8px\">Shows: ' + esc(m.shows) + ' · ' + (m.manipulated ? 'manipulated' : 'generated') + (m.artistic ? ' · artistic/satirical work' : '') + '</p>'"
             " + (m.depicts_real_person ? '<p style=\"margin:0 0 8px\">Real person depicted · consent: <code>' + esc(m.consent_reference || 'MISSING') + '</code></p>' : '')"
             " + (m.labelled_path ? '<p style=\"margin:0 0 8px\">File: <code>' + esc(m.labelled_path) + '</code> · ' + (m.burned_in ? 'label burnt in' : esc(m.label_note || 'no burnt-in label')) + '</p>' : '')"
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
            {"fieldLabel": "What does it show?", "fieldType": "dropdown", "fieldOptions": {"values": [{"option": "nothing real"}, {"option": "a real person (face or voice)"}, {"option": "a real object, place or event"}]}, "requiredField": True},
            {"fieldLabel": "Generated or manipulated?", "fieldType": "dropdown", "fieldOptions": {"values": [{"option": "generated"}, {"option": "manipulated (real footage altered)"}]}, "requiredField": True},
            {"fieldLabel": "Artistic, creative or satirical work?", "fieldType": "dropdown", "fieldOptions": {"values": [{"option": "no"}, {"option": "yes"}]}, "requiredField": True},
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
    node("Image?", "n8n-nodes-base.if", 2.2, {"conditions": cond("={{ $('Classify (Art. 50)').first().json.asset_type }}", "image"), "options": {}}, X(6), 620),
    node("Label image (Edit Image)", "n8n-nodes-base.editImage", 1.1, {
        "operation": "text", "dataPropertyName": "={{ $('Classify (Art. 50)').first().json.binary_key || 'File' }}",
        "text": "={{ $('Classify (Art. 50)').first().json.label_text }}",
        "fontSize": "={{ $('Classify (Art. 50)').first().json.label_small ? 24 : 44 }}", "fontColor": "#ffffff",
        "positionX": 24, "positionY": 60, "lineLength": 300,
        "options": {}}, X(7), 620, onError="continueErrorOutput"),
    node("Label media (service)", "n8n-nodes-base.httpRequest", 4.2, {
        "method": "POST", "url": "={{ '" + MEDIA_LABEL_URL + "?type=' + $('Classify (Art. 50)').first().json.asset_type + '&ext=' + encodeURIComponent($('Classify (Art. 50)').first().json.ext) + '&small=' + ($('Classify (Art. 50)').first().json.label_small ? 1 : 0) + '&text=' + encodeURIComponent($('Classify (Art. 50)').first().json.label_text) + '&comment=' + encodeURIComponent($('Classify (Art. 50)').first().json.label_text + '; manifest ' + $('Classify (Art. 50)').first().json.id) }}",
        "sendBody": True, "contentType": "binaryData", "inputDataFieldName": "={{ $('Classify (Art. 50)').first().json.binary_key || 'File' }}",
        "options": {"response": {"response": {"responseFormat": "file", "outputPropertyName": "={{ $('Classify (Art. 50)').first().json.binary_key || 'File' }}"}}, "timeout": 300000}},
        X(5), 440, onError="continueErrorOutput"),
    node("Write labelled file", "n8n-nodes-base.readWriteFile", 1, {
        "operation": "write", "fileName": "={{ $('Classify (Art. 50)').first().json.labelled_path }}", "dataPropertyName": "={{ $('Classify (Art. 50)').first().json.binary_key || 'File' }}", "options": {}}, X(7), 440),
    node("Burned in", "n8n-nodes-base.set", 3.4, {"assignments": {"assignments": [{"id": nid(), "name": "burned_in", "value": True, "type": "boolean"}]}, "options": {}}, X(8), 440),
    node("No burn-in", "n8n-nodes-base.set", 3.4, {"assignments": {"assignments": [
        {"id": nid(), "name": "burned_in", "value": False, "type": "boolean"},
        {"id": nid(), "name": "label_note", "value": "={{ 'No burnt-in label: ' + ($('Classify (Art. 50)').first().json.asset_type === 'audio' ? 'audio carries the disclosure in metadata and at publication' : 'the media-label service was not reachable; disclosure goes with the file at publication') }}", "type": "string"}]}, "options": {}}, X(8), 760),
    node("Build manifest", "n8n-nodes-base.code", 2, {"jsCode": MANIFEST_JS.strip()}, X(9), 300),
    pg("Store asset", "insert into assets (id, line, asset_type, category, status, model, operator, language, gate_url, execution_id, manifest) values ($1,$2,$3,$4,'pending_review',$5,$6,$7,$8,$9,$10::jsonb) on conflict (id) do update set manifest = excluded.manifest, gate_url = excluded.gate_url, execution_id = excluded.execution_id",
       "={{ [ $json.id, $json.line, $json.asset_type, $json.category, $json.model, $json.operator, $json.language, $json.gate_url, $json.execution_id, JSON.stringify($json) ] }}", X(10), 300),
    *([] if GATE_MODE == "slack" else [node("Notify reviewer (Slack)", "n8n-nodes-base.slack", 2.3, {
        "resource": "message", "operation": "post", "select": "channel",
        "channelId": {"__rl": True, "mode": "name", "value": "#ai-act-gate"},
        "text": "={{ ':vertical_traffic_light: *AI Act gate* · ' + $('Build manifest').first().json.line + ' · ' + $('Build manifest').first().json.asset_type + ' · ' + $('Build manifest').first().json.category + ' · model ' + $('Build manifest').first().json.model + '\\n' + $('Build manifest').first().json.disclosure_sentence + '\\nDecide here: ' + $('Build manifest').first().json.gate_url }}",
        "otherOptions": {}}, X(11), 160, onError="continueRegularOutput", disabled=True, notes="Disabled until a Slack credential is attached (the editor refuses to publish a node without one). Enable it, pick the channel; swap for Gmail or Telegram if that is where your reviewers live. Without a credential the node is skipped and the link still shows on the audit view.")]),
    *([
      node("Post to the review thread", "n8n-nodes-base.slack", 2.7, {
        "resource": "message", "operation": "post", "select": "channel",
        "channelId": {"__rl": True, "mode": "name", "value": SLACK_CHANNEL},
        "text": "={{ ':vertical_traffic_light: *AI Act gate* · ' + $('Build manifest').first().json.line + ' · ' + $('Build manifest').first().json.asset_type + ' · ' + $('Build manifest').first().json.category + ' · model ' + $('Build manifest').first().json.model + '\\n' + $('Build manifest').first().json.disclosure_sentence + '\\n' + ($('Build manifest').first().json.prompt ? 'Prompt: _' + String($('Build manifest').first().json.prompt).slice(0, 300) + '_\\n' : '') + ($('Build manifest').first().json.shows ? 'Shows: ' + $('Build manifest').first().json.shows + ($('Build manifest').first().json.consent_reference ? ' · consent ' + $('Build manifest').first().json.consent_reference : '') + '\\n' : '') + ($('Build manifest').first().json.disclosed_text ? '>' + String($('Build manifest').first().json.disclosed_text).slice(0, 900).replace(/\\n/g, '\\n>') + '\\n' : ($('Build manifest').first().json.labelled_path ? 'File: ' + $('Build manifest').first().json.labelled_path + ' (attached below)\\n' : '')) + 'Reply in this thread: *approve* · *editorial* (text only, you take editorial responsibility) · *return <reason>*' }}",
        "otherOptions": {}}, X(9), 300, credentials=SLACK),
      node("Has a file?", "n8n-nodes-base.if", 2.2, {"conditions": {"options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose", "version": 2},
        "conditions": [{"id": nid(), "leftValue": "={{ $('Build manifest').first().json.labelled_path || '' }}", "rightValue": "", "operator": {"type": "string", "operation": "notEmpty", "singleValue": True}}], "combinator": "and"}, "options": {}}, X(9), 460),
      node("Read labelled file", "n8n-nodes-base.readWriteFile", 1, {"operation": "read", "fileSelector": "={{ $('Build manifest').first().json.labelled_path }}", "options": {"dataPropertyName": "data"}}, X(10), 460, onError="continueRegularOutput"),
      node("Attach to the thread", "n8n-nodes-base.slack", 2.7, {
        "resource": "file", "operation": "upload", "binaryPropertyName": "data",
        "options": {"channelId": "={{ $('Post to the review thread').first().json.channel }}", "threadTs": "={{ $('Post to the review thread').first().json.ts || $('Post to the review thread').first().json.message.ts }}",
                    "fileName": "={{ String($('Build manifest').first().json.labelled_path).split('/').pop() }}", "title": "={{ $('Build manifest').first().json.label_text || 'labelled asset' }}"}},
        X(11), 460, onError="continueRegularOutput", credentials=SLACK, notes="Needs the files:write scope on the Slack app. Without it the upload is skipped and the thread still carries the file path."),
      node("Wait for the thread", "n8n-nodes-base.wait", 1.1, {"resume": "timeInterval", "amount": SLACK_POLL_SECONDS, "unit": "seconds"}, X(10), 300, webhookId="a1b2c3d4-0005-4000-8000-aiactpoll0001"),
      node("Read the thread", "n8n-nodes-base.slack", 2.7, {
        "resource": "channel", "operation": "replies", "channelId": {"__rl": True, "mode": "id", "value": "={{ $('Post to the review thread').first().json.channel }}"},
        "ts": "={{ $('Post to the review thread').first().json.ts || $('Post to the review thread').first().json.message.ts }}", "returnAll": True, "filters": {}}, X(11), 300, credentials=SLACK),
      node("Decided in the thread?", "n8n-nodes-base.code", 2, {"jsCode": SLACK_PARSE_JS.strip()}, X(12), 300),
      node("Decision found?", "n8n-nodes-base.if", 2.2, {"conditions": {"options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict", "version": 2},
        "conditions": [{"id": nid(), "leftValue": "={{ $json.decided }}", "rightValue": "", "operator": {"type": "boolean", "operation": "true", "singleValue": True}}], "combinator": "and"}, "options": {}}, X(13), 300),
      node("Who answered", "n8n-nodes-base.slack", 2.7, {"resource": "user", "operation": "info", "user": {"__rl": True, "mode": "id", "value": "={{ $json.slack_user }}"}}, X(14), 300, onError="continueRegularOutput", credentials=SLACK),
      node("Review & approve", "n8n-nodes-base.code", 2, {"jsCode": SLACK_RESOLVE_JS.strip()}, X(15), 300),
    ] if GATE_MODE == "slack" else [
      node("Review & approve", "n8n-nodes-base.wait", 1.1, {
        "resume": "form", "formTitle": "Human approval gate",
        "formDescription": "One asset, one decision. Everything below was filled by the line.",
        "formFields": GATE_FIELDS, "options": {}}, X(12), 300, webhookId="a1b2c3d4-0002-4000-8000-aiactgate0001")
    ]),
    node("Resolve decision", "n8n-nodes-base.code", 2, {"jsCode": RESOLVE_JS.strip()}, X(13), 300),
    pg("Record decision", "with d as (insert into decisions (asset_id, reviewer, decision, reason, note, disclosure_status, responsible_person, artefact, execution_id, workflow_id) values ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10) returning seq, hash) update assets a set status = $11, disclosure_status = $6, decided_at = now(), manifest = $12::jsonb from d where a.id = $1 returning d.seq, d.hash",
       "={{ [ $json.id, $json.reviewer, $json.approval.decision, $json.approval.reason, $json.approval.note, $json.disclosure_status, $json.responsible_person, $json.approval.artefact, $json.approval.execution_id, $json.approval.workflow_id, $json.status, JSON.stringify(Object.fromEntries(Object.entries($json).filter(([k]) => k !== 'approval'))) ] }}", X(14), 300),
    pg("Read assets", "select id, status, disclosure_status, manifest from assets order by created_at", "={{ [] }}", X(15), 300),
    node("Read all workflows", "n8n-nodes-base.n8n", 1, {"resource": "workflow", "operation": "getAll", "returnAll": True, "filters": {}},
         X(16), 300, onError="continueRegularOutput", executeOnce=True, credentials={"n8nApi": {"id": N8N_API_CREDENTIAL_ID, "name": N8N_API_CREDENTIAL_NAME}}),
    node("Registry rows", "n8n-nodes-base.code", 2, {"jsCode": REGISTRY_JS.strip()}, X(17), 300),
    pg("Snapshot registry", "insert into registry_snapshots (partial, systems, registry) values ($1, $2, $3::jsonb)",
       "={{ [ $json.partial, $json.systems, JSON.stringify($json.registry) ] }}", X(18), 300),
    node("Return to caller", "n8n-nodes-base.code", 2, {"jsCode": RETURN_JS.strip()}, X(19), 300),
    node("How it works", "n8n-nodes-base.stickyNote", 1, {"width": 2700, "height": 130, "content":
        "## AI Act Transparency Kit — deployer side of Article 50, as a module\n"
        "Two entries: its own intake form, or **Execute Sub-workflow** from any production line (pass asset_type, language, model, prompt, operator, depicts_real_person, public_information, caller_workflow and the file as binary `data`). "
        "classify → label (Edit Image for images, an optional ffmpeg service for video, metadata for audio; no shell) + manifest → **human gate** (form, or a Slack thread the kit polls) (link on the audit view) → approval log → registry of every AI system on this instance with **path analysis**: generator → publishing node, what stands in between. "
        "Returns `approved`, `disclosure_status`, `labelled_path`, `disclosed_text` to the caller."}, X(4), 0),
]
kit_conn = wire(
    ("Asset produced", "Prompt hash"), ("Called by another workflow", "Prompt hash"),
    ("Prompt hash", "Classify (Art. 50)"), ("Classify (Art. 50)", "Is text?"),
    ("Is text?", "Text disclosure", 0), ("Is text?", "Save incoming file", 1),
    ("Text disclosure", "Build manifest"), ("Save incoming file", "Label media (service)"),
    ("Label media (service)", "Write labelled file", 0), ("Label media (service)", "Image?", 1),
    ("Image?", "Label image (Edit Image)", 0), ("Image?", "No burn-in", 1),
    ("Label image (Edit Image)", "Write labelled file", 0), ("Label image (Edit Image)", "No burn-in", 1),
    ("Write labelled file", "Burned in"), ("Burned in", "Build manifest"), ("No burn-in", "Build manifest"),
    *(( ("Build manifest", "Store asset"), ("Store asset", "Post to the review thread"), ("Post to the review thread", "Has a file?"),
        ("Has a file?", "Read labelled file", 0), ("Has a file?", "Wait for the thread", 1), ("Read labelled file", "Attach to the thread"), ("Attach to the thread", "Wait for the thread"),
        ("Wait for the thread", "Read the thread"), ("Read the thread", "Decided in the thread?"), ("Decided in the thread?", "Decision found?"),
        ("Decision found?", "Who answered", 0), ("Decision found?", "Wait for the thread", 1), ("Who answered", "Review & approve"),
        ("Review & approve", "Resolve decision") ) if GATE_MODE == "slack" else
      ( ("Build manifest", "Store asset"), ("Store asset", "Notify reviewer (Slack)"), ("Notify reviewer (Slack)", "Review & approve"),
        ("Review & approve", "Resolve decision") )),
    ("Resolve decision", "Record decision"),
    ("Record decision", "Read assets"), ("Read assets", "Read all workflows"),
    ("Read all workflows", "Registry rows"), ("Registry rows", "Snapshot registry"), ("Snapshot registry", "Return to caller"),
)
kit = {"id": KIT_ID, "name": "AI Act Transparency Kit", "nodes": kit_nodes, "connections": kit_conn, "active": False,
       "settings": {"executionOrder": "v1", "saveManualExecutions": True}, "meta": {"templateCredsSetupCompleted": True}}

# ============================================================================ audit view
LEDGER_SQL = ("select (select coalesce(json_agg(a order by a.created_at desc), '[]'::json) from assets a) as assets, "
              "(select coalesce(json_agg(d order by d.seq desc), '[]'::json) from decisions d) as decisions, "
              "(select registry from registry_snapshots order by seq desc limit 1) as registry, "
              "(select count(*) from verify_chain() where not ok) as chain_broken, (select count(*) from decisions) as chain_len, "
              "(select hash from decisions order by seq desc limit 1) as chain_head")
RENDER_JS = (HERE / "audit_render.js").read_text()
audit_nodes = [
    node("Audit request (GET)", "n8n-nodes-base.webhook", 2, {"path": "audit", "httpMethod": "GET", "responseMode": "responseNode", "options": {}},
         0, 300, webhookId="a1b2c3d4-0004-4000-8000-aiactaudit001"),
    pg("Read the ledger", LEDGER_SQL, "={{ [] }}", 240, 300),
    node("Render audit view", "n8n-nodes-base.code", 2, {"jsCode": RENDER_JS.strip()}, 480, 300),
    node("Respond HTML", "n8n-nodes-base.respondToWebhook", 1.1, {
        "respondWith": "text", "responseBody": "={{ $json.html }}",
        "options": {"responseHeaders": {"entries": [{"name": "Content-Type", "value": "text/html; charset=utf-8"}]}}}, 720, 300),
    node("What this is", "n8n-nodes-base.stickyNote", 1, {"width": 900, "height": 100, "content":
        "## Audit view — what an auditor reads instead of the pipeline\nAwaiting a human (gate links) · AI-systems registry with path analysis (Art. 4) · synthetic media & deepfakes (Art. 50(2), 50(4)) · generated public text (Art. 50(4) §2) · approval log (Art. 14, Art. 12 voluntary). Read from the Postgres ledger; the approval log is append-only and hash-chained, verified on every render."}, 0, 120),
]
audit = {"id": AUDIT_ID, "name": "AI Act Transparency Kit — Audit view", "nodes": audit_nodes,
         "connections": wire(("Audit request (GET)", "Read the ledger"), ("Read the ledger", "Render audit view"), ("Render audit view", "Respond HTML")),
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
  shows: 'nothing real', origin: 'generated', artistic: 'no', depicts_real_person: 'no', consent_reference: '', public_information: 'yes',
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
PUBLISH_NAME_JS = r"""
// Where the approved file goes. One item per approved asset; the two file nodes after this copy it.
return $input.all().filter(it => it.json.labelled_path).map(it => ({ json: { ...it.json,
  published_path: '/data/published/' + String(it.json.labelled_path).split('/').pop() } }));
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
    node("Prepare publish", "n8n-nodes-base.code", 2, {"jsCode": PUBLISH_NAME_JS.strip()}, X(7), 100),
    node("Read approved file", "n8n-nodes-base.readWriteFile", 1, {"operation": "read", "fileSelector": "={{ $json.labelled_path }}", "options": {"dataPropertyName": "data"}}, X(8), 100),
    node("Publish to site [exit]", "n8n-nodes-base.readWriteFile", 1, {"operation": "write", "fileName": "={{ $('Prepare publish').item.json.published_path }}", "dataPropertyName": "data", "options": {}}, X(9), 100),
    node("Returned, not published", "n8n-nodes-base.noOp", 1, {}, X(7), 300),
    node("What this line is", "n8n-nodes-base.stickyNote", 1, {"width": 1500, "height": 110, "content":
        "## A real production line with the kit as a module\nnotice → **Kokoro-82M**, three stock voices (local, no cloned person) → **AI Act gate** (Loop Over Items → Execute Sub-workflow, the parent waits for the human) → publish only what was approved. "
        "The publishing node is tagged `[exit]` so the registry knows it reaches people. Voices are stock, so this is `synthetic_media`, not a deep fake."}, X(0), 100),
]
host = {"id": HOST_ID, "name": "Recycling notice · three voices", "nodes": host_nodes,
        "connections": wire(("Notice text", "Three voices"), ("Three voices", "Kokoro TTS (local)"), ("Kokoro TTS (local)", "Attach fields"),
                            ("Attach fields", "One voice at a time"), ("One voice at a time", "Human approved?", 0), ("One voice at a time", "AI Act gate", 1),
                            ("AI Act gate", "One voice at a time"),
                            ("Human approved?", "Prepare publish", 0), ("Prepare publish", "Read approved file"), ("Read approved file", "Publish to site [exit]"), ("Human approved?", "Returned, not published", 1)),
        "active": False, "settings": {"executionOrder": "v1", "saveManualExecutions": True}}

for name, wf in (("transparency-kit.json", kit), ("audit-view.json", audit), ("host-line.json", host)):
    (HERE / name).write_text(json.dumps(wf, indent=2, ensure_ascii=False))
    print("wrote", name, len(wf["nodes"]), "nodes")
