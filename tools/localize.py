"""Download the on-demand assets the template bundle loads (3D models, textures, Rive file,
sounds) and point the JS at local copies so the site runs without external hosts.

Usage: python3 -I tools/localize.py <site_dir>
"""
import glob, os, subprocess, sys

site = sys.argv[1]
LIVE = 'https://www.planetono.space'
BLOB = 'https://ljd0bcgtaoiynl4q.public.blob.vercel-storage.com'

SAME_ORIGIN = [
    '/three/scroll_camera.glb', '/three/scroll_camera_mobile.glb', '/three/scroll_model.glb',
    '/three/slider_camera.glb', '/three/slider_model.glb',
    '/three/textures/sesame.png', '/three/textures/threeTone.jpg',
    '/_nuxt/error-500.CHLIJhcO.css',
    '/_nuxt/conditional.worker-CjhnXHD9.js',
    '/three/cache/slider_geometry_cache.json', '/three/cache/scroll_geometry_cache.json',
    '/lottie/bubble01.json', '/lottie/bubble02.json', '/lottie/bubble03.json',
    '/lottie/northern.json', '/lottie/southern.json',
]
SOUNDS = ['click',   # 'ambient' (the old music) is replaced by content/media/marathon-music.mp3
           'hover', 'logo', 'swoosh', 'map-hover', 'map-click', 'map-leave', 'empty-click']
BLOB_FILES = {'/rive/rive.riv': '/media/rive.riv'}
BLOB_FILES.update({f'/sounds/{s}.mp3': f'/media/sounds/{s}.mp3' for s in SOUNDS})


def fetch(url, rel):
    path = os.path.join(site, rel.lstrip('/'))
    if os.path.exists(path):
        return
    data = subprocess.run(['curl', '-sSfL', url], capture_output=True, check=True).stdout
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, 'wb').write(data)
    print(f'fetched {rel} ({len(data)} bytes)')


for rel in SAME_ORIGIN:
    fetch(LIVE + rel, rel)
for remote, local in BLOB_FILES.items():
    fetch(BLOB + remote, local)

# Rewrite remote URLs in every JS chunk
for js in glob.glob(os.path.join(site, '_nuxt', '*.js')):
    s = open(js, encoding='utf-8').read()
    guard = 'if(t.value!==void 0)return;'
    s0 = s.replace(guard, '')
    new = (s0.replace(BLOB + '/rive/rive.riv', '/media/rive.riv')
             .replace(f'BASE_URL="{BLOB}/sounds"', 'BASE_URL="/media/sounds"')
             .replace('"https://unpkg.com/".concat(a.name,"@").concat(a.version,"/rive.wasm")', '"/vendor/rive/rive.wasm"')
             .replace('"https://cdn.jsdelivr.net/npm/".concat(a.name,"@").concat(a.version,"/rive_fallback.wasm")',
                      '"/vendor/rive/rive_fallback.wasm"')
             # Use the story embedded in the page payload instead of re-fetching it from Storyblok
             .replace('function useAsyncStoryPage(t,e,n=[],r={},i=!0){',
                      'function useAsyncStoryPage(t,e,n=[],r={},i=!0){' + guard))
    if new != s:
        open(js, 'w', encoding='utf-8').write(new)
        print('patched', os.path.relpath(js, site))
