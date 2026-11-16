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
body = re.sub(r'<p[^>]*>(?:(?!</p>).)*tubikstudio\.com(?:(?!</p>).)*</p>', '', body, flags=re.S)  # old "By tubik" line
body = body.replace('href="https://tubikstudio.com/"', 'href="https://33rdcreative.com/"')
body = body.replace('alt="Planetoño"', 'alt="' + html.escape(brand['name']) + '"')

# Logo: the Rive "loader_animation" canvas is replaced by a <div> that /brand/logo.js fills
# (see the js_swaps below for the matching bundle patch).
body = re.sub(r'<canvas class="the-preloader__logo"([^>]*?)(?: width="\d+" height="\d+")?([^>]*)></canvas>',
              r'<div class="the-preloader__logo"\1\2></div>', body)
body = re.sub(r'(<div class="decoration-bubble__inner"[^>]*>)<svg.*?</svg>', r'\1', body, flags=re.S)
# Footer credit: the 33rd//Creative logo replaces the original studio logo in the same spot
if C['footer'].get('studio_logo'):
    # 33rd//Creative credit: the old studio-logo <svg> is redrawn and animated by /brand/studio.js
    studio_logo_css = ('<style>.section-contacts__logo{display:block!important;width:max-content;margin-left:auto;'
                       'margin-right:auto;color:#f7f2e5}'
                       '.section-contacts__logo svg{width:clamp(170px,17vw,240px)!important;height:auto!important}</style>'
                       '<link rel="stylesheet" href="/brand/studio.css">'
                       '<script src="/brand/studio-data.js"></script><script src="/brand/studio.js"></script>')
else:
    studio_logo_css = '<style>.section-contacts__logo{display:none!important}</style>'
# The archived page HTML is a snapshot taken after the intro had finished, so it shows the home page
# for a moment before the app re-creates the intro screen. Keep the page hidden until the intro exists.
studio_logo_css += ('<style id="mb-boot">html:not(.mb-ready) #__nuxt,html:not(.mb-ready) #teleports{visibility:hidden}'
                    'html:not(.mb-ready) body{background:#eb3322}</style>'
                    '<script>(function(){var d=document.documentElement,done=function(){d.classList.add("mb-ready")};'
                    'var mo=new MutationObserver(function(){if(document.querySelector(".the-preloader")){done();mo.disconnect()}});'
                    'mo.observe(d,{childList:true,subtree:true});setTimeout(done,8000)})();</script>')
# palm decorations: a bit larger than the ✦ they replace so the fronds read clearly
studio_logo_css += '<style>svg.star{width:clamp(2.75rem,2.2rem + 1.7vw,4.4rem)!important;height:auto}</style>'
body = re.sub(r'<canvas class="stepper__rive"([^>]*?) width="\d+" height="\d+"([^>]*)></canvas>',
              r'<div class="stepper__rive"\1\2></div>', body)
stepper_cfg = {'steps': C['how_it_works']['steps'], 'final': C['how_it_works']['final_step']}
head += ('<link rel="stylesheet" href="/brand/logo.css"><link rel="stylesheet" href="/brand/stepper.css">'
         '<script src="/brand/logo-data.js"></script><script src="/brand/logo.js"></script>'
         '<script>window.MARATHON_STEPPER=' + json.dumps(stepper_cfg, ensure_ascii=False) + '</script>'
         '<script src="/brand/stepper.js"></script><script src="/brand/palms.js"></script>' + studio_logo_css)
H = head + body
open(html_path, 'w', encoding='utf-8').write(H)

# ---------------------------------------------------------------- 3D models (built by tools/models.py)
for f in glob.glob(rel('content/three/*.glb')):
    shutil.copy(f, os.path.join(dist, 'three', os.path.basename(f)))
if os.path.exists(rel('content/media/ambient.mp3')):     # site music (looped by the site's audio manager)
    # served under a new name (see js_swaps) so browsers can't keep playing a cached copy of the old track
    for name in ('ambient.mp3', 'marathon-music.mp3'):
        shutil.copy(rel('content/media/ambient.mp3'), os.path.join(dist, 'media', 'sounds', name))
