/* Marathon Burger animated logo — replaces Planetoño's Rive "loader_animation" logo.
 *
 * Sequence (matched to the original Rive file):
 *   loading  : a row of palm trees pops in one by one (the original used ✦ sparkles)
 *   loaded   : palms pop out, the wordmark pops in, letters wave, "Burger" pops in underneath
 *   idle     : a random letter hops every few seconds
 *   hover    : (desktop) the letter under the cursor lifts and grows, neighbours follow a little
 *   click    : squash-and-stretch bounce
 *
 * Interface used by the patched ThePreloader component:
 *   const logo = MarathonLogo.mount(el)
 *   logo.loadInput.value = true   // when the site has finished loading
 *   logo.volume = 0..1            // follows the site's sound switch
 *   logo.resizeDrawingSurfaceToCanvas()  // no-op, kept for compatibility
 * Path data comes from /brand/logo-data.js (window.MARATHON_LOGO_DATA), built by tools/apply.py.
 */
(function () {
  const NS = 'http://www.w3.org/2000/svg';
  const SPRING = 'cubic-bezier(.34,1.56,.64,1)';
  const OUT = 'cubic-bezier(.16,1,.3,1)';
  const reduced = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const canHover = () => window.matchMedia('(hover: hover) and (pointer: fine)').matches;

  function el(tag, attrs, parent) {
    const n = document.createElementNS(NS, tag);
    for (const k in attrs) n.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(n);
    return n;
  }

  // One shape drawn in the site's cartoon style: hard drop shadow, thick outline, flat fill.
  function cartoon(parent, d, fill, o) {
    const g = el('g', {}, parent);
    if (o.flat) { el('path', { d, fill }, g); return g; }
    el('path', { d, fill: '#000', stroke: '#000', 'stroke-width': o.stroke, 'stroke-linejoin': 'round',
                 transform: `translate(0 ${o.shadow})` }, g);
    el('path', { d, fill, stroke: o.outline || '#000', 'stroke-width': o.stroke, 'stroke-linejoin': 'round', 'paint-order': 'stroke' }, g);
    return g;
  }

  function anim(node, frames, opts) {
    if (!node.animate) return null;
    return node.animate(frames, Object.assign({ fill: 'forwards' }, opts));
  }

  function build(root, D) {
    const flat = D.style === 'flat';
    const [W, H] = D.box;
    const bb = D.burger.bbox;
    const pad = 40;
    const vb = [-pad, -pad - 60, W + pad * 2, bb[3] + pad * 2 + 80];
    const svg = el('svg', { viewBox: vb.join(' '), class: 'mb-logo__svg', 'aria-label': D.name, role: 'img' });
    const o = { flat, stroke: 22, shadow: 16 };

    const word = el('g', { class: 'mb-logo__word' }, svg);
    const box = el('g', { class: 'mb-logo__box' }, word);
    const rect = `M0 0H${W}V${H}H0Z`;
    cartoon(box, rect, D.colors.box, o);
    const letters = D.letters.map(l => {
      const g = el('g', { class: 'mb-logo__letter' }, word);
      cartoon(g, l.d, D.colors.letters, { flat, stroke: 14, shadow: 10 });
      return g;
    });
    const burger = el('g', { class: 'mb-logo__burger' }, svg);
    cartoon(burger, D.burger.d, D.colors.burger, { flat: true });   // "Burger" script: solid black, no outline

    // Loader: palm row centred where the wordmark sits
    const loader = el('g', { class: 'mb-logo__loader' }, svg);
    const palms = [], palmX = [];
    const count = 5, ph = H * 1.25, trees = [D.palm, D.palm_left || D.palm];   // alternate both palm trees
    const pw = D.palm.w * ph / D.palm.h, gap = 70;
    const startX = W / 2 - (count * pw + (count - 1) * gap) / 2;
    for (let i = 0; i < count; i++) {
      const tree = trees[i % 2], scale = ph / tree.h;
      const outer = el('g', { transform: `translate(${startX + i * (pw + gap) + (pw - tree.w * scale) / 2} ${H / 2 - ph / 2})` }, loader);
      const pop = el('g', { class: 'mb-logo__palm' }, outer);  // animated wrapper (no transform attribute)
      const g = el('g', { transform: `scale(${scale})` }, pop);
      cartoon(g, tree.d, D.colors.letters, { flat: false, stroke: 14 / scale, shadow: 14 / scale });
      palms.push(pop);
      palmX.push(startX + i * (pw + gap) + pw / 2);
    }
    root.appendChild(svg);
    return { svg, word, box, letters, burger, loader, palms, palmX };
  }

  function mount(root) {
    const D = window.MARATHON_LOGO_DATA;
    root.classList.add('mb-logo');
    root.innerHTML = '';
    const P = build(root, D);
    let volume = 1, loaded = false, hoverIdx = -1, idleTimer = null;
    const lift = new Array(P.letters.length).fill(0);
    const sounds = [];

    function sound(i) {
      if (!volume || !D.sound) return;
      try {
        const a = sounds[i % 3] || (sounds[i % 3] = new Audio(D.sound));
        a.currentTime = 0; a.volume = 0.35 * volume; a.preservesPitch = false;
        a.playbackRate = 0.8 + (i / P.letters.length) * 0.7;
        a.play().catch(() => {});
      } catch (e) { /* audio is optional */ }
    }

    // Loader (matches the original's ✦ row): the palms fill up like a progress bar, each one growing from
    // tiny to full size in turn, and twinkle (pulse + sway) while the site loads.
    for (const n of [P.word, P.burger]) n.style.opacity = 0;
    const t0 = performance.now();
    let progress = 0;
    function tick(now) {
      if (loaded) return;
      const t = (now - t0) / 1000;
      progress = reduced() ? 1 : 1 - Math.exp(-t / 1.4);           // eases towards 1 while loading
      P.palms.forEach((p, i) => {
        const grow = Math.max(0, Math.min(1, progress * 5.3 - i));
        const twinkle = 1 + 0.07 * Math.sin(t * 5.5 + i * 1.7);
        const sway = 7 * Math.sin(t * 2.8 + i * 1.1);
        p.style.opacity = grow > 0.02 ? 1 : 0;
        p.style.transform = `scale(${(grow * twinkle).toFixed(3)}) rotate(${sway.toFixed(2)}deg)`;
      });
      requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);

    function setLetter(i, y, s, dur, easing) {
      anim(P.letters[i], [{ transform: `translateY(${y}px) scale(${s})` }], { duration: dur, easing });
    }

    function reveal() {
      if (loaded) return;
      loaded = true;
      const fast = reduced();
      // left-to-right wipe: each palm spins away as the letters under it pop in
      const W = D.box[0], WIPE = fast ? 0 : 420;
      P.palms.forEach((p, i) => {
        const delay = (P.palmX[i] / W) * WIPE;
        anim(p, [{ transform: p.style.transform, opacity: 1 }, { transform: 'scale(1.2) rotate(30deg)', opacity: 1, offset: 0.3 },
                 { transform: 'scale(0) rotate(90deg)', opacity: 0 }], { duration: fast ? 1 : 150, delay, easing: 'ease-in' });
      });
      P.word.style.opacity = 1;
      anim(P.box, [{ transform: 'scaleX(0)', opacity: 0 }, { transform: 'scaleX(1.04)', opacity: 1, offset: 0.7 }, { transform: 'scaleX(1)', opacity: 1 }],
           { duration: fast ? 1 : WIPE + 160, easing: OUT });
      P.letters.forEach((l, i) => {
        const cx = (D.letters[i].x0 + D.letters[i].x1) / 2;
        anim(l, [{ transform: 'translateY(30px) scale(0.2)', opacity: 0 }, { transform: 'translateY(-10px) scale(1.15)', opacity: 1, offset: 0.6 },
                 { transform: 'translateY(0) scale(1)', opacity: 1 }],
             { duration: fast ? 1 : 420, delay: fast ? 0 : 110 + (cx / W) * WIPE, easing: OUT });
      });
      setTimeout(() => { P.loader.style.display = 'none'; }, fast ? 0 : WIPE + 300);
      // the wave that runs across the word once it has landed
      if (!fast) {
        P.letters.forEach((l, i) => setTimeout(() => {
          anim(l, [{ transform: 'translateY(0) scale(1)' }, { transform: 'translateY(-34px) scale(1.06)' }, { transform: 'translateY(0) scale(1)' }],
               { duration: 380, easing: 'ease-in-out' });
        }, 820 + i * 70));
      }
      setTimeout(() => {
        P.burger.style.opacity = 1;
        anim(P.burger, [{ transform: 'scale(0) rotate(-14deg)' }, { transform: 'scale(1.18) rotate(4deg)', offset: 0.65 }, { transform: 'scale(1) rotate(0)' }],
             { duration: fast ? 1 : 560, easing: OUT });
      }, fast ? 0 : 1250);
      scheduleIdle();
    }

    function scheduleIdle() {
      clearTimeout(idleTimer);
      idleTimer = setTimeout(() => {
        if (hoverIdx < 0 && !reduced()) {
          const i = Math.floor(Math.random() * P.letters.length);
          anim(P.letters[i], [{ transform: 'translateY(0) scale(1)' }, { transform: 'translateY(-40px) rotate(-6deg) scale(1.05)', offset: 0.45 },
                              { transform: 'translateY(0) scale(1)' }], { duration: 520, easing: 'ease-in-out' });
        }
        scheduleIdle();
      }, 2600 + Math.random() * 2600);
    }

    // Hover: desktop only. Find the letter under the cursor by its horizontal span.
    function onMove(e) {
      if (!loaded || !canHover()) return;
      const r = P.svg.getBoundingClientRect();
      const vb = P.svg.viewBox.baseVal;
      const x = vb.x + ((e.clientX - r.left) / r.width) * vb.width;
      let idx = D.letters.findIndex(l => x >= l.x0 - 8 && x <= l.x1 + 8);
      if (idx === hoverIdx) return;
      hoverIdx = idx;
      if (idx >= 0) sound(idx);
      P.letters.forEach((_, i) => {
        const dist = idx < 0 ? 99 : Math.abs(i - idx);
        const y = dist === 0 ? -44 : dist === 1 ? -14 : 0;
        const s = dist === 0 ? 1.1 : 1;
        if (lift[i] !== y) { lift[i] = y; setLetter(i, y, s, 320, SPRING); }
      });
    }
    function onLeave() {
      hoverIdx = -1;
      P.letters.forEach((_, i) => { if (lift[i]) { lift[i] = 0; setLetter(i, 0, 1, 420, SPRING); } });
    }
    function onClick() {
      anim(P.svg, [{ transform: 'scale(1,1)' }, { transform: 'scale(1.08,0.9)' }, { transform: 'scale(0.96,1.06)' }, { transform: 'scale(1,1)' }],
           { duration: 450, easing: 'ease-out', fill: 'none' });
      sound(0);
    }
    root.addEventListener('pointermove', onMove);
    root.addEventListener('pointerleave', onLeave);
    root.addEventListener('click', onClick);

    return {
      loadInput: { set value(v) { if (v) reveal(); }, get value() { return loaded; } },
      set volume(v) { volume = v; }, get volume() { return volume; },
      resizeDrawingSurfaceToCanvas() {},
      reveal,
    };
  }

  window.MarathonLogo = { mount };
})();
