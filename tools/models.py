"""Swap the Planetoño food/mascot models for Marathon Burger ones in the site's 3D scenes.

Usage: python tools/models.py <site_dir> <out_dir>
Needs: pygltflib trimesh numpy shapely mapbox_earcut  (pip install ...)

How it stays in the original style:
- Existing nodes are never deleted (animations and the site's code look them up by name/index);
  unwanted ones just lose their mesh.
- New parts are plain-coloured meshes named MB_*; the patched site code gives every MB_* mesh the
  same toon shading + black outlines as the original food (see apply.py).
- Each new item is placed at the world position of the item it replaces and scaled to a similar size.
"""
import math, os, sys
import numpy as np
import pygltflib
import trimesh
from shapely.geometry import Polygon, LineString, Point
from shapely import affinity

site, out = sys.argv[1], sys.argv[2]  # out: content/three (copied over site/three by apply.py)

# ---- palette (linear RGB, taken from the existing materials) ------------------------------
C = {
    'bun': [0.99, 0.45, 0.01], 'cheese': [0.98, 0.82, 0.12], 'patty': [0.12, 0.03, 0.4],
    'red': [0.94, 0.07, 0.05], 'cream': [1.0, 0.93, 0.91], 'white': [1.0, 1.0, 1.0],
    'green': [0.05, 0.85, 0.04], 'navy': [0.01, 0.06, 0.24], 'blue': [0.1, 0.85, 1.0],
    'bacon': [0.5, 0.01, 0.0], 'orange': [1.0, 0.3, 0.0], 'wing': [0.85, 0.16, 0.01],
    'hash': [0.99, 0.6, 0.06], 'yolk': [1.0, 0.62, 0.0], 'brown': [0.33, 0.1, 0.02],
    'grey': [0.45, 0.45, 0.5], 'purple': [0.44, 0.23, 0.84],
    # Marathon Burger build: brioche, grilled onions, American cheese, pickles, Fresno peppers, secret sauce
    'brioche': [0.8, 0.28, 0.02], 'onion': [0.75, 0.38, 0.06], 'sauce': [1.0, 0.38, 0.18],
    'american': [1.0, 0.62, 0.04], 'wagyu': [0.22, 0.05, 0.015], 'pickle': [0.22, 0.55, 0.02], 'fresno': [0.9, 0.03, 0.02],
}


# ---- geometry helpers ----------------------------------------------------------------------
def yup(m):
    """trimesh revolve/extrude build along +Z; the scenes are Y-up."""
    m.apply_transform(trimesh.transformations.rotation_matrix(-math.pi / 2, [1, 0, 0]))
    return m


def lathe(profile, sections=40):
    """profile: [(radius, height), ...] from the axis outwards and back. Returns a Y-up solid."""
    pts = np.array([[r, y] for r, y in profile], dtype=float)
    return yup(trimesh.creation.revolve(pts, sections=sections))


def cyl(r, h, sections=28):
    m = trimesh.creation.cylinder(radius=r, height=h, sections=sections)
    return yup(m)


def tube(p0, p1, r, sections=18):
    return trimesh.creation.cylinder(radius=r, segment=[p0, p1], sections=sections)


def sphere(r, sub=3):
    return trimesh.creation.icosphere(subdivisions=sub, radius=r)


def moved(m, x=0, y=0, z=0):
    m = m.copy(); m.apply_translation([x, y, z]); return m


def rotated(m, angle, axis, center=(0, 0, 0)):
    m = m.copy(); m.apply_transform(trimesh.transformations.rotation_matrix(angle, axis, center)); return m


def scaled(m, sx, sy=None, sz=None):
    m = m.copy(); m.apply_scale([sx, sy if sy is not None else sx, sz if sz is not None else sx]); return m


def extrude(poly, depth):
    return trimesh.creation.extrude_polygon(poly, depth)


# ---- item builders: each returns {part_name: (mesh, colour)} with base at y=0, height ~1 ----
def soda(liquid_top=None, band='red', lid=True):
    cup = lathe([(0, 0), (0.30, 0), (0.39, 0.86), (0.41, 0.88), (0.0, 0.88)])
    parts = {'Cup': (cup, 'cream'),
             'Band': (lathe([(0.0, 0.32), (0.343, 0.32), (0.38, 0.62), (0.0, 0.62)]), band)}
    if lid:
        parts['Lid'] = (lathe([(0, 0.86), (0.43, 0.86), (0.43, 0.92), (0.38, 0.93), (0.36, 0.97), (0.22, 1.0),
                               (0.08, 1.0), (0.0, 1.0)]), 'white')
        straw_top = 1.0
    else:
        parts['Juice'] = (lathe([(0, 0.80), (0.385, 0.80), (0.385, 0.84), (0, 0.84)]), liquid_top or 'orange')
        straw_top = 0.84
    straw = tube([0.06, straw_top - 0.25, 0.0], [0.16, straw_top + 0.32, 0.04], 0.035)
    parts['Straw'] = (straw, 'blue')
    return parts


