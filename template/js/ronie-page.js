/* Ronie's page glue: starts the loading sheet, wires email links, keeps the voice on the computer, and starts Ronie.
   Adapted from the portfolio's main.js; ronie.config.js must load first. */
const D = window.RONIE;
const OWNER = D.owner || 'the owner';
const OWNER_FIRST = D.ownerShort || OWNER.split(' ')[0];
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const TAU = Math.PI * 2;
const MOTION = matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : 1;

// the loading sheet shows who the agent belongs to
for (const el of $$('[data-owner]')) el.textContent = OWNER;
for (const el of $$('[data-agent]')) el.textContent = D.assistant.name || 'Ronie';
if (D.assistant.tagline) for (const el of $$('[data-tagline]')) el.textContent = D.assistant.tagline;

  function fit(canvas) {
    const dpr = Math.min(2, window.devicePixelRatio || 1);
    const { width, height } = canvas.getBoundingClientRect();
    const w = Math.max(1, Math.round(width * dpr));
    const h = Math.max(1, Math.round(height * dpr));
    const changed = canvas.width !== w || canvas.height !== h;
    if (changed) { canvas.width = w; canvas.height = h; }
    const ctx = canvas.getContext('2d');
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    return { ctx, w: width, h: height, changed };
  }


  /* ---------- Ronie loading screen: a spinning ASCII core + a boot log, while the 3D files download ---------- */
  let bootRunning = false;
  const BOOT_LOG = [
    [0, 'fetching 3D engine'],
    [10, 'loading armour textures'],
    [35, 'calibrating servos'],
    [60, 'syncing neon tubes'],
    [85, 'warming up personality'],
  ];
  // While Ronie loads: his spec sheet comes alive — SYNC drifts up, BOOT is the real download %, the CORE bar fills
  // with it, the status line follows the boot log, and the waveforms and the spectrum play. Once he's loaded the
  // sheet is hidden (assistant.js) and this stops.
  function bootScreen() {
    const box = document.getElementById('rai-loading');
    const pctEl = document.getElementById('rai-load-pct');
    if (!box || !pctEl || bootRunning || box.hidden) return;
    bootRunning = true;
    const $id = (id) => document.getElementById(id);
    const sync = $id('sp-sync'), core = $id('sp-core'), mode = $id('sp-mode'), logEl = $id('sp-log'), line = $id('sp-line'), foot = $id('sp-foot-log');
    const waves = [$id('sp-wave'), $id('sp-wave2')].filter(Boolean), spec = $id('sp-spectrum');
    let lastLog = '';
    // a little audio-style trace: a dotted baseline with a burst of thin bars travelling along it
    function wave(cv, t) {
      const { ctx, w, h } = fit(cv);
      ctx.clearRect(0, 0, w, h);
      const n = Math.floor(w / 3), mid = h / 2;
      for (let i = 0; i < n; i++) {
        const x = i * 3 + 1, u = i / n;
        const env = Math.exp(-((u - (0.5 + 0.35 * Math.sin(t * 0.0006))) ** 2) / 0.02);
        const amp = (0.08 + env * (0.5 + 0.5 * Math.sin(t * 0.012 + i * 0.9) * Math.sin(t * 0.004 + i * 0.31))) * h * 0.5;
        ctx.fillStyle = env > 0.2 ? 'rgba(220, 225, 230, .85)' : 'rgba(150, 156, 162, .45)';
        ctx.fillRect(x, mid - amp, 1, Math.max(1, amp * 2));
      }
    }
    // the rainbow spectrum along the footer, orange through violet to cyan
    function spectrum(cv, t) {
      const { ctx, w, h } = fit(cv);
      ctx.clearRect(0, 0, w, h);
      const n = Math.floor(w / 3);
      for (let i = 0; i < n; i++) {
        const u = i / n;
        const v = 0.25 + 0.75 * Math.abs(Math.sin(t * 0.003 + i * 0.35) * Math.sin(t * 0.0011 + i * 0.07)) * (0.55 + 0.45 * Math.sin(u * Math.PI));
        ctx.fillStyle = `hsl(${(28 - u * 230 + 360) % 360} 85% 62%)`;
        ctx.fillRect(i * 3, h - v * h, 1.6, v * h);
      }
    }
    // the boot count shown climbs smoothly over the sheet's few seconds rather than jumping when he loads from cache
    const bootEl = $id('sp-boot'), parts = [...box.querySelectorAll('.sp-strip figure')], tiles = [...box.querySelectorAll('.sp-tiles figure')];
    const t0 = performance.now(), SHOW = 4300;
    let shown = 0, focus = -1, focusAt = 0;
    const put = (el, v) => { if (el && el.textContent !== v) el.textContent = v; };
    // the title types itself in; the measurements count up
    const h2 = box.querySelector('.sp-title h2');
    if (h2 && !h2.dataset.typed) {
      h2.dataset.typed = '1';
      const tn = h2.firstChild;
      if (tn && tn.nodeType === 3) {
        const chars = tn.textContent.split('').map((ch, i) => `<span class="sp-ch" style="animation-delay:${(0.15 + i * 0.06).toFixed(2)}s">${ch === ' ' ? '&nbsp;' : ch}</span>`).join('');
        tn.replaceWith(document.createRange().createContextualFragment(chars));
      }
    }
    const counts = [...box.querySelectorAll('.sp-meas .sp-kv dd')].map((dd) => {
      const m = dd.textContent.match(/^(\D*)(\d+)(.*)$/);
      return m && { dd, pre: m[1], n: +m[2], post: m[3] };
    }).filter(Boolean);
    const step = (now) => {
      // stop once Ronie has loaded (or the sheet was replaced by an error message)
      if (box.hidden || !pctEl.isConnected) { bootRunning = false; return; }
      requestAnimationFrame(step);
      if (document.querySelector('[data-view="assistant"]').hidden) return;
      const t = MOTION ? now : 0;
      // the canvases first (they measure themselves), then the text — measuring after writing would make every
      // frame lay the page out twice
      for (const cv of waves) if (cv.offsetWidth) wave(cv, t);
      if (spec && spec.offsetWidth) spectrum(spec, t);
      const real = parseInt(pctEl.textContent, 10) || 0;
      const el = now - t0;
      const goal = Math.min(real, MOTION ? (el / SHOW) * 100 : 100);
      shown += (goal - shown) * (MOTION ? 0.08 : 1);
      const pct = Math.round(shown);
      put(bootEl, `${pct}%`);
      put(sync, `${(96 + pct * 0.012 + Math.sin(now / 700) * 0.35).toFixed(1)}%`);
      if (core) { const on = Math.round((pct / 100) * 7); put(core, '▮'.repeat(on) + '▯'.repeat(7 - on)); }
      put(mode, pct >= 99 ? 'Standby' : 'Booting');
      if (line) line.style.transform = `scaleX(${(shown / 100).toFixed(3)})`;
      const steps = BOOT_LOG.filter(([at]) => pct >= at);
      const cur = steps.length ? steps[steps.length - 1][1] : 'initialising';
      put(logEl, `› ${cur}${'.'.repeat(1 + (((now / 400) | 0) % 3))}`);
      if (foot) {
        const lines = [`// ${(96 + pct * 0.012).toFixed(1)}% sync`, `// ${String(pct).padStart(3, '0')} boot`, `// ${pct >= 99 ? 'standby' : 'booting'}`];
        if (foot.dataset.v !== lines.join('|')) { foot.dataset.v = lines.join('|'); foot.innerHTML = lines.join('<br>'); }
      }
      // armor components load one after another with the boot
      parts.forEach((f, i) => f.classList.toggle('ready', pct >= ((i + 1) / parts.length) * 100 - 1));
      // the focus hops from detail to detail
      if (tiles.length && MOTION && now - focusAt > 850) {
        focusAt = now;
        if (focus >= 0) tiles[focus].classList.remove('on');
        focus = (focus + 1) % tiles.length;
        tiles[focus].classList.add('on');
      }
      // measurements count up over the first second and a bit
      const k = Math.min(1, Math.max(0, (el - 400) / 1100)), e = 1 - (1 - k) ** 3;
      for (const c of counts) put(c.dd, `${c.pre}${Math.round(c.n * (MOTION ? e : 1))}${c.post}`);
    };
    requestAnimationFrame(step);
  }


  /* ---------- email links open a ready-to-send message ---------- */
  const MOBILE = matchMedia('(hover: none), (pointer: coarse)');
  function openMail(href) {
    let to = '', subject = '', body = '';
    try {
      const u = new URL(href);
      to = decodeURIComponent(u.pathname); subject = u.searchParams.get('subject') || ''; body = u.searchParams.get('body') || '';
    } catch { to = String(href).replace(/^mailto:/, '').split('?')[0]; }
    if (!subject && !body) {
      let name = '';
      try { name = localStorage.getItem('rai-name') || ''; } catch { /* private mode */ }
      subject = `Hello from your website${name ? ` — ${name}` : ''}`;
      body = [`Hi ${OWNER_FIRST},`, '', `I just came across your website at ${location.host} and wanted to get in touch.`, '', '', '',
        'Best,', name].join('\n').trim() + '\n';
    }
    const q = (k, v) => (v ? `&${k}=${encodeURIComponent(v)}` : '');
    if (MOBILE.matches) { location.href = `mailto:${to}?${q('subject', subject).slice(1)}${q('body', body)}`; return; }
    const w = window.open(`https://mail.google.com/mail/?view=cm&fs=1&to=${encodeURIComponent(to)}${q('su', subject)}${q('body', body)}`, '_blank', 'noopener');
    if (!w) location.href = `mailto:${to}?${q('subject', subject).slice(1)}${q('body', body)}`;   // (a blocked pop-up: the old way)
  }
  window.openMail = openMail;
  document.addEventListener('click', (e) => {
    const a = e.target.closest && e.target.closest('a[href^="mailto:"]');
    if (!a || e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    e.preventDefault();
    openMail(a.href);
  });


  /* ---------- the voice, kept on the computer (sw.js) ---------- */
  if ('serviceWorker' in navigator && location.protocol !== 'file:') {
    const ready = navigator.serviceWorker.register('sw.js').then(() => navigator.serviceWorker.ready).catch(() => null);
    const c = navigator.connection;
    const handheld = /Mobi|Android|iPhone|iPad/i.test(navigator.userAgent) || (/Macintosh/.test(navigator.userAgent) && navigator.maxTouchPoints > 1);
    if ('gpu' in navigator && !handheld && !(c && (c.saveData || /(^|-)2g$/.test(c.effectiveType || '')))) {
      const go = () => ready.then((reg) => reg && reg.active && reg.active.postMessage({ type: 'warm-voice' }));
      if (document.readyState === 'complete') go(); else addEventListener('load', go, { once: true });
    }
  }

  /* ---------- start ---------- */
  bootScreen();
  import('./ronie.js').then((m) => m.open()).catch((err) => {
    console.error('Ronie failed to load', err);
    const l = document.getElementById('rai-loading');
    if (l) l.textContent = "Ronie couldn't start on this browser. Try refreshing.";
  });
