"""Özel gün Reels'leri (satış içermez).

python special_reels.py ataturk <çıktı.mp4>

Görsel: dalgalanan Türk bayrağı (çizim), 09.05'i gösteren saat, metinler.
Ses   : Burada sentezlenen özgün, sakin fon müziği ve çan sesi (telifsiz).
"""
import math
import os
import subprocess
import sys
import tempfile
import wave

import numpy as np
from PIL import Image, ImageDraw

from render import F_HEAD, F_SEMI, asset, font, wrap

W, H, FPS = 1080, 1920, 30
SR = 44100
BG = (8, 8, 14)
WHITE = (245, 245, 250)
GREY = (160, 160, 175)
RED = (227, 10, 23)


def ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def mix(c, a, bg=None):
    bg = bg or BG
    return tuple(int(bg[i] + (c[i] - bg[i]) * a) for i in range(3))


# ------------------------------------------------------------- Türk bayrağı
def flag_image(G):
    """Resmi oranlara göre bayrak (G = yükseklik, genişlik = 1.5G)."""
    w, h = int(G * 1.5), int(G)
    ss = 3  # kenar yumuşatma için büyük çiz, sonra küçült
    im = Image.new("RGB", (w * ss, h * ss), RED)
    d = ImageDraw.Draw(im)
    g = G * ss
    cy = g / 2
    # dış daire: merkez 0.5G, çap 0.5G ; iç daire: merkez 0.5G+0.0625G, çap 0.4G
    cx1, r1 = 0.5 * g, 0.25 * g
    cx2, r2 = 0.5625 * g, 0.2 * g
    d.ellipse([cx1 - r1, cy - r1, cx1 + r1, cy + r1], fill=(255, 255, 255))
    d.ellipse([cx2 - r2, cy - r2, cx2 + r2, cy + r2], fill=RED)
    # yıldız: iç daireden 0.333G uzakta, çevrel çap 0.25G
    sx = cx2 + r2 + 0.0333 * g + 0.125 * g
    R, r = 0.125 * g, 0.125 * g * 0.382
    pts = []
    for k in range(10):
        rad = R if k % 2 == 0 else r
        ang = math.pi + k * math.pi / 5  # bir ucu hilale bakar
        pts.append((sx + rad * math.cos(ang), cy + rad * math.sin(ang)))
    d.polygon(pts, fill=(255, 255, 255))
    return im.resize((w, h), Image.LANCZOS)


class WavingFlag:
    def __init__(self, G=560):
        self.src = np.asarray(flag_image(G)).astype(np.float32)
        self.h, self.w = self.src.shape[:2]
        self.pad = 40

    def frame(self, t, brightness=1.0):
        h, w, pad = self.h, self.w, self.pad
        out = np.zeros((h + 2 * pad, w, 3), np.float32)
        xs = np.arange(w)
        k = xs / w  # direğe yakın taraf az dalgalanır
        phase = 2 * math.pi * (xs / (w * 0.55)) - t * 2.4
        dy = (np.sin(phase) * 26 * k).astype(int)
        shade = 1 + np.cos(phase) * 0.18 * k
        for x in range(0, w, 3):
            y0 = pad + dy[x]
            out[y0:y0 + h, x:x + 3] = self.src[:, x:x + 3] * shade[x]
        out = np.clip(out * brightness, 0, 255).astype(np.uint8)
        im = Image.fromarray(out)
        mask = Image.fromarray(((out.max(axis=2) > 0) * 255).astype(np.uint8))
        return im, mask


# ------------------------------------------------------------------- sahneler
def draw_clock(d, cx, cy, R, a, minute_frac):
    col = mix(WHITE, a)
    d.ellipse([cx - R, cy - R, cx + R, cy + R], outline=col, width=8)
    for i in range(12):
        ang = math.radians(i * 30 - 90)
        r0 = R - (40 if i % 3 == 0 else 24)
        d.line([(cx + r0 * math.cos(ang), cy + r0 * math.sin(ang)),
                (cx + (R - 12) * math.cos(ang), cy + (R - 12) * math.sin(ang))],
               fill=col, width=8 if i % 3 == 0 else 4)
    mins = 5 * minute_frac
    hang = math.radians((9 + mins / 60) * 30 - 90)
    mang = math.radians(mins * 6 - 90)
    d.line([(cx, cy), (cx + R * 0.5 * math.cos(hang), cy + R * 0.5 * math.sin(hang))], fill=col, width=16)
    d.line([(cx, cy), (cx + R * 0.8 * math.cos(mang), cy + R * 0.8 * math.sin(mang))], fill=mix(RED, a), width=10)
    d.ellipse([cx - 16, cy - 16, cx + 16, cy + 16], fill=col)


