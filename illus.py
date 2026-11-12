"""Konuya göre değişen 3B çizimler (dükkân, laptop, harita, yorum, kamera, telefon).

Her çizim önce düz (RGBA) çizilir, sonra fx3d.extrude ile kalınlık + gölge alır
ve hafif eğilir. Sonuçlar önbellekte tutulur.
"""
import math
import re

from PIL import Image, ImageDraw

import fx3d

NAVY = (22, 16, 46)
NAVY2 = (38, 30, 72)
LIME = (200, 255, 46)
WHITE = (243, 240, 255)
MUTED = (178, 172, 210)
PAPER = (236, 233, 248)
LILAC = (120, 100, 210)
GREY = (205, 200, 228)

# Sıra önemli: ilk eşleşen kazanır.
TOPICS = [
    ("camera", r"fotoğraf|çekim|video|kamera"),
    ("stars", r"yorum|yıldız|referans"),
    ("laptop", r"web sitesi|\bsiten?\b|\bsite\b|mobil uyumlu"),
    ("phone", r"whatsapp|telefon|\bdm|mesaj|arayabil"),
    ("pin", r"google|harita|konum|mahalle|adres|yol tarifi"),
    ("shop", r"dükkân|dükkan|vitrin|tabela|mağaza|esnaf"),
]
_TOPIC_RE = [(k, re.compile(p, re.I)) for k, p in TOPICS]


def topic_of(*texts):
    t = " ".join(x or "" for x in texts)
    for k, rx in _TOPIC_RE:
        if rx.search(t):
            return k
    return None


def _rgba(c, a=255):
    return tuple(c) + (a,)


def _star(d, cx, cy, r, fill):
    pts = []
    for i in range(10):
        ang = -math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.45
        pts.append((cx + rr * math.cos(ang), cy + rr * math.sin(ang)))
    d.polygon(pts, fill=fill)


# --------------------------------------------------------------------------
def shop_flat(w=420):
    import render as R
    h = int(w * 1.3)
    s = w / 420
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    # duvar
    d.rounded_rectangle([10 * s, 90 * s, w - 10 * s, h], radius=int(14 * s), fill=_rgba(PAPER))
    # tabela
    d.rounded_rectangle([0, 0, w, 100 * s], radius=int(18 * s), fill=_rgba(NAVY))
    mk = R.asset("logo_mark.png", max_h=int(58 * s))
    im.alpha_composite(mk, (int(26 * s), int(21 * s)))
    d.text((int(26 * s + mk.size[0] + 16 * s), int(24 * s)), "DÜKKÂN", fill=LIME, font=R.font(R.F_HEAD, int(48 * s)))
    # tente
    n = 7
    aw = (w - 20 * s) / n
    ay0, ay1 = 100 * s, 175 * s
    for i in range(n):
        x0 = 10 * s + i * aw
        col = LIME if i % 2 == 0 else WHITE
        d.rectangle([x0, ay0, x0 + aw, ay1], fill=_rgba(col))
        d.pieslice([x0, ay1 - aw / 2, x0 + aw, ay1 + aw / 2], 0, 180, fill=_rgba(col))
    # vitrin
    wx0, wy0, wx1, wy1 = 34 * s, 225 * s, 255 * s, 470 * s
    d.rounded_rectangle([wx0 - 8 * s, wy0 - 8 * s, wx1 + 8 * s, wy1 + 8 * s], radius=int(12 * s), fill=_rgba(NAVY2))
    d.rectangle([wx0, wy0, wx1, wy1], fill=_rgba((170, 160, 225)))
    for k, sy in enumerate((wy0 + 95 * s, wy0 + 190 * s)):
        d.rectangle([wx0, sy, wx1, sy + 8 * s], fill=_rgba(NAVY2))
        cols = [LIME, (255, 150, 90), WHITE, (255, 205, 70)] if k == 0 else [(255, 120, 150), LIME, (110, 200, 255)]
        bx = wx0 + 14 * s
        for j, c in enumerate(cols):
            bw = (36 + (j % 2) * 12) * s
            bh = (50 + (j % 3) * 14) * s
            d.rounded_rectangle([bx, sy - bh, bx + bw, sy], radius=int(6 * s), fill=_rgba(c))
            bx += bw + 14 * s
    # cam yansıması
    d.polygon([(wx0 + 120 * s, wy0), (wx0 + 170 * s, wy0), (wx0 + 60 * s, wy1), (wx0 + 10 * s, wy1)], fill=(255, 255, 255, 60))
    # kapı
    dx0, dy0, dx1 = 280 * s, 225 * s, 385 * s
    d.rounded_rectangle([dx0, dy0, dx1, h], radius=int(10 * s), fill=_rgba(NAVY))
    d.rectangle([dx0 + 14 * s, dy0 + 16 * s, dx1 - 14 * s, dy0 + 150 * s], fill=_rgba((70, 58, 130)))
    d.ellipse([dx1 - 30 * s, dy0 + 190 * s, dx1 - 16 * s, dy0 + 204 * s], fill=_rgba(LIME))
    # AÇIK levhası
    sx0, sy0 = dx0 + 12 * s, dy0 + 48 * s
    d.line([(sx0 + 20 * s, sy0 - 26 * s), (sx0 + 40 * s, sy0 - 40 * s), (sx0 + 60 * s, sy0 - 26 * s)], fill=_rgba(LIME), width=max(2, int(3 * s)))
    d.rounded_rectangle([sx0, sy0 - 26 * s, sx0 + 80 * s, sy0 + 12 * s], radius=int(8 * s), fill=_rgba(LIME))
    d.text((sx0 + 10 * s, sy0 - 26 * s), "AÇIK", fill=NAVY, font=R.font(R.F_HEAD, int(30 * s)))
    # zemin şeridi
    d.rectangle([10 * s, h - 22 * s, w - 10 * s, h], fill=_rgba(NAVY2))
    return im


