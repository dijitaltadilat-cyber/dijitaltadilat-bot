"""Dijital Tadilat görsel ve Reels üretici.

Görsel: 1080x1080 JPEG (Instagram yalnızca JPEG kabul eder)
Reels : 1080x1920 MP4, hareketli yazılar, sessiz ses kanalı
Logo  : assets/logo.png varsa kullanılır, yoksa "dijital tadilat" yazısı basılır.
"""
import os
import subprocess

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.abspath(__file__))
FONT_BOLD = os.path.join(ROOT, "fonts", "Inter-Bold.otf")
FONT_MED = os.path.join(ROOT, "fonts", "InterDisplay-Medium.otf")
LOGO_PATH = os.path.join(ROOT, "assets", "logo.png")

# Marka renkleri (logo gelince lime tonu logodan alınıp güncellenecek)
BG = (0, 0, 0)
LIME = (198, 255, 0)
WHITE = (255, 255, 255)
GREY = (163, 163, 163)
HANDLE = "@dijitaltadilat"

_font_cache = {}


def font(path, size):
    key = (path, size)
    if key not in _font_cache:
        _font_cache[key] = ImageFont.truetype(path, size)
    return _font_cache[key]


def wrap(draw, text, fnt, max_w):
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if draw.textlength(trial, font=fnt) <= max_w:
            line = trial
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def fit_lines(draw, text, path, size, max_w, max_lines, min_size=40):
    """Metni max_lines satıra sığana kadar küçültür."""
    while True:
        fnt = font(path, size)
        lines = wrap(draw, text, fnt, max_w)
        if len(lines) <= max_lines or size <= min_size:
            return fnt, lines, size
        size -= 4


def load_logo(max_w, max_h):
    if not os.path.exists(LOGO_PATH):
        return None
    logo = Image.open(LOGO_PATH).convert("RGBA")
    logo.thumbnail((max_w, max_h), Image.LANCZOS)
    return logo


def draw_brand(img, draw, x, y, max_w=360, max_h=90, color=LIME, scale=1.0):
    """Sol üst marka alanı: logo ya da yazı."""
    logo = load_logo(int(max_w * scale), int(max_h * scale))
    if logo:
        img.paste(logo, (x, y), logo)
        return logo.size[1]
    fnt = font(FONT_BOLD, int(38 * scale))
    draw.text((x, y), "dijital tadilat", fill=color, font=fnt)
    return int(46 * scale)


