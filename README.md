# Marathon

The Marathon site, built on the Planetoño site (planetono.space by Tubik Studio) with permission.
It keeps the original's 3D food trays, star maps, Rive animations, sounds and custom cursor,
and swaps in Marathon's name, logo and copy.

## Folders

| Folder | What it is |
|---|---|
| `site/` | The original Planetoño build, made runnable offline. Don't edit by hand. |
| `content/marathon.json` | **Every editable slot on the page.** Edit this file. |
| `content/brand/` | Marathon brand files (favicon; add a logo or share image here). |
| `tools/` | Scripts that extract, localise and rebrand the site. |
| `dist/` | The finished Marathon site. Host this folder. |

## Change the content

1. Edit `content/marathon.json`.
2. Rebuild: `python3 -I tools/apply.py`
3. Preview: `python3 -m http.server -d dist 8080`, then open http://localhost:8080
   (it has to be served over http; opening the file directly won't work).

### What you can change in `content/marathon.json`

| Section | Slots |
|---|---|
| `brand` | Name, meta description, author, site URL, contact email, logo (`logo_image` for your own SVG/PNG, or `logo_text` for a wordmark in the site font), favicon, share image |
| `nav` | Menu labels and links (How it works, Locations) |
| `ui` | START button, headphones message, "Contact" label |
| `hero_items` | 3 slides: headline lines, item description, mascot line. Must stay at 3, one per 3D tray. |
| `how_it_works` | Label, 3 title lines, caption |
| `locations` | Title, caption, and the pins on each star map: name, x/y position (%), popup side, detail rows. You can add or remove pins. |
| `footer` | Headline lines (with links), left and right notes, Tubik logo on or off |
| `colors` | Swap any of the 6 brand colors everywhere |

Mixed CaPiTaLs in headlines are intentional: the Futura Passata font draws upper and lower case letters in different styles.

### Still Planetoño copy (waiting for Marathon text)

Taglines, item descriptions, mascots (Major Paws, Cluck Rogers, Koalantis), How it works copy,
location names and coordinates, footer lines and credits, and the meta description.

### Baked into artwork (can't be changed from the JSON)

- The 3D food trays, mascots and the **"GALAXY BITE / 銀河バイト"** badge are 3D models (`site/three/*.glb`).
- The nav buttons and "Sound on" switch are Rive animations (`site/media/rive.riv`); their labels come from the JSON, but their look is set in the Rive file.
- The star-map artwork (`site/media/*.avif`, `site/lottie/*.json`), sounds (`site/media/sounds/`), cursor and map pins (`site/images/`).

To change these, replace the file at the same path in `site/` and rebuild.

## Rebuilding `site/` from scratch

Run this only if you have a new archive:

```
python3 -I tools/extract.py <Planetono.webarchive> site   # page, styles, scripts, fonts, images
python3 -I tools/localize.py site                          # 3D models, Rive, sounds, Lottie files from the live site
node tools/fetch_missing.js site http://localhost:8081/    # optional: catches anything else (serve site/ on :8081 first)
mkdir -p site/vendor/rive && npm pack @rive-app/canvas@2.32.2 && tar xzf rive-app-canvas-2.32.2.tgz && cp package/rive*.wasm site/vendor/rive/
python3 -I tools/apply.py
```

`localize.py` also stops the page from re-downloading its text from Storyblok, so the Marathon text isn't overwritten.
