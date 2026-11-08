# dijitaltadilat-bot

@dijitaltadilat Instagram hesabına her gün otomatik paylaşım yapar. Bilgisayarın açık olması gerekmez, GitHub Actions üzerinde çalışır.

## Takvim (Türkiye saati)
| Ne | Ne zaman | Neden |
|---|---|---|
| Görsel gönderi | Pzt–Cmt 08:37 | Esnaf dükkânı açarken telefona bakıyor |
| Reels videosu | Sal/Per/Cmt 20:43 | Kepenk kapandı, Reels izleme saati |
| Reels videosu | Pazar 12:17 | Pazar günü rahat kaydırma saati |

GitHub zamanlanmış işleri yoğunlukta 5–20 dk gecikmeli başlatabilir.

## Dosyalar
- `content/content.json` → gönderi ve Reels metinleri, İzmir ilçeleri (her paylaşımda sıradaki ilçe hedeflenir)
- `render.py` → görsel ve hareketli video üretimi
- `bot.py` → Instagram'a paylaşım
- `state.json` → sıradaki içerik sayacı ve son paylaşımlar
- `assets/logo.png` → buraya logo konursa tüm görsellerde kullanılır

## Elle çalıştırma
Actions → Instagram Bot → Run workflow. "Sadece üret" seçilirse Instagram'a atmaz, çıktıyı indirilebilir dosya olarak bırakır.

## Gerekli Secrets
`INSTAGRAM_ACCOUNT_ID`, `ACCESS_TOKEN`
