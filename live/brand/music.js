/* Site music, shared by the home page (patched AudioManager) and the menu page (menu-header.js).
 *
 * Plain <audio loop> element only — no Web Audio. On iPhone, Web Audio is muted by the ringer/silent switch
 * and stays silent if its AudioContext isn't running; a plain media element plays like the click/hover sounds.
 * unlock() must run inside a tap (phones only allow media to start there); start()/stop() fade the volume
 * (iOS ignores element.volume, so there it simply plays/pauses).
 */
window.MBMusic = (function () {
  let a = null, url = null, raf = 0, wanted = false;

  function el(src) {
    if (!a || (src && src !== url)) {
      if (a) a.pause();
      url = src;
      a = new Audio(src);
      a.loop = true;
      a.preload = 'auto';
      a.setAttribute('playsinline', '');
      a.volume = 0;
    }
    return a;
  }

  function fade(to, ms, done) {
    cancelAnimationFrame(raf);
    const from = a.volume, t0 = performance.now();
    const step = now => {
      const k = Math.min(1, (now - t0) / ms);
      try { a.volume = from + (to - from) * k; } catch (e) { /* read-only on iOS */ }
      if (k < 1) raf = requestAnimationFrame(step); else if (done) done();
    };
    raf = requestAnimationFrame(step);
  }

  // call inside a tap/click: starts the element silently so later play() calls are allowed
  function unlock(src) {
    const m = el(src);
    const p = m.play();
    if (p && p.catch) p.catch(() => {});
    setTimeout(() => { if (!wanted) m.pause(); }, 4000);      // nobody asked for music
  }

  function start(src, fadeSecs) {
    const m = el(src);
    wanted = true;
    const p = m.play();
    if (p && p.catch) p.catch(() => {});
    fade(0.5, (fadeSecs || 1.5) * 1000);
  }

  function stop(fadeSecs) {
    if (!a) return;
    wanted = false;
    fade(0, (fadeSecs || 1) * 1000, () => { if (!wanted) a.pause(); });
  }

  // pause with the page in the background, resume when it comes back
  document.addEventListener('visibilitychange', () => {
    if (!a || !wanted) return;
    if (document.hidden) a.pause();
    else { const p = a.play(); if (p && p.catch) p.catch(() => {}); }
  });

  // home page: react to the sound switch inside the tap itself (the site's own handler runs a beat later)
  function bindSwitches() {
    document.addEventListener('click', e => {
      if (!a || !e.target.closest || !e.target.closest('.the-sound-switcher, .the-sound-switcher-mobile')) return;
      if (wanted) stop(0.25); else start(url, 0.6);
    }, true);
  }

  return { unlock, start, stop, bindSwitches, get playing() { return !!(a && wanted && !a.paused); }, get el() { return a; } };
})();
