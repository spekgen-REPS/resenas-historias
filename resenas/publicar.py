"""Publica historias (MP4) en Instagram por la API de Meta (media_type=STORIES).

El video se sube al bucket público `post-media` de Supabase (el mismo flujo de las historias de FV y de
SPK-013 HSS) y de ahí Meta lo toma. Las destacadas NO se crean por API: Gibran las arma desde el celular.

    python -m resenas.publicar --cliente SPK <mp4> [<mp4> ...]            # en seco
    python -m resenas.publicar --cliente SPK <mp4> [<mp4> ...] --ejecutar

Publicar es contenido público: sólo con el OK de Gibran (o el flujo automático que él aprobó).
"""
import argparse, json, os, pathlib, re, sys, time, urllib.error, urllib.parse, urllib.request

G = "https://graph.facebook.com/v21.0"
AQUI = pathlib.Path(__file__).parent


def _env(p):
    d = {}
    for l in pathlib.Path(p).read_text(encoding="utf-8").splitlines():
        m = re.match(r"\s*([A-Z0-9_]+)\s*=\s*(.*)\s*$", l)
        if m:
            d[m.group(1)] = m.group(2).strip().strip("\"'")
    return d


def credenciales(t):
    """Token de Meta y Supabase: de variables de entorno (GitHub Actions) o de los .env locales."""
    # token de usuario de sistema «SPEKGEN Agency API» (no expira; instagram_content_publish + pages_manage_posts)
    tok = os.environ.get("META_TOKEN")
    if not tok:
        import spekgen_paths
        tok = _env(spekgen_paths.shared_unit("SPK — AGENCY") / ".env")["META_TOKEN"]
    sb_url, sb_key = os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not sb_url:
        import spekgen_paths
        e = _env(spekgen_paths.client_dir("SPK") / "_CONTENT_HUB_SHOPIFY" / ".env")
        sb_url, sb_key = e["NEXT_PUBLIC_SUPABASE_URL"], e["SUPABASE_SERVICE_ROLE_KEY"]
    return tok, sb_url.rstrip("/"), sb_key


def subir(f, carpeta, sb_url, sb_key):
    nombre = re.sub(r"[^A-Za-z0-9_.-]", "-", pathlib.Path(f).name)
    path = f"{carpeta}/{nombre}"
    req = urllib.request.Request(f"{sb_url}/storage/v1/object/post-media/{path}", data=pathlib.Path(f).read_bytes(), method="POST",
                                 headers={"Authorization": f"Bearer {sb_key}", "Content-Type": "video/mp4", "x-upsert": "true"})
    urllib.request.urlopen(req, timeout=300).read()
    return f"{sb_url}/storage/v1/object/public/post-media/{path}"


def api(tok, method, path, params):
    params = dict(params, access_token=tok)
    try:
        if method == "GET":
            return json.load(urllib.request.urlopen(f"{G}/{path}?{urllib.parse.urlencode(params)}", timeout=120))
        req = urllib.request.Request(f"{G}/{path}", data=urllib.parse.urlencode(params).encode(), method="POST")
        return json.load(urllib.request.urlopen(req, timeout=180))
    except urllib.error.HTTPError as e:
        return {"error": json.load(e).get("error", {})}


def historia_facebook(tok, page_id, url):
    """Historia de video en la página de Facebook: start → subir por URL → finish."""
    ptok = api(tok, "GET", page_id, {"fields": "access_token"}).get("access_token")
    if not ptok:
        raise RuntimeError("sin token de página")
    st = api(ptok, "POST", f"{page_id}/video_stories", {"upload_phase": "start"})
    if "video_id" not in st:
        raise RuntimeError(f"fb start: {st}")
    req = urllib.request.Request(st["upload_url"], method="POST", data=b"",
                                 headers={"Authorization": f"OAuth {ptok}", "file_url": url})
    up = json.load(urllib.request.urlopen(req, timeout=300))
    if not up.get("success"):
        raise RuntimeError(f"fb upload: {up}")
    for _ in range(40):
        fin = api(ptok, "POST", f"{page_id}/video_stories", {"upload_phase": "finish", "video_id": st["video_id"]})
        if fin.get("post_id"):
            return fin["post_id"]
        time.sleep(5)
    raise RuntimeError(f"fb finish: {fin}")


def publicar(t, archivos, carpeta):
    tok, sb_url, sb_key = credenciales(t)
    res = []
    for f in archivos:
        url = subir(f, carpeta, sb_url, sb_key)
        c = api(tok, "POST", f"{t['ig_id']}/media", {"media_type": "STORIES", "video_url": url})
        if "id" not in c:
            raise RuntimeError(f"contenedor {pathlib.Path(f).name}: {c}")
        for _ in range(60):
            st = api(tok, "GET", c["id"], {"fields": "status_code"}).get("status_code")
            if st == "FINISHED":
                break
            if st == "ERROR":
                raise RuntimeError(f"procesamiento {pathlib.Path(f).name}")
            time.sleep(5)
        p = api(tok, "POST", f"{t['ig_id']}/media_publish", {"creation_id": c["id"]})
        if "id" not in p:
            raise RuntimeError(f"publicar {pathlib.Path(f).name}: {p}")
        print(f"  instagram {pathlib.Path(f).name} → story {p['id']}")
        fb = None
        if t.get("fb_page_id"):
            try:
                fb = historia_facebook(tok, t["fb_page_id"], url)
                print(f"  facebook  {pathlib.Path(f).name} → {fb}")
            except Exception as e:   # FB no frena la publicación de IG
                print(f"  facebook  {pathlib.Path(f).name} FALLÓ: {e}")
        res.append({"archivo": pathlib.Path(f).name, "story_id": p["id"], "fb_post_id": fb, "url": url,
                    "fecha": time.strftime("%Y-%m-%d %H:%M")})
        time.sleep(3)
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--cliente", required=True); ap.add_argument("archivos", nargs="+")
    ap.add_argument("--carpeta", default=None, help="carpeta en post-media (default <cod>/resenas)")
    ap.add_argument("--ejecutar", action="store_true")
    a = ap.parse_args()
    t = json.load(open(AQUI / "temas" / f"{a.cliente.lower()}.json", encoding="utf-8"))
    print(f"{len(a.archivos)} historia(s) para @{t['ig_usuario']}: " + ", ".join(pathlib.Path(x).name for x in a.archivos))
    if not a.ejecutar:
        print("(en seco: no se subió ni publicó nada)"); sys.exit(0)
    r = publicar(t, a.archivos, a.carpeta or f"{t['cod'].lower()}/resenas")
    out = pathlib.Path(a.archivos[0]).parent / "_historias_publicadas.json"
    prev = json.loads(out.read_text(encoding="utf-8")) if out.exists() else []
    out.write_text(json.dumps(prev + r, ensure_ascii=False, indent=1), encoding="utf-8")
    print("listo →", out)
