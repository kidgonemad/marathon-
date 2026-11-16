/* How-it-works stepper — replaces the Rive "stepper_animation_reworked" artboard.
 * Three numbered steps follow the 3D scroll (burger -> drink -> fries); the last scroll phase
 * (the meal box) shows the final pill, "Claim your meal".
 * mount(el, {onHover(bool), onChange(id)}) returns { id: {value} } like the Rive view-model number.
 * Labels come from window.MARATHON_STEPPER = {steps: [3 labels], final: "Claim your meal"}.
 */
(function () {
  function mount(root, cb) {
    const cfg = window.MARATHON_STEPPER || { steps: ['Pick your burger', 'Grab a drink', 'Add fries'], final: 'Claim your meal' };
    root.classList.add('mb-stepper');  // informational only: styling must not depend on it (Vue resets the class on hover)
    root.innerHTML = '';
    const btns = cfg.steps.map((label, i) => {
      const b = document.createElement('button');
      b.type = 'button'; b.className = 'mb-stepper__btn'; b.textContent = String(i + 1);
      b.setAttribute('aria-label', `Step ${i + 1}: ${label}`);
      b.dataset.soundClick = 'click';
      root.appendChild(b);
      return b;
    });
    const pill = document.createElement('button');
    pill.type = 'button'; pill.className = 'mb-stepper__pill';
    root.appendChild(pill);
    let current = 0;

    function render(id) {
      current = id;
      const done = id >= cfg.steps.length;
      btns.forEach((b, i) => {
        b.classList.toggle('is-active', i === id);
        b.classList.toggle('is-done', i < id);
      });
      const anchor = done ? btns[btns.length - 1] : btns[Math.max(0, id)];
      anchor.after(pill);
      pill.textContent = done ? cfg.final : cfg.steps[Math.max(0, id)];
      pill.classList.toggle('is-final', done);
      pill.animate && pill.animate([{ transform: 'scale(.6)', opacity: 0 }, { transform: 'scale(1.06)', opacity: 1, offset: .7 },
                                    { transform: 'scale(1)', opacity: 1 }], { duration: 380, easing: 'cubic-bezier(.34,1.56,.64,1)' });
    }
    const go = id => { render(id); cb.onChange(-1); cb.onChange(id); };   // highlight right away, then scroll there
    btns.forEach((b, i) => b.addEventListener('click', () => go(i)));
    pill.addEventListener('click', () => go(current >= cfg.steps.length ? cfg.steps.length : current));
    root.addEventListener('pointerenter', () => cb.onHover(true));
    root.addEventListener('pointerleave', () => cb.onHover(false));
    render(0);
    return { id: { get value() { return current; }, set value(n) { if (n !== current) render(n); } } };
  }
  window.MarathonStepper = { mount };
})();
