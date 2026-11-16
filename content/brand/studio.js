/* 33rd//Creative footer credit — the studio's own intro animation (33rdcreative.com, trace-animated.svg):
 * slashes start tilted -25° and straighten, "33rd" slides in from the left, CREATIVE slides in from the
 * right letter by letter. Same paths, keyframes and timing as their site; here it plays when the footer
 * scrolls into view and replays on hover. Links to https://33rdcreative.com/.
 * Fills <svg data-studio-logo> (menu page) and the home page footer credit svg (a.section-contacts__logo svg,
 * rendered by Vue — re-applied if re-rendered). Artwork comes from /brand/studio-data.js (window.STUDIO_SVG).
 */
(function () {
  const URL = 'https://33rdcreative.com/';

  function fill(svg) {
    const D = window.STUDIO_SVG;
    if (!D || svg.dataset.studio) return;
    svg.dataset.studio = '1';
    svg.setAttribute('viewBox', D.viewBox);
    svg.setAttribute('role', 'img');
    svg.setAttribute('aria-label', '33rd Creative');
    svg.removeAttribute('id');
    svg.classList.add('studio-anim');
    svg.innerHTML = D.inner;

    const play = () => {
      svg.classList.remove('is-playing');
      void svg.getBoundingClientRect();          // restart the CSS animations
      svg.classList.add('is-playing');
    };
    if ('IntersectionObserver' in window) {
      const io = new IntersectionObserver(es => { if (es.some(e => e.isIntersecting)) { play(); io.disconnect(); } }, { threshold: .4 });
      io.observe(svg);
    } else play();
    let last = 0;
    (svg.closest('a') || svg).addEventListener('pointerenter', () => {
      const now = Date.now();
      if (now - last > 2200) { last = now; play(); }   // let one run finish (2s) before replaying
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
