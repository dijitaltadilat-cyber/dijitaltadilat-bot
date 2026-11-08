import os
import sys
import time
import requests

API_VERSION = "v26.0"
BASE_URL = f"https://graph.facebook.com/{API_VERSION}"

INSTAGRAM_ACCOUNT_ID = os.getenv("INSTAGRAM_ACCOUNT_ID")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")

IMAGE_SOURCE_URL = "https://picsum.photos/1080/1080"
CAPTION = "🚀 Dijital Tadilat otomatik paylaşım testi başarıyla çalışıyor! #dijitaltadilat"


def check_env():
    missing = [name for name, val in [
        ("INSTAGRAM_ACCOUNT_ID", INSTAGRAM_ACCOUNT_ID),
        ("ACCESS_TOKEN", ACCESS_TOKEN),
    ] if not val]
    if missing:
        print(f"❌ Eksik ortam değişkeni: {', '.join(missing)}")
        sys.exit(1)
    print("✅ Ortam değişkenleri yüklendi.")


def resolve_image_url(url):
    """picsum.photos yönlendirme yaptığı için son (sabit) görsel adresini bulur."""
    print(f"🔎 Görsel adresi çözülüyor: {url}")
    try:
        resp = requests.get(url, allow_redirects=True, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"❌ Görsel alınamadı: {e}")
        sys.exit(1)
    content_type = resp.headers.get("Content-Type", "")
    if "image" not in content_type:
        print(f"❌ Beklenmeyen içerik türü: {content_type}")
        sys.exit(1)
    print(f"✅ Son görsel adresi: {resp.url}")
    return resp.url


def handle_response(resp, step):
    try:
        data = resp.json()
    except ValueError:
        print(f"❌ {step}: JSON olmayan yanıt (HTTP {resp.status_code}): {resp.text}")
        sys.exit(1)
    if resp.status_code != 200 or "error" in data:
        err = data.get("error", {})
        print(f"❌ {step} başarısız (HTTP {resp.status_code})")
        print(f"   Mesaj : {err.get('message')}")
        print(f"   Tür   : {err.get('type')}")
        print(f"   Kod   : {err.get('code')} / Alt kod: {err.get('error_subcode')}")
        sys.exit(1)
    return data


def create_media_container(image_url):
    print("📤 1. Adım: Medya konteyneri oluşturuluyor...")
    resp = requests.post(
        f"{BASE_URL}/{INSTAGRAM_ACCOUNT_ID}/media",
        data={
            "image_url": image_url,
            "caption": CAPTION,
            "access_token": ACCESS_TOKEN,
        },
        timeout=60,
    )
    data = handle_response(resp, "Medya konteyneri oluşturma")
    creation_id = data.get("id")
    if not creation_id:
        print(f"❌ creation_id alınamadı. Yanıt: {data}")
        sys.exit(1)
    print(f"✅ creation_id: {creation_id}")
    return creation_id


def wait_until_ready(creation_id, max_attempts=10, delay=5):
    print("⏳ Konteynerin hazır olması bekleniyor...")
    for attempt in range(1, max_attempts + 1):
        resp = requests.get(
            f"{BASE_URL}/{creation_id}",
            params={"fields": "status_code", "access_token": ACCESS_TOKEN},
            timeout=30,
        )
        data = handle_response(resp, "Konteyner durum kontrolü")
        status = data.get("status_code")
        print(f"   Deneme {attempt}/{max_attempts}: durum = {status}")
        if status == "FINISHED":
            print("✅ Konteyner hazır.")
            return
        if status in ("ERROR", "EXPIRED"):
            print(f"❌ Konteyner kullanılamaz durumda: {status}")
            sys.exit(1)
        time.sleep(delay)
    print("❌ Konteyner zamanında hazır olmadı.")
    sys.exit(1)


def publish_media(creation_id):
    print("🚀 2. Adım: Gönderi yayınlanıyor...")
    resp = requests.post(
        f"{BASE_URL}/{INSTAGRAM_ACCOUNT_ID}/media_publish",
        data={
            "creation_id": creation_id,
            "access_token": ACCESS_TOKEN,
        },
        timeout=60,
    )
    data = handle_response(resp, "Gönderi yayınlama")
    media_id = data.get("id")
    print(f"🎉 Gönderi başarıyla yayınlandı! Medya ID: {media_id}")
    return media_id


def main():
    print("=== Dijital Tadilat Instagram Botu ===")
    check_env()
    image_url = resolve_image_url(IMAGE_SOURCE_URL)
    creation_id = create_media_container(image_url)
    wait_until_ready(creation_id)
    publish_media(creation_id)
    print("=== İşlem tamamlandı ===")


if __name__ == "__main__":
    main()
