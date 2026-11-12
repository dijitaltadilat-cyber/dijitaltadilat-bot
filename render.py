"""Dijital Tadilat görsel ve Reels üretici.

Görsel   : 1080x1080 JPEG, 5 farklı tasarım (sırayla döner)
Paketler : 4 sayfalık kaydırmalı karusel (fiyatlar)
Reels    : 1080x1920 MP4, hareketli yazılar, logolu kapanış
"""
import os
import subprocess

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import fx3d
import illus
from fx3d import cube, gradient_bg, floor_grid, raised_box, text3d, text3d_block

ROOT = os.path.dirname(os.path.abspath(__file__))
F_HEAD = os.path.join(ROOT, "fonts", "Baloo2-ExtraBold.ttf")
F_BOLD = os.path.join(ROOT, "fonts", "Nunito-Bold.ttf")
F_SEMI = os.path.join(ROOT, "fonts", "Nunito-SemiBold.ttf")
A = lambda n: os.path.join(ROOT, "assets", n)

# Marka renkleri (logodan alındı)
NAVY = (22, 16, 46)
LIME = (200, 255, 46)
WHITE = (243, 240, 255)
MUTED = (178, 172, 210)
NAVY2 = (38, 30, 72)

PHONE = "0507 295 06 55"
WA_LINE = f"WhatsApp {PHONE}"
HANDLE = "@dijitaltadilat"
WEB = "dijitaltadilat.com"

_fc, _ic = {}, {}


def font(path, size):
    k = (path, size)
    if k not in _fc:
        _fc[k] = ImageFont.truetype(path, size)
    return _fc[k]


def asset(name, max_w=None, max_h=None, color=None, opacity=1.0):
    """Logo dosyasını boyutlandırır; color verilirse tek renge boyar."""
    k = (name, max_w, max_h, color, opacity)
    if k in _ic:
        return _ic[k].copy()
    im = Image.open(A(name)).convert("RGBA")
    if max_w or max_h:
        im.thumbnail((max_w or 9999, max_h or 9999), Image.LANCZOS)
    if color:
        solid = Image.new("RGBA", im.size, color + (255,))
        solid.putalpha(im.split()[3])
        im = solid
    if opacity < 1:
        im.putalpha(im.split()[3].point(lambda p: int(p * opacity)))
    _ic[k] = im
    return im.copy()


def wrap(d, text, fnt, max_w):
    lines, line = [], ""
    for w in text.split():
        t = f"{line} {w}".strip()
        if d.textlength(t, font=fnt) <= max_w:
            line = t
        else:
            if line:
                lines.append(line)
            line = w
    if line:
        lines.append(line)
    return lines


def fit(d, text, path, size, max_w, max_lines, min_size=36):
    while True:
        f = font(path, size)
        lines = wrap(d, text, f, max_w)
        if len(lines) <= max_lines or size <= min_size:
            return f, lines, size
        size -= 4


def text_block(d, x, y, lines, fnt, lh, fill, center_w=None):
    for ln in lines:
        tx = x if center_w is None else x + (center_w - d.textlength(ln, font=fnt)) / 2
        d.text((tx, y), ln, fill=fill, font=fnt)
        y += lh
    return y


def paste3d(img, im, x, y, depth=8, side=None):
    """Şeffaf görseli 3B kabartma olarak yapıştırır."""
    ex, pad = fx3d.extrude(im, depth=depth, side_color=side)
    img.paste(ex, (x - pad, y - pad), ex)


