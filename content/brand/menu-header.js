/* Menu page: drives the home page's real header (markup + CSS copied in by tools/apply.py) the same way the
 * site's Vue components do, so the menu page has the identical header and phone dropdown.
 *   - nav labels / Contact / sound switch: same Rive artboards as TheNavItem, TheNavEmail, TheSoundSwitcher
 *   - phone MENU: toggles .is-open on .the-header-mobile and .the-hamburger (TheHeaderMobile / TheHamburger);
 *     closes on a link tap, a tap outside the header, or resize
 *   - desktop: red header background once the page is scrolled (.is-bg-visible)
 * Needs /vendor/rive/rive.js (standalone @rive-app/canvas, same version as the site's rive.wasm).
 */
(function () {
  const header = document.querySelector('.the-header');
  if (!header) return;
  const mobile = header.querySelector('.the-header-mobile');
  const burger = header.querySelector('.the-hamburger');
  const desktop = header.querySelector('.the-header-desktop');

  // ---- logo (same animated Marathon Burger logo as the home page) ----
  header.querySelectorAll('.mb-hdr-logo').forEach(el => {
    const logo = window.MarathonLogo.mount(el);
    logo.volume = 0;
    setTimeout(() => { logo.loadInput.value = true; }, 200);
  });

  // ---- phone dropdown ----
  const setOpen = open => {
    mobile.classList.toggle('is-open', open);
    burger.classList.toggle('is-open', open);
  };
  burger.addEventListener('click', e => { e.stopPropagation(); setOpen(!mobile.classList.contains('is-open')); });
  mobile.querySelectorAll('.the-nav__item').forEach(a => a.addEventListener('click', () => setOpen(false)));
  document.addEventListener('click', e => { if (!mobile.contains(e.target)) setOpen(false); });
  window.addEventListener('resize', () => setOpen(false));

  // ---- desktop header background when scrolled ----
  const bg = () => desktop.classList.toggle('is-bg-visible', window.scrollY > 10);
  window.addEventListener('scroll', bg, { passive: true });
  bg();

  // ---- Contact copies the email, like the home page ----
  header.querySelectorAll('.the-nav__item.--email').forEach(a => a.addEventListener('click', e => {
    e.preventDefault();
    const email = a.getAttribute('href').replace(/^mailto:/, '');
    if (navigator.clipboard) navigator.clipboard.writeText(email).catch(() => {});
  }));

  // ---- Rive: nav labels, Contact, sound switch ----
  const R = window.rive;
  if (!R) return;
  R.RuntimeLoader.setWasmUrl('/vendor/rive/rive.wasm');
  const file = new R.RiveFile({ src: '/media/rive.riv', onLoad: start, onLoadError: () => {} });
  file.init();

  function mount(canvas, opts, onReady) {
    const r = new R.Rive(Object.assign({
      canvas, riveFile: file, stateMachines: 'State Machine 1', autoplay: true,
      onLoad: () => { r.resizeDrawingSurfaceToCanvas(window.devicePixelRatio + 1); if (onReady) onReady(r); },
    }, opts));
    window.addEventListener('resize', () => r.resizeDrawingSurfaceToCanvas(window.devicePixelRatio + 1));
    return r;
  }

  function start() {
    header.querySelectorAll('a.the-nav__item').forEach(a => {
      const canvas = a.querySelector('canvas');
      const isMobile = !!a.closest('.the-header-mobile');
      if (a.classList.contains('--email')) {
        mount(canvas, { artboard: isMobile ? 'contact_animation_mobile' : 'contact_animation', autoBind: false });
        return;
      }
      const text = a.querySelector('.the-nav__item__text').textContent;
      mount(canvas, { artboard: isMobile ? 'menu_animation_mobile' : 'menu_animation', autoBind: true },
            r => { r.viewModelInstance.string('text').value = text; });
    });
    const sw = header.querySelector('.the-sound-switcher canvas');
    if (sw) {
      mount(sw, { artboard: 'sound_animation_reworked', autoBind: true },
            r => { try { r.viewModelInstance.boolean('isAudioEnabled').value = true; } catch (e) { /* optional */ } });
    }
  }
})();
