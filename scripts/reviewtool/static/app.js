// Dimguil translation review: a scene as one block per line (the line page mockup in
// rips/review/mockup, approved 2026-10-20). Each block has the speaker, the Japanese as an
// interlinear gloss, what it means, the questions about it, the English in game boxes,
// and the choice.

const $ = (sel, el = document) => el.querySelector(sel);
const $$ = (sel, el = document) => [...el.querySelectorAll(sel)];
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

const S = {
  cast: null, voices: {}, scenes: [], scene: null, focus: 0, decisions: {},
  font: null, fp: null, fits: new Map(), lookups: new Map(), glosses: [],
};
window.__review = S; // for testing from the console

async function api(path, body) {
  const r = await fetch(path, body === undefined ? {} : {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
  });
  const data = await r.json();
  if (!r.ok) throw new Error(data.error || r.statusText);
  return data;
}

// --- people ------------------------------------------------------------------------------

function personForTag(tag) { return S.cast.people.find(p => p.tags.includes(tag)) || null; }
function speakerOf(boxText) { const m = /^([^\n"]*)\n"/.exec(boxText || ''); return m ? m[1] : null; }
const lines = () => S.scene ? S.scene.lines : [];
const reading = () => S.scene && S.scene.kind === 'readthrough';

// --- box text <-> reading and editing ------------------------------------------------------

function splitBox(text) {
  const m = /^([^\n"]*)\n(?=")/.exec(text || '');
  const body = m ? text.slice(m[0].length) : (text || '');
  return { name: m ? m[1] : null, body, pages: body.split('\n\r').map(p => p.split('\n').map(l => l.replace(/^ /, ''))) };
}
function readable(text) {
  return splitBox(text).pages.map(p => p.join(' ')).join(' ').replace(/\{ff12\}/g, '[name]').replace(/\{ff11\}0/g, '[number]').replace(/\{ff30\}\w/g, '');
}
// The editor shows the box as it reads: the name, then one box line per line, a blank
// line between pages. The one-space indent of later lines is added back on the way out.
function toEditor(text) {
  const b = splitBox(text);
  return (b.name !== null ? b.name + '\n' : '') + b.pages.map(p => p.join('\n')).join('\n\n');
}
function fromEditor(ed, like) {
  const orig = splitBox(like);
  let rows = ed.replace(/\r/g, '').split('\n');
  let name = null;
  if (orig.name !== null) { name = rows[0].trim(); rows = rows.slice(1); }
  const pages = rows.join('\n').split(/\n[ \t]*\n/).map(p => p.split('\n').map(l => l.trim()).filter(Boolean)).filter(p => p.length);
  const lead = orig.body.startsWith(' ') ? ' ' : '';
  const body = pages.map((ls, k) => ls.map((l, j) => (k === 0 && j === 0 ? lead : ' ') + l).join('\n')).join('\n\r');
  return (name !== null ? name + '\n' : '') + body;
}

function diffWords(a, b) {
  const x = a.split(/\s+/).filter(Boolean), y = b.split(/\s+/).filter(Boolean);
  const n = x.length, m = y.length, L = Array.from({ length: n + 1 }, () => new Int32Array(m + 1));
  for (let i = n - 1; i >= 0; i--) for (let j = m - 1; j >= 0; j--)
    L[i][j] = x[i] === y[j] ? L[i + 1][j + 1] + 1 : Math.max(L[i + 1][j], L[i][j + 1]);
  const out = [];
  let i = 0, j = 0;
  while (i < n || j < m) {
    if (i < n && j < m && x[i] === y[j]) { out.push(esc(x[i])); i++; j++; }
    else if (i < n && (j >= m || L[i + 1][j] >= L[i][j + 1])) { out.push(`<del>${esc(x[i])}</del>`); i++; }
    else { out.push(`<ins>${esc(y[j])}</ins>`); j++; }
  }
  return out.join(' ').replace(/<\/del> <del>/g, ' ').replace(/<\/ins> <ins>/g, ' ');
}

// The diff of two speeches, with the quotes around them left out of it.
function quotedDiff(a, b) {
  const q = s => /^".*"$/s.test(s);
  return q(a) && q(b) ? `"${diffWords(a.slice(1, -1), b.slice(1, -1))}"` : diffWords(a, b);
}

// Japanese inside English prose, set in mincho.
const JPRUN = /[぀-ヿ一-鿿々〜](?:[぀-ヿ一-鿿々〜,、・]*[぀-ヿ一-鿿々〜])?/g;
const jpx = s => esc(s).replace(JPRUN, m => `<em class="jpx" lang="ja">${m}</em>`);

// --- decisions -----------------------------------------------------------------------------

const draftKey = () => `dimguil-review:${S.scene.id}`;
function needsDecision(ln) { return ln.faithful !== ln.current; }
// A line read in another scene (or a copy of one above) shows as one row, unless opened.
function collapsed(ln) { return !!ln.done_in && !S.opened[ln.ref]; }
function alreadyApplied(ln) {
  const prior = S.scene && S.scene.decision;
  if (!prior) return false;
  return [prior, ...(prior.earlier || [])].some(rec => (rec.lines || []).some(p => p.ref === ln.ref));
}
function decisionOf(ln) {
  if (collapsed(ln)) return { choice: 'current', auto: true };
  const d = S.decisions[ln.ref];
  if (d && d.choice) return d;
  return needsDecision(ln) && !alreadyApplied(ln) ? null : { choice: 'current', auto: true };
}
function textFor(ln, choice) {
  if (choice === 'faithful') return ln.faithful;
  if (choice === 'edited') return (S.decisions[ln.ref] && S.decisions[ln.ref].edited) || ln.faithful;
  return ln.current;
}
function saveDraft() { localStorage.setItem(draftKey(), JSON.stringify(S.decisions)); }

function setChoice(i, choice, { advance = false } = {}) {
  const ln = lines()[i];
  if (collapsed(ln) || (choice === 'faithful' && !needsDecision(ln))) return;
  const prev = S.decisions[ln.ref] || {};
  S.decisions[ln.ref] = { ...prev, choice };
  if (choice === 'edited' && !prev.edited) S.decisions[ln.ref].edited = ln.faithful;
  saveDraft();
  renderChoice(i);
  renderApplyBar();
  if (choice === 'edited') { openEditor(i); return; }
  if (advance) {
    const next = lines().findIndex((l, k) => k > i && !decisionOf(l));
    if (next >= 0) focusLine(next);
  }
}

// --- scene list ----------------------------------------------------------------------------

function renderSceneList() {
  const hide = !!localStorage.getItem('dimguil-review:hide-done');
  $('#hide-done').checked = hide;
  // progress in lines read, not scenes: a scene whose lines moved to a voice scene isn't read
  const pr = S.progress || { read: 0, total: 0 };
  $('#prog-done').textContent = `${pr.read} of ${pr.total} lines read`;
  $('#prog-left').textContent = `${pr.total - pr.read} left`;
  $('#prog-bar').style.width = `${pr.total ? 100 * pr.read / pr.total : 0}%`;
  const byFile = new Map();
  for (const sc of S.scenes) {
    if (hide && sc.status !== 'open' && !(S.scene && S.scene.id === sc.id)) continue;
    if (!byFile.has(sc.file)) byFile.set(sc.file, []);
    byFile.get(sc.file).push(sc);
  }
  const partyOf = f => Object.values(S.cast.parties).find(p => p.file === f);
  const STATUS = { applied: 'Applied, waiting for commit', kept: 'Reviewed, no changes', committed: 'Committed',
    covered: 'Every line was read in other scenes', moved: 'Its lines are in voice scenes, read them there' };
  const count = sc => sc.status !== 'open' ? '' : sc.left < sc.lines ? `, ${sc.left} of ${sc.lines} lines to read` : sc.kind === 'readthrough' ? `, ${sc.lines} lines` : '';
  $('#scene-list').innerHTML = [...byFile.entries()].map(([f, list]) => `
    <p class="party">${esc((partyOf(f) || { name: `NPC_MES${f}` }).name)}</p>
    <ol>${list.map(sc => `<li><button type="button" class="scene-link${sc.status === 'open' ? ' todo' : ''}" data-id="${esc(sc.id)}"
      title="${esc(sc.status === 'open' ? 'To review' : STATUS[sc.status] || sc.status)}${count(sc)}"
      ${S.scene && S.scene.id === sc.id ? 'aria-current="true"' : ''}>${esc(sc.title)}${sc.status === 'applied' ? ' <span class="wait">· applied</span>' : sc.status === 'moved' ? ' <span class="wait">· in voice scenes</span>' : ''}</button></li>`).join('')}</ol>`).join('')
    || `<p class="none">${S.scenes.length ? 'Nothing left to review.' : 'No scenes prepared yet.'}</p>`;
  $$('.scene-link').forEach(b => b.addEventListener('click', () => { setNav(false); openScene(b.dataset.id); }));
}

function setNav(open) {
  document.body.classList.toggle('nav-open', open);
  $('#nav-toggle').setAttribute('aria-expanded', String(open));
  $('#nav-toggle').textContent = open ? 'Close' : 'Scenes';
  localStorage.setItem('dimguil-review:nav', open ? '1' : '');   // a refresh keeps the list open
}

// --- opening a scene -----------------------------------------------------------------------

async function openScene(id, { line = 0, top = null } = {}) {
  S.scene = await api(`/api/scene?id=${encodeURIComponent(id)}`);
  S.decisions = JSON.parse(localStorage.getItem(draftKey()) || '{}');
  S.opened = {};
  S.glosses = [];
  const sc = S.scene;
  $('#empty').hidden = true; $('#scene').hidden = false;
  const party = Object.values(S.cast.parties).find(p => p.file === sc.file);
  $('#scene-file').textContent = [party ? party.name : '', `NPC_MES${sc.file}`, sc.priority ? `${sc.priority} priority` : ''].filter(Boolean).join(', ');
  $('#scene-title').textContent = sc.title;
  $('#mobile-title').textContent = sc.title;
  $('#scene-summary').textContent = sc.summary || '';
  $('#scene-where').textContent = [sc.where, sc.assembled].filter(Boolean).join(' ');
  $('#scene-notes').hidden = !(sc.notes || []).length;
  $('#scene-notes-body').innerHTML = (sc.notes || []).map(n => `<div class="note"><h4>${esc(n.title)}</h4><p>${jpx(n.text)}</p>${sourcesHtml(n.sources)}</div>`).join('');
  renderSceneList();
  $('#lines').innerHTML = sc.lines.map(lineHtml).join('');
  sc.lines.forEach((ln, i) => wireLine(i));
  renderApplyBar();
  S.focus = Math.max(0, Math.min(line, sc.lines.length - 1));
  markFocus();
  window.scrollTo(0, top !== null ? top : 0);
  if (line > 0 && top === null) scrollToLine(S.focus, false);
  // fill in what needs the server; once the lines above the place are drawn (they change
  // height), go back to it, unless you've scrolled since
  const fills = sc.lines.map((_, i) => fillLine(i));
  if (line > 0 && top === null) {
    const y0 = scrollY;
    await Promise.all(fills.slice(0, S.focus + 1));
    if (S.scene === sc && Math.abs(scrollY - y0) < 4) scrollToLine(S.focus, false);
  }
  updatePlace();
}

function sourcesHtml(list) {
  if (!list || !list.length) return '';
  return `<ul class="sources">${list.map(s => `<li>${s.url ? `<a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.label)}</a>` : esc(s.label)}</li>`).join('')}</ul>`;
}

// --- one line ------------------------------------------------------------------------------

function speakerFor(ln) {
  const tag = speakerOf(ln.current) || speakerOf(ln.faithful) || ln.speaker || null;
  return { tag, who: personForTag(tag) };
}

function doneHtml(ln, i) {
  const { tag, who } = speakerFor(ln);
  const d = ln.done_in;
  const link = `<button type="button" class="linkish" data-act="goto">${esc(d.here ? d.as : d.title)}</button>`;
  const why = d.here ? `The same line as ${link} above, so your choice there covers this one.`
    : d.pending ? `You'll read this in ${link}.`
    : `Read in ${link}${d.as !== ln.ref ? `, as ${esc(d.as)}` : ''}.`;
  return `<article class="line done-elsewhere" id="line-${i}" data-i="${i}" style="--c:${lighten(who ? who.color : '#5a6170')}" tabindex="-1" aria-label="${esc(ln.ref)}, ${esc(tag || 'Narration')}, read elsewhere">
    <div class="line-head">
      ${who && who.face ? `<img class="face" src="${esc(who.face)}" alt="">` : '<span class="face none"></span>'}
      <span class="who">${esc(tag || 'Narration')}</span>
      ${ln.context ? `<span class="where">${esc(ln.context)}</span>` : ''}
      <span class="ref">${esc(ln.ref)} · NPC_MES${esc(ln.ref.split(':')[0])}</span>
    </div>
    <p class="done-text">${esc(readable(ln.current))}</p>
    <p class="done-why">${why} <button type="button" class="linkish" data-act="open">Read it here anyway</button></p>
  </article>`;
}

// The rest of the party's answers to the same question, so a voice scene keeps the round.
function othersHtml(ln) {
  const os = ln.others || [];
  if (!os.length) return '';
  return `<details class="others"><summary>Others asked the same (${os.length})</summary><ul>${os.map(o => {
    const who = personForTag(o.speaker);
    return `<li style="--c:${lighten(who ? who.color : '#5a6170')}"><span class="o-who">${esc(o.speaker)}</span> <span class="o-ref">${esc(o.ref)}</span><br>${esc(readable(o.current))}</li>`;
  }).join('')}</ul></details>`;
}

function lineHtml(ln, i) {
  if (collapsed(ln)) return doneHtml(ln, i);
  const { tag, who } = speakerFor(ln);
  const color = who ? who.color : '#5a6170';
  const prop = needsDecision(ln);
  const elsewhere = (ln.elsewhere || []).length;
  return `<article class="line" id="line-${i}" data-i="${i}" style="--c:${lighten(color)}" tabindex="-1" aria-label="${esc(ln.ref)}, ${esc(tag || 'Narration')}">
    <div class="line-head">
      ${who && who.face ? `<img class="face" src="${esc(who.face)}" alt="">` : '<span class="face none"></span>'}
      <span class="who">${esc(tag || 'Narration')}</span>
      ${ln.context ? `<span class="where">${esc(ln.context)}</span>` : ''}
      <span class="status" id="pill-${i}"></span>
      <span class="ref">${esc(ln.ref)} · NPC_MES${esc(ln.ref.split(':')[0])}</span>
    </div>
    ${ln.plays || ln.plays_auto ? `<p class="plays${ln.plays ? '' : ' auto'}"><span>When it plays</span> ${jpx(ln.plays || ln.plays_auto)}</p>` : ''}
    ${othersHtml(ln)}
    <div class="jp" lang="ja" id="jp-${i}"><p class="jp-plain">${esc(jpPlain(ln.jp))}</p></div>
    <dl class="meaning">
      ${ln.literal ? `<dt>Literally</dt><dd class="literal">${jpx(quoteLiteral(ln.literal))}</dd>` : ''}
      ${goingOn(ln, prop)}
      ${elsewhere ? `<dt>Elsewhere</dt><dd class="else" id="else-${i}">${elsewhereHtml(ln)}</dd>` : ''}
    </dl>
    <section class="ask" aria-label="Questions about ${esc(ln.ref)}">
      <h5>Ask Claude</h5>
      <div class="thread"><div class="items" id="thread-${i}">${threadHtml(ln)}</div>
        <form class="asking"><input type="text" placeholder="Ask a question about this line" aria-label="Ask a question about ${esc(ln.ref)}"><button>Ask</button></form></div>
    </section>
    <div class="english">
      <div class="versions">
        <div class="version"><h5 id="cur-h-${i}">In the game now</h5><div class="boxes" id="cur-${i}"></div></div>
        ${prop ? `<div class="version proposed"><h5 id="fai-h-${i}">${proposedHead(ln)}</h5>
          <div class="boxes" id="fai-${i}"></div>
          <p class="diff">${quotedDiff(readable(ln.current), readable(ln.faithful))}</p>
          ${ln.why && !/^No change\.?$/i.test(ln.why.trim()) ? `<p class="why">${jpx(ln.why)}</p>` : ''}</div>` : ''}
      </div>
      <div class="editor" id="editor-${i}" hidden>
        <h5>Your edit <span>a new line starts a new line in the box; a blank line starts a new page</span></h5>
        <textarea class="edit" spellcheck="true" lang="en" aria-label="Edit ${esc(ln.ref)}"></textarea>
        <div class="editor-actions">
          <button type="button" data-act="rewrap">Rewrap to fit</button>
          ${prop ? '<button type="button" data-act="from-faithful" title="Throws away what you have typed and refills the editor">Discard my edit, start from the proposed line</button>' : ''}
          <button type="button" data-act="from-current" title="Throws away what you have typed and refills the editor">Discard my edit, start from the game's line</button>
        </div>
        <div class="boxes live"></div>
        <ul class="fit"></ul>
      </div>
      <div class="choice" role="group" aria-label="Your choice for ${esc(ln.ref)}">
        <h5>Your choice</h5>
        <div class="opts">
          <button type="button" class="opt" data-c="current"><kbd>c</kbd> Keep the game's line</button>
          ${prop ? '<button type="button" class="opt" data-c="faithful"><kbd>f</kbd> Use the proposed line</button>' : ''}
          <button type="button" class="opt" data-c="edited"><kbd>e</kbd> Edit it</button>
        </div>
        <textarea class="note" placeholder="Instructions for this change (optional)" aria-label="Instructions for ${esc(ln.ref)}"></textarea>
        <p class="hint">Goes with your choice when you apply, like "keep it to one page".</p>
      </div>
    </div>
  </article>`;
}

// Speaker colors are set for a light page; lift the dark ones so they read on the night.
function lighten(hex) {
  const n = parseInt(hex.slice(1), 16);
  const ch = [n >> 16, (n >> 8) & 255, n & 255].map(c => Math.round(c + (255 - c) * 0.38));
  return '#' + ch.map(c => c.toString(16).padStart(2, '0')).join('');
}

function jpPlain(src) {
  const m = /^[^\n「]*\n(?=「)/.exec(src);
  return (m ? src.slice(m[0].length) : src).replace(/^「/, '').replace(/\n\r?\s*/g, '');
}
function quoteLiteral(s) { return /^["“]/.test(s) || /^[.\s…]*$/.test(s) ? s : `"${s}"`; }

function goingOn(ln, prop) {
  const parts = (ln.notes || []).map(n => `<p>${n.title ? `<strong>${esc(n.title)}.</strong> ` : ''}${jpx(n.text)}</p>${sourcesHtml(n.sources)}`);
  if (!prop && ln.why && !/^No change\.?$/i.test(ln.why.trim())) parts.push(`<p>${jpx(ln.why)}</p>`);
  return parts.length ? `<dt>What's going on</dt><dd class="notes">${parts.join('')}</dd>` : '';
}

// The other lines an edit can go to: same-Japanese copies (ticked to start with) and the
// lines the scene lists as related (unticked). decisions[ref].copies is the ticked list;
// older drafts have true or false there, meaning all the copies or none.
function tickedOf(ln) {
  const d = S.decisions[ln.ref] || {};
  const all = (ln.elsewhere || []).map(e => e.ref);
  if (Array.isArray(d.copies)) return d.copies.filter(r => all.includes(r));
  return d.copies === false ? [] : ln.copies.slice();
}
function proposedHead(ln) {
  const t = tickedOf(ln);
  return 'Proposed' + (t.length ? `, for ${esc([ln.ref, ...t].join(' and ').replace(/ and (?=.* and )/g, ', '))}` : '');
}
function pendingChoice(ln) { const d = decisionOf(ln); return d ? d.choice : needsDecision(ln) ? 'faithful' : 'current'; }
const CHOICE_WORD = { current: "current", faithful: 'proposed', edited: 'edited' };

function lowerFirst(s) {
  const w = (s || '').split(/[\s']/)[0];
  return S.cast.people.some(p => p.name === w || p.tags.includes(w)) ? s : s.charAt(0).toLowerCase() + s.slice(1);
}
function placeWords(e) {
  return `${esc(e.party)} (NPC_MES${e.file})${e.speaker ? `, ${esc(e.speaker)}` : ''}${e.context ? `, ${esc(lowerFirst(e.context))}` : ''}`;
}

function elsewhereHtml(ln) {
  const t = tickedOf(ln);
  return (ln.elsewhere || []).map((e, k) => `<div class="erow" data-k="${k}" tabindex="0" role="button" aria-expanded="false" aria-label="${esc(e.ref)}: show its Japanese and box">
      <div class="ehead"><span class="ewhere">${placeWords(e)}</span> <span class="eref">${esc(e.ref)}</span>
        <span class="${e.kind === 'copy' ? 'copy' : 'rel'}" title="${e.kind === 'copy' ? 'The Japanese here is word for word the same, so it normally gets the same English' : 'Different Japanese, but close enough that an edit here may want one there'}">${e.kind === 'copy' ? 'Same line in Japanese' : 'Similar line, not the same'}</span></div>
      <div class="ecur">${esc(readable(e.current))}${e.same_now ? '' : ' <span class="differs">differs from this line now</span>'}</div>
      ${e.note ? `<div class="enote">${jpx(e.note)}</div>` : ''}
      <label class="tick"><input type="checkbox" ${t.includes(e.ref) ? 'checked' : ''}> Apply my change here too</label>
      <div class="edetail" hidden></div>
    </div>`).join('');
}

// The other line's Japanese and its box with this line's pending text, as it would show
// there (with its own speaker's name, the server's as_copy).
async function elsewhereDetail(ln, e) {
  const choice = pendingChoice(ln);
  const f = await fitFor(e.ref, textFor(ln, choice), true);
  const div = document.createElement('div');
  div.innerHTML = `<p class="ejp" lang="ja">${esc(jpPlain(e.jp))}</p><p class="ecap">With this line's ${CHOICE_WORD[choice]} text:</p><div class="boxes"></div>`;
  drawBoxes($('.boxes', div), f);
  return div;
}
async function openDetail(i, row) {
  const ln = lines()[i], e = ln.elsewhere[+row.dataset.k], box = $('.edetail', row);
  const div = await elsewhereDetail(ln, e);
  if (e.scene) div.insertAdjacentHTML('beforeend', `<button type="button" class="use go">Open in its scene${e.scene === S.scene.id ? '' : `: ${esc(e.scene_title)}`}</button>`);
  box.innerHTML = ''; box.append(div);
  const go = $('.go', box);
  if (go) go.addEventListener('click', ev => {
    ev.stopPropagation();
    if (e.scene === S.scene.id) focusLine(e.index); else openScene(e.scene, { line: e.index });
  });
}
function refreshDetails(i) {
  $$(`#else-${i} .erow[aria-expanded="true"]`).forEach(row => openDetail(i, row));
}

function wireElsewhere(i) {
  const ln = lines()[i];
  $$(`#else-${i} .erow`).forEach(row => {
    const e = ln.elsewhere[+row.dataset.k];
    const toggle = () => {
      const open = row.getAttribute('aria-expanded') !== 'true';
      row.setAttribute('aria-expanded', String(open));
      $('.edetail', row).hidden = !open;
      if (open) openDetail(i, row);
    };
    row.addEventListener('click', ev => { if (!ev.target.closest('label, input, button')) toggle(); });
    row.addEventListener('keydown', ev => { if ((ev.key === 'Enter' || ev.key === ' ') && ev.target === row) { ev.preventDefault(); toggle(); } });
    $('input', row).addEventListener('change', ev => {
      const t = tickedOf(ln).filter(r => r !== e.ref);
      if (ev.target.checked) t.push(e.ref);
      S.decisions[ln.ref] = { ...(S.decisions[ln.ref] || {}), copies: ln.elsewhere.map(x => x.ref).filter(r => t.includes(r)) };
      saveDraft();
      const h = $(`#fai-h-${i}`); if (h) h.innerHTML = proposedHead(ln);
      renderApplyBar();
    });
    const ref = $('.eref', row);
    ref.addEventListener('mouseenter', async () => {
      if (matchMedia('(hover: none)').matches || row.getAttribute('aria-expanded') === 'true') return;
      const div = await elsewhereDetail(ln, e);
      if (!ref.matches(':hover')) return;
      const p = peek(); p.innerHTML = ''; p.append(div); p.classList.add('wide'); p.hidden = false;
      const r = ref.getBoundingClientRect();
      p.style.left = Math.max(scrollX + 8, Math.min(r.left + scrollX, scrollX + innerWidth - p.offsetWidth - 16)) + 'px';
      p.style.top = (r.bottom + scrollY + 6) + 'px';
    });
    ref.addEventListener('mouseleave', () => { hidePeek(); peek().classList.remove('wide'); });
  });
}

function wireLine(i) {
  const ln = lines()[i], el = $(`#line-${i}`);
  el.addEventListener('pointerdown', () => { if (S.focus !== i) { S.focus = i; markFocus(); updatePlace(); } });
  if (collapsed(ln)) {
    $('[data-act="goto"]', el).addEventListener('click', () => ln.done_in.here ? focusLine(ln.done_in.index)
      : openScene(ln.done_in.scene, { line: ln.done_in.index }));
    $('[data-act="open"]', el).addEventListener('click', () => {
      S.opened[ln.ref] = true;
      el.outerHTML = lineHtml(ln, i);
      wireLine(i); fillLine(i); markFocus(); renderApplyBar();
    });
    return;
  }
  $$('.opt', el).forEach(b => b.addEventListener('click', () => setChoice(i, b.dataset.c)));
  $('.note', el).value = (S.decisions[ln.ref] && S.decisions[ln.ref].note) || '';
  $('.note', el).addEventListener('input', e => {
    const d = decisionOf(ln);
    S.decisions[ln.ref] = { ...(S.decisions[ln.ref] || { choice: d && !d.auto ? d.choice : null }), note: e.target.value };
    if (!S.decisions[ln.ref].choice) delete S.decisions[ln.ref].choice;
    saveDraft();
  });
  const ta = $('.edit', el);
  ta.addEventListener('input', () => onEdit(i));
  $$('.editor-actions button', el).forEach(b => b.addEventListener('click', async () => {
    if (b.dataset.act === 'rewrap') {
      const r = await api('/api/rewrap', { ref: ln.ref, text: textFor(ln, 'edited') });
      ta.value = toEditor(r.text);
    } else ta.value = toEditor(b.dataset.act === 'from-faithful' ? ln.faithful : ln.current);
    onEdit(i);
  }));
  wireElsewhere(i);
  $('.asking', el).addEventListener('submit', e => { e.preventDefault(); sendQuestion(i); });
  wireThread(i);
  renderChoice(i);
}
wireLine.copy = i => {   // the copy toggle, after a redraw of Elsewhere
  const ln = lines()[i], b = $(`#else-${i} .copy`);
  if (b) b.addEventListener('click', () => {
    const d = S.decisions[ln.ref] || {};
    S.decisions[ln.ref] = { ...d, copies: d.copies === false };
    saveDraft();
    $(`#else-${i}`).innerHTML = elsewhereHtml(ln);
    wireLine.copy(i);
  });
};

async function fillLine(i) {
  const ln = lines()[i], sc = S.scene;
  if (collapsed(ln)) return;
  const versions = [['cur', ln.current]];
  if (needsDecision(ln)) versions.push(['fai', ln.faithful]);
  for (const [k, text] of versions) {
    fitFor(ln.ref, text).catch(() => null).then(f => {
      if (!f) return;
      if (S.scene !== sc) return;
      drawBoxes($(`#${k}-${i}`), f);
      const h = $(`#${k}-h-${i}`);
      if (k === 'cur' && f.pages.length > 1) h.textContent = `In the game now, ${f.pages.length} pages`;
      const bad = fitMessages(f).filter(m => !m.includes('class="ok"'));
      if (bad.length) $(`#${k}-${i}`).insertAdjacentHTML('afterend', `<ul class="fit bad-fit">${bad.join('')}</ul>`);
    });
  }
  const g = await api(`/api/gloss?scene=${encodeURIComponent(sc.id)}&ref=${encodeURIComponent(ln.ref)}`).catch(e => ({ error: e.message, pages: null }));
  if (S.scene !== sc) return;
  S.glosses[i] = g;
  renderGloss(i);
}

function renderChoice(i) {
  const ln = lines()[i], el = $(`#line-${i}`);
  if (!el) return;
  const d = decisionOf(ln);
  $$('.opt', el).forEach(b => b.setAttribute('aria-pressed', String(!!d && d.choice === b.dataset.c)));
  const pill = $(`#pill-${i}`);
  const prop = needsDecision(ln);
  const label = { current: "Keeping the game's line", faithful: 'Using the proposed line', edited: 'Using your edit' };
  if (d && d.choice === 'edited') { pill.className = 'status prop'; pill.textContent = label.edited; }
  else if (!prop) { pill.className = 'status keep'; pill.textContent = 'No change proposed'; }
  else if (!d || d.auto) { pill.className = 'status prop'; pill.textContent = 'Change proposed'; }
  else { pill.className = `status ${d.choice === 'current' ? 'keep' : 'prop'}`; pill.textContent = label[d.choice]; }
  const ed = $(`#editor-${i}`);
  const editing = !!d && d.choice === 'edited';
  ed.hidden = !editing;
  if (editing && document.activeElement !== $('.edit', ed)) {
    $('.edit', ed).value = toEditor(S.decisions[ln.ref].edited);
    renderLive(i);
  }
}

function openEditor(i) {
  const ta = $(`#editor-${i} .edit`);
  ta.focus({ preventScroll: true });
  ta.setSelectionRange(ta.value.length, ta.value.length);
  ta.scrollIntoView({ block: 'nearest' });
}

const editTimers = {};
function onEdit(i) {
  const ln = lines()[i];
  S.decisions[ln.ref] = { ...(S.decisions[ln.ref] || {}), choice: 'edited', edited: fromEditor($(`#editor-${i} .edit`).value, ln.current) };
  saveDraft();
  renderLive(i, { quick: true });
  clearTimeout(editTimers[i]);
  editTimers[i] = setTimeout(() => { renderLive(i); renderApplyBar(); renderChoice(i); }, 220);
}

// The live box: drawn here at once from the font tables, then from the server's /api/fit
// (the same check apply runs), which also gives the warnings.
async function renderLive(i, { quick = false } = {}) {
  const ln = lines()[i], ed = $(`#editor-${i}`);
  const text = textFor(ln, 'edited');
  if (quick) {
    const pages = layoutHere(text);
    drawBoxes($('.live', ed), { pages, width: S.fp.width, lines: S.fp.lines, source_lines: sourceLines(ln.jp) });
    return;
  }
  const f = await fitFor(ln.ref, text).catch(() => null);
  if (!f || textFor(ln, 'edited') !== text) return;  // typed on meanwhile, or the server is away
  drawBoxes($('.live', ed), f);
  $('.fit', ed).innerHTML = fitMessages(f).join('');
  refreshDetails(i);
}

// --- the interlinear gloss -----------------------------------------------------------------

function renderGloss(i) {
  const g = S.glosses[i], box = $(`#jp-${i}`);
  if (!g || !g.pages) { box.insertAdjacentHTML('beforeend', `<p class="gloss-error">${esc(g && g.error || 'No gloss.')}</p>`); return; }
  let k = 0;
  box.innerHTML = g.pages.map((pg, p) => `<div class="jp-page" data-p="${p}">${pg.map((w, j) => {
    if (w.code) return '';
    if (w.punct) return `<span class="w punct"><span class="rd"></span><span class="sf">${esc(w.jp)}</span><span class="gl"></span></span>`;
    k++;
    const cls = ['w', w.tone ? 'tone' : '', w.trap ? 'trap' : '', w.name ? 'name' : '', w.fixed ? 'fixed' : ''].filter(Boolean).join(' ');
    return `<button type="button" class="${cls}" data-p="${p}" data-j="${j}" data-k="${k}" aria-expanded="false"><span class="rd">${esc(w.rd || '')}</span><span class="sf">${esc(w.show || w.jp)}</span><span class="gl">${esc(w.en || '')}</span></button>`;
  }).join('')}</div>`).join('')
    + (g.error ? `<p class="gloss-error">${esc(g.error)}</p>` : '')
    + (g.source === 'auto' ? `<p class="auto-note">Words grouped and glossed automatically, from the word splitter and JMdict.${
      g.pages.some(pg => pg.some(w => w.fixed)) ? ' A dotted underline marks a gloss corrected by hand; hover or click it for the dictionary\'s own.' : ''}</p>` : '');
  // punctuation stays with the word before it, so a line never starts with 。 or ,
  $$('.w.punct', box).forEach(pu => {
    const prev = pu.previousElementSibling;
    if (!prev) return;
    const grp = prev.classList.contains('grp') ? prev : prev.closest('.grp') || (() => { const s = document.createElement('span'); s.className = 'grp'; prev.before(s); s.append(prev); return s; })();
    grp.append(pu);
  });
  $$('button.w', box).forEach(b => {
    const w = g.pages[+b.dataset.p][+b.dataset.j];
    b.addEventListener('click', () => toggleEntry(i, b, w));
    b.addEventListener('mouseenter', () => showPeek(i, b, w));
    b.addEventListener('mouseleave', hidePeek);
  });
}

async function lookupWord(q, lemma) {
  const key = `${q}|${lemma || ''}`;
  if (!S.lookups.has(key)) S.lookups.set(key, api(`/api/lookup?q=${encodeURIComponent(q)}&lemma=${encodeURIComponent(lemma || '')}`));
  return S.lookups.get(key);
}

// The entry for a word: the scene's hand-written one, or one made from JMdict.
// A corrected gloss (glossfix.json) says so in its entry, with the dictionary's own first sense.
const fixedNote = w => w.fixed ? `<span class="fixed-note">Gloss corrected by hand: "${esc(w.en)}". The dictionary's first sense is "${esc(w.dict_en || 'none')}".</span>` : '';
async function entryFor(w) {
  const e = await entryFor.raw(w);
  return w.fixed ? { ...e, noteHtml: [fixedNote(w), e.noteHtml].filter(Boolean).join('<br>') } : e;
}
entryFor.raw = async function (w) {
  if (w.entry) return { ...w.entry, hand: true };
  if (w.name) return { head: w.show, label: 'name', senses: [], note: w.en };
  const r = await lookupWord(w.q || w.jp, w.lemma);
  const e = r.jmdict[0];
  const notes = (w.notes || []).map(n => (n.register ? `<span class="reg">${esc(n.register)}</span>` : '') + jpx(n.sense || '')).join('<br>');
  const role = r.role ? `<strong>${esc(r.role.type)}.</strong> ${jpx(r.role.note)}` : '';
  if (!e) {
    const wk = r.wiktionary[0];
    return { head: w.lemma || w.jp, label: wk ? wk.pos : '', senses: wk ? wk.senses.slice(0, 3).map(s => s.glosses.join('; ')) : [], noteHtml: [notes, role].filter(Boolean).join('<br>') };
  }
  const head = (e.kanji[0] && e.kanji[0].k) || (e.kana[0] && e.kana[0].r) || w.jp;
  const kana = e.kanji.length && e.kana[0] ? e.kana[0].r : '';
  const pos = (e.senses[0].tags || []).filter(t => e.senses[0].pos.includes(t.tag)).map(t => t.text)[0] || '';
  return { head, label: [kana, pos].filter(Boolean).join(', '), senses: e.senses.slice(0, 5).map(s => s.gloss.slice(0, 3).join('; ')), noteHtml: [notes, role].filter(Boolean).join('<br>') };
};

function entryHtml(e) {
  const senses = e.senses || [];
  const lis = senses.map((s, k) => `<li${k === e.here && senses.length > 1 ? ' class="here"' : ''}>${esc(s)}</li>`).join('');
  return `<div class="entry"><h4 lang="ja">${esc(e.head)} ${e.label ? `<span>${esc(e.label)}</span>` : ''}</h4>
    ${lis ? `<ol>${lis}</ol>` : ''}${e.note ? `<p>${jpx(e.note)}</p>` : ''}${e.noteHtml ? `<p>${e.noteHtml}</p>` : ''}`;
}

const peek = () => $('#peek');
let peekTimer = null;
function showPeek(i, b, w) {
  if (matchMedia('(hover: none)').matches || b.getAttribute('aria-expanded') === 'true') return;
  clearTimeout(peekTimer);
  peekTimer = setTimeout(async () => {
    const e = await entryFor(w);
    if (!b.matches(':hover')) return;
    const p = peek();
    p.innerHTML = entryHtml({ ...e, senses: (e.senses || []).slice(0, 3) }) + '</div><span class="more">Click for the full entry</span>';
    p.hidden = false;
    const r = b.getBoundingClientRect();
    p.style.left = Math.max(scrollX + 8, Math.min(r.left + scrollX, scrollX + innerWidth - p.offsetWidth - 16)) + 'px';
    p.style.top = (r.bottom + scrollY + 6) + 'px';
  }, 120);
}
function hidePeek() { clearTimeout(peekTimer); peek().hidden = true; }

async function toggleEntry(i, b, w) {
  hidePeek();
  const box = $(`#jp-${i}`);
  const open = b.getAttribute('aria-expanded') === 'true';
  $$('.w[aria-expanded="true"]', box).forEach(x => x.setAttribute('aria-expanded', 'false'));
  $$('.entry', box).forEach(x => x.remove());
  if (open) return;
  b.setAttribute('aria-expanded', 'true');
  const e = await entryFor(w);
  if (b.getAttribute('aria-expanded') !== 'true') return;
  const page = b.closest('.jp-page');
  page.insertAdjacentHTML('afterend', entryHtml(e) + `<details><summary>${e.hand ? 'More from the dictionaries' : 'Everything the dictionaries have'}</summary><div class="dict">Looking up…</div></details></div>`);
  const det = page.nextElementSibling.querySelector('details');
  det.addEventListener('toggle', () => { if (det.open) fillDict(det.querySelector('.dict'), w, lines()[i].ref); }, { once: true });
}

async function fillDict(el, w, ref) {
  const q = (w.entry && w.entry.lookup) || w.q || w.jp;
  const [r, conc] = await Promise.all([lookupWord(q, w.lemma), api(`/api/concordance?q=${encodeURIComponent(q.length > 1 ? q : w.lemma || q)}&ref=${encodeURIComponent(ref)}`)]);
  const parts = [];
  if (r.role) parts.push(`<p class="src">Role language</p><p><strong>${esc(r.role.type)}.</strong> ${jpx(r.role.note)}</p>`);
  if (r.jmdict.length) parts.push(`<p class="src">JMdict</p>${r.jmdict.slice(0, 4).map(e => `<div><span class="forms" lang="ja">${esc([...e.kanji.map(k => k.k), ...e.kana.map(k => k.r)].slice(0, 4).join(', '))}</span>
    <ol>${e.senses.map(s => `<li>${s.tags.filter(x => /arch|hon|hum|fem|male|dated|col|sl|obs|poet|vulg|derog|uk/.test(x.tag)).map(x => `<span class="tag${/arch|hon|hum|fem|male|dated|col|sl|obs|poet|vulg|derog/.test(x.tag) ? ' key' : ''}" title="${esc(x.text)}">${esc(x.text)}</span>`).join('')}${esc(s.gloss.join('; '))}${s.info.length ? ` (${esc(s.info.join('; '))})` : ''}</li>`).join('')}</ol></div>`).join('')}`);
  if (r.wiktionary.length) parts.push(`<p class="src">English Wiktionary</p>${r.wiktionary.slice(0, 3).map(x => `<div><span class="forms" lang="ja">${esc(x.word)}</span> <span class="tag">${esc(x.pos)}</span><ol>${x.senses.map(s => `<li>${s.tags.map(t => `<span class="tag">${esc(t)}</span>`).join('')}${esc(s.glosses.join('; '))}</li>`).join('')}</ol></div>`).join('')}`);
  if (r.kanji.length) parts.push(`<p class="src">Kanji</p>${r.kanji.map(k => `<div class="kanji"><span class="lit" lang="ja">${esc(k.lit)}</span><div>${esc(k.meanings.slice(0, 5).join(', '))}<div lang="ja">${esc([...k.on, ...k.kun].slice(0, 6).join('、'))}</div></div></div>`).join('')}`);
  if (conc.hits.length) parts.push(`<p class="src">Elsewhere in the game (${conc.total})</p>${conc.hits.map(h => `<div class="ex">${esc(h.ref)} <span class="ja" lang="ja">${esc(h.jp.replace(/\n\r?/g, ' '))}</span>${esc(h.en.replace(/\n\r?/g, ' '))}</div>`).join('')}`);
  if (r.examples.length) parts.push(`<p class="src">In everyday Japanese (Tatoeba)</p>${r.examples.map(x => `<div class="ex"><span class="ja" lang="ja">${esc(x.jp)}</span>${esc(x.en)}</div>`).join('')}`);
  if (!parts.length) parts.push('<p>Nothing found. Ask Claude below.</p>');
  parts.push('<p class="credit">Dictionaries: JMdict and KANJIDIC2 (EDRDG, CC BY-SA 4.0); English Wiktionary via kaikki.org (CC BY-SA 4.0); Tatoeba (CC BY 2.0 FR). Role-language notes after Kinsui Satoshi.</p>');
  el.innerHTML = parts.join('');
}

// --- the game box --------------------------------------------------------------------------

async function fitFor(ref, text, asCopy = false) {
  const key = `${ref}\u0000${text}\u0000${asCopy}`;
  if (!S.fits.has(key)) S.fits.set(key, api('/api/fit', { ref, text, as_copy: asCopy }).catch(e => { S.fits.delete(key); throw e; }));
  return S.fits.get(key);
}

// descfit.encode and server.layout, here, so the box can be redrawn on every key.
function encodeHere(text) {
  const codes = [];
  for (const word of text.match(/[^ ]* ?|[^ ]+/g) || []) {
    let i = 0;
    while (i < word.length) {
      const pair = word.slice(i, i + 2);
      if (pair.length === 2 && pair in S.fp.digraphs) { codes.push(S.fp.digraphs[pair]); i += 2; continue; }
      const c = S.fp.chars[word[i]];
      if (c === undefined) throw new Error(word[i]);
      codes.push(c); i += 1;
    }
  }
  return codes;
}
function layoutHere(text) {
  return text.split(/\n\r|\{ff40\}\r/).map(pg => pg.split('\n').map(line => {
    const shown = line.replace(/\{ff12\}/g, 'Mmmmmmmm').replace(/\{ff11\}0/g, '99999').replace(/\{ff30\}\w/g, '').replace(/\{ff[0-9a-f]{2}\}/g, '').replace(/\r/g, '');
    let codes = [];
    try { codes = encodeHere(shown).filter(c => c >= 0); } catch (e) { codes = []; }
    const width = codes.reduce((s, c) => s + (c < S.fp.lut.length ? S.fp.lut[c] + 1 : 12), 0);
    return { codes, width, placeholder: line.includes('{ff12}') };
  }));
}
function sourceLines(jp) {
  return jp.split(/\n\r|\{ff40\}\r/).map(p => p.split('\n').length);
}

function drawBoxes(el, f) {
  if (!el) return;
  el.innerHTML = '';
  f.pages.forEach((page, k) => el.append(drawPage(page, f.width, Math.max(f.lines, f.source_lines[k] || 0))));
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
      g.fillStyle = 'rgba(220, 60, 50, 0.85)'; g.fillRect(meta.origin_x + width, y, 1, meta.pitch);
      g.fillStyle = 'rgba(220, 60, 50, 0.25)'; g.fillRect(meta.origin_x + width + 1, y, line.width - width, meta.pitch);
    }
    if (j >= limit) { g.fillStyle = 'rgba(220, 60, 50, 0.3)'; g.fillRect(meta.origin_x - 2, y, width + 4, meta.pitch); }
  });
  c.setAttribute('role', 'img');
  c.setAttribute('aria-label', `${page.length} lines in the game text box`);
  return c;
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
  for (const p of f.problems || []) {
    if (/^\d+px: |^page \d+ has \d+ lines/.test(p)) continue;
    const intended = p.includes('fine if intended');
    out.push(`<li class="${intended ? 'warn' : 'bad'}">${esc(intended ? p.replace(/ \(fine if intended\)/, ". That's fine if intended.").replace(/^(\d+) pages, source has (\d+)/, 'This has $1 pages; the Japanese has $2') : p)}</li>`);
  }
  if (!out.length) out.push(`<li class="ok">Fits. The widest line is ${Math.max(...f.pages.flat().map(l => l.width))} of ${f.width} px.</li>`);
  return out;
}

// --- questions -----------------------------------------------------------------------------

const fmtTime = t => {
  const d = new Date(t.replace(/([+-]\d\d)(\d\d)$/, '$1:$2'));
  if (isNaN(d)) return t;
  return `${d.getDate()} ${d.toLocaleString('en-US', { month: 'short' })}, ${d.toLocaleString('en-US', { hour: 'numeric', minute: '2-digit' }).toLowerCase()}`;
};

function threadHtml(ln) {
  return (ln.questions || []).map(q => {
    const about = [q.ref !== ln.ref ? `about ${q.ref}` : '', q.about ? `on ${q.about}` : ''].filter(Boolean).join(', ');
    const qh = `<p class="q">${about ? `<span class="about">(${esc(about)})</span> ` : ''}${esc(q.question)}</p>`;
    if (!q.answer) return qh + `<div class="a pending"><span class="when">Waiting for Claude. Asked ${esc(fmtTime(q.asked_at))}.</span></div>`;
    const paras = q.answer.split(/\n\s*\n/).map(p => {
      if (isBoxText(p)) return `<p class="try">${esc(p)}</p><button type="button" class="use" data-text="${esc(p)}">Put this in the editor</button>`;
      return `<p>${jpx(p).replace(/\n/g, '<br>')}</p>`;
    });
    for (const s of [].concat(q.suggest || [])) paras.push(`<p class="try">${esc(s)}</p><button type="button" class="use" data-text="${esc(s)}">Put this in the editor</button>`);
    return qh + `<div class="a">${paras.join('')}<span class="when">${q.answered_at ? `Answered ${esc(fmtTime(q.answered_at))}` : 'Answered'}</span></div>`;
  }).join('');
}
// A paragraph that is a whole box: a speaker's name, then the speech in quotes.
function isBoxText(p) {
  const m = /^([^\n"]{1,40})\n"[^]*"$/.exec(p.trim());
  return !!m && !!personForTag(m[1]);
}

function wireThread(i) {
  const box = $(`#thread-${i}`);
  if (box) {   // a long thread scrolls inside its own box; show the newest exchange
    box.scrollTop = box.scrollHeight;
    box.classList.toggle('long', box.scrollHeight > box.clientHeight + 2);
  }
  $$(`#thread-${i} .use`).forEach(b => b.addEventListener('click', () => {
    const ln = lines()[i];
    const prev = S.decisions[ln.ref] || {};
    S.decisions[ln.ref] = { ...prev, choice: 'edited', edited: b.dataset.text.trim() };
    saveDraft();
    renderChoice(i); renderApplyBar(); openEditor(i);
  }));
}

async function sendQuestion(i) {
  const form = $(`#line-${i} .asking`), input = $('input', form);
  const text = input.value.trim();
  if (!text) return;
  const ln = lines()[i];
  const open = $(`#jp-${i} .w[aria-expanded="true"] .sf`);
  const q = await api('/api/ask', { scene: S.scene.id, ref: ln.ref, about: open ? open.textContent : '', question: text });
  ln.questions = [...(ln.questions || []), q];
  input.value = '';
  $(`#thread-${i}`).innerHTML = threadHtml(ln);
  wireThread(i);
  pollSoon();
}

// Answers are written into questions.json by Claude in the terminal; look for them every
// few seconds while one is waiting, and now and then otherwise.
let pollTimer = null;
function pollSoon() { clearTimeout(pollTimer); pollTimer = setTimeout(poll, 4000); }
async function poll() {
  clearTimeout(pollTimer);
  const waiting = lines().some(l => (l.questions || []).some(q => !q.answer));
  pollTimer = setTimeout(poll, waiting ? 5000 : 20000);
  if (!S.scene || document.hidden) return;
  const all = await api('/api/questions').catch(() => null);
  if (!all) return;
  lines().forEach((ln, i) => {
    const refs = [ln.ref, ...ln.copies];
    const mine = all.filter(q => refs.includes(q.ref));
    if (JSON.stringify(mine) !== JSON.stringify(ln.questions || []) && $(`#thread-${i}`)) {
      ln.questions = mine;
      $(`#thread-${i}`).innerHTML = threadHtml(ln);
      wireThread(i);
    }
  });
}
document.addEventListener('visibilitychange', () => { if (!document.hidden) poll(); });

// --- focus and place -----------------------------------------------------------------------

function markFocus() { $$('#lines .line').forEach(el => el.classList.toggle('focused', +el.dataset.i === S.focus)); }
function scrollToLine(i, smooth = true) {
  const el = $(`#line-${i}`);
  if (!el) return;
  const bar = matchMedia('(max-width: 900px)').matches ? $('.mobilebar').offsetHeight : 0;
  const y = el.getBoundingClientRect().top + scrollY - bar - 8;
  window.scrollTo({ top: y, behavior: smooth && !matchMedia('(prefers-reduced-motion: reduce)').matches ? 'smooth' : 'auto' });
}
function focusLine(i) {
  if (!S.scene) return;
  S.focus = Math.max(0, Math.min(i, lines().length - 1));
  markFocus();
  scrollToLine(S.focus);
  updatePlace();
}
function updatePlace() {
  if (!S.scene) return;
  const h = `s=${encodeURIComponent(S.scene.id)}&l=${S.focus}`;
  history.replaceState(null, '', '#' + h);
  localStorage.setItem('dimguil-review:place', h);   // some phone browsers reload an older address
}
// Scrolling moves the focus to the line in view, so j/k and a refresh carry on from there.
let scrollTimer = null;
window.addEventListener('scroll', () => {
  clearTimeout(scrollTimer);
  scrollTimer = setTimeout(() => {
    if (!S.scene) return;
    const cur = $(`#line-${S.focus}`);
    const r = cur && cur.getBoundingClientRect();
    if (!r || r.bottom < innerHeight * 0.25 || r.top > innerHeight * 0.75) {
      const els = $$('#lines .line');
      const vis = els.find(el => el.getBoundingClientRect().bottom > innerHeight * 0.3);
      if (vis) { S.focus = +vis.dataset.i; markFocus(); }
    }
    updatePlace();
  }, 250);
}, { passive: true });

// --- apply ---------------------------------------------------------------------------------

function renderApplyBar() {
  const ls = lines();
  const open = ls.filter(l => !decisionOf(l)).length;
  const changes = ls.filter(l => { const d = decisionOf(l); return d && textFor(l, d.choice) !== l.current; }).length;
  const prior = S.scene.decision;
  const nothingNew = !open && !changes && prior;
  let msg = open ? `${open} proposed ${open === 1 ? 'change needs' : 'changes need'} your decision.`
    : changes ? `Ready: ${changes} ${changes === 1 ? 'line changes' : 'lines change'}.`
    : nothingNew ? 'Nothing new to apply.' : 'Ready: no lines change.';
  if (prior) msg += prior.status === 'committed' ? ` Committed as ${prior.commit || 'a commit'}.` : ` Applied ${prior.applied_at.slice(0, 16).replace('T', ' ')}; Claude commits next.`;
  $('#apply-status').textContent = msg;
  $('#apply-open').disabled = open > 0 || !!nothingNew;
  $('#apply-open').textContent = !open && !changes && !prior ? 'Mark as reviewed' : 'Review and apply';
}

function openApply() {
  const changed = lines().filter(l => { const d = decisionOf(l); return d && textFor(l, d.choice) !== l.current; });
  $('#apply-summary').textContent = changed.length
    ? `${changed.length} ${changed.length === 1 ? 'line changes' : 'lines change'}. Everything else stays as it is.`
    : 'No lines change. Applying records that the scene was reviewed.';
  $('#apply-list').innerHTML = changed.map(l => {
    const d = decisionOf(l);
    return `<li><span class="cref">${esc(l.ref)}, ${d.choice === 'edited' ? 'your edit' : 'the proposed line'}${tickedOf(l).length ? `, also ${tickedOf(l).map(esc).join(', ')}` : ''}</span><br>
      <span class="before">${esc(readable(l.current))}</span><br>${esc(readable(textFor(l, d.choice)))}</li>`;
  }).join('');
  $('#apply-error').hidden = true;
  $('#apply-dialog').showModal();
}

// The body is the same as before the redesign, so decisions/<scene>.json is unchanged.
function applyBody() {
  return {
    scene: S.scene.id, note: $('#scene-note').value,
    lines: lines().filter(l => !collapsed(l)).map(l => {
      const d = decisionOf(l);
      const own = S.decisions[l.ref] || {};
      return { ref: l.ref, choice: d.choice, text: textFor(l, d.choice), note: own.note || '', copies: tickedOf(l) };
    }),
  };
}

async function confirmApply() {
  const btn = $('#apply-confirm');
  btn.disabled = true;
  try {
    await api('/api/apply', applyBody());
    localStorage.removeItem(draftKey());
    $('#apply-dialog').close();
    ({ scenes: S.scenes, progress: S.progress } = await api('/api/state'));
    await openScene(S.scene.id, { line: S.focus, top: scrollY });
  } catch (e) {
    $('#apply-error').textContent = e.message;
    $('#apply-error').hidden = false;
  } finally {
    btn.disabled = false;
  }
}

// --- keyboard ------------------------------------------------------------------------------

document.addEventListener('keydown', e => {
  const typing = e.target.closest('textarea, input');
  const help = $('#help');
  if (e.key === 'Escape') {
    help.hidden = true;
    if (typing) { e.target.blur(); return; }
    if (document.body.classList.contains('nav-open')) { setNav(false); return; }
    const open = $(`#jp-${S.focus} .w[aria-expanded="true"]`);
    if (open) open.click();
    return;
  }
  if (typing || e.ctrlKey || e.metaKey || e.altKey || $('dialog[open]')) return;
  if (e.key === '?') { help.hidden = !help.hidden; return; }
  if (!S.scene) return;
  const i = S.focus, line = $(`#line-${i}`);
  if (e.key === 'j') focusLine(i + 1);
  else if (e.key === 'k') focusLine(i - 1);
  else if (e.key === 'c') setChoice(i, 'current', { advance: true });
  else if (e.key === 'f') setChoice(i, 'faithful', { advance: true });
  else if (e.key === 'e') { e.preventDefault(); setChoice(i, 'edited'); }
  else if (e.key === 'a') { e.preventDefault(); const inp = $('.asking input', line); inp.focus({ preventScroll: true }); inp.scrollIntoView({ block: 'center' }); }
  else if (/^[1-9]$/.test(e.key)) { const b = $(`#jp-${i} button.w[data-k="${e.key}"]`); if (b) b.click(); }
  else if (e.key === 'r') { document.body.classList.toggle('no-rd'); localStorage.setItem('dimguil-review:no-rd', document.body.classList.contains('no-rd') ? '1' : ''); }
  else if (e.key === '[' || e.key === ']') {
    const k = S.scenes.findIndex(s => s.id === S.scene.id) + (e.key === ']' ? 1 : -1);
    if (S.scenes[k]) openScene(S.scenes[k].id);
  } else return;
  e.preventDefault();
});

// --- start ---------------------------------------------------------------------------------

function loadImage(src) {
  return new Promise((res, rej) => { const i = new Image(); i.onload = () => res(i); i.onerror = rej; i.src = src; });
}

async function main() {
  const [st, meta, atlas, box, fp] = await Promise.all([
    api('/api/state'), api('/font/font.json'), loadImage('/font/atlas.png'), loadImage('/font/box.png'), api('/api/fontpack'),
  ]);
  S.cast = st.cast; S.voices = st.voices; S.scenes = st.scenes; S.progress = st.progress;
  S.font = { meta, atlas, box }; S.fp = fp;
  if (localStorage.getItem('dimguil-review:no-rd')) document.body.classList.add('no-rd');
  renderSceneList();
  $('#hide-done').addEventListener('change', e => { localStorage.setItem('dimguil-review:hide-done', e.target.checked ? '1' : ''); renderSceneList(); });
  $('#apply-open').addEventListener('click', openApply);
  $('#apply-confirm').addEventListener('click', confirmApply);
  $('#nav-toggle').addEventListener('click', () => setNav(!document.body.classList.contains('nav-open')));
  $('#help').addEventListener('click', e => { if (e.target.id === 'help') e.target.hidden = true; });

  // Where you left off wins over the address, which a phone can bring back stale.
  const h = new URLSearchParams(localStorage.getItem('dimguil-review:place') || location.hash.slice(1));
  const id = (S.scenes.some(s => s.id === h.get('s')) && h.get('s')) || (S.scenes.find(s => s.status === 'open') || S.scenes[0] || {}).id;
  if (id) await openScene(id, { line: +(h.get('l') || 0) });
  if (matchMedia('(max-width: 900px)').matches && localStorage.getItem('dimguil-review:nav')) setNav(true);
  poll();
}

S.test = { layoutHere, toEditor, fromEditor, applyBody, tickedOf };  // for the UI checks

main().catch(e => { document.body.insertAdjacentHTML('afterbegin', `<p class="error" style="padding:1rem">The review tool couldn't start: ${esc(e.message)}</p>`); });
