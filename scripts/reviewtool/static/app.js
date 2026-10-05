// Dimguil translation review: one scene at a time, read whole, then decide line by line.

const $ = (sel, el = document) => el.querySelector(sel);
const $$ = (sel, el = document) => [...el.querySelectorAll(sel)];
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

const S = {
  cast: null, voices: {}, scenes: [], scene: null, mode: 'literal', focus: 0,
  decisions: {}, hoverPick: null, previewPick: null, word: null,
  furigana: true, font: null, tokens: new Map(), lookups: new Map(), fits: new Map(),
};

async function api(path, body) {
  const r = await fetch(path, body === undefined ? {} : {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
  });
  const data = await r.json();
  if (!r.ok) throw new Error(data.error || r.statusText);
  return data;
}

// --- people and shapes ---------------------------------------------------------------

const SHAPES = {
  circle: c => `<circle cx="7" cy="7" r="5.5" fill="${c}"/>`,
  square: c => `<rect x="1.5" y="1.5" width="11" height="11" rx="1.5" fill="${c}"/>`,
  heart: c => `<path d="M7 12.6 1.9 7.4A3.2 3.2 0 0 1 7 3.3a3.2 3.2 0 0 1 5.1 4.1Z" fill="${c}"/>`,
  book: c => `<path d="M1.5 2.5h4.2c.6 0 1.3.4 1.3 1v9c0-.6-.7-1-1.3-1H1.5Zm11 0H8.3c-.6 0-1.3.4-1.3 1v9c0-.6.7-1 1.3-1h4.2Z" fill="${c}"/>`,
  diamond: c => `<path d="M7 1 13 7 7 13 1 7Z" fill="${c}"/>`,
};
function shape(person, size = 13) {
  if (!person) return '';
  const party = S.cast.parties[person.party];
  return `<svg class="shape" width="${size}" height="${size}" viewBox="0 0 14 14" aria-hidden="true">${SHAPES[party.shape](person.color)}</svg>`;
}
function personForTag(tag) {
  return S.cast.people.find(p => p.tags.includes(tag)) || null;
}
function speakerOf(boxText) {
  const m = /^([^\n"]*)\n"/.exec(boxText || '');
  return m ? m[1] : null;
}

// --- box text <-> reading and editing --------------------------------------------------

function splitBox(text) {
  const m = /^([^\n"]*)\n"/.exec(text || '');
  const body = m ? text.slice(m[0].length) : (text || '');
  const pages = body.split('\n\r').map(p => p.split('\n').map(l => l.replace(/^ /, '')));
  return { name: m ? m[1] : null, pages };
}
function readable(text) {
  return splitBox(text).pages.map(p => p.join(' ')).join(' ').replace(/\{ff12\}/g, '[leader]').replace(/\{ff11\}0/g, '[number]');
}
function toEditor(text) {
  return splitBox(text).pages.map(p => p.join('\n')).join('\n\n');
}
function fromEditor(name, ed) {
  const pages = ed.replace(/\r/g, '').split(/\n[ \t]*\n/).map(p => p.split('\n').map(l => l.trim()).filter(l => l));
  const parts = pages.filter(p => p.length).map((lines, k) => {
    const first = (name !== null && k === 0) ? '"' : ' ';
    return first + lines[0] + lines.slice(1).map(l => '\n ' + l).join('');
  });
  return (name !== null ? name + '\n' : '') + parts.join('\n\r');
}
function jpBody(src) {
  const m = /^([^\n「]*)\n(?=「)/.exec(src);
  const body = m ? src.slice(m[0].length) : src;
  return { name: m ? m[1] : null, pages: body.split('\n\r').map(p => p.split('\n').map(l => l.replace(/^ /, ''))) };
}

// Word diff (LCS), for Compare mode.
function diffWords(a, b) {
  const x = a.split(/(\s+)/).filter(t => t.trim()), y = b.split(/(\s+)/).filter(t => t.trim());
  const n = x.length, m = y.length, L = Array.from({ length: n + 1 }, () => new Int32Array(m + 1));
  for (let i = n - 1; i >= 0; i--) for (let j = m - 1; j >= 0; j--)
    L[i][j] = x[i] === y[j] ? L[i + 1][j + 1] + 1 : Math.max(L[i + 1][j], L[i][j + 1]);
  const A = [], B = [];
  let i = 0, j = 0;
  while (i < n || j < m) {
    if (i < n && j < m && x[i] === y[j]) { A.push(esc(x[i])); B.push(esc(y[j])); i++; j++; }
    else if (j < m && (i >= n || L[i][j + 1] >= L[i + 1][j])) { B.push(`<ins>${esc(y[j])}</ins>`); j++; }
    else { A.push(`<del>${esc(x[i])}</del>`); i++; }
  }
  return [A.join(' '), B.join(' ')];
}

// --- decisions -------------------------------------------------------------------------

const lines = () => S.scene ? S.scene.lines : [];
const draftKey = () => `dimguil-review:${S.scene.id}`;
function needsDecision(ln) { return ln.faithful !== ln.current; }
function decisionOf(ln) {
  const d = S.decisions[ln.ref];
  if (d) return d;
  return needsDecision(ln) ? null : { choice: 'current', auto: true };
}
function textFor(ln, choice) {
  if (choice === 'current') return ln.current;
  if (choice === 'faithful') return ln.faithful;
  if (choice === 'edited') return (S.decisions[ln.ref] && S.decisions[ln.ref].edited) || ln.faithful;
  return ln.current;
}
function saveDraft() {
  localStorage.setItem(draftKey(), JSON.stringify(S.decisions));
}
function setChoice(i, choice, { advance = true } = {}) {
  const ln = lines()[i];
  const prev = S.decisions[ln.ref] || {};
  S.decisions[ln.ref] = { ...prev, choice, copies: prev.copies ?? true };
  if (choice === 'edited' && !prev.edited) S.decisions[ln.ref].edited = ln.faithful;
  saveDraft();
  if (S.mode === 'compare') rerenderKeepingFocus(); else renderLineState(i);
  renderApplyBar();
  if (choice === 'edited') { renderInspector(); openEditor(); return; }
  if (advance) {
    const next = lines().findIndex((l, k) => k > i && needsDecision(l) && !S.decisions[l.ref]);
    if (next >= 0) focusLine(next); else renderInspector();
  } else renderInspector();
}

// --- scene list ------------------------------------------------------------------------

function renderSceneList() {
  const byFile = new Map();
  for (const sc of S.scenes) {
    if (!byFile.has(sc.file)) byFile.set(sc.file, []);
    byFile.get(sc.file).push(sc);
  }
  const partyOf = f => Object.entries(S.cast.parties).find(([, p]) => p.file === f);
  const STATUS = { applied: 'Applied, waiting for commit', kept: 'Reviewed, no changes', committed: 'Committed' };
  $('#scene-list').innerHTML = [...byFile.entries()].map(([f, list]) => {
    const [pid, party] = partyOf(f) || ['others', { name: `NPC_MES${f}`, shape: 'diamond' }];
    const lead = S.cast.people.find(p => p.party === pid);
    return `<section class="party"><h2>${shape(lead)} ${esc(party.name)}</h2><ol>${list.map(sc => `
      <li><button type="button" class="scene-link" data-id="${esc(sc.id)}" ${S.scene && S.scene.id === sc.id ? 'aria-current="true"' : ''}>
        <span class="num">${sc.number ?? ''}</span><span>${esc(sc.title)}</span>
        <span class="meta">${sc.priority ? esc(sc.priority) + ' priority' : ''}${sc.status !== 'open' ? ` <span class="${sc.status === 'committed' ? 'done' : ''}">${STATUS[sc.status] || sc.status}</span>` : ''}</span>
      </button></li>`).join('')}</ol></section>`;
  }).join('') || '<p class="hint" style="padding:0 1.2rem">No scenes prepared yet.</p>';
  $$('.scene-link').forEach(b => b.addEventListener('click', () => openScene(b.dataset.id)));
}

// --- opening a scene -------------------------------------------------------------------

async function openScene(id, { line = 0, mode } = {}) {
  S.scene = await api(`/api/scene?id=${encodeURIComponent(id)}`);
  S.decisions = JSON.parse(localStorage.getItem(draftKey()) || '{}');
  S.mode = mode || localStorage.getItem('dimguil-review:mode') || 'literal';
  S.word = null; S.hoverPick = null; S.previewPick = null;
  $('#empty').hidden = true; $('#scene').hidden = false;
  const sc = S.scene;
  const party = Object.values(S.cast.parties).find(p => p.file === sc.file);
  $('#scene-file').innerHTML = `${shape(S.cast.people.find(p => S.cast.parties[p.party] === party))} ${esc(party ? party.name : '')}, NPC_MES${sc.file}${sc.number ? `, flagged scene ${sc.number}` : ''}${sc.priority ? `, ${esc(sc.priority)} priority` : ''}`;
  $('#scene-title').textContent = sc.title;
  $('#scene-where').textContent = sc.where || '';
  $('#scene-summary').textContent = sc.summary || '';
  $('#scene-assembled').textContent = sc.assembled || '';
  $('#scene-notes-body').innerHTML = (sc.notes || []).map(n => `<div class="note"><h4>${esc(n.title)}</h4><p>${esc(n.text)}</p>${sourcesHtml(n.sources)}</div>`).join('');
  renderSceneList();
  setMode(S.mode, { keepFocus: true });
  $('#stage').scrollTop = 0;
  focusLine(Math.min(line, sc.lines.length - 1), { scroll: line > 0 });
  renderApplyBar();
  renderQuestions();
}

function sourcesHtml(list) {
  if (!list || !list.length) return '';
  return `<ul class="sources">${list.map(s => `<li>${s.url ? `<a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.label)}</a>` : esc(s.label)}</li>`).join('')}</ul>`;
}

function setMode(mode, { keepFocus } = {}) {
  S.mode = mode;
  localStorage.setItem('dimguil-review:mode', mode);
  $$('.readings button').forEach(b => b.setAttribute('aria-selected', String(b.dataset.mode === mode)));
  renderScript();
  if (!keepFocus) focusLine(S.focus, { scroll: false });
  updateHash();
}

// --- the script ------------------------------------------------------------------------

function renderScript() {
  $('#script').innerHTML = lines().map((ln, i) => {
    const tag = speakerOf(ln.current) || speakerOf(ln.faithful);
    const who = personForTag(tag);
    const color = who ? who.color : '#4a5260';
    return `<li class="line" data-i="${i}" style="--who:${color}">
      <div class="who"><span class="name">${shape(who)}${esc(tag || 'Narration')}</span><span class="ctx">${esc(ln.context || '')}</span></div>
      <div class="said">${saidHtml(ln, i)}<div class="state" id="state-${i}"></div></div>
    </li>`;
  }).join('');
  $$('#script .line').forEach(el => {
    const i = +el.dataset.i;
    el.addEventListener('click', e => {
      const opt = e.target.closest('.opt.pickable');
      if (opt) { setChoice(i, opt.dataset.pick, { advance: true }); return; }
      if (S.focus !== i) focusLine(i, { scroll: false });
    });
    $$('.opt.pickable', el).forEach(o => {
      o.addEventListener('mouseenter', () => { if (S.focus === i) { S.hoverPick = o.dataset.pick; renderPreview(); } });
      o.addEventListener('mouseleave', () => { if (S.focus === i) { S.hoverPick = null; renderPreview(); } });
    });
  });
  lines().forEach((_, i) => renderLineState(i));
}

function silentOr(text) {
  return /^[.\s…]*$/.test(text) ? `<span class="silent">${esc(text)}</span>` : esc(text);
}

function saidHtml(ln, i) {
  const jp = jpBody(ln.jp).pages.map(p => p.map(esc).join('<br>')).join('<span class="pagebreak"></span>');
  if (S.mode === 'jp') return `<div class="jp" lang="ja">${jp}</div>`;
  if (S.mode === 'literal') return `<div>${silentOr(ln.literal)}</div>`;
  if (S.mode === 'current') return `<div>${silentOr(readable(ln.current))}</div>`;
  if (S.mode === 'faithful') return `<div>${silentOr(readable(ln.faithful))}</div>`;
  // compare and decide
  const d = decisionOf(ln);
  const cur = readable(ln.current), fai = readable(ln.faithful);
  const same = cur === fai;
  const [dc, df] = same ? [esc(cur), esc(fai)] : diffWords(cur, fai);
  const picked = c => d && !d.auto && d.choice === c ? ' picked' : '';
  const edited = S.decisions[ln.ref] && S.decisions[ln.ref].edited;
  return `<div class="cmp">
    <span class="lab">Japanese</span><div class="jp" lang="ja">${jp}</div>
    <span class="lab">Literal</span><div class="literal">${silentOr(ln.literal)}</div>
    ${same ? `<span class="lab">Current</span><div>${silentOr(cur)} <span class="same-note">Faithful is the same; no change proposed.</span></div>` : `
    <span class="lab">Current</span><div class="opt pickable${picked('current')}" data-pick="current" title="Keep current (c)">${dc}</div>
    <span class="lab">Faithful</span><div class="opt pickable${picked('faithful')}" data-pick="faithful" title="Use faithful (f)">${df}</div>`}
    ${edited ? `<span class="lab">Edited</span><div class="opt pickable${picked('edited')}" data-pick="edited">${esc(readable(edited))}</div>` : ''}
    ${ln.why ? `<span class="lab">Why</span><div class="hint" style="margin:0">${esc(ln.why)}</div>` : ''}
  </div>`;
}

function renderLineState(i) {
  const ln = lines()[i], el = $(`#state-${i}`);
  if (!el) return;
  const d = decisionOf(ln);
  const notes = (ln.notes || []).length ? ' Has notes.' : '';
  if (!needsDecision(ln) && !(S.decisions[ln.ref] && S.decisions[ln.ref].choice === 'edited')) { el.innerHTML = S.mode === 'compare' ? '' : (notes ? `<span>${notes.trim()}</span>` : ''); return; }
  const label = { current: 'Keeping current', faithful: 'Using faithful', edited: 'Using your edit' };
  if (S.mode !== 'compare') { el.innerHTML = d ? `<span class="chosen quiet">${label[d.choice]}</span>` : '<span class="quiet">Change proposed</span>'; return; }
  el.innerHTML = (d ? `<span class="chosen">${label[d.choice]}.</span>` : `<span class="needs">Change proposed.</span>`) + notes;
}

function focusLine(i, { scroll = true } = {}) {
  if (!S.scene) return;
  S.focus = Math.max(0, Math.min(i, lines().length - 1));
  S.word = null; S.hoverPick = null; S.previewPick = null;
  $$('#script .line').forEach(el => el.classList.toggle('focused', +el.dataset.i === S.focus));
  const el = $(`#script .line[data-i="${S.focus}"]`);
  if (scroll && el) el.scrollIntoView({ block: S.mode === 'compare' ? 'start' : 'center' });
  renderInspector();
  updateHash();
}

function updateHash() {
  if (!S.scene) return;
  history.replaceState(null, '', `#s=${encodeURIComponent(S.scene.id)}&l=${S.focus}&m=${S.mode}`);
}

function renderApplyBar() {
  const ls = lines();
  const open = ls.filter(l => needsDecision(l) && !S.decisions[l.ref]).length;
  const changes = ls.filter(l => { const d = decisionOf(l); return d && textFor(l, d.choice) !== l.current; }).length;
  const prior = S.scene.decision;
  let msg = open ? `${open} proposed ${open === 1 ? 'change needs' : 'changes need'} your decision.`
    : changes ? `Ready: ${changes} ${changes === 1 ? 'line changes' : 'lines change'}.` : 'Ready: no lines change.';
  if (prior) msg += prior.status === 'committed' ? ` Committed as ${prior.commit || 'a commit'}.` : ` Applied ${prior.applied_at.slice(0, 16).replace('T', ' ')}; Claude commits next.`;
  $('#apply-status').textContent = msg;
  $('#apply-open').disabled = open > 0;
}

// --- inspector -------------------------------------------------------------------------

const CONTENT = new Set(['名詞', '代名詞', '動詞', '形容詞', '形状詞', '副詞', '連体詞', '感動詞', '接頭辞']);
function wordNotesFor(ln, token) {
  if (!token || (!CONTENT.has(token.pos) && !token.span)) return [];
  return (ln.words || []).filter(w => w.jp.includes(token.span ? token.span[0] : token.s) || (CONTENT.has(token.pos) && w.jp.includes(token.s)));
}

async function renderInspector() {
  const ln = lines()[S.focus];
  if (!ln) return;
  $('#insp-empty').hidden = true; $('#insp').hidden = false;
  const tag = speakerOf(ln.current);
  const who = personForTag(tag);
  $('#inspector').style.setProperty('--who', who ? who.color : '#1c212a');
  $('#insp-ref').textContent = ln.context ? `${ln.ref}, ${ln.context}` : ln.ref;
  $('#insp-speaker').innerHTML = `${shape(who, 16)}<span style="color:${who ? who.color : 'inherit'}">${esc(tag || 'Narration')}</span>`;
  const voice = who && who.voice ? S.voices[who.voice] : null;
  $('#voice-sec').hidden = !voice;
  if (voice) { $('#voice-name').textContent = who.name; $('#voice-text').textContent = voice; }

  // line notes and why
  const notes = [...(ln.why ? [{ text: ln.why, title: 'Why the faithful version differs' }] : []), ...(ln.notes || [])];
  $('#line-notes-sec').hidden = !notes.length;
  $('#line-notes').innerHTML = notes.map(n => `<div class="note">${n.title ? `<h4>${esc(n.title)}</h4>` : ''}<p>${esc(n.text)}</p>${sourcesHtml(n.sources)}</div>`).join('')
    + (ln.confidence ? `<p class="hint">Claude's confidence in the faithful reading: ${esc(ln.confidence)}.</p>` : '');

  renderChoice();
  renderCopies();
  renderPreview();
  renderWordPanel();
  await renderJapanese(ln);
}

async function tokensFor(text) {
  if (!S.tokens.has(text)) S.tokens.set(text, api(`/api/tokens?text=${encodeURIComponent(text)}`));
  return S.tokens.get(text);
}

async function renderJapanese(ln) {
  const ref = ln.ref;
  const { pages } = jpBody(ln.jp);
  const html = [];
  for (const page of pages) {
    const ls = [];
    for (const line of page) {
      const toks = mergeSpans(await tokensFor(line));
      ls.push(toks.map((t, k) => tokenHtml(ln, t, `${html.length}-${ls.length}-${k}`)).join(''));
    }
    html.push(`<div class="page">${ls.join('<br>')}</div>`);
  }
  if (lines()[S.focus].ref !== ref) return; // moved on meanwhile
  const box = $('#insp-jp');
  box.innerHTML = html.join('') + `<p class="legend"><span class="k1">underlined</span>: Claude has a note on it. <span class="k2">orange</span>: a role-language marker. Hover for a gloss, click for everything.</p>`;
  box.classList.toggle('no-ruby', !S.furigana);
  $$('.w', box).forEach(el => {
    el.addEventListener('click', () => selectWord(JSON.parse(el.dataset.t)));
    el.addEventListener('mouseenter', () => showTip(el));
    el.addEventListener('mouseleave', hideTip);
  });
}

// A run of pieces that is one dictionary word (あの + 人, 年 + 若い) shows as one word,
// with the dictionary's reading rather than the splitter's guess for each piece.
function mergeSpans(toks) {
  const out = [];
  for (let k = 0; k < toks.length; k++) {
    const t = toks[k];
    if (t.span && t.span[1] > 1) {
      out.push({ ...t, s: t.span[0], lemma: t.span[0], reading: t.span_reading || '', merged: true });
      k += t.span[1] - 1;
    } else out.push(t);
  }
  return out;
}

function tokenHtml(ln, t, id) {
  if (t.plain) return esc(t.s);
  const punct = !/[\p{L}\p{N}]/u.test(t.s);
  if (punct) return `<span class="punct">${esc(t.s)}</span>`;
  const noted = wordNotesFor(ln, t).length > 0;
  const kanji = /[一-鿿々]/.test(t.s);
  const inner = kanji && t.reading && t.reading !== t.s ? `<ruby>${esc(t.s)}<rt>${esc(t.reading)}</rt></ruby>` : esc(t.s);
  const sel = S.word && S.word.s === t.s ? ' sel' : '';
  return `<span class="w${noted ? ' noted' : ''}${t.role ? ' role' : ''}${sel}" data-t="${esc(JSON.stringify(t))}" tabindex="0">${inner}</span>`;
}

// hover gloss
let tipEl = null, tipTimer = null;
function showTip(el) {
  clearTimeout(tipTimer);
  tipTimer = setTimeout(async () => {
    const t = JSON.parse(el.dataset.t);
    const ln = lines()[S.focus];
    const notes = wordNotesFor(ln, t);
    let text;
    if (notes.length) text = notes[0].sense;
    else {
      const r = await lookupWord(t.span ? t.span[0] : t.s, t.lemma);
      const e = r.jmdict[0];
      const w = r.wiktionary[0];
      text = e ? e.senses.slice(0, 2).map(s => s.gloss.slice(0, 3).join('; ')).join(' / ') : w ? w.senses[0].glosses[0] : 'No dictionary entry; click for more.';
      if (r.role) text = `${r.role.type}. ${text}`;
    }
    if (!el.isConnected) return;
    tipEl = tipEl || Object.assign(document.createElement('div'), { className: 'tip', role: 'tooltip' });
    tipEl.textContent = text;
    document.body.append(tipEl);
    const r = el.getBoundingClientRect();
    tipEl.style.left = `${Math.min(window.innerWidth - 340, Math.max(8, r.left))}px`;
    tipEl.style.top = `${r.bottom + 6}px`;
  }, 180);
}
function hideTip() { clearTimeout(tipTimer); if (tipEl) tipEl.remove(); }

async function lookupWord(q, lemma) {
  const key = `${q}|${lemma || ''}`;
  if (!S.lookups.has(key)) S.lookups.set(key, api(`/api/lookup?q=${encodeURIComponent(q)}&lemma=${encodeURIComponent(lemma || '')}`));
  return S.lookups.get(key);
}

function selectWord(t) {
  S.word = t;
  $$('#insp-jp .w').forEach(el => el.classList.toggle('sel', JSON.parse(el.dataset.t).s === t.s));
  renderWordPanel().then(() => {
    const smooth = !matchMedia('(prefers-reduced-motion: reduce)').matches;
    $('#word-sec').scrollIntoView({ block: 'start', behavior: smooth ? 'smooth' : 'auto' });
  });
}

async function renderWordPanel() {
  const ln = lines()[S.focus];
  const body = $('#word-body');
  $('#word-back').hidden = !S.word;
  if (!S.word) {
    $('#word-h').textContent = 'Words in this line';
    body.innerHTML = (ln.words || []).length ? ln.words.map(wnoteHtml).join('')
      : '<p class="hint">No word notes for this line. Click any word in the Japanese to look it up.</p>';
    return;
  }
  const t = S.word;
  const q = t.span ? t.span[0] : t.s;
  $('#word-h').innerHTML = `<span lang="ja" style="font-family:var(--mincho)">${esc(q)}</span>${t.lemma && t.lemma !== q ? ` <span class="hint">from ${esc(t.lemma)}</span>` : ''}`;
  body.innerHTML = '<p class="hint">Looking up…</p>';
  const [r, conc] = await Promise.all([lookupWord(q, t.lemma), api(`/api/concordance?q=${encodeURIComponent(q.length > 1 ? q : t.lemma || q)}&ref=${encodeURIComponent(ln.ref)}`)]);
  if (S.word !== t) return;
  const parts = [];
  const notes = wordNotesFor(ln, t);
  if (notes.length) parts.push(`<p class="src-label">Claude's note for this scene</p>${notes.map(wnoteHtml).join('')}`);
  if (r.role) parts.push(`<p class="src-label">Role language</p><div class="role-note"><strong>${esc(r.role.type)}.</strong> ${esc(r.role.note)}</div>`);
  if (r.wiktionary.length) parts.push(`<p class="src-label">English Wiktionary</p>${r.wiktionary.map(w => `<div class="dict-entry"><span class="forms" lang="ja">${esc(w.word)}</span> <span class="tag">${esc(w.pos)}</span>
      <ol>${w.senses.map(s => `<li>${s.tags.map(x => `<span class="tag${/archaic|honorific|humble|feminine|masculine|dated|colloquial|slang|literary|derogatory|vulgar|dialect/.test(x) ? ' key' : ''}">${esc(x)}</span>`).join('')}${esc(s.glosses.join('; '))}${s.examples.length ? `<div class="ex"><span class="ja" lang="ja">${esc(s.examples[0].text)}</span><span class="en">${esc(s.examples[0].english || '')}</span></div>` : ''}</li>`).join('')}</ol>
      ${w.etymology ? `<p class="hint">${esc(w.etymology)}</p>` : ''}</div>`).join('')}`);
  if (r.jmdict.length) parts.push(`<p class="src-label">JMdict</p>${r.jmdict.slice(0, 4).map(e => `<div class="dict-entry"><span class="forms" lang="ja">${esc([...e.kanji.map(k => k.k), ...e.kana.map(k => k.r)].slice(0, 4).join(', '))}</span>
      <ol>${e.senses.map(s => `<li>${s.tags.filter(x => !/^(n|v|adj|exp|prt|aux|int|pn|adv|conj|ctr|suf|pref)/.test(x.tag) || /arch|hon|hum|fem|male|dated|col|sl|obs|poet|vulg|derog|yoji|id/.test(x.tag)).map(x => `<span class="tag${/arch|hon|hum|fem|male|dated|col|sl|obs|poet|vulg|derog/.test(x.tag) ? ' key' : ''}" title="${esc(x.text)}">${esc(x.text)}</span>`).join('')}${esc(s.gloss.join('; '))}${s.info.length ? ` <span class="hint">(${esc(s.info.join('; '))})</span>` : ''}</li>`).join('')}</ol></div>`).join('')}`);
  if (r.kanji.length) parts.push(`<p class="src-label">Kanji</p>${r.kanji.map(k => `<div class="kanji"><span class="lit" lang="ja">${esc(k.lit)}</span><div>${esc(k.meanings.slice(0, 5).join(', '))}<div class="rd" lang="ja">${esc([...k.on, ...k.kun].slice(0, 6).join('、'))}</div></div></div>`).join('')}`);
  if (conc.hits.length) parts.push(`<p class="src-label">Elsewhere in the game (${conc.total})</p>${conc.hits.map(h => `<div class="ex"><span class="hint">${esc(h.ref)}</span><span class="ja" lang="ja">${esc(h.jp.replace(/\n\r?/g, ' '))}</span><span class="en">${esc(h.en.replace(/\n\r?/g, ' '))}</span></div>`).join('')}`);
  if (r.examples.length) parts.push(`<p class="src-label">In everyday Japanese (Tatoeba)</p>${r.examples.map(x => `<div class="ex"><span class="ja" lang="ja">${esc(x.jp)}</span><span class="en">${esc(x.en)}</span></div>`).join('')}`);
  if (!parts.length) parts.push('<p class="hint">Nothing found. Ask Claude below.</p>');
  parts.push('<p class="credit">Dictionaries: JMdict and KANJIDIC2 (EDRDG, CC BY-SA 4.0); English Wiktionary via kaikki.org (CC BY-SA 4.0); Tatoeba (CC BY 2.0 FR). Role-language notes after Kinsui Satoshi.</p>');
  body.innerHTML = parts.join('');
  $('#ask-text').placeholder = `What does ${q} mean here?`;
}

function wnoteHtml(w) {
  return `<div class="wnote"><div class="head"><span class="jpw" lang="ja">${esc(w.jp)}</span>${w.reading ? `<span class="rd" lang="ja">${esc(w.reading)}</span>` : ''}${w.register ? `<span class="reg">${esc(w.register)}</span>` : ''}${w.confidence && w.confidence !== 'high' ? `<span class="conf">${esc(w.confidence)} confidence</span>` : ''}</div>
    <p>${esc(w.sense)}</p>${sourcesHtml(w.sources)}</div>`;
}

// --- choice, editor, copies -------------------------------------------------------------

function renderChoice() {
  const ln = lines()[S.focus];
  const d = decisionOf(ln);
  $$('#choice button').forEach(b => {
    b.setAttribute('aria-pressed', String(!!d && !d.auto && d.choice === b.dataset.c));
    if (b.dataset.c === 'faithful') b.disabled = !needsDecision(ln);
  });
  $('#line-note').value = (S.decisions[ln.ref] && S.decisions[ln.ref].note) || '';
  const editing = d && d.choice === 'edited';
  $('#editor').hidden = !editing;
  if (editing) $('#edit-text').value = toEditor(S.decisions[ln.ref].edited);
}

function openEditor() {
  $('#editor').hidden = false;
  const ta = $('#edit-text');
  ta.focus();
  ta.setSelectionRange(ta.value.length, ta.value.length);
}

let editTimer = null;
function onEdit() {
  const ln = lines()[S.focus];
  const name = splitBox(ln.current).name;
  S.decisions[ln.ref] = { ...(S.decisions[ln.ref] || {}), choice: 'edited', edited: fromEditor(name, $('#edit-text').value) };
  saveDraft();
  clearTimeout(editTimer);
  editTimer = setTimeout(() => { renderPreview(); renderLineState(S.focus); renderApplyBar(); refreshCompareLine(); }, 160);
}
function refreshCompareLine() {
  if (S.mode === 'compare') rerenderKeepingFocus();
}
function rerenderKeepingFocus() {
  const stage = $('#stage'), top = stage.scrollTop;
  renderScript();
  $$('#script .line').forEach(e => e.classList.toggle('focused', +e.dataset.i === S.focus));
  stage.scrollTop = top;
}

function renderCopies() {
  const ln = lines()[S.focus];
  const box = $('#copies');
  if (!ln.copies.length) { box.innerHTML = ''; return; }
  const d = S.decisions[ln.ref];
  const on = !d || d.copies !== false;
  box.innerHTML = `<label class="copies"><input type="checkbox" id="copies-on" ${on ? 'checked' : ''}> Also change ${ln.copies.map(esc).join(', ')}, which ${ln.copies.length === 1 ? 'has' : 'have'} the same Japanese (each keeps its own speaker name).</label>`;
  $('#copies-on').addEventListener('change', e => {
    S.decisions[ln.ref] = { ...(S.decisions[ln.ref] || { choice: null }), copies: e.target.checked };
    saveDraft();
  });
}

// --- the game preview -------------------------------------------------------------------

async function fitFor(ref, text) {
  const key = `${ref}\u0000${text}`;
  if (!S.fits.has(key)) S.fits.set(key, api('/api/fit', { ref, text }));
  return S.fits.get(key);
}

function previewChoice(ln) {
  const d = decisionOf(ln);
  return S.previewPick || S.hoverPick || (d && !d.auto ? d.choice : needsDecision(ln) ? 'faithful' : 'current');
}

async function renderPreview() {
  const ln = lines()[S.focus];
  const pick = previewChoice(ln);
  const hasEdit = !!(S.decisions[ln.ref] && S.decisions[ln.ref].edited);
  $$('#preview-pick button').forEach(b => {
    b.setAttribute('aria-checked', String(b.dataset.v === pick));
    b.disabled = (b.dataset.v === 'faithful' && !needsDecision(ln)) || (b.dataset.v === 'edited' && !hasEdit);
  });
  const text = textFor(ln, pick);
  const f = await fitFor(ln.ref, text);
  if (lines()[S.focus] !== ln) return;
  const well = $('#preview');
  well.innerHTML = '';
  f.pages.forEach((page, k) => {
    const limit = Math.max(f.lines, f.source_lines[k] || 0);
    well.append(drawPage(page, f.width, limit));
    if (f.pages.length > 1 || page.some(l => l.placeholder)) {
      const cap = document.createElement('p');
      cap.className = 'pagecap';
      cap.textContent = `Page ${k + 1} of ${f.pages.length}${page.some(l => l.placeholder) ? '. The leader\'s name is drawn at its widest.' : ''}`;
      well.append(cap);
    }
  });
  $('#fit').innerHTML = fitMessages(f).join('');
}

function fitMessages(f) {
  const out = [];
  f.pages.forEach((page, k) => {
    const where = f.pages.length > 1 ? `Page ${k + 1}, line` : 'Line';
    page.forEach((l, j) => {
      if (l.width > f.width) out.push(`<li class="bad">${where} ${j + 1} is ${l.width - f.width} px too wide (${l.width} of ${f.width}).</li>`);
    });
    const limit = Math.max(f.lines, f.source_lines[k] || 0);
    if (page.length > limit) out.push(`<li class="bad">${f.pages.length > 1 ? `Page ${k + 1}` : 'The page'} has ${page.length} lines; this box takes ${limit}.</li>`);
  });
  for (const p of f.problems) {
    if (/^\d+px: |^page \d+ has/.test(p)) continue;
    const intended = p.includes('fine if intended');
    out.push(`<li class="${intended ? 'warn' : 'bad'}">${esc(intended ? p.replace(/ \(fine if intended\)/, '. That\'s fine if intended.').replace(/^(\d+) pages, source has (\d+)/, 'This has $1 pages; the Japanese has $2') : p)}</li>`);
  }
  if (!out.length) out.push(`<li class="ok">Fits. The widest line is ${Math.max(...f.pages.flat().map(l => l.width))} of ${f.width} px.</li>`);
  return out;
}

function drawPage(page, width, limit) {
  const { meta, atlas, box } = S.font;
  const c = document.createElement('canvas');
  c.width = 350; c.height = 80;
  const g = c.getContext('2d');
  g.imageSmoothingEnabled = false;
  g.drawImage(box, 0, 0);
  page.forEach((line, j) => {
    const y = meta.top + (j - 1) * meta.pitch;
    let x = meta.origin_x;
    for (const code of line.codes) {
      const gl = meta.glyphs[code];
      if (!gl) continue;
      g.drawImage(atlas, gl[0], gl[1], gl[2], meta.cell_h, x, y, gl[2], meta.cell_h);
      x += gl[2];
    }
    if (line.width > width) {
      g.fillStyle = 'rgba(220, 60, 50, 0.85)';
      g.fillRect(meta.origin_x + width, y, 1, meta.pitch);
      g.fillStyle = 'rgba(220, 60, 50, 0.25)';
      g.fillRect(meta.origin_x + width + 1, y, line.width - width, meta.pitch);
    }
    if (j >= limit) {
      g.fillStyle = 'rgba(220, 60, 50, 0.3)';
      g.fillRect(meta.origin_x - 2, y, width + 4, meta.pitch);
    }
  });
  c.setAttribute('role', 'img');
  c.setAttribute('aria-label', page.length + ' lines in the game text box');
  return c;
}

// --- apply -----------------------------------------------------------------------------

function openApply() {
  const ls = lines();
  const changed = ls.filter(l => { const d = decisionOf(l); return d && textFor(l, d.choice) !== l.current; });
  $('#apply-summary').textContent = changed.length
    ? `${changed.length} ${changed.length === 1 ? 'line changes' : 'lines change'}. Everything else stays as it is.`
    : 'No lines change. Applying records that the scene was reviewed.';
  $('#apply-list').innerHTML = changed.map(l => {
    const d = decisionOf(l);
    return `<li><span class="ref">${esc(l.ref)}, ${d.choice === 'edited' ? 'your edit' : 'faithful'}${l.copies.length && d.copies !== false ? `, also ${l.copies.map(esc).join(', ')}` : ''}</span><br>
      <span class="before">${esc(readable(l.current))}</span><br>${esc(readable(textFor(l, d.choice)))}</li>`;
  }).join('');
  $('#apply-error').hidden = true;
  $('#apply-dialog').showModal();
}

async function confirmApply() {
  const btn = $('#apply-confirm');
  btn.disabled = true;
  try {
    const body = {
      scene: S.scene.id, note: $('#scene-note').value,
      lines: lines().map(l => {
        const d = decisionOf(l);
        const own = S.decisions[l.ref] || {};
        return { ref: l.ref, choice: d.choice, text: textFor(l, d.choice), note: own.note || '', copies: own.copies === false ? [] : l.copies };
      }),
    };
    await api('/api/apply', body);
    localStorage.removeItem(draftKey());
    $('#apply-dialog').close();
    const st = await api('/api/state');
    S.scenes = st.scenes;
    await openScene(S.scene.id, { line: S.focus, mode: S.mode });
  } catch (e) {
    $('#apply-error').textContent = e.message;
    $('#apply-error').hidden = false;
  } finally {
    btn.disabled = false;
  }
}

// --- questions -------------------------------------------------------------------------

function renderQuestions() {
  const qs = (S.scene && S.scene.questions) || [];
  $('#questions').innerHTML = qs.slice().reverse().map(q => `<li><div class="q">${esc(q.ref || '')}${q.about ? ` (${esc(q.about)})` : ''}: ${esc(q.question)}</div>
    <div class="a ${q.answer ? '' : 'pending'}">${q.answer ? esc(q.answer) : 'Waiting for Claude.'}</div></li>`).join('');
}
async function sendQuestion() {
  const text = $('#ask-text').value.trim();
  if (!text) return;
  const ln = lines()[S.focus];
  const q = await api('/api/ask', { scene: S.scene.id, ref: ln.ref, about: S.word ? (S.word.span ? S.word.span[0] : S.word.s) : '', question: text });
  S.scene.questions.push(q);
  $('#ask-text').value = '';
  renderQuestions();
}
setInterval(async () => {
  if (!S.scene || document.hidden) return;
  const all = await api('/api/questions').catch(() => null);
  if (!all) return;
  const mine = all.filter(q => q.scene === S.scene.id);
  if (JSON.stringify(mine) !== JSON.stringify(S.scene.questions)) { S.scene.questions = mine; renderQuestions(); }
}, 15000);

// --- keyboard --------------------------------------------------------------------------

document.addEventListener('keydown', e => {
  const typing = e.target.closest('textarea, input');
  if (e.key === 'Escape') {
    if (typing) { e.target.blur(); return; }
    if (S.word) { S.word = null; renderWordPanel(); $$('#insp-jp .w').forEach(el => el.classList.remove('sel')); }
    return;
  }
  if (typing || e.ctrlKey || e.metaKey || e.altKey || $('dialog[open]')) return;
  if (e.key === '?') { $('#help').showModal(); return; }
  if (!S.scene) return;
  const modes = { 1: 'jp', 2: 'literal', 3: 'current', 4: 'faithful', 5: 'compare' };
  if (modes[e.key]) { setMode(modes[e.key]); e.preventDefault(); return; }
  if (e.key === 'j' || e.key === 'ArrowDown') { focusLine(S.focus + 1); e.preventDefault(); }
  else if (e.key === 'k' || e.key === 'ArrowUp') { focusLine(S.focus - 1); e.preventDefault(); }
  else if (e.key === 'c') setChoice(S.focus, 'current');
  else if (e.key === 'f' && needsDecision(lines()[S.focus])) setChoice(S.focus, 'faithful');
  else if (e.key === 'e') { setChoice(S.focus, 'edited'); e.preventDefault(); }
  else if (e.key === 'r') { S.furigana = !S.furigana; $('#furigana').checked = S.furigana; $('#insp-jp').classList.toggle('no-ruby', !S.furigana); }
  else if (e.key === '[' || e.key === ']') {
    const k = S.scenes.findIndex(s => s.id === S.scene.id) + (e.key === ']' ? 1 : -1);
    if (S.scenes[k]) openScene(S.scenes[k].id);
  }
});

// --- start -----------------------------------------------------------------------------

function loadImage(src) {
  return new Promise((res, rej) => { const i = new Image(); i.onload = () => res(i); i.onerror = rej; i.src = src; });
}

async function main() {
  const [st, meta, atlas, box] = await Promise.all([
    api('/api/state'), api('/font/font.json'), loadImage('/font/atlas.png'), loadImage('/font/box.png'),
  ]);
  S.cast = st.cast; S.voices = st.voices; S.scenes = st.scenes;
  S.font = { meta, atlas, box };
  $('#splitter-hint').hidden = st.splitter;
  renderSceneList();

  $$('.readings button').forEach(b => b.addEventListener('click', () => setMode(b.dataset.mode)));
  $$('#choice button').forEach(b => b.addEventListener('click', () => setChoice(S.focus, b.dataset.c, { advance: b.dataset.c !== 'edited' })));
  $$('#preview-pick button').forEach(b => b.addEventListener('click', () => { S.previewPick = b.dataset.v; renderPreview(); }));
  $('#edit-text').addEventListener('input', onEdit);
  $('#edit-rewrap').addEventListener('click', async () => {
    const ln = lines()[S.focus];
    const r = await api('/api/rewrap', { ref: ln.ref, text: S.decisions[ln.ref].edited });
    $('#edit-text').value = toEditor(r.text); onEdit();
  });
  $('#edit-from-faithful').addEventListener('click', () => { $('#edit-text').value = toEditor(lines()[S.focus].faithful); onEdit(); });
  $('#edit-from-current').addEventListener('click', () => { $('#edit-text').value = toEditor(lines()[S.focus].current); onEdit(); });
  $('#line-note').addEventListener('input', e => {
    const ln = lines()[S.focus];
    S.decisions[ln.ref] = { ...(S.decisions[ln.ref] || { choice: decisionOf(ln) ? decisionOf(ln).choice : null }), note: e.target.value };
    if (!S.decisions[ln.ref].choice) delete S.decisions[ln.ref].choice;
    saveDraft();
  });
  $('#furigana').addEventListener('change', e => { S.furigana = e.target.checked; $('#insp-jp').classList.toggle('no-ruby', !S.furigana); });
  $('#word-back').addEventListener('click', () => { S.word = null; renderWordPanel(); $$('#insp-jp .w').forEach(el => el.classList.remove('sel')); });
  $('#apply-open').addEventListener('click', openApply);
  $('#apply-confirm').addEventListener('click', confirmApply);
  $('#ask-send').addEventListener('click', sendQuestion);
  $('#help-open').addEventListener('click', () => $('#help').showModal());

  const h = new URLSearchParams(location.hash.slice(1));
  const id = h.get('s') || (S.scenes.find(s => s.status === 'open') || S.scenes[0] || {}).id;
  if (id) await openScene(id, { line: +(h.get('l') || 0), mode: h.get('m') || undefined });
}

window.__review = S; // for testing from the console
main().catch(e => { document.body.insertAdjacentHTML('afterbegin', `<p class="error" style="padding:1rem">The review tool couldn't start: ${esc(e.message)}</p>`); });
