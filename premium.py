"""Gerçekçi / premium gönderi tasarımı (4:5, 1080x1350).

Koyu lacivert stüdyo ışığı, kaide üstünde parlak 3B telefon, yüzen mesaj
balonları, özellik şeridi ve büyük lime buton. Renkler: marka laciverti + lime.

make_premium(post, out_path, idx=0)
"""
import math
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import illus
import sectors
import render as R
from render import F_BOLD, F_HEAD, F_SEMI, LIME, NAVY, PHONE, WEB, HANDLE, font, lockup

W, H = 1080, 1350
NAVY_D = (10, 7, 26)
NAVY_L = (48, 36, 104)
VIOLET = (110, 90, 220)
LIME_D = (120, 170, 10)
WHITE = (246, 244, 255)
MUTED = (186, 180, 220)

FEATURES = {
    "default": [("cal", "Düzenli", "paylaşım"), ("play", "Reels ve", "tasarım"), ("bars", "Aylık", "rapor")],
    "web": [("code", "Hızlı ve", "mobil uyumlu"), ("cart", "Online", "sipariş"), ("bars", "Google'da", "görünürlük")],
}


# ------------------------------------------------------------- yardımcılar
def radial(size, cx, cy, r, color, alpha=255):
    w, h = size
    y, x = np.ogrid[:h, :w]
    d = np.sqrt((x - cx) ** 2 + (y - cy) ** 2) / r
    a = np.clip(1 - d, 0, 1) ** 2 * alpha
    im = Image.new("RGBA", size, color + (0,))
    im.putalpha(Image.fromarray(a.astype(np.uint8)))
    return im


def vgrad(size, top, bottom):
    w, h = size
    t = np.linspace(0, 1, h)[:, None, None]
    arr = (np.array(top)[None, None] * (1 - t) + np.array(bottom)[None, None] * t)
    arr = np.repeat(arr, w, axis=1).astype(np.uint8)
    return Image.fromarray(arr, "RGB")


def glow(img, shape_fn, color, blur, alpha=200):
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    shape_fn(ImageDraw.Draw(layer), color + (alpha,))
    img.alpha_composite(layer.filter(ImageFilter.GaussianBlur(blur)))


def background(rng):
    img = vgrad((W, H), (20, 14, 46), NAVY_D).convert("RGBA")
    # sağda dikey ışıklı paneller (stüdyo duvarı)
    wall = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(wall)
    for i in range(9):
        x = 640 + i * 52
        d.rectangle([x, 0, x + 30, 900], fill=NAVY_L + (90,))
        d.rectangle([x + 30, 0, x + 34, 900], fill=VIOLET + (60,))
    wall = wall.filter(ImageFilter.GaussianBlur(3))
    fade = Image.linear_gradient("L").resize((W, H)).point(lambda p: 255 - p)
    wall.putalpha(Image.composite(wall.getchannel("A"), Image.new("L", (W, H), 0), fade))
    img.alpha_composite(wall)
    img.alpha_composite(radial((W, H), 860, 360, 620, VIOLET, 120))
    img.alpha_composite(radial((W, H), 120, 120, 520, (90, 70, 200), 90))
    img.alpha_composite(radial((W, H), 820, 980, 420, LIME, 55))
    # bokeh
    bok = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(bok)
    for _ in range(26):
        x, y, r = rng.randint(0, W), rng.randint(0, 900), rng.randint(6, 26)
        c = LIME if rng.random() < 0.35 else VIOLET
        d.ellipse([x - r, y - r, x + r, y + r], fill=c + (rng.randint(25, 70),))
    img.alpha_composite(bok.filter(ImageFilter.GaussianBlur(4)))
    # zemin yansıması
    floor = vgrad((W, 260), (26, 20, 60), NAVY_D).convert("RGBA")
    img.alpha_composite(floor, (0, H - 260))
    return img


