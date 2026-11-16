"""Build the Marathon site: copy site/ to dist/ and apply content/marathon.json.

Usage: python3 -I tools/apply.py [content.json] [site_dir] [dist_dir]

Text lives in two places: the server-rendered HTML and the Nuxt payload
(<script id="__NUXT_DATA__">) that the page re-renders from in the browser. The payload
is what visitors end up seeing, so every edit goes there. Matching visible text in the
HTML is updated too, for search engines and the first paint.
"""
import base64, copy, glob, html, json, os, re, shutil, sys, uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import payload  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
content_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'content', 'marathon.json')
site = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, 'site')
dist = sys.argv[3] if len(sys.argv) > 3 else os.path.join(ROOT, 'dist')
C = json.load(open(content_path, encoding='utf-8'))

# ---------------------------------------------------------------- copy base site
if os.path.basename(os.path.normpath(dist)) != 'dist':
    sys.exit('refusing to overwrite a folder not named dist: ' + dist)
if os.path.isdir(dist):
    shutil.rmtree(dist)
shutil.copytree(site, dist)


def rel(p):
    return os.path.join(ROOT, p) if not os.path.isabs(p) else p


# ---------------------------------------------------------------- payload editor
class Payload:
    def __init__(self, arr):
        self.arr = arr

    def obj(self, i):
        v = self.arr[i]
        while isinstance(v, list) and v and isinstance(v[0], str) and v[0] in payload.WRAPPERS:
            i = v[1]
            v = self.arr[i]
        return i

    def get(self, i, *path):
        for k in path:
            i = self.arr[self.obj(i)][k]
        return i

    def add(self, v):
        a = self.arr
        if isinstance(v, dict):
            idx = len(a); a.append({})
            a[idx] = {k: self.add(x) for k, x in v.items()}
            return idx
        if isinstance(v, list):
            idx = len(a); a.append([])
            a[idx] = [self.add(x) for x in v]
            return idx
        a.append(v)
        return len(a) - 1

    def set(self, i, key, value):
        self.arr[self.obj(i)][key] = self.add(value)

    def read(self, i):
        return payload.resolve(self.arr, i)


html_path = os.path.join(dist, 'index.html')
H = open(html_path, encoding='utf-8').read()
P = Payload(payload.load(H))
state = P.get(0, 'state')
stories = {}
for key in P.arr[P.obj(state)]:
    story = P.get(state, key)
    comp = P.read(P.get(story, 'content', 'component'))
    stories[comp] = story
glob_c = P.get(stories['global-page'], 'content')
home_c = P.get(stories['home-page'], 'content')

text_swaps = []  # (old, new) visible strings, mirrored into the server HTML


def swap(old, new):
    if old != new:
        text_swaps.append((old, new))


def runs_of(doc):
    out = []
    for para in doc.get('content', []):
        out.extend(r.get('text', '') for r in para.get('content', []) or [])
    return out


def richtext(lines):
    paras = []
    for line in lines:
        pieces = line if isinstance(line, list) else [line]
        runs = []
        for p in pieces:
            if isinstance(p, dict):
                runs.append({'text': p['text'], 'type': 'text', 'marks': [
                    {'type': 'link', 'attrs': {'href': p['link'], 'uuid': None, 'anchor': None,
                                               'custom': {'rel': 'noopener noreferrer'},
                                               'target': '_blank', 'linktype': 'url'}},
                    {'type': 'underline'}]})
            elif p:
                runs.append({'text': p, 'type': 'text'})
        paras.append({'type': 'paragraph', 'attrs': {'textAlign': None}, 'content': runs})
    return {'type': 'doc', 'content': paras}


def set_rich(container, key, lines):
    old = runs_of(P.read(P.get(container, key)))
    new = runs_of(richtext(lines))
    for o, n in zip(old, new):
        swap(o, n)
    P.set(container, key, richtext(lines))


def set_text(container, key, value):
    swap(P.read(P.get(container, key)), value)
    P.set(container, key, value)


def new_uid():
    return str(uuid.uuid4())


brand = C['brand']

# ---- global: email, nav, favicons
email = P.read(P.get(glob_c, 'email'))
email.update(url=brand['email'], email=brand['email'], cached_url=brand['email'])
P.set(glob_c, 'email', email)

nav_tpl = P.read(P.get(glob_c, 'nav_left'))
nav = []
for i, item in enumerate(C['nav']):
    n = copy.deepcopy(nav_tpl[min(i, len(nav_tpl) - 1)])
    if i >= len(nav_tpl):
        n['_uid'] = new_uid()
    swap(n['text'], item['text'])
    n['text'] = item['text']
    n['link'].update(url=item['link'], cached_url=item['link'])
    nav.append(n)
P.set(glob_c, 'nav_left', nav)

