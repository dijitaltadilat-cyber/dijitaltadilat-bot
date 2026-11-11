"""Paylaşım saatleri ve "şimdi ne yapılmalı?" mantığı.

Sadece standart kütüphane kullanır; böylece GitHub Actions'ta hiçbir şey
kurmadan (saniyeler içinde) çalışabilir ve gereksiz çalıştırmalar hemen biter.

GitHub zamanlanmış işleri saat başı gibi seyrek ve gecikmeli başlatabiliyor.
Bu yüzden iki önlem var:
  * LOOKAHEAD_MIN: saate en çok bu kadar dakika kala uyanan çalışma, kurulumunu
    yapıp saati bekler ve paylaşımı tam saatinde atar.
  * CATCH_UP_HOURS: saati geçmiş ama yapılmamış paylaşım bu süre içinde yakalanır.
"""
import json
import os
import sys
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.abspath(__file__))
STATE_PATH = os.path.join(ROOT, "state.json")
TR = timezone(timedelta(hours=3))

# Türkiye saati
SLOTS = [
    ("08:37", "image"),  # dükkân açılışı, çay saati
    ("13:37", "image"),  # öğle arası
    ("20:43", "reel"),   # kepenk kapandı, Reels saati
]
SPECIAL_DAYS = {"11-10": [("09:05", "special_ataturk")]}  # o gün sadece bunlar
CATCH_UP_HOURS = 4
LOOKAHEAD_MIN = 75  # GitHub'ın gözlenen en uzun zamanlayıcı boşluğundan büyük
TOLERANCE_SEC = 60  # bekleme birkaç saniye erken biterse paylaşım kaçmasın


def day_slots(now):
    return SPECIAL_DAYS.get(now.strftime("%m-%d"), SLOTS)


def pending_slot(state, now=None, lookahead_min=LOOKAHEAD_MIN):
    """Sıradaki yapılmamış paylaşım: (anahtar, tür, saniye_beklenecek) ya da None.

    Saati gelmiş ya da en çok `lookahead_min` dakika sonra gelecek olanı verir;
    saati CATCH_UP_HOURS'tan fazla geçmiş olanı atlar.
    """
    now = now or datetime.now(TR)
    done = set((state or {}).get("slots_done", []))
    # Dünün saatleri de bakılır: 20:43 paylaşımının telafisi gece yarısını aşar.
    for back in (1, 0):
        day = now - timedelta(days=back)
        date = day.strftime("%Y-%m-%d")
        for hhmm, kind in day_slots(day):
            h, m = map(int, hhmm.split(":"))
            t = day.replace(hour=h, minute=m, second=0, microsecond=0)
            key = f"{date} {hhmm}"
            if key in done:
                continue
            if t - timedelta(minutes=lookahead_min) <= now <= t + timedelta(hours=CATCH_UP_HOURS):
                return key, kind, max(0, int((t - now).total_seconds()))
    return None


def due_slot(state, now=None):
    """Saati gelmiş (ya da gelmek üzere olan) paylaşım: (anahtar, tür) ya da None."""
    p = pending_slot(state, now, lookahead_min=0)
    if p:
        return p[0], p[1]
    now = now or datetime.now(TR)
    # bekleme birkaç saniye erken bittiyse tolerans
    p = pending_slot(state, now + timedelta(seconds=TOLERANCE_SEC), lookahead_min=0)
    return (p[0], p[1]) if p else None


def main():
    """GitHub Actions için: needed/at/video değerlerini $GITHUB_OUTPUT biçiminde yazar."""
    state = {}
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH, encoding="utf-8") as fh:
            state = json.load(fh)
    now = datetime.now(TR)
    p = pending_slot(state, now)
    if not p:
        print("needed=false\nat=0\nvideo=false")
        print(f"{now:%H:%M} – şu an yapılacak paylaşım yok.", file=sys.stderr)
        return
    key, kind, wait = p
    print("needed=true")
    print(f"at={int(now.timestamp()) + wait + 3 if wait else 0}")
    print(f"video={'false' if kind == 'image' else 'true'}")
    print(f"Sıradaki: {key} → {kind}, {wait} sn sonra.", file=sys.stderr)


if __name__ == "__main__":
    main()
