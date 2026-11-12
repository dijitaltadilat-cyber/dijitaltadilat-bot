"""Özgün, telifsiz fon müziği üretici (tamamen kodla sentezlenir).

settings(n)                          -> n. Reels için müzik ayarı (tarz, tempo, ton...)
make_track(seconds, seed, path, ...) -> wav dosyası

Her Reels'te müzik değişir: tarz art arda hiç tekrar etmez, tempo / ton /
akor dizisi / enstrüman / ritim de her seferinde yeniden seçilir.
"""
import wave

import numpy as np

SR = 44100
BPM = 112              # eski çağrılar için varsayılan
BEAT = 60 / BPM

STYLES = ["lofi", "pop", "house", "chill", "funk", "akustik"]
BPMS = {"lofi": [84, 88, 92], "pop": [104, 110, 116], "house": [118, 122, 124],
        "chill": [90, 96, 100], "funk": [100, 106, 112], "akustik": [92, 98, 104]}

# Akor dizileri (yarım ton, kök notaya göre)
PROGRESSIONS = [
    [[0, 3, 7], [-4, 0, 3], [3, 7, 10], [-2, 2, 5]],                   # i VI III VII
    [[0, 4, 7], [-3, 0, 4], [-7, -3, 0], [-5, -1, 2]],                 # I vi IV V
    [[0, 4, 7, 11], [5, 9, 12, 16], [2, 5, 9, 12], [7, 11, 14, 17]],   # Imaj7 IVmaj7 ii7 V
    [[0, 3, 7, 10], [5, 8, 12, 15], [-2, 2, 5, 9], [3, 7, 10, 14]],    # i7 iv7 VII IIImaj7
    [[0, 4, 7], [7, 11, 14], [-3, 0, 4], [5, 9, 12]],                  # I V vi IV
    [[0, 3, 7], [5, 8, 12], [-5, -1, 2], [0, 3, 7]],                   # i iv V i
    [[0, 4, 7, 11], [-3, 0, 4, 7], [2, 5, 9, 12], [-5, -1, 2, 5]],     # Imaj7 vi7 ii7 V7
    [[0, 3, 7, 10], [-2, 2, 5, 9], [-4, 0, 3, 7], [-5, -2, 2, 5]],     # i7 VII VI v7
]
ROOTS = [52, 53, 55, 56, 57, 58, 59, 60]  # E3 ... C4
ARPS = [[0, 1, 2, 1, 0, 2, 1, 2], [0, 2, 1, 2, 0, 1, 2, 1], [0, 1, 2, 3, 2, 1, 0, 1],
        [2, 1, 0, 1, 2, 1, 0, 2], [0, 0, 2, 1, 0, 0, 2, 1], [0, 2, 3, 2, 1, 2, 3, 2]]
LEADS = ["pluck", "bell", "marimba", "piano", "synth"]


def settings(n):
    """n. Reels'in müziği. Tarz her seferinde değişir, diğerleri karışık seçilir."""
    rng = np.random.default_rng(n * 7919 + 17)
    style = STYLES[n % len(STYLES)]
    return {"style": style, "bpm": int(rng.choice(BPMS[style])), "seed": int(n * 7919 + 17) % 100000}


