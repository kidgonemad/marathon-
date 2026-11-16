"""Re-point a built site at a sub-path, e.g. GitHub Pages project sites (https://user.github.io/repo/).

Usage: python3 -I tools/rebase.py <dist_dir> </repo/>

The site uses root-relative URLs ("/_nuxt/...", "/three/...", "/media/..."). This rewrites them to
"/repo/..." in every HTML/CSS/JS/JSON file and sets Nuxt's app.baseURL so the router matches.
"""
import glob, os, re, sys

dist, base = sys.argv[1], sys.argv[2]
if not (base.startswith('/') and base.endswith('/')):
    sys.exit('base must look like /repo/')
DIRS = '_nuxt|three|lottie|media|draco|images|vendor|fonts|brand|menu'
# a root-relative URL to one of the site's folders, right after a quote, backtick, ( or =
ASSET = re.compile(r'''(["'`(=])/(%s)/''' % DIRS)

for path in glob.glob(os.path.join(dist, '**', '*'), recursive=True):
    if not path.endswith(('.html', '.css', '.js', '.json')):
        continue
    s = open(path, encoding='utf-8').read()
    new = ASSET.sub(lambda m: m.group(1) + base + m.group(2) + '/', s)
    # Nuxt runtime config: the router base, while buildAssetsDir stays relative to it
    # image paths go through Nuxt's publicAssetsURL (or a minified alias of it), which adds the base itself
    new = re.sub(r'([A-Za-z_$][\w$]*)\("' + re.escape(base) + r'images/', r'\1("/images/', new)
    new = new.replace('app:{baseURL:"/",', f'app:{{baseURL:"{base}",')
    new = new.replace(f'buildAssetsDir:"{base}_nuxt/"', 'buildAssetsDir:"/_nuxt/"')
    if path.endswith('.html'):
        # links back to the home page from the menu page, and the favicon/og URLs
        new = re.sub(r'href="/"', f'href="{base}"', new)
        new = re.sub(r'href="/#', f'href="{base}#', new)
    if new != s:
        open(path, 'w', encoding='utf-8').write(new)
print('rebased', dist, 'to', base)
