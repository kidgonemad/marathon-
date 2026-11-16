"""Extract a Safari .webarchive of planetono.space into a static site folder.

Usage: python3 -I tools/extract.py <file.webarchive> <out_dir>
"""
import os, plistlib, re, sys
from urllib.parse import urlparse

src, out = sys.argv[1], sys.argv[2]
arc = plistlib.load(open(src, 'rb'))

def local_path(url):
    u = urlparse(url)
    if u.netloc.endswith('planetono.space'):
        return u.path.lstrip('/')
    if u.netloc == 'a.storyblok.com':
        return 'media/' + u.path.rsplit('/', 1)[-1]
    if u.netloc == 'fonts.gstatic.com':
        return 'vendor/fonts/' + u.path.rsplit('/', 1)[-1]
    if u.netloc == 'fonts.googleapis.com':
        return 'vendor/poppins.css'
    return None

def write(rel, data):
    p = os.path.join(out, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, 'wb').write(data)

url_map = {}
for r in arc.get('WebSubresources', []):
    url = r['WebResourceURL']
    rel = local_path(url)
    if not rel or rel.startswith('_vercel'):
        continue
    url_map[url] = '/' + rel
    data = r['WebResourceData']
    if rel.endswith('.css'):
        data = re.sub(rb'https://fonts\.gstatic\.com/s/[^)]*/([^/)]+\.woff2)', rb'/vendor/fonts/\1', data)
        data = re.sub(rb'@import\s*"https://fonts\.googleapis\.com/[^"]*"', b'@import"/vendor/poppins.css"', data)
    write(rel, data)

html = arc['WebMainResource']['WebResourceData'].decode('utf-8')
# Drop Vercel analytics
html = re.sub(r'<script[^>]*_vercel/insights[^>]*>\s*</script>', '', html)
# Longest URLs first so prefixes don't clobber
for url in sorted(url_map, key=len, reverse=True):
    html = html.replace(url, url_map[url]).replace(url.replace('&', '&amp;'), url_map[url])
# Remaining storyblok assets that weren't in the archive (og image, icons) -> local media path
html = re.sub(r'https://a\.storyblok\.com/f/\d+/[^"\s]*/([^/"\s]+)', r'/media/\1', html)
html = html.replace('https://www.planetono.space/', '/')
write('index.html', html.encode('utf-8'))
print('wrote', len(url_map) + 1, 'files to', out)