def laptop_flat(w=460):
    s = w / 460
    sw, sh = w - 60 * s, 290 * s
    h = int(sh + 50 * s)
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x0 = 30 * s
    d.rounded_rectangle([x0, 0, x0 + sw, sh], radius=int(20 * s), fill=_rgba((12, 9, 28)))
    m = 14 * s
    X0, Y0, X1, Y1 = x0 + m, m, x0 + sw - m, sh - m
    d.rectangle([X0, Y0, X1, Y1], fill=_rgba(PAPER))
    # site: menü
    d.rectangle([X0, Y0, X1, Y0 + 34 * s], fill=_rgba(NAVY))
    d.ellipse([X0 + 12 * s, Y0 + 9 * s, X0 + 28 * s, Y0 + 25 * s], fill=_rgba(LIME))
    for i in range(3):
        d.rounded_rectangle([X1 - (150 - i * 45) * s, Y0 + 14 * s, X1 - (118 - i * 45) * s, Y0 + 20 * s], radius=3, fill=_rgba(MUTED))
    # hero
    d.rectangle([X0, Y0 + 34 * s, X1, Y0 + 140 * s], fill=_rgba(NAVY2))
    d.rounded_rectangle([X0 + 20 * s, Y0 + 58 * s, X0 + 200 * s, Y0 + 74 * s], radius=6, fill=_rgba(WHITE))
    d.rounded_rectangle([X0 + 20 * s, Y0 + 84 * s, X0 + 150 * s, Y0 + 96 * s], radius=6, fill=_rgba(MUTED))
    d.rounded_rectangle([X0 + 20 * s, Y0 + 106 * s, X0 + 100 * s, Y0 + 126 * s], radius=10, fill=_rgba(LIME))
    d.rounded_rectangle([X1 - 140 * s, Y0 + 50 * s, X1 - 20 * s, Y0 + 128 * s], radius=10, fill=_rgba(LIME))
    _star(d, X1 - 80 * s, Y0 + 89 * s, 24 * s, _rgba(NAVY))
    # kartlar
    cw = (X1 - X0 - 4 * 14 * s) / 3
    for i in range(3):
        cx = X0 + 14 * s + i * (cw + 14 * s)
        d.rounded_rectangle([cx, Y0 + 156 * s, cx + cw, Y1 - 12 * s], radius=8, fill=_rgba((255, 255, 255)))
        d.rounded_rectangle([cx + 10 * s, Y0 + 166 * s, cx + cw - 10 * s, Y0 + 200 * s], radius=6, fill=_rgba(GREY))
        d.rounded_rectangle([cx + 10 * s, Y0 + 210 * s, cx + cw * 0.7, Y0 + 218 * s], radius=4, fill=_rgba(MUTED))
    # gövde
    d.polygon([(0, sh + 8 * s), (w, sh + 8 * s), (w - 18 * s, h), (18 * s, h)], fill=_rgba((70, 60, 120)))
    d.rounded_rectangle([0, sh, w, sh + 18 * s], radius=int(8 * s), fill=_rgba((150, 140, 200)))
    d.rounded_rectangle([w / 2 - 50 * s, sh, w / 2 + 50 * s, sh + 8 * s], radius=4, fill=_rgba((110, 100, 170)))
    return im