def oj():
    p = soda(liquid_top='orange', band='orange', lid=False)
    p['Slice'] = (moved(rotated(trimesh.creation.torus(0.13, 0.035), math.pi / 2, [0, 0, 1]), 0.4, 0.88, 0), 'orange')
    return p


def crispy(m, amount, seed=0):
    """Bumpy fried surface: push vertices along their normals with smooth pseudo-noise."""
    m = m.copy(); m.merge_vertices()
    v, n = m.vertices, m.vertex_normals
    rng = np.random.default_rng(seed)
    f = rng.uniform(9, 17, (3, 3)); ph = rng.uniform(0, 6.3, 3)
    noise = sum(np.sin(v @ f[k] + ph[k]) for k in range(3)) / 3
    m.vertices = v + n * (noise * amount)[:, None]
    return m


def drumette(seed):
    m = trimesh.creation.capsule(height=0.26, radius=0.11, count=[20, 20])
    v = m.vertices.copy()
    t = (v[:, 2] - v[:, 2].min()) / (np.ptp(v[:, 2]) or 1)
    k = 0.55 + 0.6 * np.sin(np.clip(t, 0, 1) * math.pi * 0.8)      # thin knuckle -> fat end
    v[:, 0] *= k; v[:, 1] *= k
    m.vertices = v
    return crispy(m, 0.012, seed)


def flat(seed):
    m = trimesh.creation.capsule(height=0.24, radius=0.1, count=[20, 20])
    m.apply_scale([1.35, 0.55, 1.0])                                  # wide, flat wingette
    v = m.vertices.copy(); v[:, 1] += 0.03 * np.cos(v[:, 2] * 6)       # slight twist
    m.vertices = v
    return crispy(m, 0.01, seed)


def wing_basket():
    basket = lathe([(0, 0), (0.55, 0), (0.62, 0.26), (0.66, 0.28), (0.60, 0.28), (0.53, 0.04), (0, 0.04)])
    basket.apply_scale([1.3, 1, 1])
    liner = lathe([(0, 0.04), (0.56, 0.04), (0.62, 0.22), (0.68, 0.32), (0.58, 0.24), (0.5, 0.07), (0, 0.07)], sections=48)
    liner.apply_scale([1.25, 1, 0.95])
    # red/white checked paper: split the liner into alternating wedges
    ang = np.arctan2(liner.triangles_center[:, 2], liner.triangles_center[:, 0])
    sector = np.floor((ang + math.pi) / (2 * math.pi / 16)).astype(int) % 2
    red_paper = liner.submesh([np.where(sector == 0)[0]], append=True)
    white_paper = liner.submesh([np.where(sector == 1)[0]], append=True)
    wings, bones = [], []
    spots = [(-0.34, 0.16, -0.1, 0.3, 'd'), (0.0, 0.15, -0.22, -0.4, 'f'), (0.32, 0.16, -0.04, 0.9, 'd'),
             (-0.18, 0.18, 0.2, -1.2, 'f'), (0.18, 0.2, 0.18, 2.0, 'd'), (0.02, 0.3, 0.0, 0.6, 'f'),
             (-0.02, 0.34, -0.14, 2.6, 'd')]
    for k, (x, y, z, yaw, kind) in enumerate(spots):
        w = drumette(k) if kind == 'd' else flat(k)
        tip = w.vertices[:, 2].min()
        parts = [w]
        bone = trimesh.util.concatenate([tube([0, 0, tip + 0.04], [0, 0, tip - 0.06], 0.03, 12),
                                         moved(sphere(0.045, 2), 0, 0, tip - 0.07)])
        if kind == 'd':
            parts.append(bone)
        out = []
        for m in parts:
            m = rotated(m, math.pi / 2 * 0.9, [0, 1, 0])
            m = rotated(m, yaw, [0, 1, 0])
            m = rotated(m, 0.25 if kind == 'd' else 0.1, [1, 0, 0])
            out.append(moved(m, x, y, z))
        wings.append(out[0])
        if len(out) > 1:
            bones.append(out[1])
    return {'Basket': (basket, 'red'), 'PaperRed': (red_paper, 'red'), 'PaperWhite': (white_paper, 'white'),
            'Wings': (trimesh.util.concatenate(wings), 'wing'), 'Bones': (trimesh.util.concatenate(bones), 'cream')}


