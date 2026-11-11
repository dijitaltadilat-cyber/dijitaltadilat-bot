# dijitaltadilat-bot

@dijitaltadilat Instagram hesabına her gün otomatik paylaşım yapar. Bilgisayarın açık olması gerekmez, GitHub Actions üzerinde çalışır.

## Takvim (Türkiye saati, her gün)
| Ne | Ne zaman | Neden |
|---|---|---|
| Görsel gönderi | 08:37 | Esnaf dükkânı açarken telefona bakıyor |
| Görsel gönderi | 13:37 | Öğle arası |
| Reels videosu | 20:43 | Kepenk kapandı, Reels izleme saati |

Saatler `slots.py` içinde.

## Gecikmesiz çalışma düzeni
GitHub zamanlanmış işleri saat başı gibi seyrek ve gecikmeli başlatabiliyor, bu yüzden:
- **`kapi` işi** her 5 dakikada bir saniyeler içinde biter (apt/pip yok), paylaşım saatine
  75 dk kala ya da saat geçmişse `paylas` işini başlatır.
- **`paylas` işi** kurulumu önceden yapar, saati bekler ve paylaşımı tam saatinde atar.
- Bir çalıştırma atlanırsa sonraki yakalar; kaçan paylaşım 4 saat içinde telafi edilir.
- ffmpeg sadece Reels için kurulur; apt takılırsa pip ile gelen ffmpeg'e geçilir.
- Paylaşım sonrası `state.json` gönderilemezse çalışma hata verir (aynı saat tekrar paylaşılmasın).

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