def lockup(img, x, y, h=78, color=None):
    """Yatay logo: işaret + yazı."""
    mark = asset("logo_mark.png", max_h=h, color=color)
    word = asset("logo_word.png", max_h=int(h * 0.82), color=color)
    paste3d(img, mark, x, y, depth=max(5, h // 9))
    img.paste(word, (x + mark.size[0] + 18, y + (h - word.size[1]) // 2), word)
    return mark.size[0] + 18 + word.size[0]


def chat_icon(d, x, y, s, fill, hole):
    d.ellipse([x, y, x + s, y + s], fill=fill)
    d.polygon([(x + s * 0.12, y + s * 0.70), (x + s * 0.02, y + s * 1.0), (x + s * 0.38, y + s * 0.88)], fill=fill)
    r = s * 0.07
    for i in range(3):
        cx = x + s * (0.30 + 0.20 * i)
        d.ellipse([cx - r, y + s / 2 - r, cx + r, y + s / 2 + r], fill=hole)


def wa_pill(d, x, y, bg, fg, size=36, h=78, img=None):
    f = font(F_BOLD, size)
    tw = d.textlength(WA_LINE, font=f)
    w = int(tw + h + 40)
    if img is not None:
        raised_box(img, [x, y, x + w, y + h], h // 2, bg, depth=10)
        d = ImageDraw.Draw(img)
    else:
        d.rounded_rectangle([x, y, x + w, y + h], radius=h // 2, fill=bg)
    ic = int(h * 0.5)
    chat_icon(d, x + 24, y + (h - ic) // 2 - 2, ic, fg, bg)
    d.text((x + 24 + ic + 16, y + (h - size) // 2 - size * 0.18), WA_LINE, fill=fg, font=f)
    return w


def chip(d, x, y, label, color, filled=False, text_color=None):
    f = font(F_BOLD, 26)
    w = d.textlength(label, font=f)
    if filled:
        d.rounded_rectangle([x, y, x + w + 44, y + 52], radius=26, fill=color)
    else:
        d.rounded_rectangle([x, y, x + w + 44, y + 52], radius=26, outline=color, width=3)
    d.text((x + 22, y + 9), label, fill=text_color or color, font=f)


# --------------------------------------------------------------------------
# 3B telefon (WhatsApp / telefon / mesaj geçen paylaşımlarda)
# --------------------------------------------------------------------------
import re as _re

PHONE_RE = _re.compile(r"whatsapp|telefon|mesaj|\bdm|ara(yabil|r|y)", _re.I)
CHATS = [
    ("in", "Merhaba, bugün açık mısınız?"),
    ("out", "Açığız! Sizi bekliyoruz"),
    ("in", "Sipariş verebilir miyim?"),
    ("out", "Tabii, hemen hazırlıyoruz"),
]


def is_phone_topic(*texts):
    return bool(PHONE_RE.search(" ".join(t or "" for t in texts)))


def phone_flat(w=420, chats=CHATS):
    """Önden telefon: çerçeve + sohbet ekranı (RGBA)."""
    h = int(w * 2.05)
    s = w / 420
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=int(64 * s), fill=(12, 9, 28, 255))
    d.rounded_rectangle([4, 4, w - 5, h - 5], radius=int(60 * s), outline=(90, 80, 140, 255), width=max(2, int(3 * s)))
    m = int(16 * s)
    sx0, sy0, sx1, sy1 = m, m, w - m, h - m
    d.rounded_rectangle([sx0, sy0, sx1, sy1], radius=int(50 * s), fill=(236, 233, 248, 255))
    # üst bar
    bar = int(150 * s)
    d.rounded_rectangle([sx0, sy0, sx1, sy0 + bar], radius=int(50 * s), fill=NAVY + (255,))
    d.rectangle([sx0, sy0 + bar - int(50 * s), sx1, sy0 + bar], fill=NAVY + (255,))
    d.rounded_rectangle([w / 2 - 50 * s, sy0 + 14 * s, w / 2 + 50 * s, sy0 + 40 * s], radius=int(13 * s), fill=(0, 0, 0, 255))
    av = int(62 * s)
    ax, ay = sx0 + int(22 * s), sy0 + int(66 * s)
    d.ellipse([ax, ay, ax + av, ay + av], fill=LIME + (255,))
    mk = asset("logo_mark.png", max_h=int(av * 0.62), color=NAVY)
    im.paste(mk, (ax + (av - mk.size[0]) // 2, ay + (av - mk.size[1]) // 2), mk)
    d.text((ax + av + 16 * s, ay + 4 * s), "Dijital Tadilat", fill=WHITE, font=font(F_BOLD, int(28 * s)))
    d.text((ax + av + 16 * s, ay + 38 * s), "çevrimiçi", fill=LIME, font=font(F_SEMI, int(20 * s)))
    # mesajlar
    bf = font(F_SEMI, int(25 * s))
    y = sy0 + bar + int(30 * s)
    maxw = int((sx1 - sx0) * 0.74)
    for side, txt in chats:
        lines = wrap(d, txt, bf, maxw - int(36 * s))
        tw = max(d.textlength(l, font=bf) for l in lines)
        bw, bh = int(tw + 36 * s), int(len(lines) * 34 * s + 26 * s)
        if side == "in":
            x0, fill, fg = sx0 + int(20 * s), (255, 255, 255, 255), NAVY
        else:
            x0, fill, fg = sx1 - int(20 * s) - bw, LIME + (255,), NAVY
        d.rounded_rectangle([x0, y, x0 + bw, y + bh], radius=int(22 * s), fill=fill)
        ty = y + int(12 * s)
        for l in lines:
            d.text((x0 + 18 * s, ty), l, fill=fg, font=bf)
            ty += int(34 * s)
        y += bh + int(18 * s)
    # alt yazma kutusu
    iy = sy1 - int(90 * s)
    d.rounded_rectangle([sx0 + 18 * s, iy, sx1 - 100 * s, iy + 66 * s], radius=int(33 * s), fill=(255, 255, 255, 255))
    d.text((sx0 + 44 * s, iy + 17 * s), "Mesaj yaz...", fill=MUTED, font=bf)
    d.ellipse([sx1 - 86 * s, iy, sx1 - 20 * s, iy + 66 * s], fill=LIME + (255,))
    cx, cy = sx1 - 53 * s, iy + 33 * s
    d.polygon([(cx - 13 * s, cy - 14 * s), (cx + 16 * s, cy), (cx - 13 * s, cy + 14 * s), (cx - 7 * s, cy)], fill=NAVY + (255,))
    # ekran parlaması
    gl = Image.new("L", (w, h), 0)
    ImageDraw.Draw(gl).polygon([(w * 0.55, 0), (w, 0), (w, h * 0.35), (w * 0.15, h)], fill=26)
    wh = Image.new("RGBA", (w, h), (255, 255, 255, 255))
    gl = Image.fromarray(np.minimum(np.array(gl), np.array(im.split()[3])))
    wh.putalpha(gl)
    im.alpha_composite(wh)
    return im


_phone_cache = {}


def phone3d(w=420, angle=-9, depth=22):
    """Kalınlığı olan, hafif eğik, gölgeli telefon (RGBA) ve gölge payı."""
    k = (w, angle, depth)
    if k not in _phone_cache:
        flat = phone_flat(w)
        ex, pad = fx3d.extrude(flat, depth=depth, side_color=(70, 60, 120), direction=(1, 1))
        ex = ex.rotate(angle, resample=Image.BICUBIC, expand=True)
        _phone_cache[k] = ex
    return _phone_cache[k].copy()


# --------------------------------------------------------------------------
# Tek görseller: 5 tasarım
# --------------------------------------------------------------------------
W = 1080
X = 80
MAXW = 920


def _headline(d, post, size=92, lines=4, maxw=MAXW):
    f, ls, s = fit(d, post["headline"], F_HEAD, size, maxw, lines, min_size=56)
    return f, ls, int(s * 1.08)


def _body(d, post, size=40, lines=3, maxw=MAXW):
    f, ls, s = fit(d, post["body"], F_SEMI, size, maxw, lines, min_size=30)
    return f, ls, int(s * 1.38)


SIDE_W = (120, 104, 190)    # beyaz yazının yan yüzü (mor-lila)
SIDE_N = (118, 150, 20)     # lacivert yazının lime zemindeki yan yüzü
SIDE_L = (70, 96, 10)       # lime yazının yan yüzü


def _cubes(img, spots, top=LIME):
    for cx, cy, s in spots:
        cube(img, cx, cy, s, top)


def v_classic(post):
    img = gradient_bg((W, W), NAVY, light_xy=(0.2, 0.1), strength=2.6)
    floor_grid(img, LIME, horizon=0.66, alpha=40)
    _cubes(img, [(905, 150, 54), (990, 300, 30), (830, 330, 20)])
    d = ImageDraw.Draw(img)
    lockup(img, X, 80)
    chip(d, X, 222, post["label"], LIME)
    hf, hl, hlh = _headline(d, post)
    bf, bl, blh = _body(d, post)
    block = len(hl) * hlh + 30 + len(bl) * blh
    y = 300 + max(0, (590 - block) // 2)
    y = text3d_block(img, X, y, hl, hf, hlh, WHITE, SIDE_W, depth=9) + 30
    text_block(ImageDraw.Draw(img), X, y, bl, bf, blh, MUTED)
    wa_pill(d, X, 920, LIME, NAVY, img=img)
    return img


def v_lime(post):
    img = gradient_bg((W, W), LIME, light_xy=(0.15, 0.1), strength=1.25, falloff=0.9)
    floor_grid(img, NAVY, horizon=0.68, alpha=30)
    _cubes(img, [(915, 160, 50), (1000, 300, 28)], top=NAVY2)
    d = ImageDraw.Draw(img)
    lockup(img, X, 80, color=NAVY)
    chip(d, X, 222, post["label"], NAVY)
    hf, hl, hlh = _headline(d, post, size=100)
    bf, bl, blh = _body(d, post)
    block = len(hl) * hlh + 30 + len(bl) * blh
    y = 300 + max(0, (590 - block) // 2)
    y = text3d_block(img, X, y, hl, hf, hlh, NAVY, SIDE_N, depth=9) + 30
    text_block(ImageDraw.Draw(img), X, y, bl, bf, blh, NAVY2)
    wa_pill(d, X, 920, NAVY, LIME, img=img)
    return img


def v_watermark(post):
    img = gradient_bg((W, W), NAVY, light_xy=(0.85, 0.85), strength=2.8)
    big = asset("logo_mark.png", max_h=640, color=(120, 100, 210))
    ex, pad = fx3d.extrude(big, depth=36, side_color=(70, 55, 140), shadow=False)
    ex.putalpha(ex.split()[3].point(lambda p: int(p * 0.30)))
    img.paste(ex, (W - big.size[0] + 60 - pad, W - big.size[1] + 10 - pad), ex)
    d = ImageDraw.Draw(img)
    mark = asset("logo_mark.png", max_h=70)
    paste3d(img, mark, X, 80, depth=7)
    d.text((X + mark.size[0] + 20, 92), post["label"], fill=LIME, font=font(F_BOLD, 30))
    hf, hl, hlh = _headline(d, post, size=96, maxw=860)
    bf, bl, blh = _body(d, post, maxw=800)
    block = len(hl) * hlh + 34 + len(bl) * blh
    y = 220 + max(0, (660 - block) // 2)
    y = text3d_block(img, X, y, hl, hf, hlh, LIME, SIDE_L, depth=10) + 34
    text_block(ImageDraw.Draw(img), X, y, bl, bf, blh, WHITE)
    wa_pill(d, X, 920, WHITE, NAVY, img=img)
    return img


def v_card(post):
    img = gradient_bg((W, W), NAVY, light_xy=(0.5, 0.0), strength=2.6)
    _cubes(img, [(985, 95, 34), (40, 905, 26)])
    d = ImageDraw.Draw(img)
    lockup(img, X, 54, h=64)
    raised_box(img, [60, 165, W - 60, 865], 44, WHITE, depth=18)
    d = ImageDraw.Draw(img)
    chip(d, 110, 215, post["label"], NAVY, filled=True, text_color=LIME)
    hf, hl, hlh = _headline(d, post, size=84, maxw=820)
    bf, bl, blh = _body(d, post, size=38, maxw=820)
    block = len(hl) * hlh + 28 + len(bl) * blh
    y = 295 + max(0, (540 - block) // 2)
    y = text3d_block(img, 110, y, hl, hf, hlh, NAVY, (150, 145, 190), depth=6) + 28
    d = ImageDraw.Draw(img)
    text_block(d, 110, y, bl, bf, blh, NAVY2)
    wa_pill(d, X, 925, LIME, NAVY, size=34, h=72, img=img)
    d = ImageDraw.Draw(img)
    d.text((W - X - d.textlength(WEB, font=font(F_SEMI, 30)), 945), WEB,
           fill=MUTED, font=font(F_SEMI, 30))
    return img


def v_split(post):
    img = gradient_bg((W, W), NAVY, light_xy=(0.5, 1.0), strength=2.4)
    top = gradient_bg((W, 620), LIME, light_xy=(0.2, 0.0), strength=1.25, falloff=1.0)
    # lime blok, altında kalınlık ve gölge
    fx3d.soft_shadow(img, [0, 0, W, 620], 0, offset=(0, 30), blur=30, opacity=170)
    ImageDraw.Draw(img).rectangle([0, 600, W, 640], fill=shade_l(LIME, 0.6))
    img.paste(top, (0, 0))
    _cubes(img, [(940, 150, 46), (1020, 280, 24)], top=NAVY2)
    d = ImageDraw.Draw(img)
    mark = asset("logo_mark.png", max_h=64, color=NAVY)
    paste3d(img, mark, X, 70, depth=6, side=(60, 80, 10))
    d.text((X + mark.size[0] + 18, 80), post["label"], fill=NAVY, font=font(F_BOLD, 30))
    hf, hl, hlh = _headline(d, post, size=96, lines=4)
    y = 170 + max(0, (420 - len(hl) * hlh) // 2)
    text3d_block(img, X, y, hl, hf, hlh, NAVY, SIDE_N, depth=9)
    d = ImageDraw.Draw(img)
    bf, bl, blh = _body(d, post, size=40, lines=2)
    text_block(d, X, 690, bl, bf, blh, WHITE)
    wa_pill(d, X, 895, LIME, NAVY, img=img)
    word = asset("logo_word.png", max_h=70)
    img.paste(word, (W - X - word.size[0], 899), word)
    return img


def shade_l(c, k):
    return fx3d.shade(c, k)


VARIANTS = [v_classic, v_lime, v_watermark, v_card, v_split]


def v_art(post, kind, lime=False):
    """Konulu paylaşımlar: solda yazı, sağda konuya uygun 3B çizim."""
    bg, fg, sub, side = (LIME, NAVY, NAVY2, SIDE_N) if lime else (NAVY, WHITE, MUTED, SIDE_W)
    img = gradient_bg((W, W), bg, light_xy=(0.8, 0.35), strength=1.25 if lime else 2.6, falloff=0.85)
    floor_grid(img, NAVY if lime else LIME, horizon=0.7, alpha=30 if lime else 40)
    ph, (bx0, by0, bx1, by1) = illus.art3d(kind)
    # sağ sütuna (x 610-1055, y 140-890) sığdır, sağa yasla, dikeyde ortala
    k = min(1.0, 420 / (bx1 - bx0), 740 / (by1 - by0))
    if k < 1:
        ph = ph.resize((int(ph.size[0] * k), int(ph.size[1] * k)), Image.LANCZOS)
        bx0, by0, bx1, by1 = [int(v * k) for v in (bx0, by0, bx1, by1)]
    bh = by1 - by0
    img.paste(ph, (int(1055 - bx1), int(515 - bh / 2 - by0)), ph)
    _cubes(img, [(640, 150, 30), (1000, 960, 24)], top=NAVY2 if lime else LIME)
    d = ImageDraw.Draw(img)
    lockup(img, X, 80, color=NAVY if lime else None)
    chip(d, X, 222, post["label"], NAVY if lime else LIME)
    hf, hl, hlh = _headline(d, post, size=74, lines=5, maxw=500)
    bf, bl, blh = _body(d, post, size=34, lines=4, maxw=470)
    block = len(hl) * hlh + 28 + len(bl) * blh
    y = 300 + max(0, (590 - block) // 2)
    y = text3d_block(img, X, y, hl, hf, hlh, fg, side, depth=8) + 28
    text_block(ImageDraw.Draw(img), X, y, bl, bf, blh, sub)
    wa_pill(d, X, 920, NAVY if lime else LIME, LIME if lime else NAVY, img=img)
    return img


def make_image(post, out_path, variant=0):
    kind = illus.topic_of(post.get("headline"), post.get("body"))
    if kind:
        img = v_art(post, kind, lime=variant % 2 == 1)
    else:
        img = VARIANTS[variant % len(VARIANTS)](post)
    img.save(out_path, "JPEG", quality=94)
    return out_path


# --------------------------------------------------------------------------
# Paketler (karusel) ve kampanya
# --------------------------------------------------------------------------
PACKAGES = [
    {"name": "BAŞLANGIÇ", "price": "3.990", "tag": None,
     "items": ["Ayda 8 gönderi", "Haftada 3 story", "Profil tadilatı", "Aylık mini rapor"]},
    {"name": "STANDART", "price": "6.990", "tag": "EN ÇOK TERCİH EDİLEN",
     "items": ["Ayda 12 gönderi + 4 Reels", "Haftada 5 story", "Google İşletme profili",
               "Yorum ve mesaj takibi", "Aylık rapor"]},
    {"name": "PRO", "price": "10.990", "tag": None,
     "items": ["Ayda 16 gönderi + 8 Reels", "Her gün story", "Ayda 1 dükkânda çekim",
               "Reklam kurulumu ve yönetimi", "Aylık strateji görüşmesi"]},
]


def _check(d, x, y, s, color):
    d.line([(x, y + s * 0.55), (x + s * 0.38, y + s * 0.9), (x + s, y + s * 0.1)], fill=color, width=7)


def packages_cover():
    img = gradient_bg((W, W), NAVY, light_xy=(0.5, 0.3), strength=2.6)
    floor_grid(img, LIME, horizon=0.6, alpha=35)
    d = ImageDraw.Draw(img)
    big = asset("logo_mark.png", max_h=480)
    paste3d(img, big, (W - big.size[0]) // 2 - 10, 90, depth=30)
    f = font(F_HEAD, 120)
    t = "Paketler & Fiyatlar"
    lines = wrap(d, t, f, 940)
    y = 640
    y = text3d_block(img, 70, y, lines, f, 118, WHITE, SIDE_W, depth=10, center_w=940)
    d = ImageDraw.Draw(img)
    s = "Kaydır, dükkânına uygun paketi seç"
    sf = font(F_SEMI, 38)
    d.text(((W - d.textlength(s, font=sf)) / 2, 930), s, fill=LIME, font=sf)
    return img


def package_slide(p):
    hl = p["tag"] is not None
    bg, fg, sub, acc = (LIME, NAVY, NAVY2, NAVY) if hl else (NAVY, WHITE, MUTED, LIME)
    img = gradient_bg((W, W), bg, light_xy=(0.2, 0.1), strength=1.25 if hl else 2.6)
    _cubes(img, [(930, 170, 50), (1010, 310, 26)], top=NAVY2 if hl else LIME)
    d = ImageDraw.Draw(img)
    lockup(img, X, 70, h=60, color=NAVY if hl else None)
    if p["tag"]:
        chip(d, X, 170, p["tag"], NAVY, filled=True, text_color=LIME)
    d.text((X, 240), p["name"], fill=acc, font=font(F_BOLD, 46))
    pf = font(F_HEAD, 170)
    text3d(img, (X, 280), p["price"], pf, fg, SIDE_N if hl else SIDE_W, depth=14)
    d = ImageDraw.Draw(img)
    pw = d.textlength(p["price"], font=pf)
    d.text((X + pw + 16, 360), "₺ / ay", fill=sub, font=font(F_BOLD, 52))
    y = 520
    itf = font(F_SEMI, 44)
    for it in p["items"]:
        _check(d, X, y + 12, 34, acc)
        d.text((X + 60, y), it, fill=fg, font=itf)
        y += 70
    wa_pill(d, X, 920, NAVY if hl else LIME, LIME if hl else NAVY, size=34, h=72, img=img)
    return img


def make_packages(out_prefix):
    slides = [packages_cover()] + [package_slide(p) for p in PACKAGES] + [campaign_image()]
    paths = []
    for i, im in enumerate(slides):
        p = f"{out_prefix}-{i}.jpg"
        im.save(p, "JPEG", quality=94)
        paths.append(p)
    return paths


def campaign_image():
    img = gradient_bg((W, W), LIME, light_xy=(0.2, 0.1), strength=1.25, falloff=0.9)
    _cubes(img, [(900, 470, 70), (1000, 640, 34)], top=NAVY2)
    d = ImageDraw.Draw(img)
    lockup(img, X, 80, color=NAVY)
    chip(d, X, 210, "AÇILIŞA ÖZEL", NAVY, filled=True, text_color=LIME)
    text3d(img, (X, 270), "İlk 5 esnafa", font(F_HEAD, 96), NAVY, SIDE_N, depth=8)
    text3d(img, (X - 6, 340), "%50", font(F_HEAD, 300), NAVY, SIDE_N, depth=22)
    text3d(img, (X, 660), "ilk ay indirim", font(F_HEAD, 96), NAVY, SIDE_N, depth=8)
    d = ImageDraw.Draw(img)
    sf = font(F_SEMI, 38)
    d.text((X, 790), "Taahhüt yok · Ücretsiz ilk görüşme", fill=NAVY2, font=sf)
    wa_pill(d, X, 900, NAVY, LIME, img=img)
    return img


def make_campaign(out_path):
    campaign_image().save(out_path, "JPEG", quality=94)
    return out_path


# --------------------------------------------------------------------------
# Reels
# --------------------------------------------------------------------------
FPS = 30
RW, RH = 1080, 1920


def ease(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def mix(c, a, bg=NAVY):
    return tuple(int(bg[i] + (c[i] - bg[i]) * a) for i in range(3))


def _layout(slides):
    d = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    blocks = []
    f, ls, s = fit(d, slides[0], F_HEAD, 124, 920, 4, min_size=80)
    blocks.append((f, ls, int(s * 1.05), WHITE))
    for t in slides[1:]:
        f, ls, s = fit(d, t, F_HEAD, 88, 920, 3, min_size=56)
        num = t[:2].strip(". ").isdigit()
        blocks.append((f, ls, int(s * 1.1), LIME if num or "₺" in t or "%" in t else WHITE))
    gh, g = 120, 40
    total = sum(len(b[1]) * b[2] for b in blocks) + gh + g * (len(blocks) - 2)
    return blocks, total, gh, g


def make_reel(reel, out_path, slide_dur=None, hold=None, end_dur=None, music=None):
    # Zamanlama müziğin vuruşlarına göre: her yazı 3 vuruşta bir gelir.
    # music = music.settings(n): her Reels'te farklı tarz / tempo / ton.
    import tempfile
    import zlib

    from music import make_track
    if music is None:
        music = {"seed": zlib.crc32(" ".join(reel["slides"]).encode()) % 1000, "bpm": 112, "style": None}
    BEAT = 60 / music["bpm"]
    slide_dur = slide_dur or 3 * BEAT
    hold = hold or 2 * BEAT
    end_dur = end_dur or 6 * BEAT
    slides = reel["slides"]
    blocks, total_h, gh, g = _layout(slides)
    top, bottom = 380, 1450
    sy = top + max(0, (bottom - top - total_h) // 2)
    lead = BEAT  # ilk yazı ikinci vuruşta, sonrakiler her 3 vuruşta bir
    text_dur = lead + slide_dur * len(slides) + hold
    total = text_dur + end_dur
    n = int(total * FPS)

    seed = music["seed"]
    wav = os.path.join(tempfile.mkdtemp(), "m.wav")
    make_track(total + 0.2, seed, wav, bpm=music["bpm"], style=music.get("style"))

    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{RW}x{RH}", "-r", str(FPS), "-i", "-",
           "-i", wav, "-shortest",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
           "-profile:v", "high", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", out_path]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    # --- 3B sahne parçaları bir kez hazırlanır, karelerde sadece yapıştırılır ---
    base = gradient_bg((RW, RH), NAVY, light_xy=(0.3, 0.25), strength=2.6, falloff=0.8)
    floor_grid(base, LIME, horizon=0.72, alpha=38)
    bm = asset("logo_mark.png", max_h=820, color=(120, 100, 210))
    bg_mark, _ = fx3d.extrude(bm, depth=40, side_color=(70, 55, 140), shadow=False)
    bg_mark.putalpha(bg_mark.split()[3].point(lambda p: int(p * 0.22)))

    def cube_sprite(sz, top):
        c = Image.new("RGBA", (int(sz * 2.6), int(sz * 3.2)), (0, 0, 0, 0))
        cube(c, c.size[0] / 2, sz * 0.8, sz, top)
        return c
    cubes = [(cube_sprite(70, LIME), 860, 330, 0.0), (cube_sprite(36, LIME), 990, 560, 1.3),
             (cube_sprite(28, LIME), 120, 1560, 2.1), (cube_sprite(46, NAVY2), 930, 1640, 0.7)]

    head_lock = Image.new("RGBA", (760, 140), (0, 0, 0, 0))
    lockup(head_lock, 30, 20, h=72)

    def line_sprite(text, f, col):
        tw = int(ImageDraw.Draw(Image.new("L", (1, 1))).textlength(text, font=f))
        sz = f.size
        dep = max(6, sz // 10)
        side = SIDE_L if col == LIME else SIDE_W
        sp = Image.new("RGBA", (tw + 120, int(sz * 1.6) + 80), (0, 0, 0, 0))
        text3d(sp, (20, 10), text, f, col, side, depth=dep)
        return sp
    sprites = [[line_sprite(ln, f, col) for ln in ls] for f, ls, lh, col in blocks]

    def fade(im, a):
        if a >= 1:
            return im
        im = im.copy()
        im.putalpha(im.split()[3].point(lambda p: int(p * a)))
        return im

    # kapanış: 3B logo + 3B telefon + yükselen buton
    lg = asset("logo.png", max_h=380)
    end_logo, lpad = fx3d.extrude(lg, depth=16)
    end_kind = illus.topic_of(*slides) or ["shop", "phone", "laptop", "stars", "pin", "camera"][seed % 6]
    end_phone, pbx = illus.art3d(end_kind, scale=0.85)
    cta_card = Image.new("RGBA", (620, 520), (0, 0, 0, 0))
    cd = ImageDraw.Draw(cta_card)
    cf = font(F_HEAD, 54)
    cta = "WhatsApp'tan yaz"
    cw = int(cd.textlength(cta, font=cf))
    raised_box(cta_card, [10, 20, 10 + cw + 80, 120], 50, LIME, depth=12)
    cd = ImageDraw.Draw(cta_card)
    cd.text((50, 34), cta, fill=NAVY, font=cf)
    text3d(cta_card, (10, 175), PHONE, font(F_HEAD, 70), WHITE, SIDE_W, depth=7)
    cd = ImageDraw.Draw(cta_card)
    cd.text((12, 300), WEB, fill=MUTED, font=font(F_BOLD, 42))
    import math

    for i in range(n):
        t = i / FPS
        img = base.copy()
        img.paste(bg_mark, (int(RW - bg_mark.size[0] + 300 - t * 18), int(RH - bg_mark.size[1] - 60 + t * 10)), bg_mark)
        for sp, cx, cy, ph in cubes:
            bob = math.sin(t * 1.6 + ph) * 14
            img.paste(sp, (int(cx - sp.size[0] / 2), int(cy - sp.size[1] / 3 + bob)), sp)
        d = ImageDraw.Draw(img)
        d.rectangle([0, 0, int(RW * t / total), 12], fill=LIME)

        if t < text_dur:
            fo = 1 - ease((t - (text_dur - 0.4)) / 0.4) if t > text_dur - 0.4 else 1.0
            ha = ease(t / 0.5) * fo
            if ha > 0:
                hl_ = fade(head_lock, ha)
                img.paste(hl_, (50, 190), hl_)
            y = sy
            for bi, (f, ls, lh, col) in enumerate(blocks):
                ap = lead + bi * slide_dur - 0.08
                for li, ln in enumerate(ls):
                    lt = (t - ap - li * 0.08) / 0.45
                    a = ease(lt) * fo
                    if a > 0:
                        sp = fade(sprites[bi][li], a)
                        img.paste(sp, (60, y - 10 + int((1 - ease(lt)) * 56)), sp)
                    y += lh
                if bi == 0:
                    bt = ease((t - ap - 0.3) / 0.5)
                    if bt > 0:
                        d.rounded_rectangle([80, y + 44, 80 + int(180 * bt), y + 58], radius=7, fill=mix(LIME, fo))
                    y += gh
                else:
                    y += g
        else:
            et = t - text_dur
            a = ease(et / 0.5)
            s = 0.85 + 0.15 * ease(et / 0.7)
            el = end_logo.resize((int(end_logo.size[0] * s), int(end_logo.size[1] * s)), Image.LANCZOS)
            el = fade(el, a)
            img.paste(el, ((RW - el.size[0]) // 2, 300 - int(lpad * s) - (el.size[1] - end_logo.size[1]) // 2), el)
            tf = font(F_SEMI, 44)
            line = "Sosyal medya ajansı & yazılım"
            d = ImageDraw.Draw(img)
            d.text(((RW - d.textlength(line, font=tf)) / 2, 760), line, fill=mix(MUTED, a), font=tf)
            # telefon sağdan yükselir
            pt = ease((et - 0.3) / 0.7)
            if pt > 0:
                ep = fade(end_phone, pt)
                pcx = 1050 - (pbx[2] - pbx[0]) / 2 if pbx[2] - pbx[0] < 420 else RW - 30 - (pbx[2] - pbx[0]) / 2
                pcy = 1300
                img.paste(ep, (int(pcx - (pbx[2] + pbx[0]) / 2), int(pcy - (pbx[3] + pbx[1]) / 2 + (1 - pt) * 220)), ep)
            ct = ease((et - 0.6) / 0.5)
            if ct > 0:
                cc = fade(cta_card, ct)
                img.paste(cc, (70, 1000 + int((1 - ct) * 50)), cc)

        proc.stdin.write(img.tobytes())

    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError("ffmpeg video üretemedi")
    return out_path


if __name__ == "__main__":
    import json
    import sys

    with open(os.path.join(ROOT, "content", "content.json"), encoding="utf-8") as fh:
        content = json.load(fh)
    os.makedirs("preview", exist_ok=True)
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    singles = [p for p in content["posts"] if p.get("type", "single") == "single"]
    if which in ("all", "image"):
        for v in range(len(VARIANTS)):
            make_image(singles[v + 1], f"preview/v{v}.jpg", v)
    if which in ("all", "packages"):
        make_packages("preview/pkg")
    if which in ("all", "reel"):
        make_reel(content["reels"][1], "preview/reel.mp4")
    print("Önizlemeler preview/ klasöründe.")
