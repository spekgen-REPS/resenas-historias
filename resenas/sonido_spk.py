"""Propuestas de sonido de SPK (19-nov-2026). SSI ya quedó aprobado con sonido_v5 (maderas, marimba, patitas).
Ninguna toma de SSI se repite aquí. Banco: earshot 0.4.1 (tomas en ~/dev/_tools/earshot_takes/spk_*.wav).

  A «like»     burbuja de «me gusta» al caer la reseña · ding de notificación en «gracias» · brillo suave en el logo
  B «tech»     zip al entrar · tick digital al cargar cada tarjeta · zip de salida · sting tecnológico en el logo
  C «cristal»  swell que se resuelve en la reseña · toque de vidrio · barrido tonal al salir · shimmer en «gracias»
  D «kalimba»  roce de tela al entrar · notas de kalimba que suben con cada tarjeta · chispa en el logo
"""
import json, pathlib, re, subprocess, wave

import imageio_ffmpeg
import numpy as np

from .patitas import SR

TOMAS = pathlib.Path(__file__).parent / "sfx"   # tomas del banco de earshot (MIT), copiadas al repo
_IDX = json.load(open(TOMAS / "spk_tomas.json", encoding="utf-8"))
_C = {}


def _toma(k):
    if k not in _C:
        f, pico = _IDX[k]
        r = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-v", "error", "-i", str(TOMAS / f), "-f", "f32le", "-ac", "1",
                            "-ar", str(SR), "-"], capture_output=True, check=True)
        _C[k] = (np.frombuffer(r.stdout, dtype=np.float32).copy(), pico or 0.0)
    return _C[k]


def _ev(p, k, t_pico, db, pan=0.5, largo=None):
    x, pico = _toma(k)
    if largo:
        x = x[:int(largo * SR)].copy(); f = int(0.15 * SR); x[-f:] *= np.linspace(1, 0, f)
    x = x / (np.abs(x).max() or 1) * 10 ** (db / 20)
    st = np.stack([x * (1 - pan) * 1.4, x * pan * 1.4], axis=1)
    i = max(0, int((t_pico - pico) * SR)); j = min(len(p), i + len(st))
    p[i:j] += st[:j - i]


def pista(propuesta, diseno, n=1, dur=5.0):
    p = np.zeros((int(dur * SR), 2))
    single = diseno == "spk_s1"
    llegadas = [0.80] if single else [0.75 + .25 * k for k in range(n)]
    salidas = [3.10] if single else [3.55 + .1 * k for k in range(n)]
    gracias, logo = (3.52, 4.12) if single else (None, 4.05)
    if propuesta == "A":
        _ev(p, "glide", 0.35, -27)
        for k, t in enumerate(llegadas):
            _ev(p, ["popin_round", "popin_airy", "popin_double", "popin_round"][k], t, -15 - k, 0.4 + .1 * k)
        for k, t in enumerate(salidas):
            _ev(p, "velvet", t, -27, 0.7 if k % 2 == 0 else 0.3)
        if gracias: _ev(p, "ding", gracias, -19)
        _ev(p, "bloom", logo + 0.25, -24, largo=0.85)
    elif propuesta == "B":
        _ev(p, "zip_up", 0.35, -24)
        for k, t in enumerate(llegadas):
            _ev(p, "glitch_mid", t, -22 - k, 0.4 + .1 * k); _ev(p, "ping", t + 0.02, -21, 0.5)
        for k, t in enumerate(salidas):
            _ev(p, "zip_down", t, -24, 0.7 if k % 2 == 0 else 0.3)
        if gracias: _ev(p, "taps_tone", gracias + 0.1, -20)
        _ev(p, "zap_bloom", logo + 0.1, -21, largo=0.85)
    elif propuesta == "C":
        _ev(p, "rev_short", llegadas[0], -27)
        for k, t in enumerate(llegadas):
            _ev(p, "tap_glass" if k % 2 == 0 else "ptap_glass", t, -17 - k, 0.4 + .1 * k)
        for k, t in enumerate(salidas[:1] if single else salidas[:1]):
            _ev(p, "tonal", t + 0.05, -25)
        if gracias: _ev(p, "shimmer3", gracias + 0.05, -23, largo=1.0)
        _ev(p, "whoosh_glass", logo + 0.2, -25, largo=0.8)
    elif propuesta == "D":
        _ev(p, "cloth", 0.35, -26)
        notas = ["kal_C5", "kal_E5", "kal_G5", "kal_C6"]
        for k, t in enumerate(llegadas):
            _ev(p, notas[k] if not single else "kal_E5", t, -17 - k, 0.4 + .1 * k, largo=1.2)
        for k, t in enumerate(salidas):
            _ev(p, "cloth", t, -27, 0.7 if k % 2 == 0 else 0.3)
        if gracias: _ev(p, "kal_G5", gracias, -18, largo=1.0); _ev(p, "kal_C6", gracias + 0.18, -21, largo=0.9)
        _ev(p, "spark", logo + 0.05, -22, largo=0.8)
    fo = int(0.25 * SR); p[-fo:] *= np.linspace(1, 0, fo)[:, None]
    return p


def mezclar(mp4_mudo, propuesta, diseno, salida, n=1, lufs=-24.0):
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    x = pista(propuesta, diseno, n)
    wav = pathlib.Path(salida).with_suffix(".wav")

    def escribe(y):
        with wave.open(str(wav), "w") as w:
            w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
            w.writeframes((np.clip(y, -0.89, 0.89) * 32767).astype(np.int16).tobytes())
    escribe(x)
    r = subprocess.run([ff, "-hide_banner", "-i", str(wav), "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True, errors="ignore")
    medido = float(re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)[-1])
    escribe(x * 10 ** ((lufs - medido) / 20))          # todas las propuestas al mismo volumen
    subprocess.run([ff, "-y", "-loglevel", "error", "-i", str(mp4_mudo), "-i", str(wav), "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(salida)], check=True)
    wav.unlink()
