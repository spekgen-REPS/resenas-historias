# Reseñas → historias

Cada 30 minutos, GitHub Actions revisa los perfiles públicos de Google Maps de la marca. Cada reseña **nueva** de 4–5★ con texto se captura tal como se ve en Google (screenshot real, sin el precio ni el servicio que Google pone debajo), se monta en una historia animada de 5 s con su sonido y se publica en Instagram y Facebook por la API de Meta.

- `resenas/temas/<cod>.json`: perfiles, cuentas y diseño de cada marca. Ninguna marca repite el template de otra.
- `resenas/disenos.py`: animaciones (HTML/CSS cuadro a cuadro con Playwright + ffmpeg).
- `resenas/sonido_v5.py`, `resenas/sonido_spk.py`: sonido amarrado a lo que se mueve; tomas del banco de [earshot](https://github.com/Leonxlnx/earshot) (MIT) en `resenas/sfx/`.
- `estado/vistas_<cod>.json`: IDs **cifrados** (sha256) de las reseñas ya vistas. Sin nombres.
- Secretos (Settings → Secrets): `META_TOKEN`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`.

Correr a mano: Actions → «Reseñas nuevas → historias» → Run workflow (con «seco» sólo revisa).
