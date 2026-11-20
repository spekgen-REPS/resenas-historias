"""Correteo de cucarachas sintetizado (SSI) y la frecuencia de muestreo común. Código propio, sin dependencias
más allá de numpy. El filtro es el mismo pasa-banda por FFT del kit de SPEKGEN (sintetizar_sfx.py)."""
import numpy as np

SR = 48_000


def _bandpass(x, lo, hi):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X[(f < lo) | (f > hi)] = 0
    return np.fft.irfft(X, n=len(x))


def patitas(dur, seed, bichos=3):
    """Ráfagas de clics finos (2-7 kHz) a paso irregular, varios bichos paneados, que se apagan al salir de cuadro.
    earshot la lee como «small insects scurrying» (strong, z +3.1) cuando suena sola. Devuelve estéreo (n, 2)."""
    n = int(dur * SR)
    rng = np.random.default_rng(seed)
    st = np.zeros((n, 2))
    clic_n = int(0.0025 * SR)
    clic_env = np.exp(-np.linspace(0, 6, clic_n))
    for b in range(bichos):
        pan = rng.uniform(0.15, 0.85)
        t = rng.uniform(0, 0.12)
        while t < dur - 0.01:
            i = int(t * SR)
            ruido = _bandpass(rng.standard_normal(clic_n * 4), 2000, 7000)[:clic_n] * clic_env
            amp = rng.uniform(0.35, 1.0) * (0.55 + 0.45 * np.sin(2 * np.pi * 9 * t + b) ** 2)
            st[i:i + clic_n, 0] += ruido * amp * (1 - pan)
            st[i:i + clic_n, 1] += ruido * amp * pan
            t += rng.uniform(0.014, 0.034)
    env = np.ones(n)
    a, r = int(0.12 * SR), int(dur * 0.55 * SR)
    env[:a] = np.linspace(0, 1, a); env[-r:] = np.linspace(1, 0, r) ** 1.6
    return st * env[:, None]