def pin_flat(w=420):
    import render as R
    s = w / 420
    h = int(w * 1.25)
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    my0 = 120 * s
    d.rounded_rectangle([0, my0, w, h], radius=int(30 * s), fill=_rgba((214, 208, 238)))
    # park, su
    d.rounded_rectangle([24 * s, my0 + 24 * s, 160 * s, my0 + 140 * s], radius=int(16 * s), fill=_rgba((176, 226, 120)))
    d.rounded_rectangle([w - 150 * s, h - 130 * s, w - 20 * s, h - 24 * s], radius=int(16 * s), fill=_rgba((140, 190, 250)))
    # yollar
    rw = int(22 * s)
    d.line([(0, my0 + 200 * s), (w, my0 + 160 * s)], fill=_rgba(WHITE), width=rw)
    d.line([(200 * s, my0), (250 * s, h)], fill=_rgba(WHITE), width=rw)
    d.line([(0, h - 70 * s), (w * 0.6, h - 120 * s)], fill=_rgba(WHITE), width=int(rw * 0.7))
    # rota
    d.line([(60 * s, h - 60 * s), (120 * s, h - 95 * s), (215 * s, h - 110 * s), (228 * s, my0 + 190 * s)],
           fill=_rgba(NAVY2), width=int(8 * s), joint="curve")
    # pin
    px, py, pr = 230 * s, my0 + 30 * s, 78 * s
    d.ellipse([px - pr, py - pr, px + pr, py + pr], fill=_rgba(LIME))
    d.polygon([(px - pr * 0.82, py + pr * 0.55), (px + pr * 0.82, py + pr * 0.55), (px, my0 + 185 * s)], fill=_rgba(LIME))
    d.ellipse([px - pr * 0.48, py - pr * 0.48, px + pr * 0.48, py + pr * 0.48], fill=_rgba(NAVY))
    mk = R.asset("logo_mark.png", max_h=int(pr * 0.6), color=LIME)
    im.alpha_composite(mk, (int(px - mk.size[0] / 2), int(py - mk.size[1] / 2)))
    d.ellipse([px - 26 * s, my0 + 178 * s, px + 26 * s, my0 + 192 * s], fill=(0, 0, 0, 60))
    return im


def stars_flat(w=420):
    import render as R
    s = w / 420
    h = int(w * 1.05)
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)

    def card(y, avatar_col, lines):
        d.rounded_rectangle([0, y, w, y + 190 * s], radius=int(26 * s), fill=_rgba((255, 255, 255)))
        d.ellipse([24 * s, y + 24 * s, 84 * s, y + 84 * s], fill=_rgba(avatar_col))
        d.rounded_rectangle([100 * s, y + 32 * s, 230 * s, y + 46 * s], radius=6, fill=_rgba(NAVY2))
        for i in range(5):
            _star(d, 112 * s + i * 34 * s, y + 70 * s, 15 * s, _rgba((255, 196, 0)))
        yy = y + 112 * s
        for L in lines:
            d.rounded_rectangle([24 * s, yy, 24 * s + L * s, yy + 12 * s], radius=6, fill=_rgba(GREY))
            yy += 26 * s

    card(0, LILAC, [330, 250])
    card(230 * s, LIME, [360, 280])
    # 5.0 rozeti
    bx, by, br = w - 70 * s, 214 * s, 64 * s
    d.ellipse([bx - br, by - br, bx + br, by + br], fill=_rgba(NAVY))
    t = "5,0"
    f = R.font(R.F_HEAD, int(50 * s))
    d.text((bx - d.textlength(t, font=f) / 2, by - 36 * s), t, fill=LIME, font=f)
    return im


def camera_flat(w=440):
    s = w / 440
    h = int(320 * s)
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([110 * s, 0, 260 * s, 70 * s], radius=int(18 * s), fill=_rgba(NAVY2))
    d.rounded_rectangle([0, 40 * s, w, h], radius=int(40 * s), fill=_rgba(NAVY))
    d.rectangle([0, 120 * s, w, 250 * s], fill=_rgba((50, 40, 96)))
    d.rounded_rectangle([w - 110 * s, 62 * s, w - 40 * s, 96 * s], radius=int(8 * s), fill=_rgba(WHITE))
    d.ellipse([40 * s, 10 * s, 92 * s, 50 * s], fill=_rgba(LIME))
    cx, cy = w / 2 + 10 * s, 190 * s
    for r, c in ((122, (70, 60, 120)), (104, LIME), (88, (30, 24, 60)), (66, (60, 70, 160)), (36, (14, 12, 34))):
        r *= s
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=_rgba(c))
    d.ellipse([cx - 40 * s, cy - 50 * s, cx - 10 * s, cy - 22 * s], fill=(255, 255, 255, 170))
    return im


def phone_flat(w=330):
    import render as R
    return R.phone_flat(w)


ART = {
    "shop": (shop_flat, 420, 30, -6),
    "laptop": (laptop_flat, 460, 22, -7),
    "pin": (pin_flat, 400, 26, -6),
    "stars": (stars_flat, 400, 18, -7),
    "camera": (camera_flat, 420, 34, -8),
    "phone": (phone_flat, 330, 22, -10),
}
_cache = {}


def art3d(kind, scale=1.0):
    """(sprite RGBA, opak sınır kutusu)"""
    k = (kind, scale)
    if k not in _cache:
        fn, w, depth, ang = ART[kind]
        flat = fn(int(w * scale))
        ex, _ = fx3d.extrude(flat, depth=int(depth * scale), side_color=(70, 60, 120))
        ex = ex.rotate(ang, resample=Image.BICUBIC, expand=True)
        box = ex.getchannel("A").point(lambda p: 255 if p > 200 else 0).getbbox()
        _cache[k] = (ex, box)
    ex, box = _cache[k]
    return ex.copy(), box