for f in glob.glob(rel('content/lottie/*.json')):     # badges, built by tools/badges.py
    shutil.copy(f, os.path.join(dist, 'lottie', os.path.basename(f)))

# ---------------------------------------------------------------- brand files
os.makedirs(os.path.join(dist, 'brand'), exist_ok=True)
shutil.copy(rel(brand['favicon']), os.path.join(dist, 'brand', 'favicon.svg'))
if brand.get('og_image'):
    shutil.copy(rel(brand['og_image']), os.path.join(dist, 'brand', os.path.basename(brand['og_image'])))
if C['footer'].get('studio_logo'):
    shutil.copy(rel(C['footer']['studio_logo']), os.path.join(dist, 'brand', 'studio-logo.svg'))
# 33rd//Creative credit artwork: the studio's own animated logo (33rdcreative.com trace-animated.svg)
_svg = open(rel('content/brand/33rd-trace-animated.svg'), encoding='utf-8').read()
_inner = re.sub(r'<defs>.*?</defs>', '', _svg[_svg.index('>', _svg.index('<svg')) + 1:_svg.rindex('</svg>')], flags=re.S)
open(os.path.join(dist, 'brand', 'studio-data.js'), 'w', encoding='utf-8').write(
    'window.STUDIO_SVG=' + json.dumps({'viewBox': re.search(r'viewBox="([^"]+)"', _svg).group(1), 'inner': _inner.strip()}) + ';\n')
for f in ('logo.js', 'logo.css', 'stepper.js', 'stepper.css', 'studio.js', 'studio.css'):
    shutil.copy(rel(os.path.join('content', 'brand', f)), os.path.join(dist, 'brand', f))

traced = json.load(open(rel('content/brand/traced.json'), encoding='utf-8'))
flat = brand.get('logo_style') == 'flat'
logo_colors = ({'box': '#e31e26', 'letters': '#ffffff', 'burger': '#000000'} if flat else
               {'box': '#e31e26', 'letters': '#f7f2e5', 'burger': '#000000'})
logo_data = dict(traced, name=brand['name'], style='flat' if flat else 'cartoon', colors=logo_colors,
                 sound='/media/sounds/hover.mp3')
open(os.path.join(dist, 'brand', 'logo-data.js'), 'w', encoding='utf-8').write(
    'window.MARATHON_LOGO_DATA=' + json.dumps(logo_data, ensure_ascii=False) + ';\n')

# Static logo (used by the header's TheLogo image) built from the same traced paths
W, Hh = traced['box']; bb = traced['burger']['bbox']


def static_shape(d, fill, stroke, shadow, outline='#000'):
    if flat:
        return f'<path d="{d}" fill="{fill}"/>'
    return (f'<path d="{d}" fill="#000" stroke="#000" stroke-width="{stroke}" stroke-linejoin="round" transform="translate(0 {shadow})"/>'
            f'<path d="{d}" fill="{fill}" stroke="{outline}" stroke-width="{stroke}" stroke-linejoin="round" paint-order="stroke"/>')


svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="-40 -40 {W + 80} {bb[3] + 80}">'
       + static_shape(f'M0 0H{W}V{Hh}H0Z', logo_colors['box'], 22, 16)
       + ''.join(static_shape(l['d'], logo_colors['letters'], 14, 10) for l in traced['letters'])
       + f'<path d="{traced["burger"]["d"]}" fill="{logo_colors["burger"]}"/>' + '</svg>')
logo_out = os.path.join(dist, 'images', 'logo.svg')
if brand.get('logo_image'):
    shutil.copy(rel(brand['logo_image']), logo_out)
else:
    open(logo_out, 'w', encoding='utf-8').write(svg)

# ---------------------------------------------------------------- Rive animation labels
# The "Email copied" toast is a text run inside the Rive file. Each is stored as property 0x8c02 + a one-byte length + UTF-8 text.
RIVE_TEXTS = [('Email copied', C['ui'].get('email_copied', 'Email copied'))]
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

# ---------------------------------------------------------------- sparkles -> palm tree
# The ✦ decoration ("Star" component) is a black shadow path + cream outlined path in a 46x51 box.
# Swap both for the Marathon palm, keeping the same shadow offset and outline.
# Both trees from the icon are used: decorations alternate between the right (big) and left (small) one.
palm = traced['palm']


