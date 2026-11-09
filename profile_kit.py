"""Instagram profil kiti: öne çıkan hikâye kapakları + hikâye sayfaları.

python profile_kit.py <çıktı_klasörü>
"""
import os
import sys

from PIL import Image, ImageDraw

from render import (F_BOLD, F_HEAD, F_SEMI, LIME, MUTED, NAVY, NAVY2, PHONE, WHITE,
                    asset, chat_icon, font, lockup, wrap)

SW, SH = 1080, 1920
WEB = "dijitaltadilat.com"
HANDLE = "@dijitaltadilat"


# ------------------------------------------------------------------ simgeler
def ic_logo(d, img, cx, cy, s):
    m = asset("logo_mark.png", max_h=int(s * 1.1))
    img.paste(m, (cx - m.size[0] // 2 + 8, cy - m.size[1] // 2), m)


def ic_grid(d, img, cx, cy, s):
    g, r = s * 0.12, s * 0.12
    w = (s - g) / 2
    for i in range(2):
        for j in range(2):
            x = cx - s / 2 + i * (w + g)
            y = cy - s / 2 + j * (w + g)
            d.rounded_rectangle([x, y, x + w, y + w], radius=r, fill=LIME if (i + j) % 2 == 0 else WHITE)


def ic_text(txt, size_k=1.0):
    def f(d, img, cx, cy, s):
        fn = font(F_HEAD, int(s * size_k))
        w = d.textlength(txt, font=fn)
        bb = d.textbbox((0, 0), txt, font=fn)
        d.text((cx - w / 2, cy - (bb[1] + bb[3]) / 2), txt, fill=LIME, font=fn)
    return f


def ic_chat(d, img, cx, cy, s):
    chat_icon(d, cx - s / 2, cy - s / 2 - s * 0.05, s, LIME, NAVY)


def ic_star(d, img, cx, cy, s):
    import math
    pts = []
    for k in range(10):
        r = s / 2 if k % 2 == 0 else s / 4.6
        a = -math.pi / 2 + k * math.pi / 5
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    d.polygon(pts, fill=LIME)


HIGHLIGHTS = [
    ("hakkimizda", "Hakkımızda", ic_logo),
    ("hizmetler", "Hizmetler", ic_grid),
    ("paketler", "Paketler", ic_text("₺", 1.25)),
    ("web-yazilim", "Web & Yazılım", ic_text("</>", 0.9)),
    ("neden-biz", "Neden Biz", ic_star),
    ("iletisim", "İletişim", ic_chat),
]


def cover(icon):
    img = Image.new("RGB", (SW, SH), NAVY)
    d = ImageDraw.Draw(img)
    cx, cy = SW // 2, SH // 2
    d.ellipse([cx - 330, cy - 330, cx + 330, cy + 330], fill=NAVY2)
    d.ellipse([cx - 330, cy - 330, cx + 330, cy + 330], outline=LIME, width=10)
    icon(d, img, cx, cy, 300)
    return img


# ------------------------------------------------------------ hikâye sayfası
def story_base(title, kicker):
    img = Image.new("RGB", (SW, SH), NAVY)
    big = asset("logo_mark.png", max_h=900, opacity=0.06)
    img.paste(big, (SW - big.size[0] + 260, SH - big.size[1] - 160), big)
    d = ImageDraw.Draw(img)
    lockup(img, 80, 230, h=80)
    d.text((80, 400), kicker, fill=LIME, font=font(F_BOLD, 40))
    tf = font(F_HEAD, 120)
    y = 450
    for ln in wrap(d, title, tf, 920):
        d.text((80, y), ln, fill=WHITE, font=tf)
        y += 128
    return img, d, y + 40


def footer(img, d, y=1500):
    # WhatsApp + site + kullanıcı adı
    d.rounded_rectangle([80, y, SW - 80, y + 120], radius=60, fill=LIME)
    chat_icon(d, 120, y + 30, 58, NAVY, LIME)
    d.text((200, y + 22), f"WhatsApp {PHONE}", fill=NAVY, font=font(F_HEAD, 58))
    sf = font(F_BOLD, 44)
    d.text((80, y + 160), f"{WEB}  ·  {HANDLE}", fill=MUTED, font=sf)


def bullets(d, y, items, size=52, gap=86):
    f = font(F_SEMI, size)
    for it in items:
        d.rounded_rectangle([80, y + size * 0.35, 80 + 22, y + size * 0.35 + 22], radius=6, fill=LIME)
        d.text((130, y), it, fill=WHITE, font=f)
        y += gap
    return y


def s_hakkimizda():
    img, d, y = story_base("Biz Dijital Tadilat", "MERHABA İZMİR 👋".replace(" 👋", ""))
    f = font(F_SEMI, 54)
    txt = ("Sosyal medya ajansıyız ve yazılım geliştiriyoruz. "
           "İzmir esnafının Instagram'ını yönetiyor, web sitesi ve "
           "işine özel yazılımlar yapıyoruz.")
    for ln in wrap(d, txt, f, 920):
        d.text((80, y), ln, fill=MUTED, font=f)
        y += 76
    d.text((80, y + 50), "Dükkânın dijitalde de", fill=WHITE, font=font(F_HEAD, 72))
    d.text((80, y + 130), "en bilineni olsun.", fill=LIME, font=font(F_HEAD, 72))
    footer(img, d)
    return img


def s_hizmetler():
    img, d, y = story_base("Neler yapıyoruz?", "HİZMETLER")
    bullets(d, y, ["Instagram hesap yönetimi", "Reels ve içerik üretimi", "Google İşletme profili",
                   "Reklam kurulumu ve yönetimi", "Web sitesi tasarımı", "Online randevu ve özel yazılım"])
    footer(img, d)
    return img


def s_paketler():
    img, d, y = story_base("Sosyal medya paketleri", "PAKETLER")
    rows = [("Başlangıç", "3.990"), ("Standart ⭐".replace(" ⭐", ""), "6.990"), ("Pro", "10.990")]
    for i, (n, p) in enumerate(rows):
        hl = i == 1
        d.rounded_rectangle([80, y, SW - 80, y + 150], radius=34, fill=LIME if hl else NAVY2)
        d.text((120, y + 38), n, fill=NAVY if hl else WHITE, font=font(F_HEAD, 64))
        pf = font(F_HEAD, 72)
        t = f"{p} ₺/ay"
        d.text((SW - 120 - d.textlength(t, font=pf), y + 30), t, fill=NAVY if hl else LIME, font=pf)
        y += 180
    d.text((80, y + 20), "İlk 5 esnafa ilk ay %50 indirim", fill=LIME, font=font(F_HEAD, 60))
    d.text((80, y + 100), "Taahhüt yok · Detaylar sabit gönderide", fill=MUTED, font=font(F_SEMI, 44))
    footer(img, d)
    return img


def s_web():
    img, d, y = story_base("Web sitesi ve yazılım", "WEB & YAZILIM")
    y = bullets(d, y, ["Tanıtım ve kurumsal site", "Menü ve katalog sitesi", "Online randevu sistemi",
                       "Mobil uyumlu, hızlı, SEO uyumlu", "İşine özel yazılım"])
    d.text((80, y + 30), "Fiyat için WhatsApp'tan yaz,", fill=WHITE, font=font(F_HEAD, 60))
    d.text((80, y + 105), "ihtiyacına göre teklif verelim.", fill=LIME, font=font(F_HEAD, 60))
    footer(img, d)
    return img


def s_nedenbiz():
    img, d, y = story_base("Neden Dijital Tadilat?", "NEDEN BİZ")
    bullets(d, y, ["Esnafı anlayan, yerel ekip", "Sosyal medya + yazılım tek elden",
                   "Net fiyat, taahhüt yok", "Her ay düzenli rapor", "WhatsApp'tan hızlı iletişim"])
    footer(img, d)
    return img


def s_iletisim():
    img, d, y = story_base("Bize ulaş", "İLETİŞİM")
    rows = [("WhatsApp", PHONE), ("Web", WEB), ("Instagram", HANDLE), ("Konum", "İzmir")]
    for k, v in rows:
        d.text((80, y), k, fill=MUTED, font=font(F_BOLD, 44))
        d.text((80, y + 52), v, fill=WHITE, font=font(F_HEAD, 76))
        y += 170
    d.text((80, y + 20), "İlk görüşme ücretsiz ☕".replace(" ☕", ""), fill=LIME, font=font(F_HEAD, 64))
    footer(img, d)
    return img


STORIES = {"hakkimizda": s_hakkimizda, "hizmetler": s_hizmetler, "paketler": s_paketler,
           "web-yazilim": s_web, "neden-biz": s_nedenbiz, "iletisim": s_iletisim}


def build(out):
    os.makedirs(out, exist_ok=True)
    files = []
    for i, (slug, name, icon) in enumerate(HIGHLIGHTS, 1):
        c = os.path.join(out, f"{i}_{slug}_kapak.jpg")
        s = os.path.join(out, f"{i}_{slug}_hikaye.jpg")
        cover(icon).save(c, quality=94)
        STORIES[slug]().save(s, quality=94)
        files += [c, s]
    return files


if __name__ == "__main__":
    print("\n".join(build(sys.argv[1] if len(sys.argv) > 1 else "profil_kiti")))