fav = P.read(P.get(glob_c, 'favicons'))
for f in fav:
    for k, v in f.items():
        if isinstance(v, dict) and 'filename' in v:
            v['filename'] = '/brand/favicon.svg'
P.set(glob_c, 'favicons', fav)

# ---- SEO
seo = P.get(home_c, 'seo', 0)
main = P.read(P.get(seo, 'main'))
main.update(title=brand['name'], description=brand['description'])
P.set(seo, 'main', main)
if brand.get('og_image'):
    og = P.read(P.get(seo, 'og_image'))
    og['filename'] = '/brand/' + os.path.basename(brand['og_image'])
    P.set(seo, 'og_image', og)

# ---- sections
sections = {P.read(P.get(home_c, 'sections', i, 'component')): P.get(home_c, 'sections', i)
            for i in range(len(P.arr[P.obj(P.get(home_c, 'sections'))]))}

hero = sections['section-hero']
slides_i = P.get(hero, 'slider')
n_slides = len(P.arr[P.obj(slides_i)])
if len(C['hero_items']) != n_slides:
    sys.exit(f'hero_items must have exactly {n_slides} entries (one per 3D tray), got {len(C["hero_items"])}')
for i, item in enumerate(C['hero_items']):
    s = P.get(slides_i, i)
    set_rich(s, 'title', item['headline'])
    set_text(s, 'desc_1', item['item'])
    set_text(s, 'desc_2', item['mascot'])

how = sections['section-process']
set_rich(how, 'title', C['how_it_works']['title'])
set_text(how, 'caption', C['how_it_works']['caption'])
set_text(how, 'timeline_title', C['how_it_works']['label'])

loc = sections['section-location']
set_rich(loc, 'title', C['locations']['title'])
set_text(loc, 'caption', C['locations']['caption'])
for side, key in (('north_map', 'markers_north'), ('south_map', 'markers_south')):
    tpl_list = P.read(P.get(loc, key))
    tpl = tpl_list[0]
    markers = []
    for i, m in enumerate(C['locations'][side]):
        base = copy.deepcopy(tpl_list[i] if i < len(tpl_list) else tpl)
        if i >= len(tpl_list):
            base['_uid'] = new_uid()
        swap(base['title'], m['name'])
        base.update(title=m['name'], position_x=str(m['x']), position_y=str(m['y']))
        if m.get('direction'):
            base['direction'] = m['direction']
        else:
            base.pop('direction', None)
        rows = []
        for label, value in m['details']:
            rows.append({'_uid': new_uid(), 'component': '_table_row', 'body': [
                {'_uid': new_uid(), 'value': label, 'component': '_table_col'},
                {'_uid': new_uid(), 'value': value, 'component': '_table_col'}]})
        base['data']['tbody'] = rows
        markers.append(base)
    P.set(loc, key, markers)

foot = sections['section-contacts']
set_rich(foot, 'title', C['footer']['headline'])
set_rich(foot, 'footer_caption_left', C['footer']['left_note'])
set_rich(foot, 'footer_caption_right', C['footer']['right_note'])

H = payload.dump(H, P.arr)

# ---------------------------------------------------------------- server HTML
head_end = H.index('</head>')
head, body = H[:head_end], H[head_end:]
ORIG_DESC = "We tried making this real. NASA said No. So for now, it's just a delicious concept by Tubik."
head = (head.replace(html.escape(ORIG_DESC), html.escape(brand['description']))
            .replace(ORIG_DESC, html.escape(brand['description']))
            .replace('Planetoño', html.escape(brand['name']))
            .replace('Tubik Studio', html.escape(brand['author']))
            .replace('https://planetono.space/', html.escape(brand['site_url'])))
head = re.sub(r'(<link rel="(?:shortcut )?icon"[^>]*href=")[^"]*(")', r'\1/brand/favicon.svg\2', head)
head = re.sub(r'(<link rel="apple-touch-icon"[^>]*href=")[^"]*(")', r'\1/brand/favicon.svg\2', head)
if brand.get('og_image'):
    head = re.sub(r'/media/og\.png(\?cv=\d+)?', '/brand/' + os.path.basename(brand['og_image']), head)

for old, new in text_swaps:
    o, n = html.escape(old, quote=False), html.escape(new, quote=False)
    body = body.replace('>' + o + '<', '>' + n + '<')
body = body.replace('mail@tubikstudio.com', html.escape(brand['email']))
body = body.replace('alt="Planetoño"', 'alt="' + html.escape(brand['name']) + '"')

