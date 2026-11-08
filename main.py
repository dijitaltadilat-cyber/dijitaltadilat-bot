import os
import json
import urllib.request
import urllib.error

# .strip() ekleyerek kopyalamadan kaynaklı gizli alt satır (\n) karakterlerini temizliyoruz
instagram_account_id = (os.environ.get("INSTAGRAM_ACCOUNT_ID") or "").strip()
access_token = (os.environ.get("ACCESS_TOKEN") or "").strip()

if not instagram_account_id or not access_token:
    print("HATA: INSTAGRAM_ACCOUNT_ID veya ACCESS_TOKEN gizli anahtarı bulunamadı!")
    exit(1)

url = f"https://graph.facebook.com/v20.0/{instagram_account_id}?fields=id,username,name&access_token={access_token}"

try:
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        print("----------------------------------------")
        print("✅ Instagram API Bağlantısı Başarılı!")
        print(f"Kullanıcı Adı: @{data.get('username')}")
        print(f"Hesap Adı: {data.get('name')}")
        print(f"Hesap ID: {data.get('id')}")
        print("----------------------------------------")
except urllib.error.HTTPError as e:
    error_body = e.read().decode()
    print("----------------------------------------")
    print("❌ API Hatası:", error_body)
    print("----------------------------------------")
    exit(1)
except Exception as e:
    print("❌ Beklenmeyen Hata:", str(e))
    exit(1)