def palm_path(dx, dy, tree=None):
    tree = tree or palm
    k = 44.0 / tree['h']
    ox = (46 - tree['w'] * k) / 2 - 1.5 + dx
    def fix(m):
        x = float(m.group(1)) * k + ox
        y = float(m.group(2)) * k + 2 + dy
        return f'{x:.2f} {y:.2f}'
    return re.sub(r'(-?\d+(?:\.\d+)?) (-?\d+(?:\.\d+)?)', fix, tree['d'])


entry_js = os.path.join(dist, '_nuxt', 'CJbJqNFW.js')
ejs = open(entry_js, encoding='utf-8').read()
star_shadow = re.search(r'createBaseVNode\("path",\{d:"(M21\.8002[^"]*)"', ejs).group(1)
star_main = re.search(r'createBaseVNode\("path",\{d:"(M18\.2466[^"]*)"', ejs).group(1)
palm_shadow, palm_main = palm_path(0.9, 1.2), palm_path(0, 0)
left_shadow, left_main = palm_path(0.9, 1.2, traced['palm_left']), palm_path(0, 0, traced['palm_left'])
# every other decoration shows the left tree (set in the browser by /brand/palms.js)
open(os.path.join(dist, 'brand', 'palms.js'), 'w', encoding='utf-8').write(
    '(function(){var L=' + json.dumps([left_shadow, left_main]) + ';var n=0;'
    'function run(){document.querySelectorAll("svg.star:not([data-palm])").forEach(function(s){'
    's.setAttribute("data-palm",n%2?"left":"right");if(n++%2){var p=s.querySelectorAll("path");'
    'if(p.length>1){p[0].setAttribute("d",L[0]);p[1].setAttribute("d",L[1]);}}});}'
    'new MutationObserver(run).observe(document.documentElement,{childList:true,subtree:true});'
    'document.addEventListener("DOMContentLoaded",run);})();\n')
for f in (entry_js, html_path):
    s = open(f, encoding='utf-8').read()
    s = s.replace(star_shadow, palm_shadow).replace(star_main, palm_main)
    # thinner outline: the star's 3px stroke swamps the palm's thin fronds
    s = s.replace(palm_main + '",fill:"#F7F2E5",stroke:"black","stroke-width":"3"',
                  palm_main + '",fill:"#F7F2E5",stroke:"black","stroke-width":"0.4"')
    s = re.sub('(' + re.escape(palm_main) + r'" fill="#F7F2E5" stroke="black" stroke-width=")3(")', r'\g<1>0.4\2', s)
    open(f, 'w', encoding='utf-8').write(s)

