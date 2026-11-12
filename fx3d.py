"""Görsellere derinlik katan efektler (sadece Pillow + numpy).

* gradient_bg      : ışık alan yumuşak degrade zemin
* floor_grid       : perspektifli ızgara zemin (sahne hissi)
* soft_shadow      : yuvarlatılmış kutulara yumuşak gölge
* text3d           : katmanlı, kalınlığı olan 3B yazı
* extrude          : logo gibi şeffaf görselleri 3B kabartma yapar
* cube             : izometrik yüzen küpler (süs)
"""
import numpy as np
from PIL import Image, ImageDraw, ImageFilter


def shade(c, k):
    """k<1 koyulaştırır, k>1 açar."""
    if k <= 1:
        return tuple(int(v * k) for v in c)
    return tuple(int(v + (255 - v) * (k - 1)) for v in c)


def gradient_bg(size, base, light_xy=(0.25, 0.15), strength=1.35, falloff=0.75):
    """Bir köşeden ışık alan radyal degrade."""
    w, h = size
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    lx, ly = light_xy[0] * w, light_xy[1] * h
    dist = np.sqrt((xx - lx) ** 2 + (yy - ly) ** 2) / (max(w, h) * falloff)
    t = np.clip(1 - dist, 0, 1) ** 1.6
    # rengi beyaza değil kendi tonuna doğru aydınlat (lacivert -> mor)
    hi = np.array([min(255, v * strength + 6) for v in base], np.float32)
    lo = np.array(shade(base, 0.72), np.float32)
    arr = lo + (hi - lo) * t[..., None]
    return Image.fromarray(arr.clip(0, 255).astype(np.uint8), "RGB")


def floor_grid(img, color, horizon=0.62, alpha=60, lines=14):
    """Alt yarıya ufka doğru kaçan ızgara zemin çizer."""
    w, h = img.size
    hy = int(h * horizon)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    vx = w / 2
    for i in range(-lines, lines + 1):
        x_bottom = vx + i * w / lines * 1.6
        d.line([(vx + i * 6, hy), (x_bottom, h)], fill=color + (alpha,), width=2)
    for k in range(1, 12):
        t = (k / 11) ** 2.2
        y = hy + (h - hy) * t
        d.line([(0, y), (w, y)], fill=color + (int(alpha * (0.3 + 0.7 * t)),), width=2)
    # ufukta kaybolma
    fade = Image.new("L", img.size, 0)
    fd = ImageDraw.Draw(fade)
    for y in range(hy, h):
        fd.line([(0, y), (w, y)], fill=int(255 * min(1, (y - hy) / (h - hy) * 1.8)))
    layer.putalpha(Image.fromarray(np.minimum(np.array(layer.split()[3]), np.array(fade))))
    img.paste(layer, (0, 0), layer)


def soft_shadow(img, box, radius, offset=(0, 22), blur=28, opacity=150, color=(0, 0, 0)):
    x0, y0, x1, y1 = box
    pad = blur * 3
    sh = Image.new("L", (int(x1 - x0) + pad * 2, int(y1 - y0) + pad * 2), 0)
    ImageDraw.Draw(sh).rounded_rectangle([pad, pad, pad + x1 - x0, pad + y1 - y0], radius=radius, fill=opacity)
    sh = sh.filter(ImageFilter.GaussianBlur(blur))
    col = Image.new("RGBA", sh.size, color + (255,))
    col.putalpha(sh)
    img.paste(col, (int(x0 - pad + offset[0]), int(y0 - pad + offset[1])), col)


def raised_box(img, box, radius, face, depth=14, shadow=True):
    """Kalınlığı olan, yerden yükselmiş kutu (kart, buton)."""
    if shadow:
        soft_shadow(img, box, radius, offset=(0, depth + 14), blur=26, opacity=140)
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = box
    side = shade(face, 0.62)
    for i in range(depth, 0, -1):
        d.rounded_rectangle([x0, y0 + i, x1, y1 + i], radius=radius, fill=side)
    d.rounded_rectangle(box, radius=radius, fill=face)
    # üst kenarda ince parlama
    hl = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(hl).rounded_rectangle([x0 + 3, y0 + 3, x1 - 3, y1 - 3], radius=radius,
                                         outline=shade(face, 1.45) + (150,), width=3)
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).rectangle([x0, y0, x1, y0 + (y1 - y0) * 0.45], fill=255)
    hl.putalpha(Image.fromarray(np.minimum(np.array(hl.split()[3]), np.array(mask))))
    img.paste(hl, (0, 0), hl)


