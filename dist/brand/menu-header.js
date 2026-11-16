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

  // ---- music: same song and same on/off setting as the home page (pinia "audio" store in localStorage) ----
  const MUSIC = '/media/sounds/marathon-music-2.mp3';
  try { if (!localStorage.getItem('mbAudioFix1')) { localStorage.removeItem('audio'); localStorage.setItem('mbAudioFix1', '1'); } } catch (e) { /* private mode */ }
  const readPref = () => { try { return JSON.parse(localStorage.getItem('audio') || '{}').isAudioEnabled !== false; } catch (e) { return true; } };
  const savePref = on => { try { localStorage.setItem('audio', JSON.stringify({ isAudioEnabled: on })); } catch (e) { /* private mode */ } };
  let audioOn = readPref(), riveSound = null;
  const WAVES = { on: ['M 33 16 Q 37 20 33 24', 'M 37 13 Q 44 20 37 27'], off: ['M 33 16.5 Q 36.5 20 40 23.5', 'M 40 16.5 Q 36.5 20 33 23.5'] };
  function showSound() {
    header.querySelectorAll('.the-sound-switcher-mobile').forEach(btn => {
      btn.classList.toggle('is-muted', !audioOn);
      const waves = [...btn.querySelectorAll('path.wave')];      // both sound waves (they become the "x" when muted)
      waves.forEach((p, i) => { if (WAVES.on[i]) p.setAttribute('d', (audioOn ? WAVES.on : WAVES.off)[i]); });
    });
    if (riveSound && riveSound.value !== audioOn) riveSound.value = audioOn;
  }
  function setAudio(on) {
    audioOn = on; savePref(on); showSound();
    if (!window.MBMusic) return;
    if (on) { window.MBMusic.unlock(MUSIC); window.MBMusic.start(MUSIC, 1.5); }
    else window.MBMusic.stop(0.25);
  }
  // browsers only allow sound after a tap: start the music on the first tap anywhere if sound is on
  const firstTap = e => {
    if (e.target.closest && e.target.closest('.the-sound-switcher, .the-sound-switcher-mobile')) return;   // the switch handles itself
    window.removeEventListener('pointerdown', firstTap, true);
    if (audioOn && window.MBMusic) { window.MBMusic.unlock(MUSIC); window.MBMusic.start(MUSIC, 1.5); }
  };
  window.addEventListener('pointerdown', firstTap, true);
  header.querySelectorAll('.the-sound-switcher-mobile').forEach(b => b.addEventListener('click', e => { e.stopPropagation(); setAudio(!audioOn); }));
  showSound();

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
      mount(sw, { artboard: 'sound_animation_reworked', autoBind: true }, r => {
        try {
          riveSound = r.viewModelInstance.boolean('isAudioEnabled');
          riveSound.value = audioOn;
          // only real clicks count: the Rive state machine reports its own default ("off") while loading
          let userTap = 0;
          sw.addEventListener('pointerdown', () => { userTap = Date.now(); });
          riveSound.on(v => { if (Date.now() - userTap < 1500 && v !== audioOn) setAudio(v); else if (v !== audioOn) riveSound.value = audioOn; });
        } catch (e) { /* optional */ }
      });
    }
  }
})();
