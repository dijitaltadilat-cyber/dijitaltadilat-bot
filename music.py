"""Özgün, telifsiz fon müziği üretici (tamamen kodla sentezlenir).

make_track(seconds, seed, path) -> wav dosyası
Her seed farklı ton / akor dizisi / ritim varyasyonu üretir; tempo sabit (BPM),
böylece Reels'teki yazılar vuruşlara denk getirilebilir.
"""
import wave

import numpy as np

SR = 44100
BPM = 112
BEAT = 60 / BPM

# Akor dizileri (yarım ton, kök notaya göre): pop / lo-fi ilerlemeleri
PROGRESSIONS = [
    [[0, 3, 7], [-4, 0, 3], [3, 7, 10], [-2, 2, 5]],     # i - VI - III - VII
    [[0, 4, 7], [-3, 0, 4], [-7, -3, 0], [-5, -1, 2]],   # I - vi - IV - V
    [[0, 4, 7, 11], [5, 9, 12, 16], [2, 5, 9, 12], [7, 11, 14, 17]],  # Imaj7 - IVmaj7 - ii7 - V
    [[0, 3, 7, 10], [5, 8, 12, 15], [-2, 2, 5, 9], [3, 7, 10, 14]],   # i7 - iv7 - VII - IIImaj7
]
ROOTS = [57, 55, 60, 53, 58]  # A3, G3, C4, F3, A#3 (MIDI)


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
    t = np.arange(n) / SR
    return np.exp(-t / decay)


def make_track(seconds, seed=0, path=None):
    rng = np.random.default_rng(seed)
    prog = PROGRESSIONS[seed % len(PROGRESSIONS)]
    root = ROOTS[seed % len(ROOTS)]
    n = int(seconds * SR)
    out = np.zeros(n)
    bar = 4 * BEAT
    nbars = int(np.ceil(seconds / bar)) + 1

    # --- akor pad (yumuşak, filtreli) + vuruşa göre "pompalama"
    pad = np.zeros(n)
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
                seg += np.sin(2 * np.pi * f * (1 + det) * t) + 0.3 * np.sin(4 * np.pi * f * (1 + det) * t)
        a = np.clip(t / 0.25, 0, 1) * np.clip((e - s) / SR - t, 0, 0.3) / 0.3
        pad[s:e] += seg * a
    pump = 0.55 + 0.45 * np.clip(((np.arange(n) / SR) % BEAT) / (BEAT * 0.6), 0, 1)
    out += pad / (np.max(np.abs(pad)) + 1e-9) * 0.22 * pump

    # --- arpej (pluck)
    step = BEAT / 2
    pattern = [0, 1, 2, 1, 0, 2, 1, 2] if seed % 2 else [0, 2, 1, 2, 0, 1, 2, 1]
    for k in range(int(seconds / step) + 1):
        b = int(k * step / bar)
        ch = prog[b % len(prog)]
        note = root + 12 + ch[pattern[k % 8] % len(ch)]
        s = int(k * step * SR)
        L = min(int(0.35 * SR), n - s)
        if L <= 0:
            break
        t = np.arange(L) / SR
        f = hz(note)
        tone = (np.sin(2 * np.pi * f * t) + 0.4 * np.sin(4 * np.pi * f * t)
                + 0.15 * np.sin(6 * np.pi * f * t)) * env_exp(L, 0.12)
        out[s:s + L] += tone * 0.10

    # --- bas
    for b in range(nbars):
        ch = prog[b % len(prog)]
        for beat_i in (0, 2.5, 3) if seed % 3 else (0, 1.5, 2, 3.5):
            s = int((b * bar + beat_i * BEAT) * SR)
            L = min(int(BEAT * 0.9 * SR), n - s)
            if s >= n or L <= 0:
                continue
            t = np.arange(L) / SR
            f = hz(root - 24 + ch[0])
            tone = np.sin(2 * np.pi * f * t) + 0.25 * np.sin(4 * np.pi * f * t)
            out[s:s + L] += tone * env_exp(L, 0.28) * np.clip(t / 0.01, 0, 1) * 0.30

    # --- davul: kick 1-3, snare 2-4, hi-hat sekizlik
    for k in range(int(seconds / BEAT) + 1):
        s = int(k * BEAT * SR)
        if s >= n:
            break
        if k % 2 == 0 or (seed % 2 and k % 4 == 3):
            L = min(int(0.30 * SR), n - s)
            t = np.arange(L) / SR
            f = 50 + 90 * np.exp(-t / 0.03)
            out[s:s + L] += np.sin(2 * np.pi * np.cumsum(f) / SR) * env_exp(L, 0.12) * 0.55
        if k % 2 == 1:
            L = min(int(0.22 * SR), n - s)
            noise = rng.standard_normal(L)
            noise = noise - lowpass(noise, 1200)
            out[s:s + L] += noise * env_exp(L, 0.06) * 0.20
        for half in (0, 0.5):
            hs = int((k + half) * BEAT * SR)
            L = min(int(0.05 * SR), n - hs)
            if L > 0:
                noise = rng.standard_normal(L)
                noise = noise - lowpass(noise, 6000)
                out[hs:hs + L] += noise * env_exp(L, 0.015) * (0.07 if half else 0.05)

    # --- giriş/çıkış, normalize
    t = np.arange(n) / SR
    out *= np.clip(t / 0.4, 0, 1) * np.clip((seconds - t) / 1.5, 0, 1)
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
    import sys
    for s in range(int(sys.argv[1]) if len(sys.argv) > 1 else 4):
        print(make_track(16, s, f"preview/muzik_{s}.wav"))
