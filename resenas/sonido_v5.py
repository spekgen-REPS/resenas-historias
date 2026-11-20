"""Sonido v5 (19-nov-2026): banco de earshot (Leonxlnx/earshot 0.4.1, MIT, revisado) + patitas sintetizadas.

Cada sonido corresponde a algo que se mueve en el video de 5 s (disenos.*_v5); cuadro quieto = silencio.
  SPK single : swish al entrar el título · pop cuando aterriza la reseña · whoosh corto al salir ·
               glockenspiel en «¡Gracias…!» y celesta cuando aparece el logo.
  SPK múltiple: swish · un pop por tarjeta que aterriza · un flick por tarjeta que sale · celesta en el logo.
  SSI single : swish · golpe de madera al caer la reseña · patitas de cucaracha mientras huyen ·
               whoosh al salir · marimba en «Gracias…» y marimba grave en el logo (madera, no campana: no repite SPK).
  SSI múltiple: swish · golpe de madera por tarjeta · flick al salir · marimba en el logo.

Las tomas se rinden una vez con earshot (`earshot sfx render <id> -o <wav> [--pitch X]`) en TOMAS.
"""
import pathlib, subprocess, wave

import imageio_ffmpeg
import numpy as np

from .patitas import SR, patitas

TOMAS = pathlib.Path(__file__).parent / "sfx"   # tomas del banco de earshot (MIT), copiadas al repo
# id del banco → (archivo, segundo del pico dentro de la toma, según earshot)
T = {
    "glock": ("mallet_glock_B5.wav", 0.004), "celesta": ("mallet_celesta_E5.wav", 0.021),
    "marimba": ("mallet_marimba_G4.wav", 0.006), "marimba_grave": ("mallet_marimba_C4.wav", 0.009),
    "pop_soft": ("ui_pop_soft.wav", 0.042), "pop_wide": ("ui_pop_wide.wav", 0.044), "pop_step": ("ui_pop_step.wav", 0.044),
    "madera": ("knock_wood.wav", 0.015), "escritorio": ("knock_desk.wav", 0.025),
    "swish": ("swish_soft.wav", 0.110), "flick": ("swish_flick.wav", 0.111),
    "whoosh": ("whoosh_fast_tight.wav", 0.162), "tine": ("notify_mid_wood.wav", 0.038),
}
_CACHE = {}


def toma(clave):
    if clave not in _CACHE:
        f, pico = T[clave]
        r = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-v", "error", "-i", str(TOMAS / f), "-f", "f32le",
                            "-ac", "1", "-ar", str(SR), "-"], capture_output=True, check=True)
        _CACHE[clave] = (np.frombuffer(r.stdout, dtype=np.float32).copy(), pico)
    return _CACHE[clave]


def _pon(pista, x, t, db, pan=0.5):
    x = x / (np.abs(x).max() or 1) * 10 ** (db / 20)
    if x.ndim == 1:
        x = np.stack([x * (1 - pan) * 1.4, x * pan * 1.4], axis=1)
    i = max(0, int(t * SR)); j = min(len(pista), i + len(x))
    pista[i:j] += x[:j - i]


def evento(pista, clave, t_pico, db, pan=0.5):
    """Coloca la toma de modo que su PICO caiga en t_pico (el cuadro donde pasa la acción)."""
    x, pico = toma(clave)
    _pon(pista, x, t_pico - pico, db, pan)


def pista(diseno, dur=5.0, n=1, plagas=True):
    p = np.zeros((int(dur * SR), 2))
    if diseno == "spk_s1":
        evento(p, "swish", 0.35, -25)                  # título entra (0-0.8)
        evento(p, "pop_soft", 0.80, -15)               # la reseña aterriza
        evento(p, "whoosh", 3.10, -23)                 # todo sale hacia arriba (2.9-3.45)
        evento(p, "glock", 3.52, -18)                  # «¡Gracias por tu reseña!»
        evento(p, "celesta", 4.12, -21)                # logo
    elif diseno == "spk_m2":
        evento(p, "swish", 0.35, -25)
        pops = ["pop_wide", "pop_step", "pop_soft", "pop_wide"]
        for k in range(n):
            evento(p, pops[k], 0.3 + .25 * k + .45, -16 - k, pan=0.4 + .1 * k)   # cada tarjeta aterriza
            evento(p, "flick", 3.35 + .1 * k + .2, -25, pan=0.7 if k % 2 == 0 else 0.3)  # y sale
        evento(p, "celesta", 4.05, -19)                # logo
    elif diseno == "ssi_a":
        evento(p, "swish", 0.30, -26)
        evento(p, "escritorio", 0.72, -15)             # la reseña cae como en una mesa de trabajo
        if plagas:
            _pon(p, patitas(2.1, 7, bichos=4), 0.85, -20)   # las cucarachas corren mientras están en cuadro
        else:
            for k in range(4):
                evento(p, "tine", 0.95 + .1 * k, -26 - k, pan=0.3 + .15 * k)
        evento(p, "whoosh", 3.10, -24)
        evento(p, "marimba", 3.52, -18)                # «Gracias por tu confianza»
        evento(p, "marimba_grave", 4.12, -21)          # logo
    elif diseno == "ssi_m2b":
        evento(p, "swish", 0.35, -26)
        for k in range(n):
            evento(p, "madera", 0.3 + .25 * k + .45, -15 - k, pan=0.4 + .1 * k)
            evento(p, "flick", 3.35 + .1 * k + .2, -25, pan=0.7 if k % 2 == 0 else 0.3)
        evento(p, "marimba", 4.05, -19)
    return p


def mezclar(mp4_mudo, diseno, salida, n=1, plagas=True, dur=5.0, ganancia_db=12):
    """ganancia_db=12 deja la historia cerca de -24 LUFS (medido con earshot el 19-nov; sin ella quedaba en -36)."""
    x = np.clip(pista(diseno, dur, n, plagas) * 10 ** (ganancia_db / 20), -0.89, 0.89)
    wav = pathlib.Path(salida).with_suffix(".wav")
    with wave.open(str(wav), "w") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-i", str(mp4_mudo), "-i", str(wav),
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest",
                    "-movflags", "+faststart", str(salida)], check=True)
    wav.unlink()
