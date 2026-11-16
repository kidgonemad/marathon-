# Marathon Burger

The Marathon Burger website, built on the Planetoño site (planetono.space by Tubik Studio, used with permission).
Design by 33rdcreative.

It keeps the original's look and motion: the intro and START screen, the 3D trays, the scroll-built meal, the star
maps, the sounds and the custom cursor. Everything brand-specific is now Marathon Burger:

- **Logo.** The real Marathon Burger logo (red MARATHON box with the "Burger" script), traced to vectors.
  It is rebuilt in code with the original's intro (palm-tree loader, then the logo pops in, the letters wave and
  "Burger" pops in) and its per-letter hover lift on desktop. The Rive logo is removed, not covered.
- **3D trays.**
  1. $20 combo: double wagyu burger, fries and a drink.
  2. Hot Wing Basket: wings with fries and a drink.
  3. Breakfast: breakfast sandwich, hashbrowns, coffee and fresh OJ.

  The cat, chick, koala, donut, hot dog, pizza and ice cream are gone. New models use the site's own toon shading
  and black outlines.
- **How it works.** 3 steps (burger, drink, fries), ending with the meal box and "Claim your meal".
  The planets and stars are now a California state shape, a bike, a skateboard and palm trees.
- **Badges** on each slide: $20 COMBO, HOT WING BASKET and MARATHON BREAKFAST.
- **Decorations.** The ✦ sparkles are now the palm tree.
- **Locations.** The 5 real locations on the star maps.
- **Menu page** at `/menu/`, with the full menu.

## Folders

| Folder | What it is |
|---|---|
| `site/` | The original Planetoño build, made runnable offline. Don't edit by hand. |
| `content/marathon.json` | Home page copy: brand, nav, hero slides, badges, how-it-works, locations, footer, colours |
| `content/menu.json` | The menu page (sections, items, prices, descriptions) |
| `content/brand/` | Logo source and traced paths, palm, logo/stepper code, menu page template |
| `content/three/`, `content/lottie/` | Generated 3D models and badge animations (from the tools below) |
| `tools/` | Build scripts |
| `dist/` | **The finished site. Host this folder.** |

## Edit and rebuild

```
python3 -I tools/apply.py                      # rebuild dist/ from content/
python3 -m http.server -d dist 8080            # preview at http://localhost:8080 (must be served, not opened as a file)
```

If you change the 3D items, badge text or logo artwork, regenerate them first. They need a few Python packages:

```
pip install pygltflib trimesh numpy shapely mapbox_earcut fonttools brotli potracer pillow
python tools/trace_brand.py content/brand/marathon-burger-logo.webp content/brand/palm.jpg content/brand/traced.json
python tools/models.py site content/three
python tools/badges.py site content/marathon.json content/lottie
python3 -I tools/apply.py
```

## Still to confirm

- The contact email is a placeholder (`hello@marathon.example`). Set `brand.email` in `content/marathon.json`.
- Menu descriptions are transcribed from the menu-board photo. Check them against the current menu.

## Rebuilding `site/` from the original archive

Run this only if starting over:

```
python3 -I tools/extract.py <Planetono.webarchive> site
python3 -I tools/localize.py site     # 3D models, Rive, sounds, Lottie files from the live site
```
