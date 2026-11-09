"""Dijital Tadilat Instagram botu.

Kullanım:
  python bot.py --kind image            # günün gönderisini üret + paylaş
  python bot.py --kind reel             # günün Reels videosunu üret + paylaş
  python bot.py --kind image --dry-run  # sadece üret, paylaşma

Sıradaki içerik state.json'daki sayaçtan seçilir. Paylaşım başarılı olunca
sayaç artırılıp repoya kaydedilir; hata olursa aynı içerik bir sonraki
çalışmada tekrar denenir, içerik atlanmaz.
"""
import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone

import requests

from render import make_image, make_reel

API_VERSION = "v26.0"
BASE_URL = f"https://graph.facebook.com/{API_VERSION}"
RUPLOAD_URL = f"https://rupload.facebook.com/ig-api-upload/{API_VERSION}"

ROOT = os.path.dirname(os.path.abspath(__file__))
CONTENT_PATH = os.path.join(ROOT, "content", "content.json")
STATE_PATH = os.path.join(ROOT, "state.json")
MEDIA_DIR = os.path.join(ROOT, "media")
TR = timezone(timedelta(hours=3))

def _clean(v):
    """Yapıştırırken kalan boşluk, tırnak ve virgülleri temizler."""
    return (v or "").strip().strip('"\'').strip(",").strip().strip('"\'') or None


INSTAGRAM_ACCOUNT_ID = _clean(os.getenv("INSTAGRAM_ACCOUNT_ID"))
def _extract_token(v):
    """Yanlışlıkla JSON parçasıyla yapıştırılırsa içindeki EAA... token'ını alır."""
    import re
    v = _clean(v)
    if not v:
        return None
    m = re.search(r"EAA[A-Za-z0-9]+", v)
    return m.group(0) if m else v


ACCESS_TOKEN = _extract_token(os.getenv("ACCESS_TOKEN"))
REPO = os.getenv("GITHUB_REPOSITORY", "dijitaltadilat-cyber/dijitaltadilat-bot")


# ---------------------------------------------------------------- yardımcılar
def fail(msg):
    print(f"❌ {msg}")
    sys.exit(1)


