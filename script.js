// ---------- Hero slider ----------
const slides = [...document.querySelectorAll('.slide')];
const dotsWrap = document.querySelector('.dots');
let current = 0;
let timer;

slides.forEach((_, i) => {
  const b = document.createElement('button');
  b.setAttribute('role', 'tab');
  b.setAttribute('aria-label', `Slide ${i + 1}`);
  b.addEventListener('click', () => go(i, true));
  dotsWrap.appendChild(b);
});
const dots = [...dotsWrap.children];

function go(i, user) {
  current = (i + slides.length) % slides.length;
  slides.forEach((s, k) => s.classList.toggle('is-active', k === current));
  dots.forEach((d, k) => d.setAttribute('aria-selected', k === current));
  if (window.scrollY < window.innerHeight * 0.6) document.body.dataset.theme = slides[current].dataset.theme;
  if (user) restart();
}
function restart() { clearInterval(timer); timer = setInterval(() => go(current + 1), 6000); }
document.querySelector('.prev').addEventListener('click', () => go(current - 1, true));
document.querySelector('.next').addEventListener('click', () => go(current + 1, true));

let touchX = null;
const hero = document.querySelector('.hero');
hero.addEventListener('touchstart', e => (touchX = e.touches[0].clientX), { passive: true });
hero.addEventListener('touchend', e => {
  if (touchX === null) return;
  const dx = e.changedTouches[0].clientX - touchX;
  if (Math.abs(dx) > 50) go(current + (dx < 0 ? 1 : -1), true);
  touchX = null;
});
go(0);
restart();

// Reset page colour once you scroll past the hero
window.addEventListener('scroll', () => {
  document.body.dataset.theme = window.scrollY < window.innerHeight * 0.6 ? slides[current].dataset.theme : 'orange';
}, { passive: true });

// ---------- Mobile menu ----------
const menuBtn = document.querySelector('.menu-btn');
const mobileMenu = document.getElementById('mobile-menu');
function setMenu(open) {
  mobileMenu.hidden = !open;
  menuBtn.setAttribute('aria-expanded', open);
  menuBtn.textContent = open ? 'close' : 'menu';
  document.body.classList.toggle('menu-open', open);
}
menuBtn.addEventListener('click', () => setMenu(mobileMenu.hidden));
mobileMenu.addEventListener('click', e => { if (e.target.tagName === 'A') setMenu(false); });

// ---------- Route map ----------
const stops = [
  { mile: '0', name: 'Start Line', at: 0.0, hours: '5am – 11am', special: 'Overnight oats & cold brew' },
  { mile: '5', name: 'Riverside', at: 0.19, hours: '6am – 2pm', special: 'Banana bites by the bag' },
  { mile: '13.1', name: 'Halfway House', at: 0.5, hours: '7am – 9pm', special: 'Split-time pasta bowl' },
  { mile: '18', name: 'Hill Street', at: 0.69, hours: '7am – 9pm', special: 'Long Run Burger' },
  { mile: '22', name: 'The Wall', at: 0.84, hours: '8am – 10pm', special: 'Emergency pizza slice' },
  { mile: '26.2', name: 'Finish Line', at: 1.0, hours: 'Open till the last runner', special: 'Recovery wrap & lemonade' },
];
const route = document.getElementById('route');
const pinsG = document.querySelector('.pins');
const card = document.querySelector('.loc-card');
const len = route.getTotalLength();
const NS = 'http://www.w3.org/2000/svg';

stops.forEach((s, i) => {
  const p = route.getPointAtLength(len * s.at);
  const g = document.createElementNS(NS, 'g');
  g.setAttribute('class', 'pin');
  g.setAttribute('tabindex', '0');
  g.setAttribute('role', 'button');
  g.setAttribute('aria-label', `Mile ${s.mile}: ${s.name}`);
  const c = document.createElementNS(NS, 'circle');
  c.setAttribute('cx', p.x); c.setAttribute('cy', p.y); c.setAttribute('r', 14);
  const t = document.createElementNS(NS, 'text');
  t.setAttribute('x', p.x); t.setAttribute('y', p.y - 26); t.setAttribute('text-anchor', 'middle');
  t.textContent = s.mile;
  g.append(c, t);
  const select = () => showStop(i);
  g.addEventListener('click', select);
  g.addEventListener('mouseenter', select);
  g.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); select(); } });
  pinsG.appendChild(g);
});

function showStop(i) {
  const s = stops[i];
  [...pinsG.children].forEach((g, k) => g.classList.toggle('is-active', k === i));
  card.innerHTML = `
    <span class="mile">Mile ${s.mile}</span>
    <h3>${s.name}</h3>
    <dl><dt>Hours</dt><dd>${s.hours}</dd><dt>Try</dt><dd>${s.special}</dd></dl>`;
}
showStop(2);

// ---------- Custom cursor ----------
const cursor = document.querySelector('.cursor');
window.addEventListener('pointermove', e => {
  cursor.classList.add('on');
  cursor.style.left = e.clientX + 'px';
  cursor.style.top = e.clientY + 'px';
});
document.querySelectorAll('a, button, .pin').forEach(el => {
  el.addEventListener('pointerenter', () => cursor.classList.add('big'));
  el.addEventListener('pointerleave', () => cursor.classList.remove('big'));
});