def text3d(img, xy, text, fnt, face, side=None, depth=12, direction=(1, 1), shadow=True):
    """Kalın, kabartma 3B yazı."""
    x, y = xy
    side = side or shade(face, 0.55)
    dx, dy = direction
    if shadow:
        sh = Image.new("L", img.size, 0)
        ImageDraw.Draw(sh).text((x + dx * depth * 1.6, y + dy * depth * 2.2), text, font=fnt, fill=120)
        sh = sh.filter(ImageFilter.GaussianBlur(14))
        blk = Image.new("RGBA", img.size, (0, 0, 0, 255))
        blk.putalpha(sh)
        img.paste(blk, (0, 0), blk)
    d = ImageDraw.Draw(img)
    for i in range(depth, 0, -1):
        k = 0.45 + 0.25 * (1 - i / depth)  # arkaya doğru koyulaşır
        d.text((x + dx * i, y + dy * i), text, font=fnt, fill=shade(side, k / 0.55 * 0.9))
    d.text((x, y), text, font=fnt, fill=face)


def text3d_block(img, x, y, lines, fnt, lh, face, side=None, depth=10, center_w=None):
    d = ImageDraw.Draw(img)
    for ln in lines:
        tx = x if center_w is None else x + (center_w - d.textlength(ln, font=fnt)) / 2
        text3d(img, (tx, y), ln, fnt, face, side, depth)
        y += lh
    return y


def extrude(im, depth=18, side_color=None, direction=(1, 1), shadow=True):
    """Şeffaf RGBA görseli (logo) kalınlığı olan 3B bloğa çevirir. Yeni RGBA döner."""
    dx, dy = direction
    pad = depth + 60
    W, H = im.size[0] + pad * 2, im.size[1] + pad * 2
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    a = im.split()[3]
    if shadow:
        sh = Image.new("L", (W, H), 0)
        sh.paste(a.point(lambda p: int(p * 0.55)), (pad + dx * depth * 2, pad + dy * depth * 2 + 10))
        sh = sh.filter(ImageFilter.GaussianBlur(18))
        blk = Image.new("RGBA", (W, H), (0, 0, 0, 255))
        blk.putalpha(sh)
        out = Image.alpha_composite(out, blk)
    if side_color is None:
        rgb = np.array(im.convert("RGB"))[np.array(a) > 128]
        side_color = tuple(int(v) for v in (rgb.mean(0) if len(rgb) else (80, 80, 80)))
    for i in range(depth, 0, -1):
        k = 0.38 + 0.3 * (1 - i / depth)
        layer = Image.new("RGBA", im.size, shade(side_color, k) + (255,))
        layer.putalpha(a)
        out.alpha_composite(layer, (pad + dx * i, pad + dy * i))
    out.alpha_composite(im, (pad, pad))
    return out, pad


def cube(img, cx, cy, s, top, left=None, right=None, shadow=True, alpha=255):
    """İzometrik küp. (cx, cy) üst yüzün merkezi."""
    left = left or shade(top, 0.72)
    right = right or shade(top, 0.5)
    h = s * 0.5
    T = (cx, cy - h)
    R = (cx + s * 0.866, cy)
    B = (cx, cy + h)
    L = (cx - s * 0.866, cy)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    if shadow:
        sh = Image.new("L", img.size, 0)
        ImageDraw.Draw(sh).ellipse([cx - s, cy + s * 1.55, cx + s, cy + s * 1.95], fill=110)
        sh = sh.filter(ImageFilter.GaussianBlur(max(6, s * 0.18)))
        blk = Image.new("RGBA", img.size, (0, 0, 0, 255))
        blk.putalpha(sh)
        img.paste(blk, (0, 0), blk)
    d.polygon([L, B, (B[0], B[1] + s), (L[0], L[1] + s)], fill=left + (alpha,))
    d.polygon([B, R, (R[0], R[1] + s), (B[0], B[1] + s)], fill=right + (alpha,))
    d.polygon([T, R, B, L], fill=top + (alpha,))
    img.paste(layer, (0, 0), layer)
