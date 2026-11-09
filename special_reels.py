"""Özel gün Reels'leri (satış içermez). python special_reels.py ataturk <çıktı.mp4>"""
import subprocess
import sys

from PIL import Image, ImageDraw

from render import F_HEAD, F_SEMI, asset, font, wrap

W, H, FPS = 1080, 1920, 30
BG = (10, 10, 16)
WHITE = (245, 245, 250)
GREY = (150, 150, 165)
RED = (227, 10, 23)


def ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def mix(c, a):
    return tuple(int(BG[i] + (c[i] - BG[i]) * a) for i in range(3))


# (başlangıç sn, bitiş sn, çizim fonksiyonu)
def scene_date(d, a):
    f = font(F_SEMI, 84)
    t = "10 Kasım 1938"
    d.text(((W - d.textlength(t, font=f)) / 2, 820), t, fill=mix(GREY, a), font=f)
    d.rectangle([W / 2 - 70 * a, 950, W / 2 + 70 * a, 957], fill=mix(RED, a))


def scene_time(d, a):
    f = font(F_HEAD, 300)
    t = "09.05"
    d.text(((W - d.textlength(t, font=f)) / 2, 700), t, fill=mix(WHITE, a), font=f)


def scene_text(lines, size=88, color=WHITE, y0=None, lh=1.15):
    def draw(d, a):
        f = font(F_HEAD, size)
        ls = []
        for ln in lines:
            ls += wrap(d, ln, f, 900)
        step = int(size * lh)
        y = y0 if y0 is not None else (H - len(ls) * step) // 2 - 40
        for ln in ls:
            d.text(((W - d.textlength(ln, font=f)) / 2, y), ln, fill=mix(color, a), font=f)
            y += step
    return draw


def scene_quote(d, a):
    f = font(F_SEMI, 58)
    q = ("“Benim naçiz vücudum elbet bir gün toprak olacaktır, "
         "fakat Türkiye Cumhuriyeti ilelebet payidar kalacaktır.”")
    ls = wrap(d, q, f, 880)
    y = (H - len(ls) * 82) // 2 - 80
    for ln in ls:
        d.text(((W - d.textlength(ln, font=f)) / 2, y), ln, fill=mix(WHITE, a), font=f)
        y += 82
    s = "Mustafa Kemal Atatürk"
    sf = font(F_HEAD, 54)
    d.text(((W - d.textlength(s, font=sf)) / 2, y + 50), s, fill=mix(GREY, a), font=sf)
    d.rectangle([W / 2 - 50, y + 140, W / 2 + 50, y + 146], fill=mix(RED, a))


def scene_end(img, d, a):
    m = asset("logo_mark.png", max_h=120, opacity=0.9 * a)
    img.paste(m, ((W - m.size[0]) // 2, 860), m)
    f = font(F_SEMI, 40)
    t = "Dijital Tadilat"
    d.text(((W - d.textlength(t, font=f)) / 2, 1010), t, fill=mix(GREY, a), font=f)


def ataturk_scenes():
    return [
        (0.0, 3.6, scene_date),
        (3.6, 7.2, scene_time),
        (7.2, 11.0, scene_text(["Aramızdan ayrılışının", "88. yılında"], 92)),
        (11.0, 15.5, scene_text(["Gazi Mustafa", "Kemal Atatürk'ü", "saygı, minnet", "ve özlemle anıyoruz."], 84)),
        (15.5, 22.0, scene_quote),
        (22.0, 25.5, "end"),
    ]


def render(scenes, out):
    total = scenes[-1][1]
    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100", "-shortest",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    fade = 0.9
    for i in range(int(total * FPS)):
        t = i / FPS
        img = Image.new("RGB", (W, H), BG)
        d = ImageDraw.Draw(img)
        for s, e, fn in scenes:
            if s <= t < e:
                a = min(ease((t - s) / fade), 1 - ease((t - (e - fade)) / fade)) if e != total else ease((t - s) / fade)
                if fn == "end":
                    scene_end(img, d, a)
                else:
                    fn(d, a)
        p.stdin.write(img.tobytes())
    p.stdin.close()
    if p.wait() != 0:
        raise RuntimeError("ffmpeg hata")
    return out


CAPTIONS = {
    "ataturk": ("Aramızdan ayrılışının 88. yılında Cumhuriyetimizin kurucusu "
                "Gazi Mustafa Kemal Atatürk'ü saygı, minnet ve özlemle anıyoruz. 🇹🇷\n\n"
                "#10Kasım #Atatürk #10Kasım1938 #UnutmadıkUnutmayacağız #izmir"),
}

if __name__ == "__main__":
    which, out = sys.argv[1], sys.argv[2]
    render({"ataturk": ataturk_scenes}[which](), out)
    print(out)
