"""Trace the Marathon Burger logo and the palm-tree icon into SVG path data.

Usage: python tools/trace_brand.py <logo.webp> <palm.jpg> <out.json>
Needs: pillow, numpy, potracer  (pip install pillow numpy potracer)

Output JSON (coordinates in source pixels, logo origin = top-left of the red box):
  box: [w, h]
  letters: [{char, d, x0, x1}]   one path per MARATHON letter
  burger: {d, bbox}              the script "Burger"
  palm:   {d, w, h}            the larger of the two palm trees
"""
import json, sys
import numpy as np
import potrace
from PIL import Image


def trace(mask, dx=0, dy=0):
    bmp = potrace.Bitmap(~mask)  # potracer traces the False pixels
    path = bmp.trace(turdsize=8, alphamax=1.0, opticurve=True, opttolerance=0.2)
    out = []
    for curve in path:
        sx, sy = curve.start_point.x, curve.start_point.y
        seg = [f'M{sx + dx:.1f} {sy + dy:.1f}']
        for s in curve.segments:
            if s.is_corner:
                seg.append(f'L{s.c.x + dx:.1f} {s.c.y + dy:.1f}L{s.end_point.x + dx:.1f} {s.end_point.y + dy:.1f}')
            else:
                seg.append(f'C{s.c1.x + dx:.1f} {s.c1.y + dy:.1f} {s.c2.x + dx:.1f} {s.c2.y + dy:.1f} '
                           f'{s.end_point.x + dx:.1f} {s.end_point.y + dy:.1f}')
        out.append(''.join(seg) + 'Z')
    return ''.join(out)


def runs(cols, offset):
    out, start = [], None
    for i, c in enumerate(cols):
        if c and start is None:
            start = i
        if not c and start is not None:
            out.append((start + offset, i + offset)); start = None
    if start is not None:
        out.append((start + offset, len(cols) + offset))
    return out


logo_path, palm_path, out_path = sys.argv[1:4]
a = np.asarray(Image.open(logo_path).convert('RGB')).astype(int)
red = (a[:, :, 0] > 180) & (a[:, :, 1] < 80) & (a[:, :, 2] < 80)
ys, xs = np.where(red)
X0, X1, Y0, Y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
white = a.min(2) > 160
inside = np.zeros_like(white); inside[Y0:Y1, X0:X1] = True
letter_mask = white & inside
letters = []
for (l, r), ch in zip(runs(letter_mask[Y0:Y1, X0:X1].any(0), X0), 'MARATHON'):
    m = np.zeros_like(letter_mask); m[:, l:r] = letter_mask[:, l:r]
    letters.append({'char': ch, 'd': trace(m, -X0, -Y0), 'x0': int(l - X0), 'x1': int(r - X0)})

black = a.sum(2) < 300
below = np.zeros_like(black); below[Y1 + 5:, :] = True
bm = black & below
bys, bxs = np.where(bm)
burger = {'d': trace(bm, -X0, -Y0),
          'bbox': [int(bxs.min() - X0), int(bys.min() - Y0), int(bxs.max() - X0), int(bys.max() - Y0)]}

p = np.asarray(Image.open(palm_path).convert('L')).astype(int)
pm = p < 128
pm[:, :int(pm.shape[1] * 0.42)] = False  # keep only the big palm (the icon has two trees)
pys, pxs = np.where(pm)
pm = pm[pys.min():pys.max() + 1, pxs.min():pxs.max() + 1]
palm = {'d': trace(pm), 'w': int(pm.shape[1]), 'h': int(pm.shape[0])}

json.dump({'box': [int(X1 - X0), int(Y1 - Y0)], 'letters': letters, 'burger': burger, 'palm': palm},
          open(out_path, 'w'), indent=1)
print('box', X1 - X0, Y1 - Y0, 'letters', len(letters), 'burger bbox', burger['bbox'], 'palm', palm['w'], palm['h'])
