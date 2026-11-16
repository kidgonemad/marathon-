"""Make the GitHub Pages copy of the site.

Pages is set to "Deploy from a branch" (repo root), so the live site is served from the `live/` folder:
  https://kidgonemad.github.io/marathon-/live/   (the root index.html redirects there)
Usage: python3 -I tools/build_live.py   (run after tools/apply.py)
"""
import os, re, shutil, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
live = os.path.join(ROOT, 'live')
if os.path.isdir(live):
    shutil.rmtree(live)
shutil.copytree(os.path.join(ROOT, 'dist'), live)
subprocess.run([sys.executable, '-I', os.path.join(ROOT, 'tools', 'rebase.py'), live, '/marathon-/live/'], check=True)
open(os.path.join(ROOT, '.nojekyll'), 'w').close()          # serve _nuxt/ (Jekyll would skip it)
# link previews (iMessage, WhatsApp, ...) need absolute image URLs
LIVE_URL = 'https://kidgonemad.github.io/marathon-/live/'
for page in (os.path.join(live, 'index.html'), os.path.join(live, 'menu', 'index.html')):
    s = open(page, encoding='utf-8').read()
    s = re.sub(r'(<meta (?:property|name)="(?:og:image|og:image:secure_url|twitter:image)" content=")[^"]*(")',
               r'\g<1>' + LIVE_URL + r'brand/og.png\2', s)
    s = re.sub(r'(<meta property="og:url" content=")[^"]*(")', r'\g<1>' + LIVE_URL + r'\2', s)
    s = s.replace('<meta name="twitter:card" content="summary">', '<meta name="twitter:card" content="summary_large_image">')
    if 'og:image' not in s:                    # the menu page has no share tags of its own
        s = s.replace('</head>', '<meta property="og:title" content="Menu · Marathon Burger">'
                      f'<meta property="og:image" content="{LIVE_URL}brand/og.png">'
                      '<link rel="apple-touch-icon" sizes="180x180" href="/marathon-/live/brand/apple-touch-icon.png"></head>', 1)
    open(page, 'w', encoding='utf-8').write(s)
open(os.path.join(ROOT, 'index.html'), 'w').write(
    '<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Marathon Burger</title>'
    '<meta name="description" content="Double wagyu smash burgers, hot wings and breakfast.">'
    '<meta property="og:type" content="website"><meta property="og:title" content="Marathon Burger">'
    '<meta property="og:description" content="Double wagyu smash burgers, hot wings and breakfast.">'
    f'<meta property="og:url" content="{LIVE_URL}"><meta property="og:image" content="{LIVE_URL}brand/og.png">'
    '<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">'
    '<meta name="twitter:card" content="summary_large_image">'
    f'<meta name="twitter:image" content="{LIVE_URL}brand/og.png">'
    '<link rel="apple-touch-icon" sizes="180x180" href="live/brand/apple-touch-icon.png">'
    '<link rel="icon" type="image/svg+xml" href="live/brand/favicon.svg">'
    '<meta http-equiv="refresh" content="0; url=live/"></head><body><a href="live/">Marathon Burger</a></body></html>\n')
print('live copy ready in live/')