def bun(bottom=True):
    if bottom:
        return lathe([(0, 0), (0.5, 0), (0.56, 0.06), (0.55, 0.14), (0, 0.14)])
    return lathe([(0, 0), (0.56, 0), (0.58, 0.07), (0.52, 0.2), (0.38, 0.28), (0.18, 0.32), (0, 0.33)])


def breakfast_sandwich():
    y = 0.14
    egg_white = Polygon([(math.cos(a) * (0.6 + 0.06 * math.sin(a * 5)), math.sin(a) * (0.6 + 0.06 * math.sin(a * 5)))
                         for a in np.linspace(0, 2 * math.pi, 60, endpoint=False)])
    white = yup(extrude(egg_white, 0.07)); white.apply_translation([0, y, 0])
    yolk = moved(scaled(sphere(0.2), 1, 0.45, 1), 0.08, y + 0.08, -0.05)
    cheese = yup(extrude(affinity.rotate(Polygon([(-0.5, -0.5), (0.5, -0.5), (0.5, 0.5), (-0.5, 0.5)]), 45), 0.04))
    cheese.apply_translation([0, y + 0.07, 0])
    strips = []
    for dz in (-0.14, 0.14):
        xs = np.linspace(-0.62, 0.62, 25)
        line = LineString([(x, 0.03 * math.sin(x * 14)) for x in xs]).buffer(0.035, cap_style=2)
        s = extrude(line, 0.11)   # wave in XY, strip width along Z
        strips.append(moved(s, 0, y + 0.17, dz - 0.055))
    top = moved(bun(False), 0, y + 0.2, 0)
    return {'BunBottom': (bun(True), 'bun'), 'EggWhite': (white, 'white'), 'Yolk': (yolk, 'yolk'),
            'Cheese': (cheese, 'cheese'), 'Bacon': (trimesh.util.concatenate(strips), 'bacon'), 'BunTop': (top, 'bun')}


def hashbrowns():
    def patty(seed):
        m = trimesh.creation.capsule(height=0.5, radius=0.25, count=[24, 24])
        m = rotated(m, math.pi / 2, [0, 1, 0])
        m.apply_scale([1.0, 0.36, 1.0])
        return crispy(m, 0.014, seed)        # shredded-potato surface
    a = moved(rotated(patty(1), 0.15, [0, 0, 1]), -0.05, 0.1, -0.18)
    b = moved(rotated(rotated(patty(2), 0.5, [0, 1, 0]), -0.35, [0, 0, 1]), 0.05, 0.22, 0.15)
    return {'Hashbrowns': (trimesh.util.concatenate([a, b]), 'hash')}


CA = [(-124.21, 41.99), (-120.0, 41.99), (-120.0, 39.0), (-114.63, 35.0), (-114.6, 34.3), (-114.72, 32.72),
      (-117.12, 32.53), (-117.25, 32.75), (-117.4, 33.2), (-118.0, 33.7), (-118.4, 33.75), (-118.5, 34.0),
      (-119.2, 34.15), (-120.45, 34.45), (-120.65, 34.9), (-121.0, 35.6), (-121.9, 36.6), (-122.4, 37.2),
      (-122.5, 37.8), (-123.0, 38.0), (-123.7, 38.9), (-123.8, 39.8), (-124.4, 40.4), (-124.1, 41.0)]


def california():
    k = math.cos(math.radians(37))
    pts = [((lon + 119.4) * k, lat - 37.25) for lon, lat in CA]
    poly = Polygon(pts)
    s = 1.0 / (max(p[1] for p in pts) - min(p[1] for p in pts))
    poly = affinity.scale(poly, s, s, origin=(0, 0))
    state = extrude(poly, 0.12)                       # lies in XY, thickness along Z (faces the camera)
    la = ((-118.24 + 119.4) * k * s, (34.05 - 37.25) * s)
    pin_head = moved(sphere(0.06), la[0], la[1] + 0.16, 0.06)
    cone = trimesh.creation.cone(radius=0.045, height=0.13, sections=20)   # tip along +Z
    pin_tip = moved(rotated(cone, math.pi / 2, [1, 0, 0]), la[0], la[1] + 0.14, 0.06)  # tip points down
    return {'State': (state, 'cheese'), 'Pin': (trimesh.util.concatenate([pin_head, pin_tip]), 'red')}


