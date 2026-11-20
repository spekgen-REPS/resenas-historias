"""Historias de Instagram con reseñas REALES de Google Maps (screenshot), animadas.

  python -m resenas nuevas    --cliente SSI [--sembrar] [--dry] [--publicar]
  python -m resenas destacada --cliente SSI --capturas <dir> [--salida <dir>]
  python -m resenas singles   --cliente SSI --capturas <dir> [--solo 02_victor ...]
  python -m resenas capturar  --cliente SSI --ids <ids.json> --salida <dir> [--excluir "Nombre"]

nuevas     Abre el perfil público (sin sesión), ve qué reseñas hay y compara contra el
           registro ~/.spekgen/<cod>/resenas/vistas.json. Cada reseña nueva de >= min_estrellas
           y con texto se captura por su ID y se vuelve la historia SINGLE del tema del cliente,
           en <unidad>/04 Content/Social Media/<AAAA-MM>/RESENAS_NUEVAS/. --sembrar sólo marca
           como vistas las que ya existen (primera corrida), sin producir nada.
destacada  Arma los slides MÚLTIPLES de la destacada RESEÑAS con las capturas de una carpeta.
capturar   Captura por ID una lista de reseñas (los IDs se sacan una vez con Chrome con sesión).

--publicar (sólo en `nuevas`) sube la historia a Instagram y Facebook: Gibran lo autorizó el 19-nov-2026 para el
flujo automático de reseñas nuevas (GitHub Actions). Lo demás no publica.
Corre con PYTHONPATH=~/dev/spekgen-tools (spekgen_paths) y PYTHONUTF8=1.
"""
import argparse, datetime, json, os, pathlib, re, sys

from playwright.sync_api import sync_playwright

from . import captura, disenos, sonido_v5, sonido_spk

AQUI = pathlib.Path(__file__).parent
UA = captura.UA


def tema(cod):
    return json.load(open(AQUI / "temas" / f"{cod.lower()}.json", encoding="utf-8"))


def unidad(t):
    import spekgen_paths
    return spekgen_paths.shared_unit(t["unidad"])


def _h(rid):
    """ID de reseña cifrado (sha256): el registro no guarda nombres ni IDs en claro."""
    import hashlib
    return hashlib.sha256(rid.encode()).hexdigest()[:20]


def registro(cod):
    """Registro de reseñas ya vistas. En GitHub Actions vive en RESENAS_ESTADO (se commitea al repo); en local, en ~/.spekgen."""
    base = os.environ.get("RESENAS_ESTADO")
    p = pathlib.Path(base) / f"vistas_{cod.lower()}.json" if base else pathlib.Path(os.path.expanduser(f"~/.spekgen/{cod.lower()}/resenas/vistas.json"))
    p.parent.mkdir(parents=True, exist_ok=True)
    reg = json.load(open(p, encoding="utf-8")) if p.exists() else {"vistas": {}}
    reg["vistas"] = {(k if len(k) == 20 else _h(k)): {kk: vv for kk, vv in v.items() if kk != "nombre"} for k, v in reg["vistas"].items()}
    return p, reg


def navegador(p, alto=1400):
    b = p.chromium.launch(channel="chrome", headless=True)
    ctx = b.new_context(viewport={"width": 420, "height": alto}, device_scale_factor=3, locale="es-419", user_agent=UA)
    return b, ctx.new_page()


def perfil_publico(pg, place_id=None, url=None):
    """Calificación, total y reseñas visibles (id, nombre) del perfil, sin sesión."""
    pg.goto(url or f"https://www.google.com/maps/place/?q=place_id:{place_id}&hl=es-419", wait_until="domcontentloaded")
    pg.wait_for_timeout(4000)
    for t in ("Ignorar", "Ahora no"):
        x = pg.get_by_role("button", name=t)
        if x.count(): x.first.evaluate("e=>e.click()"); pg.wait_for_timeout(500)
    info = pg.evaluate("""()=>{const b=[...document.querySelectorAll('button,span')].map(e=>e.getAttribute('aria-label')||'')
        .find(a=>/^\\d+[\\s\\u00a0](opiniones|opini[oó]n|reseñas|reseña)/.test(a));const r=document.querySelector('div.fontDisplayLarge');
        return {total: b?parseInt(b):null, calificacion: r?r.innerText.trim():null}}""")
    tab = pg.locator('button[role="tab"][aria-label*="pinion"], button[role="tab"][aria-label*="evisiones"]').first
    tab.evaluate("e=>e.click()"); pg.wait_for_timeout(2500)
    info["visibles"] = pg.evaluate("""()=>[...document.querySelectorAll('div.jftiEf')].map(d=>({id:d.getAttribute('data-review-id'),
        nombre:(d.querySelector('.d4r55')||{}).innerText, estrellas:parseInt((d.querySelector('.kvMYJc')||{getAttribute:()=>0}).getAttribute('aria-label'))||null,
        texto:((d.querySelector('.MyEned .wiI7pd')||{}).innerText||'').length}))""")
    return info


