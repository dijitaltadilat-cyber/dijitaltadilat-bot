"""Sektöre özel 3B görünümlü nesneler (araba, berber direği, manav kasası...).

art(kind) -> RGBA görsel (şeffaf zemin, gölgeli, ışıklı)
sector_of(post) -> kind ya da None

Hepsi kodla çizilir: degrade dolgu + yumuşak gölge + parlama ile 3B hissi.
"""
import math
import random
import re

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

LIME = (200, 255, 46)
NAVY = (22, 16, 46)
CW, CH = 1000, 800          # çizim tuvali (sonra küçültülür → yumuşak kenar)


# ------------------------------------------------------------ 3B araç kiti
def sh(c, k):
    """Rengi açar (k>1) ya da koyulaştırır (k<1)."""
    if k >= 1:
        return tuple(int(v + (255 - v) * (k - 1)) for v in c)
    return tuple(int(v * k) for v in c)


def grad(size, c0, c1, horiz=False):
    w, h = max(1, int(size[0])), max(1, int(size[1]))
    t = np.linspace(0, 1, w if horiz else h)
    arr = np.array(c0)[None] * (1 - t)[:, None] + np.array(c1)[None] * t[:, None]
    arr = arr[None, :, :] if horiz else arr[:, None, :]
    arr = np.broadcast_to(arr, (h, w, 3)).astype(np.uint8)
    return Image.fromarray(np.ascontiguousarray(arr), "RGB").convert("RGBA")


def cyl_grad(size, c):
    """Silindir gibi yatay ışık: kenarlar koyu, sol-orta parlak."""
    w, h = max(1, int(size[0])), max(1, int(size[1]))
    x = np.linspace(-1, 1, w)
    k = 0.45 + 0.75 * np.clip(np.cos((x + 0.35) * 1.25), 0, 1) + 0.25 * np.exp(-((x + 0.45) / 0.12) ** 2)
    arr = np.clip(np.array(c)[None] * k[:, None] + 255 * np.clip(k - 1, 0, 1)[:, None] * 0.6, 0, 255)
    arr = np.broadcast_to(arr[None], (h, w, 3)).astype(np.uint8)
    return Image.fromarray(np.ascontiguousarray(arr), "RGB").convert("RGBA")


def sphere_grad(size, c, light=(0.35, 0.3)):
    w, h = max(1, int(size[0])), max(1, int(size[1]))
    y, x = np.mgrid[0:h, 0:w]
    dx, dy = x / w - light[0], y / h - light[1]
    d = np.sqrt(dx ** 2 + dy ** 2)
    k = np.clip(1.25 - d * 1.2, 0.35, 1.25)
    arr = np.clip(np.array(c)[None, None] * k[..., None] + 255 * np.clip(k - 1, 0, 1)[..., None], 0, 255)
    return Image.fromarray(arr.astype(np.uint8), "RGB").convert("RGBA")


def fill(img, box, draw_mask, src):
    """box içine draw_mask(d, w, h) ile çizilen şekli src dokusuyla doldurur."""
    x0, y0, x1, y1 = [int(v) for v in box]
    w, h = max(1, x1 - x0), max(1, y1 - y0)
    m = Image.new("L", (w, h), 0)
    draw_mask(ImageDraw.Draw(m), w, h)
    tex = src((w, h)) if callable(src) else src.resize((w, h))
    tex.putalpha(Image.composite(tex.getchannel("A"), Image.new("L", (w, h), 0), m))
    img.alpha_composite(tex, (x0, y0))


def ell(img, box, c, kind="sphere", light=(0.35, 0.3)):
    f = {"sphere": lambda s: sphere_grad(s, c, light), "cyl": lambda s: cyl_grad(s, c),
         "flat": lambda s: Image.new("RGBA", s, c + (255,)),
         "v": lambda s: grad(s, sh(c, 1.25), sh(c, 0.6))}[kind]
    fill(img, box, lambda d, w, h: d.ellipse([0, 0, w - 1, h - 1], fill=255), f)


def rrect(img, box, r, c, kind="v"):
    f = {"v": lambda s: grad(s, sh(c, 1.2), sh(c, 0.62)), "h": lambda s: grad(s, sh(c, 1.2), sh(c, 0.62), True),
         "cyl": lambda s: cyl_grad(s, c), "flat": lambda s: Image.new("RGBA", s, c + (255,))}[kind]
    fill(img, box, lambda d, w, h: d.rounded_rectangle([0, 0, w - 1, h - 1], radius=int(r), fill=255), f)