# ---------------------------------------------------------------- scripts and colours
ui = C['ui']
js_swaps = [
    ('"Planetoño"', json.dumps(brand['name'], ensure_ascii=False)),
    ('"Tubik Studio"', json.dumps(brand['author'], ensure_ascii=False)),
    ('"https://planetono.space/"', json.dumps(brand['site_url'])),
    ('createTextVNode("StArt"', 'createTextVNode(' + json.dumps(ui['start_button'], ensure_ascii=False)),
    ('"Immersive sound ahead. Use headphones for best effect"', json.dumps(ui['sound_message'], ensure_ascii=False)),
    ('text:"Contact"', 'text:' + json.dumps(ui['contact_label'], ensure_ascii=False)),
    # Replace the Rive logo with the Marathon Burger logo component (/brand/logo.js)
    ('createBaseVNode("canvas",{class:"the-preloader__logo",ref:"logo",onClick:y},null,512)',
     'createBaseVNode("div",{class:"the-preloader__logo",ref:"logo",onClick:y},null,512)'),
    ('E=new riveExports.Rive({canvas:o.value,riveFile:e.$riveFile,artboard:"loader_animation",stateMachines:"Loader02",'
     'autoplay:!0,onLoad:()=>{E.resizeDrawingSurfaceToCanvas(),d=E.stateMachineInputs("Loader02").find(T=>T.name==="CheckLoad")}})',
     'E=window.MarathonLogo.mount(o.value),d=E.loadInput'),
    ('"Click | Planetoño logo"', '"Click | Logo"'),
    ('ambient:`${BASE_URL}/ambient.mp3`', 'ambient:`${BASE_URL}/marathon-music.mp3`'),   # new site music
    # footer credit links to 33rd Creative (the logo itself is drawn/animated by /brand/studio.js)
    ('section-contacts__logo",href:"https://tubikstudio.com/"', 'section-contacts__logo",href:"https://33rdcreative.com/"'),
    # New Marathon Burger 3D parts (MB_*) get the same toon shading + outlines as the original food
    ('get(e){const t=this.params[e];return{...this.defaultParams,...t||{}}}',
     'get(e){const t=this.params[e]||(e&&e.startsWith("MB_")?{toonShadingEnabled:!0,geometryEnabled:!0,'
     'conditionalGeometryEnabled:!0}:void 0);return{...this.defaultParams,...t||{}}}'),
    ('function gi(a){const e=a.material.color||0', 'function gi(a){if(!a.material)return;const e=a.material.color||0'),
    # The 3D scenes waited for a hard-coded number of outlined meshes (100 / 30); count the real ones
    ('_addConditionalGeometry(e,t){e.isMesh&&(Ie.generate(e.geometry,t)',
     '_addConditionalGeometry(e,t){e.isMesh&&(this.conditionalGeometryCalls=(this.conditionalGeometryCalls||0)+1,Ie.generate(e.geometry,t)'),
    ('this.conditionalGeometryLoaded>=this.conditionalGeometryCount&&',
     'this.conditionalGeometryLoaded>=this.conditionalGeometryCalls&&'),
    # How-it-works stepper: Rive artboard -> /brand/stepper.js (3 steps + "Claim your meal")
    ('const e=new R.Rive({canvas:d.value,riveFile:s.$riveFile,artboard:"stepper_animation_reworked",stateMachines:"State Machine",'
     'autoplay:!0,autoBind:!0,onLoad:()=>{let r=e.viewModelInstance;r.boolean("isHovered").on(n=>{v.value=n}),f=r.number("id"),'
     'f.on(n=>{c.value=n}),e.resizeDrawingSurfaceToCanvas(window.devicePixelRatio+1)}});window.addEventListener("resize",()=>'
     '{e.resizeDrawingSurfaceToCanvas(window.devicePixelRatio+1)})',
     'f=window.MarathonStepper.mount(d.value,{onHover:n=>{v.value=n},onChange:n=>{c.value=n}}).id'),
    ('_("canvas",{class:D(["stepper__rive",{"is-hovered":I(v)}]),ref:"canvas"},null,2)',
     '_("div",{class:D(["stepper__rive",{"is-hovered":I(v)}]),ref:"canvas"},null,2)'),
]
REQUIRED_JS = [a for a, _ in js_swaps[-9:]]
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
    if path.endswith('.js'):
        REQUIRED_JS = [a for a in REQUIRED_JS if a not in s]
if REQUIRED_JS:
    sys.exit('bundle patch target not found: ' + REQUIRED_JS[0][:80])

# ---------------------------------------------------------------- menu page (/menu/)
M = json.load(open(rel('content/menu.json'), encoding='utf-8'))
esc = lambda s: html.escape(s, quote=True)
slug = lambda s: re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')
secs, chips = [], []
for sec in M['sections']:
    sid = slug(sec['title'])
    chips.append(f'<a class="chip" href="#{sid}">{esc(sec["title"].title())}</a>')
    items = []
    for it in sec['items']:
        veg = '<span class="veg">VEG</span>' if it.get('veg') else ''
        desc = f'<p class="desc">{esc(it["desc"])}</p>' if it.get('desc') else ''
        items.append(f'<li><div class="row"><span class="name">{esc(it["name"])}{veg}</span>'
                     f'<span class="price">{esc(it["price"])}</span></div>{desc}</li>')
    note = f'<p class="note">{esc(sec["note"])}</p>' if sec.get('note') else ''
    secs.append(f'<section id="{sid}"><h2>{esc(sec["title"])}</h2>{note}<ul>{"".join(items)}</ul></section>')
palm_svg = (f'<svg viewBox="0 0 46 51" xmlns="http://www.w3.org/2000/svg"><path d="{palm_shadow}" fill="#000"/>'
            f'<path d="{palm_main}" fill="#F7F2E5" stroke="#000" stroke-width="0.4"/></svg>')