def load_json(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def git(*args):
    print(f"   $ git {' '.join(args)}")
    subprocess.run(["git", *args], cwd=ROOT, check=True)


def git_out(*args):
    return subprocess.run(["git", *args], cwd=ROOT, check=True,
                          capture_output=True, text=True).stdout.strip()


def build_caption(item, district):
    tag = item.get("tag", "esnaf")
    hashtags = [
        "#izmir", f"#{district['tag']}", f"#{district['tag']}esnafı", "#izmiresnafı",
        f"#{tag}", "#esnaf", "#küçükişletme", "#sosyalmedyayönetimi", "#dijitaltadilat",
    ]
    seen, uniq = set(), []
    for h in hashtags:
        if h not in seen:
            seen.add(h)
            uniq.append(h)
    return (
        f"{item['caption']}\n\n"
        f"📍 İzmir · {district['name']} esnafı, bu paylaşım sana!\n"
        "Dükkânının Instagram'ını biz yönetelim. İlk görüşme ücretsiz, DM'den yaz 👋\n\n"
        + " ".join(uniq)
    )


# ----------------------------------------------------------------- Graph API
def handle(resp, step):
    try:
        data = resp.json()
    except ValueError:
        fail(f"{step}: JSON olmayan yanıt (HTTP {resp.status_code}): {resp.text[:300]}")
    if resp.status_code != 200 or (isinstance(data, dict) and "error" in data):
        err = data.get("error", {}) if isinstance(data, dict) else {}
        print(f"❌ {step} başarısız (HTTP {resp.status_code})")
        print(f"   Mesaj : {err.get('message')}")
        print(f"   Kod   : {err.get('code')} / Alt kod: {err.get('error_subcode')}")
        if err.get("code") == 190:
            print("   ⚠️  ACCESS_TOKEN süresi dolmuş ya da geçersiz. Yeni token alıp "
                  "GitHub > Settings > Secrets > ACCESS_TOKEN değerini güncelle.")
        sys.exit(1)
    return data


def wait_ready(creation_id, max_wait=600, delay=10):
    print("⏳ Instagram medyayı işliyor...")
    waited = 0
    while waited <= max_wait:
        r = requests.get(f"{BASE_URL}/{creation_id}",
                         params={"fields": "status_code,status", "access_token": ACCESS_TOKEN},
                         timeout=30)
        data = handle(r, "Durum kontrolü")
        status = data.get("status_code")
        print(f"   {waited:>3} sn: {status}")
        if status == "FINISHED":
            return
        if status in ("ERROR", "EXPIRED"):
            fail(f"Medya işlenemedi: {status} – {data.get('status')}")
        time.sleep(delay)
        waited += delay
    fail("Medya zamanında hazır olmadı.")


def publish(creation_id):
    for attempt in range(3):
        r = requests.post(f"{BASE_URL}/{INSTAGRAM_ACCOUNT_ID}/media_publish",
                          data={"creation_id": creation_id, "access_token": ACCESS_TOKEN},
                          timeout=60)
        try:
            body = r.json()
        except ValueError:
            body = {}
        if r.status_code == 200 and "id" in body:
            media_id = body["id"]
            print(f"🎉 Yayınlandı! Medya ID: {media_id}")
            return media_id
        print(f"   Yayınlama denemesi {attempt + 1} olmadı, tekrar denenecek...")
        time.sleep(15)
    handle(r, "Yayınlama")


def post_image(image_url, caption):
    print("📤 Görsel konteyneri oluşturuluyor...")
    r = requests.post(f"{BASE_URL}/{INSTAGRAM_ACCOUNT_ID}/media",
                      data={"image_url": image_url, "caption": caption,
                            "access_token": ACCESS_TOKEN}, timeout=60)
    cid = handle(r, "Görsel konteyneri")["id"]
    wait_ready(cid, max_wait=120, delay=5)
    return publish(cid)


def post_reel(video_path, caption):
    print("📤 Reels konteyneri oluşturuluyor (doğrudan yükleme)...")
    r = requests.post(f"{BASE_URL}/{INSTAGRAM_ACCOUNT_ID}/media",
                      data={"media_type": "REELS", "upload_type": "resumable",
                            "caption": caption, "share_to_feed": "true",
                            "thumb_offset": "4000", "access_token": ACCESS_TOKEN},
                      timeout=60)
    cid = handle(r, "Reels konteyneri")["id"]

    size = os.path.getsize(video_path)
    print(f"⬆️  Video yükleniyor ({size / 1e6:.1f} MB)...")
    with open(video_path, "rb") as fh:
        r = requests.post(f"{RUPLOAD_URL}/{cid}",
                          headers={"Authorization": f"OAuth {ACCESS_TOKEN}",
                                   "offset": "0", "file_size": str(size)},
                          data=fh, timeout=300)
    handle(r, "Video yükleme")
    wait_ready(cid, max_wait=600, delay=10)
    return publish(cid)


# --------------------------------------------------------------------- akış
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kind", choices=["image", "reel"], required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    content = load_json(CONTENT_PATH)
    state = load_json(STATE_PATH, {"post": 0, "reel": 0, "history": []})
    pool = content["posts"] if args.kind == "image" else content["reels"]
    key = "post" if args.kind == "image" else "reel"
    idx = state[key] % len(pool)
    item = pool[idx]
    districts = content["districts"]
    district = districts[(state["post"] + state["reel"]) % len(districts)]
    caption = build_caption(item, district)

    now = datetime.now(TR)
    stamp = now.strftime("%Y%m%d-%H%M")
    os.makedirs(MEDIA_DIR, exist_ok=True)

    print(f"=== Dijital Tadilat botu · {args.kind} #{idx} · {district['name']} ===")
    print(caption)
    print("---")

    if not args.dry_run and not (INSTAGRAM_ACCOUNT_ID and ACCESS_TOKEN):
        fail("INSTAGRAM_ACCOUNT_ID veya ACCESS_TOKEN eksik (GitHub Secrets).")
    if ACCESS_TOKEN:
        t = ACCESS_TOKEN
        print(f"🔑 Token kontrolü: uzunluk={len(t)}, EAA ile başlıyor={t.startswith('EAA')}, "
              f"boşluk var={any(c.isspace() for c in t)}, tırnak/virgül var={any(c in t for c in '{}:,')}")
        print(f"🔑 Hesap no kontrolü: uzunluk={len(INSTAGRAM_ACCOUNT_ID or '')}, "
              f"sadece rakam={(INSTAGRAM_ACCOUNT_ID or '').isdigit()}")

    if args.kind == "image":
        rel = f"media/{stamp}-post{idx}.jpg"
        make_image(item, os.path.join(ROOT, rel))
        print(f"🖼️  Görsel üretildi: {rel}")
        if args.dry_run:
            return
        # Görseli repoya koy, Instagram oradan çeksin
        git("add", rel)
        git("commit", "-m", f"Görsel: {rel}")
        git("push")
        sha = git_out("rev-parse", "HEAD")
        url = f"https://raw.githubusercontent.com/{REPO}/{sha}/{rel}"
        print(f"🔗 {url}")
        for _ in range(12):  # raw adresi birkaç saniyede yayına girer
            if requests.head(url, timeout=20).status_code == 200:
                break
            time.sleep(5)
        media_id = post_image(url, caption)
    else:
        path = os.path.join(MEDIA_DIR, f"{stamp}-reel{idx}.mp4")
        make_reel(item, path)
        print(f"🎬 Video üretildi: {os.path.relpath(path, ROOT)}")
        if args.dry_run:
            return
        media_id = post_reel(path, caption)
        os.remove(path)  # videolar repoya eklenmez

    state[key] += 1
    state["history"] = (state.get("history", []) + [{
        "time": now.isoformat(timespec="minutes"), "kind": args.kind,
        "index": idx, "district": district["name"], "media_id": media_id,
    }])[-60:]
    save_json(STATE_PATH, state)
    git("add", "state.json")
    git("commit", "-m", f"Paylaşıldı: {args.kind} #{idx} ({district['name']})")
    git("push")
    print("=== Tamamlandı ===")


if __name__ == "__main__":
    main()
