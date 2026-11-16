/* 33rd//Creative footer credit — animated, links to 33rdcreative.com.
 *   entrance (when scrolled into view): glyphs pop up one after another, the slashes swipe in
 *   hover: a wave runs through the letters while the slashes zip across and back
 * Fills any <svg data-studio-logo> (menu page) and the footer credit svg of the home page
 * (a.section-contacts__logo svg, which Vue renders — re-applied if it is re-rendered).
 * Glyph paths come from /brand/studio-data.js (window.STUDIO_LOGO, built by tools/apply.py).
 */
(function () {
  const NS = 'http://www.w3.org/2000/svg';
  const URL = 'https://33rdcreative.com/';
  const SPRING = 'cubic-bezier(.34,1.56,.64,1)';
  const reduced = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  function fill(svg) {
    const D = window.STUDIO_LOGO;
    if (!D || svg.dataset.studio) return;
    svg.dataset.studio = '1';
    svg.setAttribute('viewBox', `0 -40 ${D.w} ${D.h + 80}`);
    svg.setAttribute('role', 'img');
    svg.setAttribute('aria-label', '33rd Creative');
    svg.removeAttribute('id');
    svg.innerHTML = '';
    const glyphs = D.glyphs.map(g => {
      const grp = document.createElementNS(NS, 'g');
      grp.setAttribute('class', 'studio-glyph' + (g.kind === 'slash' ? ' is-slash' : ''));
      grp.style.transformBox = 'fill-box';
      grp.style.transformOrigin = '50% 100%';
      const p = document.createElementNS(NS, 'path');
      p.setAttribute('d', g.d);
      p.setAttribute('fill', 'currentColor');
      grp.appendChild(p);
      svg.appendChild(grp);
      return grp;
    });
    const anim = (el, frames, opts) => el.animate ? el.animate(frames, Object.assign({ fill: 'both' }, opts)) : null;

    // entrance
    glyphs.forEach(g => { g.style.opacity = 0; });
    let shown = false;
    const enter = () => {
      if (shown) return; shown = true;
      glyphs.forEach((g, i) => {
        g.style.opacity = 1;
        if (reduced()) return;
        const slash = g.classList.contains('is-slash');
        anim(g, slash
          ? [{ transform: 'translateX(-120%) skewX(-20deg)', opacity: 0 }, { transform: 'translateX(0) skewX(0)', opacity: 1 }]
          : [{ transform: 'translateY(60%) scale(.4)', opacity: 0 }, { transform: 'translateY(-12%) scale(1.08)', opacity: 1, offset: .65 },
             { transform: 'translateY(0) scale(1)', opacity: 1 }],
          { duration: slash ? 420 : 520, delay: 60 * i, easing: slash ? 'cubic-bezier(.16,1,.3,1)' : SPRING });
      });
    };
    if ('IntersectionObserver' in window) {
      const io = new IntersectionObserver(es => { if (es.some(e => e.isIntersecting)) { enter(); io.disconnect(); } }, { threshold: .4 });
      io.observe(svg);
    } else enter();

    // hover: letter wave + slashes zip
    let busy = false;
    const host = svg.closest('a') || svg;
    host.addEventListener('pointerenter', () => {
      if (!shown || busy || reduced()) return;
      busy = true;
      glyphs.forEach((g, i) => {
        const slash = g.classList.contains('is-slash');
        anim(g, slash
          ? [{ transform: 'translateX(0)' }, { transform: 'translateX(55%) skewX(-12deg)', offset: .45 }, { transform: 'translateX(0)' }]
          : [{ transform: 'translateY(0)' }, { transform: 'translateY(-28%) rotate(-4deg)', offset: .45 }, { transform: 'translateY(0)' }],
          { duration: 460, delay: 35 * i, easing: 'ease-in-out', fill: 'none' });
      });
      setTimeout(() => { busy = false; }, 460 + 35 * glyphs.length);
    });
  }

  function link(a) {
    if (!a || a.dataset.studioLink) return;
    a.dataset.studioLink = '1';
    a.setAttribute('href', URL);
    a.setAttribute('target', '_blank');
    a.setAttribute('rel', 'noopener noreferrer');
    a.setAttribute('aria-label', '33rd Creative');
  }

  function run() {
    document.querySelectorAll('svg[data-studio-logo], a.section-contacts__logo svg').forEach(fill);
    document.querySelectorAll('a.section-contacts__logo, a.studio-link').forEach(link);
  }
  new MutationObserver(run).observe(document.documentElement, { childList: true, subtree: true });
  document.addEventListener('DOMContentLoaded', run);
  run();
})();