def bike():
    rear, front = np.array([-0.55, 0.36, 0]), np.array([0.6, 0.36, 0])
    bb = np.array([-0.02, 0.32, 0]); seat = np.array([-0.18, 0.86, 0]); head = np.array([0.42, 0.9, 0])
    wheels = []
    for c in (rear, front):
        t = trimesh.creation.torus(0.33, 0.045, major_sections=48, minor_sections=14)  # ring in XY: upright
        wheels.append(moved(t, *c))
    hubs = [moved(rotated(cyl(0.06, 0.1), math.pi / 2, [1, 0, 0]), *c) for c in (rear, front)]
    spokes = []
    for c in (rear, front):
        for a in np.linspace(0, math.pi, 4, endpoint=False):
            d = np.array([math.cos(a), math.sin(a), 0]) * 0.3
            spokes.append(tube(c - d, c + d, 0.012, 8))
    frame = [tube(rear, bb, 0.035), tube(rear, seat, 0.035), tube(bb, seat, 0.04), tube(bb, head, 0.045),
             tube(seat + [0, -0.05, 0], head + [0, -0.05, 0], 0.04), tube(head, front, 0.035),
             tube(head, head + [0.02, 0.18, 0], 0.035), tube(seat, seat + [0, 0.08, 0], 0.03)]
    bars = tube(head + [0.02, 0.18, -0.24], head + [0.02, 0.18, 0.24], 0.03)
    saddle = moved(scaled(sphere(0.1), 1.5, 0.45, 0.8), *(seat + [0, 0.1, 0]))
    basket = moved(trimesh.creation.box([0.26, 0.18, 0.3]), *(front + [0.08, 0.66, 0]))
    return {'Frame': (trimesh.util.concatenate(frame), 'red'), 'Tyres': (trimesh.util.concatenate(wheels), 'navy'),
            'Hubs': (trimesh.util.concatenate(hubs + spokes + [bars]), 'grey'),
            'Saddle': (saddle, 'navy'), 'Basket': (basket, 'cream')}


def skateboard():
    deck = LineString([(-0.5, 0), (0.5, 0)]).buffer(0.17, resolution=16)
    d = extrude(deck, 0.035)                          # XY outline, thickness along Z
    d = rotated(d, -math.pi / 2, [1, 0, 0])           # lay flat: thickness along Y
    v = d.vertices.copy()
    tail = np.clip(np.abs(v[:, 0]) - 0.38, 0, None)
    v[:, 1] += (tail ** 2) * 2.4                      # kick-tails
    d.vertices = v
    d.apply_translation([0, 0.12, 0])
    wheels, trucks = [], []
    for x in (-0.3, 0.3):
        trucks.append(moved(trimesh.creation.box([0.06, 0.05, 0.26]), x, 0.09, 0))
        for z in (-0.13, 0.13):
            wheels.append(moved(rotated(cyl(0.05, 0.05, 20), math.pi / 2, [1, 0, 0]), x, 0.05, z))
    return {'Deck': (d, 'red'), 'Trucks': (trimesh.util.concatenate(trucks), 'grey'),
            'Wheels': (trimesh.util.concatenate(wheels), 'cream')}


def palm3d():
    # trunk: tapered tube following a gentle curve
    rings, n, seg = [], 14, 16
    pts = [np.array([0.12 * (t ** 2), t * 0.9, 0]) for t in np.linspace(0, 1, n)]
    verts, faces = [], []
    for i, p in enumerate(pts):
        r = 0.07 * (1 - 0.45 * i / (n - 1)) * (1.08 if i % 2 else 1.0)   # bumpy segments
        for j in range(seg):
            a = 2 * math.pi * j / seg
            verts.append(p + np.array([math.cos(a) * r, 0, math.sin(a) * r]))
    for i in range(n - 1):
        for j in range(seg):
            a, b = i * seg + j, i * seg + (j + 1) % seg
            c, d = a + seg, b + seg
            faces += [[a, c, b], [b, c, d]]
    trunk = trimesh.Trimesh(np.array(verts), np.array(faces))
    trunk = trimesh.util.concatenate([trunk, moved(cyl(0.04, 0.01), *pts[-1])])
    top = pts[-1]
    leaves = []
    leaf_shape = Polygon([(0, 0), (0.12, 0.07), (0.3, 0.09), (0.45, 0.05), (0.55, 0), (0.45, -0.05),
                          (0.3, -0.09), (0.12, -0.07)])
    for k in range(7):
        leaf = extrude(leaf_shape, 0.025)
        leaf = rotated(leaf, -math.pi / 2, [1, 0, 0])          # flat, pointing +X
        v = leaf.vertices.copy(); v[:, 1] -= 0.9 * v[:, 0] ** 2 - 0.25 * v[:, 0]  # arch then droop
        leaf.vertices = v
        leaf = rotated(leaf, 2 * math.pi * k / 7, [0, 1, 0])
        leaves.append(moved(leaf, *top))
    nuts = [moved(sphere(0.05, 2), *(top + [math.cos(a) * 0.05, -0.05, math.sin(a) * 0.05])) for a in (0, 2.1, 4.2)]
    return {'Trunk': (trunk, 'bacon'), 'Leaves': (trimesh.util.concatenate(leaves), 'green'),
            'Coconuts': (trimesh.util.concatenate(nuts), 'brown')}


