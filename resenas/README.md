# resenas — historias de IG con reseñas reales de Google Maps

Toma el **screenshot real** de cada reseña de Google Maps (sin sesión, en alta resolución) y lo monta en una historia **animada** (MP4 1080×1920) con el tema de cada cliente. La reseña nunca se reescribe: lo que se ve es la captura de Google, sin el precio pagado ni el tipo de servicio que Google pone debajo.

Dos formatos por cliente, definidos en `temas/<cod>.json`:

| Formato | Para qué | SPK | SSI |
|---|---|---|---|
| **single** | una reseña nueva → una historia (evento suelto, orgánico) | `spk_s1` «Customer Review» (fondo que respira, anillos, corazones) | `ssi_a` «Plagas fuera» (cucarachas si la reseña es de plagas; palomitas si no) |
| **múltiple** | slides de la destacada RESEÑAS (2–4 reseñas por slide) | `spk_m2` «Cuadrícula» | `ssi_m2b` «Plano técnico» |

Regla de Gibran (18-nov-2026): **ningún cliente repite el template de otro**. Variaciones sí; idénticos no. Un cliente nuevo = un tema nuevo con sus propias funciones en `disenos.py`.

## Uso

```bash
export PYTHONPATH="$HOME/dev/spekgen-tools" PYTHONUTF8=1   # spekgen_paths para las rutas del Drive
python -m resenas nuevas --cliente SSI --dry     # ¿hay reseñas nuevas? (no produce nada)
python -m resenas nuevas --cliente SSI           # produce la historia single de cada nueva (>= 4★ y con texto)
python -m resenas destacada --cliente SSI --capturas "<unidad>/04 Content/Social Media/2026-11/SSI-088_DESTACADA-RESENAS/capturas"
python -m resenas capturar --cliente SPK --ids ~/.spekgen/spk/resenas/ids_2026-11-18.json --salida <carpeta> --excluir "Nombre"
```

- `nuevas` compara contra `~/.spekgen/<cod>/resenas/vistas.json` (nombres de clientes finales: **no** van al repo). La historia sale en `<unidad>/04 Content/Social Media/<AAAA-MM>/RESENAS_NUEVAS/`.
- **Nada se publica aquí.** Publicar en Instagram lleva el OK de Gibran pieza por pieza.

## Cómo funciona por dentro

- **Captura por ID** (`captura.py`): `https://www.google.com/maps/reviews/data=!4m8!14m7!1m6!2m5!1s<ID>!2m1!1s0x0:<CID>!3m1!1s2@1:CAIQACoMCAAS` abre una reseña sin sesión. Ahí el nombre vive fuera de la tarjeta, así que se recortan cabecera y cuerpo por separado y se unen (píxeles reales).
- **Detección sin sesión**: el perfil público enseña sólo 5 reseñas («más relevantes») y no deja ordenar por recientes; las nuevas con texto suelen salir ahí con la marca «NUEVA». Los IDs de todas las reseñas viejas se sacan **una vez** con Chrome con sesión. La búsqueda de Google sin sesión pide CAPTCHA: no se usa.
- **Adorno según servicio**: Google pone en la reseña los atributos «Servicios» y «Tipo de plaga»; `servicio_de()` los lee y `disenos.ssi_a` elige cucarachas o palomitas.
- **Video**: animaciones CSS pausadas y puestas en cada tiempo t, un screenshot por cuadro (30 fps) y ffmpeg de `imageio-ffmpeg`. Costo $0, sin IA. Requiere `playwright` y Chrome instalado (`channel="chrome"`).

## Pendiente

- Disparador automático (correo de «nueva reseña» o cron) y a dónde llega la historia para el OK de Gibran: ver la task de ClickUp `1dfkggwm4hn`.
