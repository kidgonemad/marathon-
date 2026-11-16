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
    el('path', { d, fill, stroke: '#000', 'stroke-width': o.stroke, 'stroke-linejoin': 'round', 'paint-order': 'stroke' }, g);
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
    cartoon(burger, D.burger.d, D.colors.burger, { flat, stroke: 16, shadow: 10 });

    // Loader: palm row centred where the wordmark sits
    const loader = el('g', { class: 'mb-logo__loader' }, svg);
    const palms = [];
    const count = 5, ph = H * 1.25;
    const scale = ph / D.palm.h, pw = D.palm.w * scale, gap = 70;
    const startX = W / 2 - (count * pw + (count - 1) * gap) / 2;
    for (let i = 0; i < count; i++) {
      const outer = el('g', { transform: `translate(${startX + i * (pw + gap)} ${H / 2 - (D.palm.h * scale) / 2})` }, loader);
      const pop = el('g', { class: 'mb-logo__palm' }, outer);  // animated wrapper (no transform attribute)
      const g = el('g', { transform: `scale(${scale})` }, pop);
      cartoon(g, D.palm.d, D.colors.letters, { flat: false, stroke: 14 / scale, shadow: 14 / scale });
      palms.push(pop);
    }
    root.appendChild(svg);
    return { svg, word, box, letters, burger, loader, palms };
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

    // Start hidden; loader palms pop in one by one and bob while the site loads
    for (const n of [P.word, P.burger]) n.style.opacity = 0;
    P.palms.forEach((p, i) => {
      p.style.opacity = 0;
      setTimeout(() => {
        p.style.opacity = 1;
        anim(p, [{ transform: 'scale(0)' }, { transform: 'scale(1.15)' }, { transform: 'scale(1)' }], { duration: 420, easing: OUT });
      }, 250 + i * 260);
    });
    P.loader.style.transformBox = 'fill-box';
    P.loader.style.transformOrigin = '50% 50%';
    const bob = anim(P.loader, [{ transform: 'translateY(0)' }, { transform: 'translateY(-14px)' }, { transform: 'translateY(0)' }],
                     { duration: 900, iterations: Infinity, easing: 'ease-in-out', fill: 'none' });

    function setLetter(i, y, s, dur, easing) {
      anim(P.letters[i], [{ transform: `translateY(${y}px) scale(${s})` }], { duration: dur, easing });
    }

    function reveal() {
      if (loaded) return;
      loaded = true;
      if (bob) bob.cancel();
      const fast = reduced();
      anim(P.loader, [{ opacity: 1, transform: 'scale(1)' }, { opacity: 0, transform: 'scale(0.6)' }], { duration: fast ? 1 : 260, easing: 'ease-in' });
      setTimeout(() => {
        P.loader.style.display = 'none';
        P.word.style.opacity = 1;
        anim(P.box, [{ transform: 'scale(0.4)', opacity: 0 }, { transform: 'scale(1.08)', opacity: 1, offset: 0.6 }, { transform: 'scale(1)', opacity: 1 }],
             { duration: fast ? 1 : 520, easing: OUT });
        P.letters.forEach((l, i) => {
          anim(l, [{ transform: 'translateY(-90px) scale(0.6)', opacity: 0 }, { transform: 'translateY(0) scale(1)', opacity: 1 }],
               { duration: fast ? 1 : 520, delay: fast ? 0 : 60 + i * 45, easing: SPRING });
        });
        // the wave that runs across the word once it has landed
        if (!fast) {
          P.letters.forEach((l, i) => setTimeout(() => {
            anim(l, [{ transform: 'translateY(0) scale(1)' }, { transform: 'translateY(-34px) scale(1.06)' }, { transform: 'translateY(0) scale(1)' }],
                 { duration: 380, easing: 'ease-in-out' });
          }, 700 + i * 70));
        }
        setTimeout(() => {
          P.burger.style.opacity = 1;
          anim(P.burger, [{ transform: 'scale(0) rotate(-14deg)' }, { transform: 'scale(1.18) rotate(4deg)', offset: 0.65 }, { transform: 'scale(1) rotate(0)' }],
               { duration: fast ? 1 : 560, easing: OUT });
        }, fast ? 0 : 1150);
        scheduleIdle();
      }, fast ? 0 : 220);
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