def toppings():
    """House pickles + Fresno pepper rings, laid flat (replaces the lettuce)."""
    pickles, rings = [], []
    for k in range(5):
        a = k * 2 * math.pi / 5 + 0.3
        d = moved(cyl(0.075, 0.018, 24), math.cos(a) * 0.17, 0, math.sin(a) * 0.17)
        pickles.append(d)
    for k in range(5):
        a = k * 2 * math.pi / 5 + 0.9
        r = trimesh.creation.torus(0.04, 0.014, major_sections=24, minor_sections=10)  # ring in XY
        r = rotated(r, math.pi / 2, [1, 0, 0])                                          # lay flat
        rings.append(moved(r, math.cos(a) * 0.12, 0.02, math.sin(a) * 0.12))
    return {'Pickles': (trimesh.util.concatenate(pickles), 'pickle'),
            'Fresno': (trimesh.util.concatenate(rings), 'fresno')}


def coffee_cup():
    """Hot Marathon Coffee: white cup, brown sleeve, sip lid."""
    return {'Cup': (lathe([(0, 0), (0.28, 0), (0.37, 0.82), (0, 0.82)]), 'white'),
            'Sleeve': (lathe([(0, 0.24), (0.318, 0.24), (0.355, 0.56), (0, 0.56)]), 'brown'),
            'Lid': (lathe([(0, 0.8), (0.40, 0.8), (0.40, 0.87), (0.33, 0.9), (0.33, 0.95), (0, 0.97)]), 'white'),
            'SipTab': (moved(scaled(sphere(0.06, 2), 1.4, 0.5, 0.8), 0.22, 0.95, 0), 'brown')}


def egg():
    white = Polygon([(math.cos(a) * (0.6 + 0.05 * math.sin(a * 5)), math.sin(a) * (0.6 + 0.05 * math.sin(a * 5)))
                     for a in np.linspace(0, 2 * math.pi, 60, endpoint=False)])
    w = yup(extrude(white, 0.07))
    yolk = moved(scaled(sphere(0.22), 1, 0.45, 1), 0.08, 0.07, -0.05)
    return {'EggWhite': (w, 'white'), 'Yolk': (yolk, 'yolk')}


# ---- glTF editing ----------------------------------------------------------------------------
def trs_matrix(n):
    if n.matrix:
        return np.array(n.matrix, dtype=float).reshape(4, 4).T
    t = np.array(n.translation or [0, 0, 0], dtype=float)
    q = n.rotation or [0, 0, 0, 1]
    s = np.array(n.scale or [1, 1, 1], dtype=float)
    R = trimesh.transformations.quaternion_matrix([q[3], q[0], q[1], q[2]])
    M = R @ np.diag([s[0], s[1], s[2], 1])
    M[:3, 3] = t
    return M


