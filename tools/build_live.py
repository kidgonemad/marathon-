"""Make the GitHub Pages copy of the site.

Pages is set to "Deploy from a branch" (repo root), so the live site is served from the `live/` folder:
  https://kidgonemad.github.io/marathon-/live/   (the root index.html redirects there)
Usage: python3 -I tools/build_live.py   (run after tools/apply.py)
"""
import os, shutil, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
live = os.path.join(ROOT, 'live')
if os.path.isdir(live):
    shutil.rmtree(live)
shutil.copytree(os.path.join(ROOT, 'dist'), live)
subprocess.run([sys.executable, '-I', os.path.join(ROOT, 'tools', 'rebase.py'), live, '/marathon-/live/'], check=True)
open(os.path.join(ROOT, '.nojekyll'), 'w').close()          # serve _nuxt/ (Jekyll would skip it)
open(os.path.join(ROOT, 'index.html'), 'w').write(
    '<!doctype html><meta charset="utf-8"><title>Marathon Burger</title>'
    '<meta http-equiv="refresh" content="0; url=live/"><a href="live/">Marathon Burger</a>\n')
print('live copy ready in live/')