# ------------------------------------------------------------- telefon
def screen_content(post, sw, sh):
    scr = Image.new("RGBA", (sw, sh), (14, 12, 30, 255))
    d = ImageDraw.Draw(scr)
    d.text((34, 22), "09:41", fill=WHITE, font=font(F_BOLD, 24))
    d.rounded_rectangle([sw - 70, 28, sw - 30, 46], radius=5, outline=WHITE, width=2)
    d.rectangle([sw - 66, 32, sw - 42, 42], fill=LIME)
    # profil satırı
    y = 80
    d.ellipse([28, y, 88, y + 60], fill=LIME)
    mk = R.asset("logo_mark.png", max_h=34, color=NAVY)
    scr.alpha_composite(mk, (58 - mk.size[0] // 2 + 2, y + 13))
    d.text((104, y + 4), "senin_dukkanin", fill=WHITE, font=font(F_BOLD, 26))
    d.text((104, y + 34), "İzmir", fill=MUTED, font=font(F_SEMI, 21))
    d.text((sw - 60, y + 6), "···", fill=WHITE, font=font(F_BOLD, 28))
    # "fotoğraf"
    py0, py1 = y + 80, sh - 150
    photo = vgrad((sw, py1 - py0), (64, 50, 140), (24, 18, 56)).convert("RGBA")
    photo.alpha_composite(radial(photo.size, sw * 0.7, 80, 360, LIME, 70))
    sec = sectors.sector_of(post)
    if sec:
        art = sectors.art(sec)
    else:
        kind = illus.topic_of(post.get("headline", ""), post.get("body", ""), post.get("tag", "")) or "shop"
        art, _ = illus.art3d(kind, scale=0.62)
    art.thumbnail((int(sw * 0.82), int((py1 - py0) * 0.8)), Image.LANCZOS)
    photo.alpha_composite(art, ((sw - art.size[0]) // 2, (py1 - py0 - art.size[1]) // 2 + 10))
    pd = ImageDraw.Draw(photo)
    pd.rounded_rectangle([sw - 230, photo.size[1] - 70, sw - 22, photo.size[1] - 22], radius=24, fill=LIME)
    pd.text((sw - 208, photo.size[1] - 64), "Hemen yaz  ›", fill=NAVY, font=font(F_HEAD, 28))
    scr.alpha_composite(photo, (0, py0))
    # beğeni satırı
    iy = py1 + 26
    heart(d, 36, iy, 40, LIME)
    d.ellipse([100, iy, 140, iy + 38], outline=WHITE, width=4)
    d.polygon([(164, iy + 2), (206, iy + 18), (164, iy + 36), (172, iy + 18)], outline=WHITE, width=4)
    d.rounded_rectangle([sw - 70, iy, sw - 40, iy + 40], radius=4, outline=WHITE, width=4)
    if not sec:
        d.text((36, iy + 56), "Mahallenin yeni favorisi", fill=WHITE, font=font(F_BOLD, 24))
    return scr


def heart(d, x, y, s, color):
    r = s / 4
    d.ellipse([x, y, x + 2 * r, y + 2 * r], fill=color)
    d.ellipse([x + 2 * r, y, x + 4 * r, y + 2 * r], fill=color)
    d.polygon([(x + 1, y + r * 1.3), (x + 4 * r - 1, y + r * 1.3), (x + 2 * r, y + s)], fill=color)


def phone(post, pw=372, ph=760):
    pad = 40
    im = Image.new("RGBA", (pw + 2 * pad, ph + 2 * pad), (0, 0, 0, 0))
    # metal çerçeve (yan yüz): koyudan açığa geçiş
    frame = vgrad((pw, ph), (150, 140, 200), (40, 32, 90)).convert("RGBA")
    m = Image.new("L", (pw, ph), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, pw - 1, ph - 1], radius=64, fill=255)
    frame.putalpha(m)
    im.alpha_composite(frame, (pad + 12, pad + 10))           # kalınlık
    face = vgrad((pw, ph), (205, 198, 240), (90, 78, 160)).convert("RGBA")
    face.putalpha(m)
    im.alpha_composite(face, (pad, pad))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([pad + 8, pad + 8, pad + pw - 9, pad + ph - 9], radius=58, fill=(6, 5, 14))
    sx, sy, sw, sh = pad + 22, pad + 22, pw - 44, ph - 44
    scr = screen_content(post, sw, sh)
    sm = Image.new("L", (sw, sh), 0)
    ImageDraw.Draw(sm).rounded_rectangle([0, 0, sw - 1, sh - 1], radius=46, fill=255)
    scr.putalpha(sm)
    im.alpha_composite(scr, (sx, sy))
    d.rounded_rectangle([pad + pw / 2 - 62, sy + 14, pad + pw / 2 + 62, sy + 46], radius=16, fill=(0, 0, 0))
    # cam yansıması
    gl = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
    ImageDraw.Draw(gl).polygon([(sw * 0.55, 0), (sw, 0), (sw, sh * 0.25), (sw * 0.05, sh)], fill=(255, 255, 255, 22))
    gl.putalpha(Image.composite(gl.getchannel("A"), Image.new("L", (sw, sh), 0), sm))
    im.alpha_composite(gl, (sx, sy))
    # lime kenar ışığı
    d.rounded_rectangle([pad, pad, pad + pw - 1, pad + ph - 1], radius=64, outline=LIME + (170,), width=3)
    return im.rotate(-8, resample=Image.BICUBIC, expand=True)


def pedestal(img, cx, top, rw=300, h=120, rng=None):
    rh = rw * 0.26
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    # gövde
    body = vgrad((2 * rw, int(h + rh)), (34, 28, 70), (8, 6, 20)).convert("RGBA")
    bm = Image.new("L", body.size, 0)
    bd = ImageDraw.Draw(bm)
    bd.rectangle([0, rh / 2, 2 * rw, h + rh / 2], fill=255)
    bd.ellipse([0, h, 2 * rw, h + rh], fill=255)
    body.putalpha(bm)
    # mermer damarları
    vd = ImageDraw.Draw(body)
    rng = rng or random.Random(1)
    for _ in range(7):
        x = rng.randint(20, 2 * rw - 20)
        pts = [(x + rng.randint(-40, 40), rh / 2 + k * (h / 5)) for k in range(6)]
        vd.line(pts, fill=(150, 140, 210, 40), width=2)
    layer.alpha_composite(body, (int(cx - rw), int(top)))
    # üst yüzey
    d.ellipse([cx - rw, top, cx + rw, top + rh], fill=(44, 36, 92, 255))
    d.ellipse([cx - rw, top, cx + rw, top + rh], outline=LIME + (230,), width=4)
    img.alpha_composite(layer)
    glow(img, lambda dd, c: dd.ellipse([cx - rw, top - 6, cx + rw, top + rh + 6], outline=c, width=10), LIME, 14, 150)


def bubble(img, x, y, w, h, kind="dots"):
    glow(img, lambda d, c: d.rounded_rectangle([x, y, x + w, y + h], radius=h // 2.6, fill=c), LIME, 26, 110)
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.rounded_rectangle([x + 6, y + 10, x + w + 6, y + h + 10], radius=int(h // 2.6), fill=LIME_D + (255,))
    d.rounded_rectangle([x, y, x + w, y + h], radius=int(h // 2.6), fill=LIME + (255,))
    d.polygon([(x + w * 0.62, y + h - 4), (x + w * 0.86, y + h + 34), (x + w * 0.84, y + h - 4)], fill=LIME + (255,))
    hl = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(hl).rounded_rectangle([x + 12, y + 8, x + w - 12, y + h * 0.4], radius=int(h // 4), fill=(255, 255, 255, 80))
    lay.alpha_composite(hl.filter(ImageFilter.GaussianBlur(2)))
    d = ImageDraw.Draw(lay)
    if kind == "dots":
        for k in range(3):
            cx = x + w / 2 + (k - 1) * w * 0.22
            d.ellipse([cx - 11, y + h / 2 - 11, cx + 11, y + h / 2 + 11], fill=NAVY + (255,))
    else:
        cx = x + w / 2
        d.ellipse([cx - 15, y + h * 0.2, cx + 15, y + h * 0.2 + 30], fill=NAVY + (255,))
        d.pieslice([cx - 30, y + h * 0.55, cx + 30, y + h * 0.55 + 56], 180, 360, fill=NAVY + (255,))
    img.alpha_composite(lay)


# ------------------------------------------------------------- ikonlar
def icon(d, kind, x, y, s):
    c, wdt = LIME, max(3, s // 12)
    if kind == "cal":
        d.rounded_rectangle([x, y + s * 0.12, x + s, y + s], radius=s // 7, outline=c, width=wdt)
        d.line([x, y + s * 0.38, x + s, y + s * 0.38], fill=c, width=wdt)
        for i in range(3):
            d.ellipse([x + s * (0.2 + i * 0.25) - 5, y + s * 0.62 - 5, x + s * (0.2 + i * 0.25) + 5, y + s * 0.62 + 5], fill=c)
    elif kind == "play":
        d.rounded_rectangle([x, y + s * 0.1, x + s, y + s * 0.9], radius=s // 5, outline=c, width=wdt)
        d.polygon([(x + s * 0.4, y + s * 0.32), (x + s * 0.7, y + s * 0.5), (x + s * 0.4, y + s * 0.68)], fill=c)
    elif kind == "bars":
        for i, hh in enumerate((0.4, 0.65, 0.9)):
            d.rounded_rectangle([x + i * s * 0.36, y + s * (1 - hh), x + i * s * 0.36 + s * 0.24, y + s], radius=4, fill=c)
    elif kind == "code":
        f = font(F_HEAD, int(s * 0.8))
        d.text((x - 4, y + s * 0.02), "</>", fill=c, font=f)
    elif kind == "cart":
        d.line([(x, y + s * 0.15), (x + s * 0.2, y + s * 0.15), (x + s * 0.32, y + s * 0.7), (x + s * 0.9, y + s * 0.7),
                (x + s, y + s * 0.3), (x + s * 0.26, y + s * 0.3)], fill=c, width=wdt, joint="curve")
        for cx in (0.4, 0.82):
            d.ellipse([x + s * cx - 7, y + s * 0.86 - 7, x + s * cx + 7, y + s * 0.86 + 7], fill=c)


# ------------------------------------------------------------- metin
def split_headline(text):
    import re
    parts = [p.strip() for p in re.split(r"(?<=[.!?])\s+(?=[^\d\s])", text) if p.strip()]
    if len(parts) >= 2:
        return " ".join(parts[:-1]), parts[-1]
    words = text.split()
    k = max(1, math.ceil(len(words) * 0.55))
    return " ".join(words[:k]), " ".join(words[k:])


def fit_lines(d, text, fpath, size, maxw, maxlines, min_size=44):
    while size >= min_size:
        f = font(fpath, size)
        lines = R.wrap(d, text, f, maxw)
        if len(lines) <= maxlines and all(d.textlength(ln, font=f) <= maxw for ln in lines):
            return f, lines
        size -= 4
    f = font(fpath, min_size)
    return f, R.wrap(d, text, f, maxw)[:maxlines]


def shadow_text(img, xy, text, f, fill, blur=8):
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).text((xy[0] + 3, xy[1] + 6), text, font=f, fill=(0, 0, 0, 170))
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(blur)))
    ImageDraw.Draw(img).text(xy, text, font=f, fill=fill)


# ------------------------------------------------------------- sahne
def make_premium(post, out_path, idx=0):
    rng = random.Random(idx * 31 + len(post.get("headline", "")))
    img = background(rng)
    d = ImageDraw.Draw(img)

    # üst satır: logo + etiket
    lockup(img, 64, 58, h=70)
    label = (post.get("label") or "DİJİTAL TADİLAT").upper()
    lf = font(F_HEAD, 30)
    lw = d.textlength(label, font=lf)
    d.line([W - 80 - lw - 26, 66, W - 80 - lw - 26, 116], fill=LIME, width=3)
    d.text((W - 80 - lw, 70), label, fill=WHITE, font=lf)

    # sahne: kaide + telefon + balonlar
    pedestal(img, 820, 925, rw=250, h=80, rng=rng)
    ph = phone(post)
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).ellipse([640, 915, 1000, 975], fill=(0, 0, 0, 190))
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(18)))
    bb = ph.getchannel("A").point(lambda p: 255 if p > 128 else 0).getbbox()
    img.alpha_composite(ph, (820 - (bb[0] + bb[2]) // 2, 978 - bb[3]))
    bubble(img, 556, 300, 118, 84, "dots")
    bubble(img, 590, 420, 96, 74, "person")


    # başlık (beyaz + lime) ve gövde
    white_part, lime_part = split_headline(post.get("headline", ""))
    maxw = 480
    y = 200
    f1, l1 = fit_lines(d, white_part, F_HEAD, 92, maxw, 3)
    for ln in l1:
        shadow_text(img, (64, y), ln, f1, WHITE)
        y += int(f1.size * 0.98)
    if lime_part:
        f2, l2 = fit_lines(d, lime_part, F_HEAD, f1.size, maxw, 3)
        for ln in l2:
            shadow_text(img, (64, y), ln, f2, LIME)
            y += int(f2.size * 0.98)
    d = ImageDraw.Draw(img)
    y += 14
    d.line([64, y + 10, 300, y + 10], fill=LIME, width=4)
    bf, bl = fit_lines(d, post.get("body", ""), F_SEMI, 36, 470, 4, 28)
    y += 46
    for ln in bl:
        d.text((64, y), ln, fill=MUTED, font=bf)
        y += int(bf.size * 1.25)

    # sektöre özel 3B nesne: telefonun önünde, kaidenin üstünde
    sec = sectors.sector_of(post)
    if sec:
        hero = sectors.art(sec)
        hero.thumbnail((400, max(160, min(300, 1062 - (y + 20)))), Image.LANCZOS)
        cx = max(690, 560 + hero.size[0] // 2) if y + 20 > 1062 - hero.size[1] else 690
        glow(img, lambda dd, c: dd.ellipse([cx - hero.size[0] // 2, 1060 - hero.size[1],
                                            cx + hero.size[0] // 2, 1060], fill=c), VIOLET, 50, 90)
        img.alpha_composite(hero, (cx - hero.size[0] // 2, 1062 - hero.size[1]))
        d = ImageDraw.Draw(img)

    # özellik şeridi
    is_web = any(k in (post.get("tag", "") + post.get("label", "")).lower() for k in ("web", "yazılım", "yazilim", "site"))
    feats = FEATURES["web" if is_web else "default"]
    sy0, sy1 = 1080, 1170
    strip = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(strip).rounded_rectangle([56, sy0, W - 56, sy1], radius=45, fill=(255, 255, 255, 16), outline=LIME + (220,), width=3)
    img.alpha_composite(strip)
    d = ImageDraw.Draw(img)
    cw = (W - 112) / 3
    for i, (ic, a, b) in enumerate(feats):
        x0 = 56 + i * cw
        icon(d, ic, int(x0 + 34), sy0 + 22, 46)
        d.text((x0 + 100, sy0 + 14), a, fill=WHITE, font=font(F_BOLD, 28))
        d.text((x0 + 100, sy0 + 46), b, fill=WHITE, font=font(F_BOLD, 28))
        if i:
            d.line([x0, sy0 + 20, x0, sy1 - 20], fill=LIME_D, width=2)

    # CTA butonu
    by0, by1 = 1196, 1278
    glow(img, lambda dd, c: dd.rounded_rectangle([60, by0, W - 60, by1], radius=41, fill=c), LIME, 22, 120)
    btn = Image.new("RGBA", (W - 120, by1 - by0), (0, 0, 0, 0))
    g = vgrad(btn.size, (226, 255, 120), (160, 220, 20)).convert("RGBA")
    bm = Image.new("L", btn.size, 0)
    ImageDraw.Draw(bm).rounded_rectangle([0, 0, btn.size[0] - 1, btn.size[1] - 1], radius=41, fill=255)
    g.putalpha(bm)
    img.alpha_composite(g, (60, by0))
    d = ImageDraw.Draw(img)
    R.chat_icon(d, 100, by0 + 16, 50, NAVY, LIME)
    cta = f"WhatsApp'tan yaz · {PHONE}"
    cf = font(F_HEAD, 46)
    d.text((W / 2 - d.textlength(cta, font=cf) / 2 + 30, by0 + 14), cta, fill=NAVY, font=cf)
    ff = font(F_BOLD, 26)
    foot = f"{WEB}  ·  {HANDLE}"
    d.text((W / 2 - d.textlength(foot, font=ff) / 2, 1296), foot, fill=MUTED, font=ff)

    img.convert("RGB").save(out_path, quality=93)
    return out_path


if __name__ == "__main__":
    import json
    import os
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else "preview"
    os.makedirs(out, exist_ok=True)
    posts = [p for p in json.load(open("content/content.json"))["posts"] if p.get("type", "single") == "single"]
    for i in [int(a) for a in sys.argv[2:]] or [0, 1, 5]:
        print(make_premium(posts[i % len(posts)], os.path.join(out, f"premium_{i}.jpg"), i))