class Scene:
    def __init__(self, path):
        self.g = pygltflib.GLTF2().load(path)
        self.blob = bytearray(self.g.binary_blob())
        self.parent = {}
        for i, n in enumerate(self.g.nodes):
            for c in n.children or []:
                self.parent[c] = i
        self.materials = {}

    def idx(self, name):
        for i, n in enumerate(self.g.nodes):
            if n.name == name:
                return i
        raise KeyError(name)

    def world(self, i):
        M = trs_matrix(self.g.nodes[i])
        while i in self.parent:
            i = self.parent[i]
            M = trs_matrix(self.g.nodes[i]) @ M
        return M

    def subtree(self, i):
        out = [i]
        for c in self.g.nodes[i].children or []:
            out += self.subtree(c)
        return out

    def bbox(self, name):
        lo, hi = np.full(3, np.inf), np.full(3, -np.inf)
        for i in self.subtree(self.idx(name)):
            n = self.g.nodes[i]
            if n.mesh is None:
                continue
            W = self.world(i)
            for pr in self.g.meshes[n.mesh].primitives:
                a = self.g.accessors[pr.attributes.POSITION]
                for corner in np.array(np.meshgrid(*zip(a.min, a.max))).T.reshape(-1, 3):
                    p = W @ np.append(corner, 1)
                    lo, hi = np.minimum(lo, p[:3]), np.maximum(hi, p[:3])
        return lo, hi

    def hide(self, name):
        # keep the node (animations/code use it) but drop its mesh; rename mesh nodes so the
        # site's per-name styling (which expects a material) no longer applies to them
        for i in self.subtree(self.idx(name)):
            n = self.g.nodes[i]
            if n.mesh is not None:
                n.mesh = None
                n.name = 'Removed_' + n.name

    def remat(self, name, colour, only=None):
        """Give every primitive of this node's mesh (or only those using material `only`) a new colour."""
        n = self.g.nodes[self.idx(name)]
        for pr in self.g.meshes[n.mesh].primitives:
            if only is None or self.g.materials[pr.material].name == only:
                pr.material = self.material(colour)

    def swap_mesh(self, name, src, new_name):
        """Point node `name` at node `src`'s mesh; rename so the site recomputes its outlines."""
        n = self.g.nodes[self.idx(name)]
        n.mesh = self.g.nodes[self.idx(src)].mesh
        n.name = new_name

    def _view(self, data, target=None):
        while len(self.blob) % 4:
            self.blob.append(0)
        off = len(self.blob)
        self.blob += data
        self.g.bufferViews.append(pygltflib.BufferView(buffer=0, byteOffset=off, byteLength=len(data), target=target))
        return len(self.g.bufferViews) - 1

    def material(self, colour):
        if colour not in self.materials:
            rgb = C[colour]
            self.g.materials.append(pygltflib.Material(
                name='MB_' + colour, pbrMetallicRoughness=pygltflib.PbrMetallicRoughness(
                    baseColorFactor=rgb + [1.0], metallicFactor=0, roughnessFactor=1)))
            self.materials[colour] = len(self.g.materials) - 1
        return self.materials[colour]

    def mesh(self, m, colour, name):
        m = m.copy()
        m.merge_vertices()
        pos = m.vertices.astype(np.float32)
        nor = m.vertex_normals.astype(np.float32)
        ind = m.faces.astype(np.uint32).reshape(-1)
        acc = []
        for arr, typ, tgt in ((pos, 'VEC3', 34962), (nor, 'VEC3', 34962)):
            bv = self._view(arr.tobytes(), tgt)
            self.g.accessors.append(pygltflib.Accessor(bufferView=bv, componentType=5126, count=len(arr), type=typ,
                                                       min=arr.min(0).tolist() if arr is pos else None,
                                                       max=arr.max(0).tolist() if arr is pos else None))
            acc.append(len(self.g.accessors) - 1)
        bv = self._view(ind.tobytes(), 34963)
        self.g.accessors.append(pygltflib.Accessor(bufferView=bv, componentType=5125, count=len(ind), type='SCALAR'))
        prim = pygltflib.Primitive(attributes=pygltflib.Attributes(POSITION=acc[0], NORMAL=acc[1]),
                                   indices=len(self.g.accessors) - 1, material=self.material(colour))
        self.g.meshes.append(pygltflib.Mesh(name=name, primitives=[prim]))
        return len(self.g.meshes) - 1

    def add_node(self, parent, name, local, mesh=None):
        p = parent if isinstance(parent, int) else self.idx(parent)
        node = pygltflib.Node(name=name, matrix=local.T.reshape(-1).tolist(), mesh=mesh, children=[])
        self.g.nodes.append(node)
        i = len(self.g.nodes) - 1
        self.g.nodes[p].children = (self.g.nodes[p].children or []) + [i]
        self.parent[i] = p
        return i

    def place(self, parent_name, item_name, parts, pos, height, yaw=0.0, extra=None, width=None, parent_world=None):
        """Put an item (dict of parts) under parent so that its base sits at world `pos`,
        scaled to world `height`, rotated by `yaw` around world Y."""
        allv = np.vstack([m.vertices for m, _ in parts.values()])
        h = np.ptp(allv[:, 1]) or 1
        k = height / h
        if width is not None:   # size by footprint instead of height
            k = width / max(np.ptp(allv[:, 0]), np.ptp(allv[:, 2]))
        S = np.diag([k] * 3 + [1])
        R = trimesh.transformations.rotation_matrix(yaw, [0, 1, 0])
        if extra is not None:
            R = R @ extra
        T = np.eye(4); T[:3, 3] = pos
        desired = T @ R @ S
        pidx = parent_name if isinstance(parent_name, int) else self.idx(parent_name)
        local = np.linalg.inv(parent_world if parent_world is not None else self.world(pidx)) @ desired
        # group nodes are MBG_* (no styling); meshes are MB_* (toon shading + outlines in the site code)
        grp = self.add_node(parent_name, 'MBG_' + item_name, local)
        for part, (m, colour) in parts.items():
            mi = self.mesh(m, colour, f'MB_{item_name}_{part}')
            self.add_node(grp, f'MB_{item_name}_{part}', np.eye(4), mi)
        return grp

    def pivot(self, name, base):
        """Base point under the node's own origin: the site spins items around that origin, so new items
        centred there spin in place like the originals instead of orbiting."""
        o = self.world(self.idx(name))[:3, 3]
        return np.array([o[0], base[1], o[2]])

    def anim_end(self, name):
        """World matrix of a root node at the last keyframe of its animation."""
        i = self.idx(name)
        n = self.g.nodes[i]
        trs = {'translation': n.translation, 'rotation': n.rotation, 'scale': n.scale}
        blob = self.g.binary_blob()
        for an in self.g.animations:
            for ch in an.channels:
                if ch.target.node == i and ch.target.path in trs:
                    a = self.g.accessors[an.samplers[ch.sampler].output]
                    bv = self.g.bufferViews[a.bufferView]
                    k = {'VEC3': 3, 'VEC4': 4}[a.type]
                    off = (bv.byteOffset or 0) + (a.byteOffset or 0)
                    trs[ch.target.path] = np.frombuffer(blob[off:off + a.count * k * 4], np.float32).reshape(-1, k)[-1].tolist()
        return trs_matrix(pygltflib.Node(**trs))

    def save(self, path):
        self.g.buffers[0].byteLength = len(self.blob)
        self.g.set_binary_blob(bytes(self.blob))
        self.g.save_binary(path)


