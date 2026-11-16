// Load the extracted site, interact with it, and download from the live site any
// same-origin file the page requests that is missing locally. Repeats until none are missing.
// Usage: node tools/fetch_missing.js <site_dir> <local_base_url>
const { chromium } = require('playwright');
const { execFileSync } = require('child_process');
const fs = require('fs'), path = require('path');
const [,, siteDir, base] = process.argv;
const LIVE = 'https://www.planetono.space';
const notFound = new Set();

(async () => {
  const b = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  for (let round = 1; round <= 6; round++) {
    const fetched = [];
    for (const vp of [{ width: 1440, height: 900 }, { width: 390, height: 844 }]) {
      const p = await b.newPage({ viewport: vp });
      await p.route(u => u.origin === new URL(base).origin, async route => {
        const rel = decodeURIComponent(new URL(route.request().url()).pathname);
        const file = path.join(siteDir, rel.endsWith('/') ? rel + 'index.html' : rel);
        if (!fs.existsSync(file) && !notFound.has(rel)) {
          try {
            const data = execFileSync('curl', ['-sSfL', LIVE + rel], { maxBuffer: 200 * 1024 * 1024 });
            fs.mkdirSync(path.dirname(file), { recursive: true });
            fs.writeFileSync(file, data);
            fetched.push(rel);
          } catch { notFound.add(rel); console.log('  not on live site:', rel); }
        }
        await route.continue();
      });
      await p.goto(base, { waitUntil: 'networkidle' }).catch(() => {});
      for (let i = 0; i < 4; i++) {
        await p.keyboard.press('ArrowRight');
        await p.mouse.click(vp.width - 60, vp.height / 2).catch(() => {});
        await p.waitForTimeout(800);
      }
      for (let y = 0; y < 8000; y += 500) { await p.mouse.wheel(0, 500); await p.waitForTimeout(300); }
      for (const m of await p.$$('[class*="marker"]')) {
        await m.hover({ force: true, timeout: 1000 }).catch(() => {});
        await m.click({ force: true, timeout: 1000 }).catch(() => {});
      }
      await p.waitForTimeout(3000);
      await p.close();
    }
    console.log(`round ${round}: fetched ${fetched.length}`, fetched);
    if (!fetched.length) break;
  }
  await b.close();
})();