def producir(salida, body, dur, pg, t, diseno, n=1, plagas=True):
    """Video mudo → SFX del pack del tema (sin música) → salida.mp4."""
    mudo = salida.with_name(salida.stem + "_mudo.mp4")
    disenos.render(mudo, body, dur, pg)
    prop = t.get("sonido", {}).get("single" if diseno == t["single"] else "multi")
    if prop:   # SPK: propuesta elegida del banco (sonido_spk); SSI: sonido_v5
        sonido_spk.mezclar(mudo, prop, diseno, salida, n)
    else:
        sonido_v5.mezclar(mudo, diseno, salida, n, plagas)
    mudo.unlink(missing_ok=True)
    c = mudo.with_name(mudo.stem + "_cuadro.png")
    if c.exists(): c.replace(salida.with_name(salida.stem + "_cuadro.png"))


def total_txt(info):
    return f"{info.get('calificacion') or '5.0'} en Google · {info.get('total')} opiniones"


def cmd_nuevas(a):
    t = tema(a.cliente); reg_p, reg = registro(a.cliente)
    hoy = datetime.date.today()
    publicados = []
    with sync_playwright() as p:
        b, pg = navegador(p)
        perfiles = t.get("perfiles") or [{"nombre": t["cod"], "url": None, "cid": t["cid"]}]
        visibles = []
        for pf in perfiles:
            i = perfil_publico(pg, t.get("place_id"), pf.get("url"))
            for r in i["visibles"]:
                r["cid"] = pf["cid"]
            visibles += i["visibles"]
            print(f"{t['cod']} · {pf['nombre']}: {i.get('total')} reseñas, {len(i['visibles'])} visibles")
        nuevas = [r for r in visibles if r["id"] and _h(r["id"]) not in reg["vistas"]]
        print(f"{t['cod']}: {len(nuevas)} nueva(s)")
        if a.sembrar:
            for r in visibles:
                reg["vistas"].setdefault(_h(r["id"]), {"visto": str(hoy), "historia": None})
            json.dump(reg, open(reg_p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            print("sembradas:", len(reg["vistas"])); b.close(); return
        salida = os.environ.get("RESENAS_SALIDA")
        carpeta = pathlib.Path(salida) if salida else unidad(t) / "04 Content" / "Social Media" / hoy.strftime("%Y-%m") / "RESENAS_NUEVAS"
        for k, r in enumerate(nuevas, 1):
            entrada = {"visto": str(hoy), "historia": None}
            if (r["estrellas"] or 0) < t.get("min_estrellas", 4) or not r["texto"]:
                print(f"  #{k}: se salta ({r['estrellas']}★ o sin texto)"); reg["vistas"][_h(r["id"])] = entrada; continue
            if a.dry:
                print(f"  #{k}: nueva de {r['estrellas']}★ (en seco, no se produce)"); continue
            carpeta.mkdir(parents=True, exist_ok=True)
            base = f"{t['cod']}_{hoy:%Y%m%d}_{_h(r['id'])[:8]}"
            png = carpeta / f"{base}_captura.png"
            det = captura.capturar(pg, r["id"], r.get("cid") or t["cid"], str(png), r["nombre"])
            servicio = captura.servicio_de(det["atributos"])
            pg2 = pg.context.browser.new_page(viewport={"width": 1080, "height": 1920})
            body, dur = disenos.SINGLES[t["single"]](png.as_uri(), servicio)
            mp4 = carpeta / f"{base}.mp4"
            producir(mp4, body, dur, pg2, t, t["single"], 1, bool(disenos.PLAGAS.search(servicio))); pg2.close()
            entrada["historia"] = mp4.name
            print(f"  #{k}: historia lista ({r['estrellas']}★) → {mp4.name}")
            if a.publicar:
                from . import publicar as pub
                res = pub.publicar(t, [str(mp4)], f"{t['cod'].lower()}/resenas/{hoy:%Y-%m}")
                entrada.update(story_id=res[0]["story_id"], fb_post_id=res[0].get("fb_post_id"))
                publicados.append(res[0])
            reg["vistas"][_h(r["id"])] = entrada
            json.dump(reg, open(reg_p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)   # guarda tras cada una
        b.close()
    if not a.dry:
        json.dump(reg, open(reg_p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(f"### {t['cod']}: {len(nuevas)} reseña(s) nueva(s), {len(publicados)} publicada(s)\n")
            for x in publicados:
                f.write(f"- IG story {x['story_id']} · FB {x.get('fb_post_id')}\n")


def grupos(capturas):
    """3 por slide; 2 si alguna es larga (>180); 4 si todas son cortas (<=45)."""
    res, i = [], 0
    while i < len(capturas):
        n = 3
        if any(c["largo"] > 180 for c in capturas[i:i + 3]): n = 2
        elif len(capturas) - i >= 4 and all(c["largo"] <= 45 for c in capturas[i:i + 4]): n = 4
        res.append(capturas[i:i + n]); i += n
    if len(res) > 1 and len(res[-1]) == 1:   # nunca un slide con una sola
        res[-2].append(res.pop()[0])
    return res


def cmd_destacada(a):
    t = tema(a.cliente)
    cap_dir = pathlib.Path(a.capturas); salida = pathlib.Path(a.salida or cap_dir.parent / "historias")
    caps = json.load(open(cap_dir / "capturas.json", encoding="utf-8"))
    caps.sort(key=lambda c: -c["largo"])  # lo más concreto primero
    with sync_playwright() as p:
        b, pg = navegador(p, 900)
        info = perfil_publico(pg, t["place_id"]); pg.close()
        pg = b.new_page(viewport={"width": 1080, "height": 1920})
        salida.mkdir(parents=True, exist_ok=True)
        for k, g in enumerate(grupos(caps), 1):
            imgs = [(cap_dir / c["archivo"]).as_uri() for c in g]
            body, dur = disenos.MULTIS[t["multi"]](imgs, total_txt(info))
            f = salida / f"{t['cod']}_HL_RESENAS_{k:02d}.mp4"
            producir(f, body, dur, pg, t, t["multi"], len(g)); print("ok", f.name, [c["nombre"] for c in g])
        b.close()


def cmd_singles(a):
    """Una historia single por cada captura (p. ej. para soltar las reseñas viejas de una en una)."""
    t = tema(a.cliente)
    cap_dir = pathlib.Path(a.capturas); salida = pathlib.Path(a.salida or cap_dir.parent / "singles")
    caps = json.load(open(cap_dir / "capturas.json", encoding="utf-8"))
    salida.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome"); pg = b.new_page(viewport={"width": 1080, "height": 1920})
        for c in caps:
            if a.solo and not any(s in c["archivo"] for s in a.solo):
                continue
            body, dur = disenos.SINGLES[t["single"]]((cap_dir / c["archivo"]).as_uri(), c.get("servicio", ""))
            f = salida / f"{t['cod']}_RESENA_{pathlib.Path(c['archivo']).stem}.mp4"
            producir(f, body, dur, pg, t, t["single"], 1, bool(disenos.PLAGAS.search(c.get("servicio", ""))))
            print("ok", f.name, "plagas" if disenos.PLAGAS.search(c.get("servicio", "")) else "palomitas")
        b.close()


def cmd_capturar(a):
    t = tema(a.cliente); d = json.load(open(a.ids, encoding="utf-8")); os.makedirs(a.salida, exist_ok=True)
    out = []
    with sync_playwright() as p:
        b, pg = navegador(p)
        for n, r in enumerate(d["resenas"], 1):
            if r.get("largo_texto", 1) < 1 or r["nombre"] in a.excluir:
                continue
            f = os.path.join(a.salida, f"{n:02d}_{captura.slug(r['nombre'])}.png")
            info = captura.capturar(pg, r["id"], t["cid"], f, r["nombre"])
            out.append({"n": n, "id": r["id"], "nombre": r["nombre"], "estrellas": info["estrellas"],
                        "servicio": captura.servicio_de(info["atributos"]), "largo": len(info["texto"]),
                        "archivo": os.path.basename(f)})
            print("ok", os.path.basename(f))
        b.close()
    json.dump(out, open(os.path.join(a.salida, "capturas.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(prog="python -m resenas")
    sp = ap.add_subparsers(dest="cmd", required=True)
    n = sp.add_parser("nuevas"); n.add_argument("--cliente", required=True); n.add_argument("--sembrar", action="store_true"); n.add_argument("--dry", action="store_true"); n.add_argument("--publicar", action="store_true")
    d = sp.add_parser("destacada"); d.add_argument("--cliente", required=True); d.add_argument("--capturas", required=True); d.add_argument("--salida")
    s = sp.add_parser("singles"); s.add_argument("--cliente", required=True); s.add_argument("--capturas", required=True); s.add_argument("--salida"); s.add_argument("--solo", nargs="*")
    c = sp.add_parser("capturar"); c.add_argument("--cliente", required=True); c.add_argument("--ids", required=True); c.add_argument("--salida", required=True); c.add_argument("--excluir", action="append", default=[])
    a = ap.parse_args()
    {"nuevas": cmd_nuevas, "destacada": cmd_destacada, "singles": cmd_singles, "capturar": cmd_capturar}[a.cmd](a)