def base_of(sc, name):
    lo, hi = sc.bbox(name)
    return np.array([(lo[0] + hi[0]) / 2, lo[1], (lo[2] + hi[2]) / 2]), hi - lo


def centre_of(sc, name):
    lo, hi = sc.bbox(name)
    return (lo + hi) / 2, hi - lo


os.makedirs(out, exist_ok=True)

# ===================================== hero slider =========================================
# New items are parented to the (now empty) item nodes the slider animates when changing slides
# (Astro_Cat, Hot_Dog, Pizza, ... in the site's swipe list), so they slide in and out with their tray.
sc = Scene(os.path.join(site, 'three', 'slider_model.glb'))
spots = {n: base_of(sc, n) for n in ['Astro_Cat', 'Donut', 'Burger', 'French_Fries', 'Astro_Chik', 'Hot_Dog',
                                     'Ice_Cream', 'Astro_Koala', 'Pizza', 'Pizza_French_Fries', 'Coffee']}
for n, (p, s) in spots.items():
    print(f'  {n:20s} base {np.round(p, 2)} size {np.round(s, 2)}')
burger_h = spots['Burger'][1][1]

# Tray 1 — Marathon Burger combo: the original burger reskinned to the menu build, fries, drink
for n in ('Astro_Cat', 'Donut', 'Plat_3'):   # Plat_3 was the dessert plate
    sc.hide(n)
sc.place('Astro_Cat', 'Soda', soda(), sc.pivot('Astro_Cat', spots['Astro_Cat'][0]), burger_h * 1.55, yaw=0.4)


def marathon_burger(sc, part_of=lambda n: n):
    """Reskin Planetoño's burger as the Marathon Burger (menu: two wagyu patties smashed with grilled
    onions, toasted brioche bun, Fresno peppers, house pickles, American cheese, secret sauce)."""
    lo, hi = sc.bbox('Burger_Salad')
    sc.hide('Burger_Bun_Sesame')                                   # brioche: no sesame
    sc.swap_mesh('Burger_Tomato', 'Burger_Patty', 'MB_Burger_Patty_2')   # tomato -> second wagyu patty
    for n, c in (('Burger_Bun_Top', 'brioche'), ('Burger_Bun_Bottom', 'brioche'), ('Burger_Onions_Top', 'onion'),
                 ('Burger_Onions_Bottom', 'onion'), ('Burger_Mayonnaise_Bottom', 'sauce'), ('Burger_Cheese', 'american'),
                 ('Burger_Patty', 'wagyu')):
        sc.remat(n, c)
    sc.hide('Burger_Salad')                                        # lettuce -> pickles + Fresno peppers
    parent = sc.parent[sc.idx('Removed_Burger_Salad')]
    sc.place(parent, 'Toppings', toppings(), np.array([(lo[0] + hi[0]) / 2, lo[1], (lo[2] + hi[2]) / 2]), 0,
             width=max(hi[0] - lo[0], hi[2] - lo[2]) * 0.92)


marathon_burger(sc)

# Tray 2 — Hot Wing Basket: wings, fries, drink
for n in ('Astro_Chik', 'Hot_Dog', 'Ice_Cream'):
    sc.hide(n)
sc.place('Hot_Dog', 'WingBasket', wing_basket(), sc.pivot('Hot_Dog', spots['Hot_Dog'][0]), 0, yaw=0.3, width=spots['Burger'][1][0] * 1.35)
sc.place('Astro_Chik', 'Soda', soda(), sc.pivot('Astro_Chik', spots['Astro_Chik'][0]), burger_h * 1.55, yaw=-0.3)

