"""Trace the 33rd//Creative logo into one path per glyph, so the footer credit can animate letter by letter.

Usage: python tools/trace_studio.py content/brand/33rd-creative.png content/brand/studio-traced.json
Needs: pillow numpy scipy potracer
Output: {w, h, glyphs: [{d, x0, x1, kind}]}  kind = "slash" for the two slashes, else "char"
"""
import json, sys
import numpy as np
import potrace
from PIL import Image
from scipy import ndimage

src, out = sys.argv[1], sys.argv[2]
a = np.asarray(Image.open(src).convert('RGB')).astype(int)
mask = a.sum(2) < 720                         # grey logo on white
ys, xs = np.where(mask)
mask = mask[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
h, w = mask.shape


def trace(m):
    path = potrace.Bitmap(~m).trace(turdsize=4, alphamax=1.0, opticurve=True)   # potracer traces False pixels
    parts = []
    for c in path:
        s = [f'M{c.start_point.x:.1f} {c.start_point.y:.1f}']
        for g in c.segments:
            s.append(f'L{g.c.x:.1f} {g.c.y:.1f}L{g.end_point.x:.1f} {g.end_point.y:.1f}' if g.is_corner else
                     f'C{g.c1.x:.1f} {g.c1.y:.1f} {g.c2.x:.1f} {g.c2.y:.1f} {g.end_point.x:.1f} {g.end_point.y:.1f}')
        parts.append(''.join(s) + 'Z')
    return ''.join(parts)


labels, n = ndimage.label(mask)
glyphs = []
for i in range(1, n + 1):
    comp = labels == i
    cys, cxs = np.where(comp)
    if comp.sum() < 50:
        continue
    gh, gw = cys.max() - cys.min(), cxs.max() - cxs.min()
    kind = 'slash' if gh > h * 0.8 and gw < w * 0.1 else 'char'     # the two tall thin diagonals
    glyphs.append({'d': trace(comp), 'x0': int(cxs.min()), 'x1': int(cxs.max()), 'kind': kind})
glyphs.sort(key=lambda g: g['x0'])
json.dump({'w': int(w), 'h': int(h), 'glyphs': glyphs}, open(out, 'w'))
print('studio logo', w, h, 'glyphs', len(glyphs), [g['kind'] for g in glyphs])