def centered(d, text, f, y, color):
    d.text(((W - d.textlength(text, font=f)) / 2, y), text, fill=color, font=f)


def lines_block(d, lines, f, step, color, y=None):
    ls = []
    for ln in lines:
        ls += wrap(d, ln, f, 900)
    y = y if y is not None else (H - len(ls) * step) // 2
    for ln in ls:
        centered(d, ln, f, y, color)
        y += step
    return y


QUOTE = ("“Benim naçiz vücudum elbet bir gün toprak olacaktır, "
         "fakat Türkiye Cumhuriyeti ilelebet payidar kalacaktır.”")

# (başlangıç, bitiş, sahne adı)
SCENES = [(0.0, 4.0, "date"), (4.0, 8.4, "clock"), (8.4, 12.2, "years"),
          (12.2, 16.8, "remember"), (16.8, 23.4, "quote"), (23.4, 27.0, "end")]
TOTAL = SCENES[-1][1]
FADE = 0.9


def scene_alpha(t, s, e):
    if e == TOTAL:
        return ease((t - s) / FADE)
    return min(ease((t - s) / FADE), 1 - ease((t - (e - FADE)) / FADE))


def render_video(out_path):
    flag = WavingFlag(560)
    fx = (W - flag.w) // 2
    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", out_path]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(int(TOTAL * FPS)):
        t = i / FPS
        img = Image.new("RGB", (W, H), BG)
        d = ImageDraw.Draw(img)
        name, a = None, 0
        for s, e, n in SCENES:
            if s <= t < e:
                name, a = n, scene_alpha(t, s, e)

        # bayrak: saat sahnesi dışında üstte dalgalanır
        fb = 0.0
        if name in ("date", "years", "remember"):
            fb = 0.95 * a
        elif name == "end":
            fb = 0.95 * a
        if fb > 0.01:
            fim, fm = flag.frame(t, brightness=fb)
            fy = 360
            img.paste(fim, (fx, fy - flag.pad), fm)

        if name == "date":
            f = font(F_HEAD, 104)
            centered(d, "10 Kasım 1938", f, 1150, mix(WHITE, a))
            d.rectangle([W / 2 - 80 * a, 1290, W / 2 + 80 * a, 1298], fill=mix(RED, a))
        elif name == "clock":
            frac = ease((t - 4.4) / 2.2)
            draw_clock(d, W // 2, 780, 300, a, frac)
            centered(d, "09.05", font(F_HEAD, 190), 1170, mix(WHITE, a))
        elif name == "years":
            lines_block(d, ["Aramızdan ayrılışının", "88. yılında"], font(F_HEAD, 84), 100, mix(WHITE, a), y=1150)
        elif name == "remember":
            lines_block(d, ["Gazi Mustafa Kemal", "Atatürk'ü saygı,", "minnet ve özlemle", "anıyoruz."],
                        font(F_HEAD, 80), 96, mix(WHITE, a), y=1120)
        elif name == "quote":
            y = lines_block(d, [QUOTE], font(F_SEMI, 62), 88, mix(WHITE, a), y=760)
            centered(d, "Mustafa Kemal Atatürk", font(F_HEAD, 56), y + 50, mix(GREY, a))
            d.rectangle([W / 2 - 55, y + 142, W / 2 + 55, y + 149], fill=mix(RED, a))
        elif name == "end":
            centered(d, "Unutmadık, unutmayacağız.", font(F_HEAD, 76), 1150, mix(WHITE, a))
            m = asset("logo_mark.png", max_h=90, opacity=0.9 * a)
            img.paste(m, ((W - m.size[0]) // 2, 1340), m)
            centered(d, "Dijital Tadilat", font(F_SEMI, 38), 1450, mix(GREY, a))

        p.stdin.write(img.tobytes())
    p.stdin.close()
    if p.wait() != 0:
        raise RuntimeError("ffmpeg hata")


# ---------------------------------------------------------------------- ses
def render_audio(path):
    n = int(TOTAL * SR)
    t = np.arange(n) / SR
    pad = np.zeros(n)
    # Re minör, ağır ve sakin akorlar (özgün)
    chords = [(0.0, [73.42, 110.0, 146.83, 174.61]),      # Dm
              (8.4, [58.27, 116.54, 146.83, 174.61]),     # Bb
              (16.8, [65.41, 98.0, 130.81, 164.81]),      # C
              (23.4, [73.42, 110.0, 146.83, 220.0])]      # Dm
    for idx, (st, notes) in enumerate(chords):
        en = chords[idx + 1][0] if idx + 1 < len(chords) else TOTAL
        seg = (t >= st - 1.0) & (t < en + 1.5)
        tt = t[seg] - st
        env = np.clip((tt + 1.0) / 2.0, 0, 1) * np.clip((en - st + 1.5 - tt) / 2.5, 0, 1)
        s = np.zeros(seg.sum())
        for f in notes:
            for k, amp in [(1, 1.0), (2, 0.35), (3, 0.12)]:
                s += amp * np.sin(2 * np.pi * f * k * tt + k) * (1 + 0.003 * np.sin(2 * np.pi * 0.2 * tt))
                s += amp * 0.5 * np.sin(2 * np.pi * f * k * 1.003 * tt)
        pad[seg] += s * env
    pad *= 0.5 + 0.08 * np.sin(2 * np.pi * 0.12 * t)

    def bell(at, f0, gain):
        out = np.zeros(n)
        m = t >= at
        tt = t[m] - at
        for ratio, amp, dec in [(1, 1.0, 5.5), (2.0, 0.5, 3.5), (2.76, 0.35, 2.5), (5.4, 0.18, 1.2)]:
            out[m] += amp * np.sin(2 * np.pi * f0 * ratio * tt) * np.exp(-tt / dec)
        return out * gain

    audio = pad / np.max(np.abs(pad)) * 0.55
    audio += bell(4.2, 146.83, 0.30) + bell(16.8, 130.81, 0.22)
    fade = np.clip((TOTAL - t) / 3.0, 0, 1) * np.clip(t / 1.5, 0, 1)
    audio *= fade
    audio = audio / np.max(np.abs(audio)) * 0.7
    stereo = np.stack([audio, np.roll(audio, 220)], axis=1)
    pcm = (stereo * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def render(out):
    if os.path.exists(PHOTO) and os.path.exists(ANONS):
        return render_photo_version(out)
    tmp = tempfile.mkdtemp()
    v, a = os.path.join(tmp, "v.mp4"), os.path.join(tmp, "a.wav")
    render_video(v)
    render_audio(a)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", v, "-i", a, "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", out], check=True)
    return out


# ------------------------------------------------- fotoğraflı + anonslu sürüm
ROOT = os.path.dirname(os.path.abspath(__file__))
PHOTO = os.path.join(ROOT, "assets", "special", "ataturk.jpg")
ANONS = os.path.join(ROOT, "assets", "special", "ataturk_anons.mp3")


def audio_duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", path], capture_output=True, text=True).stdout
    return float(out.strip())


def render_photo_version(out):
    adur = audio_duration(ANONS)
    total = adur + 7.0  # anons bitince anma metni ve kapanış için süre
    src = Image.open(PHOTO).convert("RGB")
    # dikey kadraj: yüz merkezde
    sw, sh = src.size
    cw = int(sh * 9 / 16)
    cx = int(sw * 0.52)
    left = max(0, min(sw - cw, cx - cw // 2))
    crop = src.crop((left, 0, left + cw, sh))
    base = crop.resize((int(W * 1.12), int(H * 1.12)), Image.LANCZOS)
    # alttan karartma (yazı okunurluğu)
    grad = np.zeros((H, W, 1), np.float32)
    ys = np.linspace(0, 1, H)[:, None]
    grad[:, :, 0] = np.clip((ys - 0.45) / 0.55, 0, 1) ** 1.3 * 0.85
    top = np.clip((0.18 - ys) / 0.18, 0, 1) * 0.55
    grad[:, :, 0] = np.maximum(grad[:, :, 0], top)

    # Ses analizi: 0-13.5 sn müzik; İtalyanca anons ~13.6-31.2 sn (4 cümle bloğu)
    texts = [
        (1.0, 6.6, ["10 Kasım 1938", "09.05"]),
        (7.0, 13.2, ["Aramızdan ayrılışının", "88. yılında"]),
        (13.6, 17.25, ("sub", ["“Sezar, İskender, Napolyon…”"])),
        (17.3, 23.3, ("sub", ["“Ayağa kalkınız!”"])),
        (23.4, 31.3, ("sub", ["“Büyüğünüz geliyor…”"])),
        (31.6, total - 3.8, ["Gazi Mustafa Kemal", "Atatürk'ü saygı,", "minnet ve özlemle", "anıyoruz."]),
        (total - 3.6, total + 1, "end"),
    ]
    tmpv = out + ".v.mp4"
    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", tmpv]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    n = int(total * FPS)
    for i in range(n):
        t = i / FPS
        z = 1.0 + 0.10 * (t / total)            # yavaş yakınlaşma
        bw, bh = base.size
        vw, vh = int(bw / 1.12 / z * 1.12 / 1.12 * 1.0), 0
        cw2, ch2 = int(bw / z), int(bh / z)
        x0 = (bw - cw2) // 2
        y0 = int((bh - ch2) * 0.35)
        frame = base.crop((x0, y0, x0 + cw2, y0 + ch2)).resize((W, H), Image.BILINEAR)
        arr = np.asarray(frame).astype(np.float32)
        fin = ease(t / 2.0)
        end_dark = ease((t - (total - 3.6)) / 1.2) * 0.55
        arr = arr * (1 - grad) * fin * (1 - end_dark)
        img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
        d = ImageDraw.Draw(img)
        for s, e, what in texts:
            if not (s <= t < e):
                continue
            fd = 0.25 if isinstance(what, tuple) else 0.9
            a = min(ease((t - s) / fd), 1 - ease((t - (e - fd)) / fd))
            if isinstance(what, tuple) and what[0] == "sub":
                sf = font(F_SEMI, 58)
                y = 1500
                for ln in what[1]:
                    tw = d.textlength(ln, font=sf)
                    d.text(((W - tw) / 2, y), ln, font=sf, fill=mix(WHITE, a, (0, 0, 0)),
                           stroke_width=3, stroke_fill=(0, 0, 0))
                    y += 76
            elif what == "end":
                a = ease((t - s) / 0.9)
                f = font(F_HEAD, 80)
                centered(d, "Unutmadık,", f, 1330, mix(WHITE, a, (0, 0, 0)))
                centered(d, "unutmayacağız.", f, 1420, mix(WHITE, a, (0, 0, 0)))
            else:
                f = font(F_HEAD, 86)
                y = 1560 - len(what) * 100
                for ln in what:
                    centered(d, ln, f, y, mix(WHITE, a, (0, 0, 0)))
                    y += 100
        p.stdin.write(img.tobytes())
    p.stdin.close()
    if p.wait() != 0:
        raise RuntimeError("ffmpeg hata")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", tmpv, "-i", ANONS,
                    "-af", f"afade=t=in:d=0.8,afade=t=out:st={adur - 1.2:.2f}:d=1.2,apad",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest",
                    "-movflags", "+faststart", out], check=True)
    os.remove(tmpv)
    return out


CAPTIONS = {
    "ataturk": ("Aramızdan ayrılışının 88. yılında Cumhuriyetimizin kurucusu "
                "Gazi Mustafa Kemal Atatürk'ü saygı, minnet ve özlemle anıyoruz. 🇹🇷\n\n"
                "#10Kasım #Atatürk #10Kasım1938 #UnutmadıkUnutmayacağız #izmir"),
}

if __name__ == "__main__":
    which, out = sys.argv[1], sys.argv[2]
    assert which == "ataturk"
    print(render(out))