# Logo: cover the animated Rive "Planetoño" logo with the Marathon logo
studio_logo_css = '' if C['footer'].get('show_studio_logo', True) else '.section-contacts__logo{display:none!important}'
brand_css = f'''<style id="marathon-brand">
.the-preloader__logo{{visibility:hidden!important}}
:has(> canvas.the-preloader__logo){{position:relative}}
:has(> canvas.the-preloader__logo)::after{{content:"";position:absolute;left:50%;top:50%;
  width:min(300px,100%);aspect-ratio:600/170;transform:translate(-50%,-50%);
  background:url(/images/logo.svg) center/contain no-repeat;pointer-events:none}}
{studio_logo_css}
</style>'''
head = head + brand_css
H = head + body
open(html_path, 'w', encoding='utf-8').write(H)

# ---------------------------------------------------------------- brand files
os.makedirs(os.path.join(dist, 'brand'), exist_ok=True)
shutil.copy(rel(brand['favicon']), os.path.join(dist, 'brand', 'favicon.svg'))
if brand.get('og_image'):
    shutil.copy(rel(brand['og_image']), os.path.join(dist, 'brand', os.path.basename(brand['og_image'])))

logo_out = os.path.join(dist, 'images', 'logo.svg')
if brand.get('logo_image'):
    shutil.copy(rel(brand['logo_image']), logo_out)
else:
    font = base64.b64encode(open(os.path.join(site, 'fonts', 'passata.woff2'), 'rb').read()).decode()
    word = html.escape(brand.get('logo_text') or brand['name'].upper())
    t = ('x="300" y="122" text-anchor="middle" textLength="560" lengthAdjust="spacingAndGlyphs" '
         'font-family="Passata" font-weight="700" font-size="128"')
    open(logo_out, 'w', encoding='utf-8').write(f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 170" width="600" height="170">
<defs><style>@font-face{{font-family:Passata;font-weight:700;src:url(data:font/woff2;base64,{font}) format("woff2")}}</style></defs>
<text {t} transform="translate(0 9)" fill="#000" stroke="#000" stroke-width="14" stroke-linejoin="round">{word}</text>
<text {t} fill="#f7f2e5" stroke="#000" stroke-width="10" stroke-linejoin="round" paint-order="stroke">{word}</text>
</svg>
''')

# ---------------------------------------------------------------- Rive animation labels
# The How-it-works step buttons and the "Email copied" toast are text runs inside the Rive
# file. Each is stored as property 0x8c02 + a one-byte length + UTF-8 text.
RIVE_TEXTS = list(zip(['Choose your meal', 'Pick a snack', 'Size your fries', 'Claim your toy'],
                      C['how_it_works']['steps']))
RIVE_TEXTS.append(('Email copied', C['ui'].get('email_copied', 'Email copied')))
riv_path = os.path.join(dist, 'media', 'rive.riv')
riv = open(riv_path, 'rb').read()
for old, new in RIVE_TEXTS:
    o, n = old.encode(), new.encode()
    if len(n) > 127:
        sys.exit(f'Rive label too long (max 127 bytes): {new!r}')
    tag = bytes([0x8c, 0x02])
    if riv.count(tag + bytes([len(o)]) + o) == 0:
        sys.exit(f'Rive label not found: {old!r}')
    riv = riv.replace(tag + bytes([len(o)]) + o, tag + bytes([len(n)]) + n)
open(riv_path, 'wb').write(riv)

# ---------------------------------------------------------------- scripts and colours
ui = C['ui']
js_swaps = [
    ('"Planetoño"', json.dumps(brand['name'], ensure_ascii=False)),
    ('"Tubik Studio"', json.dumps(brand['author'], ensure_ascii=False)),
    ('"https://planetono.space/"', json.dumps(brand['site_url'])),
    ('createTextVNode("StArt"', 'createTextVNode(' + json.dumps(ui['start_button'], ensure_ascii=False)),
    ('"Immersive sound ahead. Use headphones for best effect"', json.dumps(ui['sound_message'], ensure_ascii=False)),
    ('text:"Contact"', 'text:' + json.dumps(ui['contact_label'], ensure_ascii=False)),
]
colors = {k.lower(): v for k, v in C['colors'].items() if k.startswith('#') and k.lower() != v.lower()}
color_re = re.compile('|'.join(re.escape(k) for k in colors) + r'(?![0-9a-fA-F])', re.I) if colors else None

for path in glob.glob(os.path.join(dist, '**', '*'), recursive=True):
    if not path.endswith(('.js', '.css', '.html')):
        continue
    s = open(path, encoding='utf-8').read()
    new = s
    if path.endswith('.js'):
        for a, b in js_swaps:
            new = new.replace(a, b)
    if color_re:
        new = color_re.sub(lambda m: colors[m.group(0).lower()], new)
    if new != s:
        open(path, 'w', encoding='utf-8').write(new)

print(f'built {os.path.relpath(dist, ROOT)}/ for "{brand["name"]}": {len(text_swaps)} text changes')