left_svg = (f'<svg viewBox="0 0 46 51" xmlns="http://www.w3.org/2000/svg"><path d="{left_shadow}" fill="#000"/>'
            f'<path d="{left_main}" fill="#F7F2E5" stroke="#000" stroke-width="0.4"/></svg>')
palms = ''.join(f'<div class="palm" style="left:{x}%;top:{y}%;animation-delay:{d}s">{left_svg if i % 2 else palm_svg}</div>'
                for i, (x, y, d) in enumerate( ((10, 12, 0), (86, 18, .8), (20, 46, 1.6), (76, 44, 2.2))))
# The menu page uses the home page's own header (same markup, styles and Rive nav), driven by
# /brand/menu-header.js, so the desktop nav and the phone MENU dropdown are identical.
home = open(html_path, encoding='utf-8').read()
home_head = home[:home.index('</head>')]
header_styles = re.sub(r'<style id="mb-boot">.*?</style>', '',
                       ''.join(re.findall(r'<style[^>]*>.*?</style>', home_head, flags=re.S)), flags=re.S)
hi = home.index('<header class="the-header"')
hdr = home[hi:home.index('</header>', hi) + len('</header>')]


def nav_items(scope):
    out = []
    for n in C['nav']:
        href = '/' + n['link'] if n['link'].startswith('#') else n['link']
        out.append(f'<a class="the-nav__item" href="{esc(href)}" data-sound-hover="hover" data-sound-click="click" '
                   f'data-v-{scope}="" data-v-01873299=""><span class="the-nav__item__text" data-v-01873299="">'
                   f'{esc(n["text"])}</span><canvas class="the-nav__item__rive" data-v-01873299=""></canvas></a>')
    return ''.join(out)


# nav links are rebuilt from the content (the saved page snapshot only had the app's first render)
hdr = re.sub(r'(<nav class="the-nav the-header-desktop__nav --start"[^>]*>).*?(</nav>)',
             lambda m: m.group(1) + nav_items('d87ca48c') + m.group(2), hdr, count=1, flags=re.S)
mi = hdr.index('<div class="the-header-mobile__nav"')
mob = hdr[mi:]
mob = re.sub(r'<a class="the-nav__item" href=.*?</a>', '', mob, flags=re.S)
mob = re.sub(r'(<nav class="the-nav"[^>]*>)', lambda m: m.group(1) + nav_items('3e1a866d'), mob, count=1)
hdr = hdr[:mi] + mob
hdr = re.sub(r'<div class="the-preloader__logo"[^>]*></div>', '', hdr)     # old logo element from the snapshot
logo_div = '<div class="the-preloader__logo mb-hdr-logo" data-v-2fa055d1=""></div>'
hdr = re.sub(r'(<span class="the-header-(?:desktop|mobile)__logo__inner"[^>]*>.*?)(</span>)',
             lambda m: m.group(1) + logo_div + m.group(2), hdr, flags=re.S)
hdr = hdr.replace('href="#hero"', 'href="/"')
shutil.copy(rel('content/brand/menu-header.js'), os.path.join(dist, 'brand', 'menu-header.js'))
os.makedirs(os.path.join(dist, 'vendor', 'rive'), exist_ok=True)
shutil.copy(rel('content/brand/rive.js'), os.path.join(dist, 'vendor', 'rive', 'rive.js'))   # @rive-app/canvas 2.32.2

page = open(rel('content/brand/menu.html'), encoding='utf-8').read()
for k, v in {'NAME': esc(brand['name']), 'EMAIL': esc(brand['email']), 'SECTIONS': '\n'.join(secs),
             'CHIPS': ''.join(chips), 'PALMS': palms, 'FOOTNOTE': esc(M.get('footnote', '')),
             'HEADER': hdr, 'HEADER_STYLES': header_styles}.items():
    page = page.replace('{{' + k + '}}', v)
os.makedirs(os.path.join(dist, 'menu'), exist_ok=True)
open(os.path.join(dist, 'menu', 'index.html'), 'w', encoding='utf-8').write(page)

print(f'built {os.path.relpath(dist, ROOT)}/ for "{brand["name"]}": {len(text_swaps)} text changes')