def poly(img, pts, c, kind="v"):
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    box = (min(xs), min(ys), max(xs) + 1, max(ys) + 1)
    loc = [(x - box[0], y - box[1]) for x, y in pts]
    f = {"v": lambda s: grad(s, sh(c, 1.2), sh(c, 0.62)), "h": lambda s: grad(s, sh(c, 1.15), sh(c, 0.6), True),
         "cyl": lambda s: cyl_grad(s, c), "flat": lambda s: Image.new("RGBA", s, c + (255,)),
         "sphere": lambda s: sphere_grad(s, c)}[kind]
    fill(img, box, lambda d, w, h: d.polygon(loc, fill=255), f)


def shadow(img, box, alpha=150, blur=22):
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(lay).ellipse(box, fill=(0, 0, 0, alpha))
    img.alpha_composite(lay.filter(ImageFilter.GaussianBlur(blur)))


def shine(img, box, alpha=120, blur=8, shape="ellipse"):
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    if shape == "ellipse":
        d.ellipse(box, fill=(255, 255, 255, alpha))
    else:
        d.rounded_rectangle(box, radius=(box[3] - box[1]) // 2, fill=(255, 255, 255, alpha))
    img.alpha_composite(lay.filter(ImageFilter.GaussianBlur(blur)))


def line(img, pts, c, w, alpha=255):
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(lay).line(pts, fill=c + (alpha,), width=int(w), joint="curve")
    img.alpha_composite(lay)


def canvas():
    return Image.new("RGBA", (CW, CH), (0, 0, 0, 0))


# ------------------------------------------------------------ nesneler
def wheel(img, cx, cy, r):
    ell(img, (cx - r, cy - r, cx + r, cy + r), (30, 28, 40), "sphere")
    ell(img, (cx - r * 0.62, cy - r * 0.62, cx + r * 0.62, cy + r * 0.62), (200, 200, 215), "sphere")
    for k in range(5):
        a = k * 2 * math.pi / 5 - 0.3
        line(img, [(cx, cy), (cx + r * 0.55 * math.cos(a), cy + r * 0.55 * math.sin(a))], (120, 120, 140), r * 0.12)
    ell(img, (cx - r * 0.18, cy - r * 0.18, cx + r * 0.18, cy + r * 0.18), LIME, "sphere")


def car(img=None, color=(230, 40, 60), wash=False):
    img = img or canvas()
    shadow(img, (90, 600, 910, 690), 170, 20)
    # gövde
    poly(img, [(110, 520), (180, 455), (300, 430), (700, 430), (850, 470), (905, 520), (905, 600), (95, 600), (95, 545)], color, "v")
    # kabin
    poly(img, [(270, 440), (370, 330), (610, 322), (735, 440)], sh(color, 0.9), "v")
    # camlar
    poly(img, [(305, 432), (385, 350), (480, 346), (480, 432)], (40, 60, 110), "v")
    poly(img, [(500, 432), (500, 344), (600, 342), (695, 432)], (40, 60, 110), "v")
    line(img, [(330, 425), (400, 355)], (255, 255, 255), 10, 90)
    line(img, [(530, 425), (590, 350)], (255, 255, 255), 10, 90)
    # kapı çizgisi, kolu
    line(img, [(490, 440), (490, 590)], sh(color, 0.55), 4)
    rrect(img, (420, 470, 470, 482), 6, (220, 220, 230), "flat")
    rrect(img, (560, 470, 610, 482), 6, (220, 220, 230), "flat")
    # far / stop
    rrect(img, (852, 500, 900, 530), 12, (255, 240, 170), "v")
    rrect(img, (96, 500, 130, 528), 10, (255, 70, 70), "v")
    rrect(img, (95, 580, 905, 606), 12, (40, 38, 52), "v")  # tampon hattı
    shine(img, (200, 440, 760, 470), 110, 10, "pill")
    wheel(img, 255, 600, 88)
    wheel(img, 745, 600, 88)
    if wash:
        rng = random.Random(4)
        for _ in range(16):
            x, y, r = rng.randint(80, 920), rng.randint(250, 640), rng.randint(16, 46)
            lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
            ImageDraw.Draw(lay).ellipse([x - r, y - r, x + r, y + r], fill=(200, 230, 255, 70), outline=(255, 255, 255, 200), width=4)
            img.alpha_composite(lay)
            shine(img, (x - r * 0.5, y - r * 0.6, x - r * 0.1, y - r * 0.2), 200, 2)
    return img


def scissors(img, cx, cy, s=1.0, rot=0):
    lay = canvas()
    steel = (215, 215, 232)
    # bıçaklar (kalın, sivri)
    poly(lay, [(470, 372), (505, 360), (850, 245), (862, 262), (520, 420)], steel, "v")
    poly(lay, [(470, 428), (505, 440), (850, 555), (862, 538), (520, 380)], sh(steel, 0.85), "v")
    shine(lay, (560, 300, 800, 320), 150, 4, "pill")
    # saplar + halkalar
    line(lay, [(500, 390), (400, 330)], LIME, 34)
    line(lay, [(500, 410), (400, 470)], LIME, 34)
    for y0 in (315, 485):
        ring = Image.new("RGBA", lay.size, (0, 0, 0, 0))
        ImageDraw.Draw(ring).ellipse([270, y0 - 75, 420, y0 + 75], outline=LIME + (255,), width=34)
        lay.alpha_composite(ring)
        shine(lay, (290, y0 - 70, 340, y0 - 40), 140, 5)
    ell(lay, (486, 386, 516, 416), (80, 80, 100), "sphere")
    lay = lay.rotate(rot, center=(500, 400), resample=Image.BICUBIC)
    lay = lay.resize((int(CW * s), int(CH * s)), Image.LANCZOS)
    img.alpha_composite(lay, (int(cx - 500 * s), int(cy - 400 * s)))


def comb(img, x, y, w, h, c=(30, 30, 40)):
    rrect(img, (x, y, x + w, y + h * 0.35), 10, c, "v")
    for k in range(int(w // 18)):
        rrect(img, (x + 8 + k * 18, y + h * 0.3, x + 18 + k * 18, y + h), 4, c, "h")


def barber():
    img = canvas()
    shadow(img, (120, 690, 420, 740), 160, 18)
    # direk: kırmızı-beyaz-mavi şerit + silindir ışığı
    x0, y0, x1, y1 = 200, 150, 340, 680
    pw, phh = x1 - x0, y1 - y0
    stripes = Image.new("RGBA", (pw * 3, phh * 3), (250, 250, 250, 255))
    sd = ImageDraw.Draw(stripes)
    cols = [(220, 30, 50), (250, 250, 250), (30, 60, 170), (250, 250, 250)]
    for k in range(-30, 60):
        c = cols[k % 4]
        sd.polygon([(0, k * 40), (pw * 3, k * 40 - 160), (pw * 3, k * 40 - 120), (0, k * 40 + 40)], fill=c + (255,))
    stripes = stripes.crop((pw, phh, pw * 2, phh * 2))
    shade = cyl_grad((pw, phh), (128, 128, 128))
    arr = np.array(stripes).astype(float)
    k = np.array(shade)[..., :1].astype(float) / 128
    arr[..., :3] = np.clip(arr[..., :3] * k * 0.95 + 30 * np.clip(k - 1.1, 0, 1), 0, 255)
    img.alpha_composite(Image.fromarray(arr.astype(np.uint8), "RGBA"), (x0, y0))
    shine(img, (x0 + 22, y0 + 20, x0 + 46, y1 - 20), 110, 6, "pill")
    # kapaklar
    rrect(img, (x0 - 18, y0 - 46, x1 + 18, y0 + 6), 14, (210, 210, 225), "cyl")
    ell(img, (x0 + 30, y0 - 120, x1 - 30, y0 - 40), (230, 230, 240), "sphere")
    rrect(img, (x0 - 18, y1 - 6, x1 + 18, y1 + 46), 14, (210, 210, 225), "cyl")
    # makas + tarak
    comb(img, 470, 560, 380, 110)
    scissors(img, 640, 330, 0.95, 20)
    return img


def salon():
    img = canvas()
    shadow(img, (300, 660, 820, 730), 150, 20)
    # fön makinesi
    rrect(img, (300, 220, 700, 400), 90, (200, 60, 140), "v")
    ell(img, (230, 220, 410, 400), sh((200, 60, 140), 1.1), "sphere")
    rrect(img, (690, 255, 800, 365), 30, (60, 50, 80), "v")
    rrect(img, (480, 360, 580, 640), 40, sh((200, 60, 140), 0.85), "h")
    ell(img, (262, 255, 378, 365), (50, 40, 70), "sphere")
    shine(img, (340, 235, 640, 265), 140, 8, "pill")
    rrect(img, (510, 520, 550, 560), 10, LIME, "flat")
    scissors(img, 760, 520, 0.6, -30)
    comb(img, 120, 600, 260, 80, (240, 200, 60))
    return img


def fruit(img, cx, cy, r, c, leaf=True):
    ell(img, (cx - r, cy - r, cx + r, cy + r), c, "sphere")
    if leaf:
        line(img, [(cx, cy - r * 0.8), (cx + 4, cy - r * 1.15)], (90, 60, 30), r * 0.12)
        poly(img, [(cx + 4, cy - r * 1.05), (cx + r * 0.6, cy - r * 1.3), (cx + r * 0.25, cy - r * 0.9)], (60, 170, 60), "v")


def produce():
    img = canvas()
    shadow(img, (130, 680, 870, 750), 170, 22)
    rng = random.Random(2)
    # kasanın arka kenarı
    poly(img, [(170, 380), (830, 380), (870, 420), (130, 420)], (130, 80, 40), "v")
    # meyveler (arkadan öne)
    items = [(250, 360, 70, (240, 140, 20)), (380, 340, 72, (215, 30, 40)), (520, 345, 75, (240, 140, 20)),
             (660, 340, 70, (215, 30, 40)), (770, 365, 62, (120, 190, 40)),
             (300, 420, 72, (215, 30, 40)), (450, 415, 75, (120, 190, 40)), (600, 420, 74, (240, 140, 20)),
             (730, 420, 70, (215, 30, 40))]
    for x, y, r, c in items:
        fruit(img, x + rng.randint(-8, 8), y, r, c, leaf=c != (240, 140, 20))
    # muz
    poly(img, [(330, 300), (420, 250), (560, 245), (640, 290), (560, 275), (430, 285)], (250, 215, 40), "v")
    # marul
    for k in range(6):
        ell(img, (120 + k * 18, 250 + (k % 2) * 30, 250 + k * 18, 380), sh((70, 170, 60), 0.85 + k * 0.05), "sphere")
    # kasa önü (tahta çıtalar)
    for k in range(3):
        y = 450 + k * 80
        rrect(img, (120, y, 880, y + 66), 10, (170, 110, 55), "v")
        line(img, [(150, y + 20), (850, y + 24)], (120, 75, 35), 3, 120)
    rrect(img, (120, 450, 150, 700), 8, (120, 75, 35), "h")
    rrect(img, (850, 450, 880, 700), 8, (120, 75, 35), "h")
    rrect(img, (380, 520, 620, 600), 16, LIME, "v")
    return img


def coffee():
    img = canvas()
    shadow(img, (220, 640, 780, 720), 170, 20)
    ell(img, (200, 560, 800, 700), (240, 240, 245), "v")         # tabak
    ell(img, (260, 580, 740, 670), (215, 215, 225), "v")
    # fincan gövdesi
    poly(img, [(290, 330), (710, 330), (670, 600), (330, 600)], (250, 250, 252), "cyl")
    ell(img, (330, 570, 670, 630), (235, 235, 240), "v")
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(lay).ellipse([660, 380, 820, 520], outline=(235, 235, 240, 255), width=34)
    img.alpha_composite(lay)
    rrect(img, (290, 380, 710, 420), 0, LIME, "cyl")          # marka bandı
    ell(img, (290, 290, 710, 370), (240, 240, 245), "v")      # ağız
    ell(img, (310, 300, 690, 362), (120, 70, 35), "sphere")   # kahve
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    hd = ImageDraw.Draw(lay)
    hd.ellipse([450, 310, 505, 350], fill=(240, 220, 190, 255))
    hd.ellipse([495, 310, 550, 350], fill=(240, 220, 190, 255))
    hd.polygon([(452, 335), (548, 335), (500, 362)], fill=(240, 220, 190, 255))
    img.alpha_composite(lay)
    for k, x in enumerate((420, 500, 580)):  # buhar
        pts = [(x + 25 * math.sin(t / 12 + k), 270 - t * 2.2) for t in range(0, 70)]
        lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(lay).line(pts, fill=(255, 255, 255, 150), width=14, joint="curve")
        img.alpha_composite(lay.filter(ImageFilter.GaussianBlur(5)))
    return img


def bread():
    img = canvas()
    shadow(img, (130, 640, 880, 720), 170, 22)
    # simit (halka)
    ell(img, (110, 300, 520, 650), (190, 110, 45), "sphere")
    ell(img, (245, 420, 385, 530), (0, 0, 0), "flat")
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(lay).ellipse([245, 420, 385, 530], fill=(0, 0, 0, 255))
    a = np.array(img)
    a[..., 3] = np.where(np.array(lay)[..., 3] > 0, 0, a[..., 3])
    img = Image.fromarray(a)
    rng = random.Random(3)
    for _ in range(90):
        ang, rr = rng.uniform(0, 2 * math.pi), rng.uniform(0.4, 0.95)
        x, y = 315 + 200 * rr * math.cos(ang), 475 + 170 * rr * math.sin(ang)
        if ((x - 315) / 70) ** 2 + ((y - 475) / 55) ** 2 > 1.3:
            ImageDraw.Draw(img).ellipse([x - 5, y - 3, x + 5, y + 3], fill=(250, 235, 190, 255))
    # somun ekmek
    rrect(img, (470, 330, 900, 640), 150, (205, 140, 60), "v")
    shine(img, (530, 350, 840, 400), 90, 12, "pill")
    for k in range(4):
        x = 560 + k * 85
        line(img, [(x, 380), (x + 50, 440)], (245, 215, 150), 14)
    return img


def cake():
    img = canvas()
    shadow(img, (180, 650, 820, 730), 170, 22)
    ell(img, (160, 600, 840, 700), (240, 240, 245), "v")
    rrect(img, (240, 420, 760, 650), 20, (250, 200, 210), "cyl")
    ell(img, (240, 610, 760, 680), (230, 170, 185), "flat")
    rrect(img, (240, 520, 760, 545), 0, (120, 60, 40), "cyl")
    ell(img, (240, 380, 760, 460), (255, 240, 245), "v")
    for k in range(8):  # krema damlaları
        x = 260 + k * 64
        rrect(img, (x, 420, x + 34, 470 + (k % 3) * 22), 17, (255, 240, 245), "h")
    for k in range(5):
        x = 300 + k * 100
        ell(img, (x, 360, x + 50, 405), (255, 250, 252), "sphere")
    fruit(img, 500, 340, 40, (215, 20, 50))
    return img


def burger():
    img = canvas()
    shadow(img, (210, 650, 790, 730), 170, 22)
    ell(img, (230, 560, 770, 690), (220, 150, 70), "v")                       # alt ekmek
    rrect(img, (220, 500, 780, 590), 40, (95, 50, 30), "v")                  # köfte
    poly(img, [(230, 495), (770, 495), (720, 560), (640, 520), (560, 575), (470, 520), (380, 570), (300, 520)], (255, 190, 40), "v")
    for k in range(9):                                                       # marul
        ell(img, (210 + k * 62, 455, 300 + k * 62, 525), (90, 190, 60), "sphere")
    ell(img, (260, 430, 520, 490), (220, 50, 50), "v")                       # domates
    ell(img, (480, 430, 740, 490), (220, 50, 50), "v")
    fill(img, (220, 230, 780, 470), lambda d, w, h: d.chord([0, 0, w - 1, h * 2], 180, 360, fill=255),
         lambda s: sphere_grad(s, (225, 150, 60), (0.4, 0.2)))               # üst ekmek
    rng = random.Random(5)
    for _ in range(26):
        x, y = rng.randint(290, 710), rng.randint(260, 400)
        ImageDraw.Draw(img).ellipse([x - 7, y - 4, x + 7, y + 4], fill=(255, 245, 210, 255))
    return img


def meat():
    img = canvas()
    shadow(img, (120, 640, 880, 720), 170, 22)
    rrect(img, (110, 470, 890, 650), 40, (160, 105, 60), "v")                  # tahta
    line(img, [(150, 520), (850, 525)], (120, 75, 40), 4, 120)
    pts = [(220, 380), (320, 300), (480, 290), (600, 330), (640, 420), (580, 520), (420, 560), (260, 530), (200, 460)]
    poly(img, [(x - 12, y - 12) for x, y in pts], (250, 235, 225), "v")       # yağ kenarı
    poly(img, pts, (190, 40, 50), "sphere")
    rng = random.Random(6)
    for _ in range(12):
        x, y = rng.randint(280, 560), rng.randint(340, 500)
        line(img, [(x, y), (x + rng.randint(20, 60), y + rng.randint(-15, 15))], (240, 200, 200), 5, 150)
    shine(img, (300, 320, 520, 350), 90, 10, "pill")
    # satır
    rrect(img, (660, 230, 900, 430), 18, (215, 215, 230), "v")
    shine(img, (680, 245, 880, 270), 140, 6, "pill")
    rrect(img, (720, 430, 790, 640), 20, (60, 40, 30), "h")
    return img


def flower_head(img, cx, cy, r, c):
    for k in range(6):
        a = k * math.pi / 3
        x, y = cx + r * 0.6 * math.cos(a), cy + r * 0.6 * math.sin(a)
        ell(img, (x - r * 0.55, y - r * 0.55, x + r * 0.55, y + r * 0.55), c, "sphere")
    ell(img, (cx - r * 0.35, cy - r * 0.35, cx + r * 0.35, cy + r * 0.35), (255, 210, 60), "sphere")


def flowers():
    img = canvas()
    shadow(img, (320, 660, 680, 730), 170, 20)
    heads = [(380, 230, 80, (240, 80, 140)), (520, 180, 90, (255, 255, 255)), (650, 250, 78, (240, 80, 140)),
             (450, 330, 70, LIME), (600, 350, 70, (170, 110, 240))]
    for x, y, r, c in heads:
        line(img, [(x, y), (500, 520)], (60, 140, 60), 12)
    for x, y, r, c in heads:
        flower_head(img, x, y, r, c)
    poly(img, [(380, 460), (620, 460), (590, 690), (410, 690)], (90, 70, 190), "cyl")    # vazo
    ell(img, (375, 440, 625, 490), sh((90, 70, 190), 1.2), "v")
    rrect(img, (400, 560, 600, 590), 0, LIME, "cyl")
    return img


def dress():
    img = canvas()
    shadow(img, (230, 680, 820, 740), 160, 20)
    line(img, [(500, 130), (500, 100), (520, 80), (540, 100)], (190, 190, 205), 10)
    line(img, [(340, 210), (500, 130), (660, 210)], (190, 190, 205), 14)
    poly(img, [(400, 200), (600, 200), (580, 360), (420, 360)], (200, 50, 120), "cyl")      # üst
    poly(img, [(420, 350), (580, 350), (720, 690), (280, 690)], (220, 60, 135), "cyl")      # etek
    rrect(img, (415, 345, 585, 375), 10, LIME, "cyl")                                       # kemer
    # alışveriş çantası
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(lay).arc([690, 380, 840, 520], 180, 360, fill=(40, 30, 70, 255), width=14)
    img.alpha_composite(lay)
    rrect(img, (660, 450, 870, 700), 10, LIME, "v")
    shine(img, (680, 470, 700, 680), 120, 4, "pill")
    return img


def tailor():
    img = canvas()
    shadow(img, (150, 650, 850, 730), 160, 20)
    # makara
    rrect(img, (180, 300, 420, 340), 12, (200, 150, 90), "cyl")
    rrect(img, (205, 335, 395, 600), 10, (215, 40, 80), "cyl")
    for k in range(10):
        line(img, [(205, 350 + k * 25), (395, 345 + k * 25)], (160, 20, 60), 3, 120)
    rrect(img, (180, 595, 420, 640), 12, (200, 150, 90), "cyl")
    # mezura
    ell(img, (470, 420, 800, 690), (250, 210, 40), "sphere")
    ell(img, (570, 500, 700, 610), (60, 50, 80), "sphere")
    poly(img, [(700, 600), (900, 640), (900, 690), (690, 660)], (250, 220, 60), "v")
    for k in range(9):
        x = 720 + k * 20
        line(img, [(x, 640), (x, 655)], (40, 30, 30), 3)
    scissors(img, 640, 250, 0.6, 10)
    return img


def house():
    img = canvas()
    shadow(img, (150, 650, 860, 740), 170, 22)
    poly(img, [(220, 400), (560, 400), (560, 680), (220, 680)], (240, 235, 250), "v")       # ön
    poly(img, [(560, 400), (760, 340), (760, 620), (560, 680)], (200, 195, 225), "v")       # yan
    poly(img, [(190, 410), (390, 220), (590, 410)], (90, 60, 170), "v")                     # çatı ön
    poly(img, [(390, 220), (740, 160), (790, 350), (590, 410)], (70, 45, 140), "v")         # çatı yan
    rrect(img, (640, 170, 690, 260), 6, (150, 90, 70), "h")                                  # baca
    rrect(img, (340, 520, 440, 680), 10, (60, 45, 120), "v")                                 # kapı
    ell(img, (420, 595, 432, 607), LIME, "flat")
    for x0 in (250, 470):
        rrect(img, (x0, 450, x0 + 70, 520), 6, (255, 220, 120), "v")
    poly(img, [(610, 450), (690, 430), (690, 500), (610, 520)], (255, 220, 120), "v")
    # SATILIK tabelası
    rrect(img, (812, 380, 828, 690), 6, (150, 100, 60), "h")
    rrect(img, (760, 390, 960, 480), 12, LIME, "v")
    from render import F_HEAD, font
    ImageDraw.Draw(img).text((778, 408), "SATILIK", fill=NAVY + (255,), font=font(F_HEAD, 46))
    return img


def tools():
    img = canvas()
    shadow(img, (150, 640, 850, 720), 160, 20)
    lay = canvas()
    rrect(lay, (440, 120, 560, 620), 40, (205, 205, 220), "h")                              # İngiliz anahtarı
    ell(lay, (390, 60, 610, 250), (205, 205, 220), "sphere")
    ImageDraw.Draw(lay).rectangle([470, 50, 530, 160], fill=(0, 0, 0, 0))
    ell(lay, (420, 560, 580, 720), (205, 205, 220), "sphere")
    ImageDraw.Draw(lay).ellipse([465, 605, 535, 675], fill=(0, 0, 0, 0))
    img.alpha_composite(lay.rotate(35, center=(500, 400), resample=Image.BICUBIC))
    lay = canvas()
    rrect(lay, (470, 250, 530, 720), 24, (190, 130, 60), "h")                               # çekiç sapı
    rrect(lay, (330, 160, 670, 270), 22, (70, 70, 85), "v")
    rrect(lay, (460, 600, 540, 720), 20, LIME, "h")
    img.alpha_composite(lay.rotate(-35, center=(500, 420), resample=Image.BICUBIC))
    return img


def beauty():
    img = canvas()
    shadow(img, (200, 650, 820, 730), 160, 20)
    # ruj
    rrect(img, (250, 400, 400, 680), 14, (210, 170, 70), "cyl")
    rrect(img, (270, 300, 380, 410), 10, (225, 190, 90), "cyl")
    poly(img, [(285, 305), (365, 305), (365, 200), (285, 250)], (210, 30, 80), "cyl")
    # oje
    rrect(img, (500, 400, 730, 680), 50, (230, 70, 140), "cyl")
    shine(img, (525, 430, 555, 650), 150, 6, "pill")
    rrect(img, (560, 230, 670, 410), 20, (30, 25, 40), "cyl")
    rrect(img, (540, 520, 690, 570), 10, LIME, "cyl")
    return img


def gym():
    img = canvas()
    shadow(img, (120, 600, 880, 690), 170, 22)
    rrect(img, (230, 400, 770, 450), 20, (200, 200, 215), "v")                              # bar
    for x0, w in ((150, 70), (225, 60), (705, 60), (775, 70)):
        rrect(img, (x0, 270 if w == 70 else 300, x0 + w, 580 if w == 70 else 550), 22, (40, 38, 52), "h")
    rrect(img, (420, 390, 580, 460), 14, LIME, "v")
    # kettlebell
    img2 = canvas()
    shadow(img2, (250, 660, 750, 740), 170, 22)
    lay = Image.new("RGBA", img2.size, (0, 0, 0, 0))
    ImageDraw.Draw(lay).arc([380, 330, 620, 560], 180, 360, fill=(50, 46, 64, 255), width=40)
    img2.alpha_composite(lay)
    ell(img2, (320, 440, 680, 720), (50, 46, 64), "sphere")
    rrect(img2, (440, 560, 560, 610), 10, LIME, "flat")
    small = img2.resize((500, 400), Image.LANCZOS)
    img.alpha_composite(small, (500, 330))
    return img


def glasses():
    img = canvas()
    shadow(img, (150, 600, 850, 690), 150, 22)
    for cx in (320, 680):
        ell(img, (cx - 170, 300, cx + 170, 560), (35, 30, 50), "v")
        ell(img, (cx - 140, 325, cx + 140, 535), (150, 200, 240), "sphere")
        line(img, [(cx - 90, 360), (cx - 30, 330)], (255, 255, 255), 16, 140)
    rrect(img, (470, 360, 530, 395), 14, (35, 30, 50), "v")
    poly(img, [(150, 360), (110, 340), (60, 470), (80, 480)], (35, 30, 50), "h")
    poly(img, [(850, 360), (890, 340), (940, 470), (920, 480)], (35, 30, 50), "h")
    rrect(img, (455, 365, 545, 380), 7, LIME, "flat")
    return img


def pet():
    img = canvas()
    shadow(img, (160, 640, 860, 720), 160, 22)
    ell(img, (180, 470, 640, 700), (90, 70, 190), "v")                                    # mama kabı
    ell(img, (210, 450, 610, 540), sh((90, 70, 190), 1.3), "v")
    ell(img, (240, 465, 580, 530), (150, 90, 50), "flat")
    rng = random.Random(7)
    for _ in range(40):
        x, y = rng.randint(260, 560), rng.randint(470, 520)
        ell(img, (x - 14, y - 10, x + 14, y + 10), (170, 105, 55), "sphere")
    # kemik
    lay = canvas()
    rrect(lay, (560, 300, 860, 360), 30, (250, 245, 235), "v")
    for x in (560, 860):
        for y in (300, 360):
            ell(lay, (x - 45, y - 45, x + 45, y + 45), (250, 245, 235), "sphere")
    img.alpha_composite(lay.rotate(-15, center=(710, 330), resample=Image.BICUBIC))
    # pati
    ell(img, (720, 520, 850, 630), LIME, "sphere")
    for k, (x, y) in enumerate(((700, 490), (745, 455), (800, 455), (850, 490))):
        ell(img, (x - 26, y - 30, x + 26, y + 30), LIME, "sphere")
    return img


ART = {"car": car, "carwash": lambda: car(wash=True), "barber": barber, "salon": salon,
       "produce": produce, "coffee": coffee, "bread": bread, "cake": cake, "burger": burger,
       "meat": meat, "flowers": flowers, "dress": dress, "tailor": tailor, "house": house,
       "tools": tools, "beauty": beauty, "gym": gym, "glasses": glasses, "pet": pet}

TAGS = {"otoyıkama": "carwash", "otogaleri": "car", "oto": "car", "galeri": "car", "berber": "barber",
        "kuaför": "salon", "manav": "produce", "market": "produce", "kafe": "coffee", "fırın": "bread",
        "pastane": "cake", "restoran": "burger", "kasap": "meat", "çiçekçi": "flowers", "butik": "dress",
        "terzi": "tailor", "emlak": "house", "usta": "tools", "güzellik": "beauty", "spor": "gym",
        "optik": "glasses", "petshop": "pet"}

WORDS = [("carwash", r"oto yıkama|otoyıkama|yıkamacı"), ("car", r"galeri|araba|araç|otomobil|oto\b"),
         ("barber", r"berber|tıraş|sakal"), ("salon", r"kuaför|saç|fön"), ("produce", r"manav|meyve|sebze|market|bakkal"),
         ("coffee", r"kafe|kahve|çay ocağı"), ("cake", r"pastane|pasta|tatlı"), ("bread", r"fırın|simit|ekmek|poğaça"),
         ("burger", r"restoran|lokanta|burger|yemek"), ("meat", r"kasap|et\b|şarküteri"),
         ("flowers", r"çiçek"), ("dress", r"butik|giyim|elbise|moda"), ("tailor", r"terzi|dikiş"),
         ("house", r"emlak|ilan|portföy|daire|kiralık|satılık"), ("tools", r"usta|tamir|tesisat|elektrikçi"),
         ("beauty", r"güzellik|makyaj|cilt|manikür|nail"), ("gym", r"spor|fitness|gym|antrenman"),
         ("glasses", r"optik|gözlük"), ("pet", r"petshop|pet shop|kedi|köpek|mama")]
_WORDS = [(k, re.compile(p, re.I)) for k, p in WORDS]


def sector_of(post):
    tag = (post.get("tag") or "").lower()
    if tag in TAGS:
        return TAGS[tag]
    text = " ".join(str(post.get(k, "")) for k in ("label", "headline", "body"))
    for k, rx in _WORDS:
        if rx.search(text):
            return k
    return None


_cache = {}


def art(kind):
    """Kırpılmış RGBA sahne (şeffaf zemin)."""
    if kind not in _cache:
        im = ART[kind]()
        _cache[kind] = im.crop(im.getchannel("A").getbbox())
    return _cache[kind].copy()


if __name__ == "__main__":
    import os
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else "preview"
    os.makedirs(out, exist_ok=True)
    kinds = sys.argv[2:] or list(ART)
    cols = 5
    sheet = Image.new("RGBA", (cols * 420, ((len(kinds) + cols - 1) // cols) * 380), (24, 18, 52, 255))
    for i, k in enumerate(kinds):
        a = art(k)
        a.thumbnail((380, 340), Image.LANCZOS)
        sheet.alpha_composite(a, ((i % cols) * 420 + (420 - a.size[0]) // 2, (i // cols) * 380 + (380 - a.size[1]) // 2))
    sheet.convert("RGB").save(os.path.join(out, "sektorler.jpg"), quality=90)
    print(os.path.join(out, "sektorler.jpg"))
