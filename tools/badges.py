"""Rewrite the text on the hero badges (Lottie bubble01-03.json) using the site's Futura Passata font.

Usage: python tools/badges.py <site_dir> <content.json> <out_dir>
Needs: fonttools brotli

Each badge has a text layer with two groups: Group 1 = small top line, Group 2 = big two-line title.
Their path shapes are replaced with outlines of the new text, centred and fitted to the same box,
so the badge's own fill colour, pop animation and bubble shape stay exactly as they were.
"""
import copy, json, os, sys
from fontTools.ttLib import TTFont
from fontTools.pens.basePen import BasePen

site, content_path, out = sys.argv[1:4]
badges = json.load(open(content_path, encoding='utf-8'))['badges']
font = TTFont(os.path.join(site, 'fonts', 'passata.woff2'))
gs = font.getGlyphSet()
cmap = font.getBestCmap()
upm = font['head'].unitsPerEm


class LottiePen(BasePen):
    """Collects glyph contours as cubic Bézier contours: [[(p0), (c1, c2, p1), ...], ...]."""
    def __init__(self, glyphset, dx):
        super().__init__(glyphset)
        self.dx, self.contours, self.cur = dx, [], None

    def _moveTo(self, p):
        self.cur = [('M', self._t(p))]

    def _lineTo(self, p):
        self.cur.append(('L', self._t(p)))

    def _curveToOne(self, c1, c2, p):
        self.cur.append(('C', self._t(c1), self._t(c2), self._t(p)))

    def _closePath(self):
        self.contours.append(self.cur); self.cur = None

    _endPath = _closePath

    def _t(self, p):
        return (p[0] + self.dx, -p[1])   # font y-up -> Lottie y-down


def line_contours(text):
    x, contours = 0, []
    for ch in text:
        g = cmap.get(ord(ch))
        if g is None:
            x += upm * 0.3; continue
        pen = LottiePen(gs, x)
        gs[g].draw(pen)
        contours += pen.contours
        x += gs[g].width
    return contours, x


def to_lottie(contour, sx, ox, oy):
    """One contour -> Lottie path data (vertices with relative in/out tangents)."""
    pts = lambda p: [round(p[0] * sx + ox, 3), round(p[1] * sx + oy, 3)]
    v, i_t, o_t = [], [], []
    for seg in contour:
        if seg[0] in ('M', 'L'):
            v.append(pts(seg[1])); i_t.append([0, 0]); o_t.append([0, 0])
        else:
            _, c1, c2, p = seg
            a = v[-1]; b = pts(p)
            o_t[-1] = [pts(c1)[0] - a[0], pts(c1)[1] - a[1]]
            v.append(b); i_t.append([pts(c2)[0] - b[0], pts(c2)[1] - b[1]]); o_t.append([0, 0])
    if len(v) > 1 and abs(v[0][0] - v[-1][0]) < 1e-3 and abs(v[0][1] - v[-1][1]) < 1e-3:
        i_t[0] = i_t[-1]; v.pop(); i_t.pop(); o_t.pop()
    return {'i': i_t, 'o': o_t, 'v': v, 'c': True}


def block(lines, max_w, max_h, line_gap=0.12):
    """Lay out lines centred at (0,0); scale to fit max_w x max_h."""
    laid, widths = [], []
    for ln in lines:
        c, w = line_contours(ln); laid.append(c); widths.append(w)
    cap = upm * 0.72                       # approx cap height of Futura
    total_h = cap * len(lines) + cap * line_gap * (len(lines) - 1)
    s = min(max_w / max(widths), max_h / total_h)
    shapes, y = [], -total_h * s / 2 + cap * s
    for c, w in zip(laid, widths):
        ox = -w * s / 2
        shapes += [to_lottie(ct, s, ox, y) for ct in c]
        y += cap * s * (1 + line_gap)
    return shapes


def bbox(group):
    vs = [v for it in group['it'] if it['ty'] == 'sh' for v in it['ks']['k']['v']]
    xs, ys = [v[0] for v in vs], [v[1] for v in vs]
    return max(xs) - min(xs), max(ys) - min(ys)


os.makedirs(out, exist_ok=True)
for fname, spec in ((k, v) for k, v in badges.items() if not k.startswith('_')):
    d = json.load(open(os.path.join(site, 'lottie', fname + '.json'), encoding='utf-8'))
    layer = next(l for l in d['layers'] if 'Outlines' in l['nm'])
    anchor_w = layer['ks']['a']['k'][0] * 2
    for group, lines, max_h in ((layer['shapes'][0], [spec['small']], 22),
                                (layer['shapes'][1], spec['big'], 118)):
        w, _ = bbox(group)
        template = next(it for it in group['it'] if it['ty'] == 'sh')
        others = [it for it in group['it'] if it['ty'] != 'sh']
        new = []
        for k, path in enumerate(block(lines, max(w, anchor_w * 0.82), max_h)):
            sh = copy.deepcopy(template)
            sh['nm'] = f'Path {k + 1}'
            sh['ks'] = {'a': 0, 'k': path, 'ix': 2}
            new.append(sh)
        group['it'] = new + others
    json.dump(d, open(os.path.join(out, fname + '.json'), 'w', encoding='utf-8'), separators=(',', ':'))
    print('badge', fname, spec)
