/* Site music, shared by the home page (patched AudioManager) and the menu page (menu-header.js).
 *
 * Phones and Safari only let an <audio> element start inside a tap. The home page asks for the music
 * 600 ms after START, outside the tap, so it was silently blocked. unlock() runs inside the tap: it starts
 * the element at volume 0 (through a Web Audio gain node, because iOS ignores element.volume); start() /
 * stop() then just fade that gain. Streaming via <audio> keeps the 2.6 MB song from being decoded whole.
 */
window.MBMusic = (function () {
  let g = null, gen = 0;

  function graph(ctx, url) {
    if (g) return g;
    const a = new Audio(url);
    a.loop = true;
    a.preload = 'auto';
    a.crossOrigin = 'anonymous';
    a.setAttribute('playsinline', '');
    const src = ctx.createMediaElementSource(a);
    const gain = ctx.createGain();
    gain.gain.value = 0;
    src.connect(gain);
    gain.connect(ctx.destination);
    g = { a, gain, ctx, wanted: false };
    return g;
  }

  function ramp(to, secs) {
    const p = g.gain.gain, t = g.ctx.currentTime;
    p.cancelScheduledValues(t);
    p.setValueAtTime(p.value, t);
    p.linearRampToValueAtTime(to, t + secs);
  }

  // call inside a tap/click
  function unlock(ctx, url) {
    const m = graph(ctx, url);
    if (ctx.state === 'suspended') ctx.resume();
    m.a.play().catch(() => {});
    const my = gen;
    setTimeout(() => { if (!m.wanted && gen === my) m.a.pause(); }, 4000);   // nobody asked for music
    return m;
  }

  function start(ctx, url, fade) {
    const m = graph(ctx, url);
    gen++;
    m.wanted = true;
    if (ctx.state === 'suspended') ctx.resume();
    m.a.play().catch(() => {});
    ramp(0.5, fade || 1.5);
    return gen;
  }

  function stop(fade) {
    if (!g) return;
    g.wanted = false;
    const my = ++gen;
    ramp(0, fade || 1);
    setTimeout(() => { if (gen === my) g.a.pause(); }, (fade || 1) * 1000 + 60);
  }

  return { unlock, start, stop, get playing() { return !!(g && g.wanted); } };
})();