# Tray 3 — Breakfast: Marathon Breakfast Sandwich (original brioche bun + cheese + sausage patty + egg),
# hashbrowns, Marathon Coffee, fresh squeezed OJ
for n in ('Astro_Koala', 'Pizza', 'Pizza_French_Fries', 'Coffee'):
    sc.hide(n)
bw = sc.world(sc.idx('Burger'))
shift = np.eye(4); shift[:3, 3] = sc.pivot('Pizza', spots['Pizza'][0]) - sc.pivot('Burger', spots['Burger'][0])
grp = sc.add_node('Pizza', 'MBG_BreakfastSandwich', np.linalg.inv(sc.world(sc.idx('Pizza'))) @ shift @ bw)
for src, new in (('Burger_Bun_Bottom', 'MB_BK_Bun_Bottom'), ('Burger_Patty', 'MB_BK_Sausage'),
                 ('Burger_Cheese', 'MB_BK_Cheese'), ('Burger_Bun_Top', 'MB_BK_Bun_Top')):
    s = sc.g.nodes[sc.idx(src)]
    sc.add_node(grp, new, trs_matrix(s), s.mesh)
for part, (m, colour) in egg().items():
    mi = sc.mesh(m, colour, 'MB_BK_' + part)
    T = np.diag([0.5, 0.5, 0.5, 1.0]); T[:3, 3] = [0, 0.205, 0]
    sc.add_node(grp, 'MB_BK_' + part, T, mi)
sc.place('Pizza_French_Fries', 'Hashbrowns', hashbrowns(), sc.pivot('Pizza_French_Fries', spots['Pizza_French_Fries'][0]), 0, yaw=0.6,
         width=spots['Burger'][1][0] * 0.8)
sc.place('Coffee', 'Coffee', coffee_cup(), sc.pivot('Coffee', spots['Coffee'][0]), burger_h * 1.2)
sc.place('Astro_Koala', 'OJ', oj(), sc.pivot('Astro_Koala', spots['Astro_Koala'][0]), burger_h * 1.45)
sc.save(os.path.join(out, 'slider_model.glb'))

# ===================================== how-it-works scroll =================================
sc = Scene(os.path.join(site, 'three', 'scroll_model.glb'))
spots = {n: centre_of(sc, n) for n in ['Donut', 'Astro_Cat', 'Planet_Empty', 'Planet_H_Empty', 'Meteor_Empty',
                                     'Star_Empty', 'Star_2_Empty', 'Burger', 'French_Fries']}
for n, (p, s) in spots.items():
    print(f'  {n:20s} centre {np.round(p, 2)} size {np.round(s, 2)}')


def put(parent, item, parts, centre, size, yaw=0.0, extra=None):
    allv = np.vstack([m.vertices for m, _ in parts.values()])
    h = np.ptp(allv[:, 1])
    base = centre - np.array([0, size / 2, 0])
    sc.place(parent, item, parts, base, size, yaw, extra)


marathon_burger(sc)
for n in ('Donut', 'Astro_Cat', 'Planet_Empty', 'Planet_H_Empty', 'Meteor_Empty', 'Star_Empty', 'Star_2_Empty'):
    sc.hide(n)
# drink: placed against the Donut node's FINAL pose (it ends upright in the meal box), centred on its spin axis
Wend = sc.anim_end('Donut')
cup_h = 9.0
end_base = Wend[:3, 3] + np.array([0, 0.4, 0])          # box floor is at the Donut's final height
sc.place('Donut', 'Soda', soda(), end_base, cup_h, yaw=0.3, parent_world=Wend)
p = spots['Planet_Empty']; put('Planet_Empty', 'California', california(), p[0], max(p[1]) * 1.15)
p = spots['Planet_H_Empty']; put('Planet_H_Empty', 'Bike', bike(), p[0], max(p[1]) * 0.75, yaw=-0.5)
p = spots['Meteor_Empty']; put('Meteor_Empty', 'Skateboard', skateboard(), p[0], max(p[1]) * 0.45, yaw=0.6,
                               extra=trimesh.transformations.rotation_matrix(0.5, [0, 0, 1]))
p = spots['Star_Empty']; put('Star_Empty', 'Palm', palm3d(), p[0], max(p[1]) * 1.25)
p = spots['Star_2_Empty']; put('Star_2_Empty', 'Palm_2', palm3d(), p[0], max(p[1]) * 1.25, yaw=1.2)
sc.save(os.path.join(out, 'scroll_model.glb'))
print('wrote', out)