def hz(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


def lowpass(x, cutoff):
    a = np.exp(-2 * np.pi * cutoff / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):  # tek kutuplu filtre
        acc = (1 - a) * x[i] + a * acc
        y[i] = acc
    return y


def env_exp(n, decay):
    return np.exp(-np.arange(n) / SR / decay)


def lead_tone(kind, f, L):
    t = np.arange(L) / SR
    s = lambda k: np.sin(2 * np.pi * f * k * t)  # noqa: E731
    if kind == "bell":
        return (s(1) + 0.5 * s(2.76) + 0.25 * s(5.4)) * env_exp(L, 0.35)
    if kind == "marimba":
        return (s(1) + 0.35 * s(4)) * env_exp(L, 0.09)
    if kind == "piano":
        return (s(1) + 0.5 * s(2) + 0.25 * s(3) + 0.12 * s(4)) * env_exp(L, 0.25) * np.clip(t / 0.004, 0, 1)
    if kind == "synth":
        saw = sum(np.sin(2 * np.pi * f * k * t) / k for k in range(1, 7))
        return saw * 0.6 * env_exp(L, 0.18)
    return (s(1) + 0.4 * s(2) + 0.15 * s(3)) * env_exp(L, 0.12)  # pluck


def make_track(seconds, seed=0, path=None, bpm=None, style=None):
    rng = np.random.default_rng(seed)
    style = style or STYLES[seed % len(STYLES)]
    bpm = bpm or BPM
    beat = 60 / bpm
    prog = PROGRESSIONS[rng.integers(len(PROGRESSIONS))]
    root = int(rng.choice(ROOTS))
    arp = ARPS[rng.integers(len(ARPS))]
    lead = {"lofi": "piano", "akustik": "marimba", "house": "synth"}.get(style) \
        if rng.random() < 0.5 else LEADS[rng.integers(len(LEADS))]
    lead = lead or LEADS[rng.integers(len(LEADS))]
    swing = 0.09 if style in ("lofi", "chill") else (0.04 if style == "funk" else 0.0)
    n = int(seconds * SR)
    out = np.zeros(n)
    bar = 4 * beat
    nbars = int(np.ceil(seconds / bar)) + 1

    def at(x):  # zamanı örnek indeksine çevirir (sekizliklerde swing)
        frac = (x / (beat / 2)) % 2
        if 0.99 < frac < 1.01:
            x += swing * beat
        return int(x * SR)

    # --- akor pad
    pad = np.zeros(n)
    bright = {"house": 0.45, "pop": 0.35, "funk": 0.3}.get(style, 0.2)
    for b in range(nbars):
        ch = prog[b % len(prog)]
        s, e = int(b * bar * SR), min(n, int((b + 1) * bar * SR) + int(0.3 * SR))
        if s >= n:
            break
        t = np.arange(e - s) / SR
        seg = np.zeros(e - s)
        for iv in ch:
            f = hz(root + iv)
            for det in (-0.004, 0.004):
                seg += np.sin(2 * np.pi * f * (1 + det) * t) + bright * np.sin(4 * np.pi * f * (1 + det) * t)
        a = np.clip(t / 0.25, 0, 1) * np.clip((e - s) / SR - t, 0, 0.3) / 0.3
        pad[s:e] += seg * a
    tt = np.arange(n) / SR
    pump_amt = 0.6 if style == "house" else 0.35
    pump = (1 - pump_amt) + pump_amt * np.clip((tt % beat) / (beat * 0.6), 0, 1)
    pad_lvl = {"chill": 0.32, "lofi": 0.26}.get(style, 0.2)
    out += pad / (np.max(np.abs(pad)) + 1e-9) * pad_lvl * pump

    # --- melodi / arpej
    step = beat / 2 if style != "funk" else beat / 4
    for k in range(int(seconds / step) + 1):
        if style == "chill" and k % 2:
            continue
        if style == "funk" and arp[k % 8] == 0 and k % 3 == 1:
            continue
        b = int(k * step / bar)
        ch = prog[b % len(prog)]
        note = root + 12 + ch[arp[k % 8] % len(ch)]
        s = at(k * step)
        L = min(int(0.5 * SR), n - s)
        if L <= 0:
            break
        out[s:s + L] += lead_tone(lead, hz(note), L) * 0.09

    # --- bas
    bass_pat = {"house": [0.5, 1.5, 2.5, 3.5], "funk": [0, 0.75, 1.5, 2, 2.75, 3.5],
                "lofi": [0, 2.5], "chill": [0, 2], "akustik": [0, 2, 3]}.get(style, [0, 1.5, 2, 3.5])
    for b in range(nbars):
        ch = prog[b % len(prog)]
        for bi in bass_pat:
            s = int((b * bar + bi * beat) * SR)
            L = min(int(beat * 0.9 * SR), n - s)
            if s >= n or L <= 0:
                continue
            t = np.arange(L) / SR
            f = hz(root - 24 + ch[0] + (7 if style == "funk" and bi == 2.75 else 0))
            tone = np.sin(2 * np.pi * f * t) + 0.25 * np.sin(4 * np.pi * f * t)
            out[s:s + L] += tone * env_exp(L, 0.28) * np.clip(t / 0.01, 0, 1) * 0.30

    # --- davul
    for k in range(int(seconds / beat) + 1):
        s = int(k * beat * SR)
        if s >= n:
            break
        kick = {"house": True, "lofi": k % 4 in (0, 2) or (k % 4 == 3 and seed % 2),
                "chill": k % 4 == 0, "funk": k % 4 in (0, 2)}.get(style, k % 2 == 0)
        if kick:
            L = min(int(0.30 * SR), n - s)
            t = np.arange(L) / SR
            f = 50 + 90 * np.exp(-t / 0.03)
            out[s:s + L] += np.sin(2 * np.pi * np.cumsum(f) / SR) * env_exp(L, 0.12) * \
                (0.6 if style == "house" else 0.5)
        if k % 2 == 1 and style != "chill":
            L = min(int(0.22 * SR), n - s)
            noise = rng.standard_normal(L)
            noise = noise - lowpass(noise, 1200 if style != "lofi" else 2500)
            out[s:s + L] += noise * env_exp(L, 0.06) * (0.12 if style == "lofi" else 0.2)
        if style == "chill" and k % 4 == 2:  # rimshot
            L = min(int(0.05 * SR), n - s)
            out[s:s + L] += np.sin(2 * np.pi * 1700 * np.arange(L) / SR) * env_exp(L, 0.01) * 0.12
        subdiv = (0, 0.25, 0.5, 0.75) if style == "funk" else (0, 0.5)
        for half in subdiv:
            hs = at((k + half) * beat)
            L = min(int((0.12 if style == "house" and half == 0.5 else 0.05) * SR), n - hs)
            if L > 0:
                noise = rng.standard_normal(L)
                noise = noise - lowpass(noise, 6000)
                lvl = 0.08 if half == 0.5 else 0.04
                out[hs:hs + L] += noise * env_exp(L, 0.04 if style == "house" else 0.015) * lvl

    # --- lofi: plak cızırtısı
    if style == "lofi":
        crackle = (rng.random(n) < 0.0006) * rng.standard_normal(n) * 0.15
        out += crackle + rng.standard_normal(n) * 0.004

    # --- giriş/çıkış, normalize
    out *= np.clip(tt / 0.4, 0, 1) * np.clip((seconds - tt) / 1.5, 0, 1)
    out = np.tanh(out * 1.2)
    out = out / (np.max(np.abs(out)) + 1e-9) * 0.8
    st = np.stack([out, np.roll(out, 90)], axis=1)
    if path:
        with wave.open(path, "wb") as w:
            w.setnchannels(2)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes((st * 32767).astype(np.int16).tobytes())
    return path


if __name__ == "__main__":
    import os
    import sys
    os.makedirs("preview", exist_ok=True)
    for i in range(int(sys.argv[1]) if len(sys.argv) > 1 else 6):
        m = settings(i)
        print(i, m, make_track(14, m["seed"], f"preview/muzik_{i}_{m['style']}.wav", m["bpm"], m["style"]))
