"""Builds a static site: every folder that holds images (or has subfolders that do) becomes a page.
Pages show only the images, stacked top to bottom like a PDF. Folders with subfolders get a small link list on top.
Runs in GitHub Actions on every push. Output goes to _site/."""
import html, os, re, shutil, sys
from pathlib import Path
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve(); OUT = Path(sys.argv[2] if len(sys.argv) > 2 else "_site").resolve()
EXT = {".png", ".jpg", ".jpeg", ".webp"}; SKIP = {".git", ".github", "_site", "node_modules"}; MAXW = 2400
def nice(name): return re.sub(r"\s+", " ", re.sub(r"[-_]+", " ", name)).strip().title() if name else "Gallery"
def nat(s): return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", s)]
def size_key(p):
    with Image.open(p) as im: return im.width * im.height
def pick_images(folder):
    imgs = sorted([p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in EXT], key=lambda p: nat(p.name)); best = {}
    for p in imgs:                       # same picture saved at several sizes: keep the largest
        k = re.sub(r"_?\d+x\d+(_\d+dpi)?", "", p.stem)
        if k not in best or size_key(p) > size_key(best[k]): best[k] = p
    keep = set(best.values()); return [p for p in imgs if p in keep]
CSS = """*{box-sizing:border-box}html{background:#101010}body{margin:0;color:#ddd;font:16px/1.4 system-ui,-apple-system,Segoe UI,sans-serif}
.top{position:sticky;top:0;z-index:5;background:rgba(16,16,16,.88);backdrop-filter:blur(6px);padding:10px 16px;font-size:14px;display:flex;gap:10px;flex-wrap:wrap;align-items:center}
.top a{color:#aaa;text-decoration:none}.top a:hover{color:#fff}.top b{color:#fff;font-weight:600}
.links{max-width:900px;margin:18px auto 6px;padding:0 16px;display:grid;gap:10px}
.links a{display:block;padding:16px 18px;border:1px solid #333;border-radius:12px;color:#fff;text-decoration:none;font-size:18px;background:#181818}
.links a:hover{background:#222}.links small{display:block;color:#888;font-size:13px;margin-top:2px}
.pages{max-width:1400px;margin:0 auto;padding:12px 12px 60px}.pages img{display:block;width:100%;height:auto;margin:0 auto 28px;background:#000;border-radius:2px}
.pages img.p{max-width:900px}.pages img.a{background:#2b2b2b repeating-conic-gradient(#3a3a3a 0 25%,#2b2b2b 0 50%) 0 0/28px 28px}
"""
def build(folder, rel):
    subs = [d for d in sorted(folder.iterdir(), key=lambda p: nat(p.name)) if d.is_dir() and d.name not in SKIP and not d.name.startswith(".")]
    sub_pages = []; 
    for d in subs:
        r = build(d, rel / d.name)
        if r: sub_pages.append((d.name, r))
    imgs = pick_images(folder); 
    if not imgs and not sub_pages: return 0
    dest = OUT / rel; dest.mkdir(parents=True, exist_ok=True); tags = []
    for p in imgs:
        with Image.open(p) as im:
            im.load(); w, h = im.size
            if w > MAXW: im = im.resize((MAXW, round(h * MAXW / w)), Image.LANCZOS)
            if im.mode not in ("RGB", "RGBA"): im = im.convert("RGBA" if "A" in im.getbands() else "RGB")
            outn = re.sub(r"[^A-Za-z0-9._-]", "_", p.stem) + ".webp"; im.save(dest / outn, "WEBP", quality=90, method=4)
        alpha = "A" in im.getbands() and im.getchannel("A").getextrema()[0] < 250
        cls = " ".join(c for c in ("p" if h > w * 1.1 else "", "a" if alpha else "") if c)
        tags.append(f'<img class="{cls}" src="{html.escape(outn)}" alt="{html.escape(p.stem)}" loading="lazy" width="{im.width}" height="{im.height}" style="max-width:{im.width}px">')
    depth = len(rel.parts); up = "../" * depth
    crumbs = [f'<a href="{up or "./"}">Home</a>']
    for i, part in enumerate(rel.parts):
        href = "../" * (depth - 1 - i) or "./"
        crumbs.append(f"<span>/</span>" + (f'<b>{html.escape(nice(part))}</b>' if i == depth - 1 else f'<a href="{href}">{html.escape(nice(part))}</a>'))
    links = "".join(f'<a href="{html.escape(n)}/">{html.escape(nice(n))}<small>{c} image{"s" if c != 1 else ""}</small></a>' for n, c in sub_pages)
    title = nice(rel.name) if rel.parts else "Gallery"
    page = f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)}</title><style>{CSS}</style></head><body><div class="top">{"".join(crumbs)}</div>' \
           + (f'<div class="links">{links}</div>' if links else "") + (f'<div class="pages">{"".join(tags)}</div>' if tags else "") + "</body></html>"
    (dest / "index.html").write_text(page, encoding="utf-8"); return len(imgs) + sum(c for _, c in sub_pages)
if OUT.exists(): shutil.rmtree(OUT)
n = build(ROOT, Path("")); (OUT / ".nojekyll").write_text(""); print("images on pages:", n)