# --------------------------------------------------------------------------
# Tek görsel (gönderi)
# --------------------------------------------------------------------------
def make_image(post, out_path):
    W = 1080
    img = Image.new("RGB", (W, W), BG)
    d = ImageDraw.Draw(img)
    X, MAXW = 80, 920

    # Üst: marka
    d.rectangle([X, 100, X + 100, 108], fill=LIME)
    draw_brand(img, d, X, 132)

    # Etiket (ör. KAFELER İÇİN)
    lf = font(FONT_BOLD, 28)
    label = post["label"]
    lw = d.textlength(label, font=lf)
    d.rounded_rectangle([X, 250, X + lw + 44, 302], radius=26, outline=LIME, width=3)
    d.text((X + 22, 258), label, fill=LIME, font=lf)

    # Başlık + açıklama, ortalanmış blok
    hf, hlines, hsize = fit_lines(d, post["headline"], FONT_BOLD, 88, MAXW, 4)
    bf, blines, bsize = fit_lines(d, post["body"], FONT_MED, 40, MAXW, 3, min_size=32)
    h_lh, b_lh = int(hsize * 1.18), int(bsize * 1.4)
    block_h = len(hlines) * h_lh + 36 + len(blines) * b_lh
    top, bottom = 340, 880
    y = top + max(0, (bottom - top - block_h) // 2)
    for ln in hlines:
        d.text((X, y), ln, fill=WHITE, font=hf)
        y += h_lh
    y += 36
    for ln in blines:
        d.text((X, y), ln, fill=GREY, font=bf)
        y += b_lh

    # Alt: çağrı + kullanıcı adı
    cf = font(FONT_BOLD, 34)
    cta = "DM'den yaz, konuşalım"
    cw = d.textlength(cta, font=cf)
    d.rounded_rectangle([X, 925, X + cw + 64, 995], radius=35, fill=LIME)
    d.text((X + 32, 940), cta, fill=BG, font=cf)
    mf = font(FONT_MED, 32)
    d.text((W - 80 - d.textlength(HANDLE, font=mf), 944), HANDLE, fill=GREY, font=mf)

    img.save(out_path, "JPEG", quality=94)
    return out_path


# --------------------------------------------------------------------------
# Reels (hareketli video)
# --------------------------------------------------------------------------
FPS = 30
RW, RH = 1080, 1920


def ease_out(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def dim(color, a):
    """Siyah zemin üstünde saydamlık: rengi alfa oranında karart."""
    return tuple(int(c * a) for c in color)


def _layout_slides(slides):
    probe = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    MAXW = 920
    blocks = []
    hook_f, hook_lines, hook_size = fit_lines(probe, slides[0], FONT_BOLD, 112, MAXW, 4)
    blocks.append((hook_f, hook_lines, int(hook_size * 1.15), WHITE))
    for s in slides[1:]:
        f, lines, size = fit_lines(probe, s, FONT_BOLD, 84, MAXW, 3, min_size=52)
        blocks.append((f, lines, int(size * 1.25), LIME if s[:2].strip(". ").isdigit() else WHITE))
    # Kalan satırlar gri tonda okunurluğu bozmasın diye: hook sonrası satırlar beyaz,
    # numaralı listeler lime.
    gap_after_hook, gap = 90, 44
    total = sum(len(b[1]) * b[2] for b in blocks) + gap_after_hook + gap * (len(blocks) - 2)
    return blocks, total, gap_after_hook, gap


def make_reel(reel, out_path, slide_dur=1.6, hold=1.4, end_dur=2.6):
    slides = reel["slides"]
    blocks, total_h, gap_hook, gap = _layout_slides(slides)
    # Güvenli alan: Instagram arayüzü üstte ~250, altta ~420 px kaplar
    safe_top, safe_bottom = 360, 1450
    start_y = safe_top + max(0, (safe_bottom - safe_top - total_h) // 2)

    text_dur = 0.35 + slide_dur * len(slides) + hold
    total = text_dur + end_dur
    n_frames = int(total * FPS)

    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{RW}x{RH}", "-r", str(FPS), "-i", "-",
        "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
        "-shortest",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
        "-profile:v", "high", "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart", out_path,
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    cta_f = font(FONT_BOLD, 52)
    handle_f = font(FONT_MED, 46)
    tag_f = font(FONT_MED, 40)

    for i in range(n_frames):
        t = i / FPS
        img = Image.new("RGB", (RW, RH), BG)
        d = ImageDraw.Draw(img)

        # Üst ilerleme çubuğu
        d.rectangle([0, 0, int(RW * t / total), 10], fill=LIME)

        if t < text_dur:
            # Metin çıkışı (son 0.35 sn sönme)
            fade_out = 1 - ease_out((t - (text_dur - 0.35)) / 0.35) if t > text_dur - 0.35 else 1.0
            draw_brand(img, d, 80, 200) if fade_out > 0.99 else None
            y = start_y
            for bi, (f, lines, lh, color) in enumerate(blocks):
                appear = 0.25 + bi * slide_dur
                for li, ln in enumerate(lines):
                    lt = (t - appear - li * 0.08) / 0.45
                    a = ease_out(lt) * fade_out
                    if a > 0:
                        dy = int((1 - ease_out(lt)) * 50)
                        d.text((80, y + dy), ln, fill=dim(color, a), font=f)
                    y += lh
                if bi == 0:
                    # Hook altında büyüyen lime çizgi
                    bt = ease_out((t - appear - 0.3) / 0.5)
                    if bt > 0:
                        d.rectangle([80, y + 18, 80 + int(160 * bt), 28 + y],
                                    fill=dim(LIME, fade_out))
                    y += gap_hook
                else:
                    y += gap
        else:
            # Kapanış kartı
            et = t - text_dur
            a = ease_out(et / 0.5)
            s = 0.85 + 0.15 * ease_out(et / 0.6)
            logo = load_logo(int(640 * s), int(220 * s))
            cy = 760
            if logo:
                if a < 1:
                    alpha = logo.split()[3].point(lambda p: int(p * a))
                    logo.putalpha(alpha)
                img.paste(logo, ((RW - logo.size[0]) // 2, cy - logo.size[1] // 2), logo)
            else:
                bf = font(FONT_BOLD, int(110 * s))
                word = "dijital tadilat"
                d.text(((RW - d.textlength(word, font=bf)) // 2, cy - int(60 * s)), word,
                       fill=dim(LIME, a), font=bf)
            line = "Esnafın sosyal medya ortağı"
            d.text(((RW - d.textlength(line, font=tag_f)) // 2, 900), line, fill=dim(GREY, a), font=tag_f)

            pt = ease_out((et - 0.4) / 0.5)
            if pt > 0:
                cta = "DM'den yaz, konuşalım"
                cw = d.textlength(cta, font=cta_f)
                px = (RW - cw - 90) // 2
                py = 1060 + int((1 - pt) * 40)
                d.rounded_rectangle([px, py, px + cw + 90, py + 104], radius=52, fill=dim(LIME, pt))
                d.text((px + 45, py + 24), cta, fill=BG, font=cta_f)
                d.text(((RW - d.textlength(HANDLE, font=handle_f)) // 2, py + 150), HANDLE,
                       fill=dim(WHITE, pt), font=handle_f)

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
    if which in ("all", "image"):
        for idx in (0, 2, 9):
            make_image(content["posts"][idx], f"preview/post_{idx}.jpg")
    if which in ("all", "reel"):
        make_reel(content["reels"][1], "preview/reel_1.mp4")
    print("Önizlemeler preview/ klasöründe.")
