"""Captura real de una reseña de Google Maps por su ID, sin sesión.

La imagen lleva sólo cabecera (avatar + nombre) y estrellas + texto, recortados de la
página de Google y unidos; nunca el precio pagado ni el tipo de servicio, que Google
pone debajo. Los atributos sí se leen (servicio_de) para escoger el adorno.
"""
import argparse, json, os, re, unicodedata
from playwright.sync_api import sync_playwright

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"


def slug(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()[:40]


def url_resena(rid, cid):
    return f"https://www.google.com/maps/reviews/data=!4m8!14m7!1m6!2m5!1s{rid}!2m1!1s0x0:{cid}!3m1!1s2@1:CAIQACoMCAAS?hl=es-419"


def capturar(pg, rid, cid, salida, nombre=""):
    pg.goto(url_resena(rid, cid), wait_until="domcontentloaded")
    pg.wait_for_selector("div.jftiEf", timeout=20000); pg.wait_for_timeout(1200)
    for t in ("Ignorar", "Ahora no"):
        x = pg.get_by_role("button", name=t)
        if x.count(): x.first.evaluate("e=>e.click()"); pg.wait_for_timeout(500)
    card = pg.locator("div.jftiEf").first
    mas = card.locator("button.w8nwRe")
    if mas.count(): mas.first.evaluate("e=>e.click()"); pg.wait_for_timeout(400)
    # ocultar tooltips y la tarjeta del lugar que no son parte de la reseña
    pg.add_style_tag(content="[role=tooltip],.ITvuef{display:none!important}")
    info = card.evaluate("""c=>{const t=c.querySelector('.MyEned .wiI7pd');const at=c.querySelector('.MyEned');
      const est=c.querySelector('[role=img][aria-label*=estrella], .kvMYJc');
      return {texto:t?t.innerText:'', atributos:at?at.innerText.replace(t?t.innerText:'','').trim():'',
              estrellas:est?parseInt(est.getAttribute('aria-label')):null}}""")
    from PIL import Image
    import io
    bx = card.bounding_box()
    # cabecera: avatar + nombre (en la vista por ID vive fuera de la tarjeta)
    nm = pg.get_by_text(nombre, exact=True).first if nombre else pg.locator("button.P9Vtnb").first   # sin nombre: el botón del autor
    nb = nm.bounding_box()
    cab = pg.screenshot(clip={"x": bx["x"], "y": nb["y"] - 20, "width": bx["width"], "height": nb["height"] + 46})
    # cuerpo: estrellas + texto
    est = card.locator("[role=img][aria-label*=estrella], .kvMYJc").first.bounding_box()
    fin = card.locator(".MyEned .wiI7pd").first
    fb = fin.bounding_box() if fin.count() else est
    fotos = card.locator(".KtCyie").first          # fotos que dejó el cliente (se muestran completas)
    if fotos.count():
        fotos.scroll_into_view_if_needed(); pg.wait_for_timeout(1500)   # las miniaturas cargan perezosas
        bx = card.bounding_box(); est = card.locator("[role=img][aria-label*=estrella], .kvMYJc").first.bounding_box()
        fb = fotos.bounding_box()
    info["fotos"] = card.locator(".KtCyie button").count()
    cue = pg.screenshot(clip={"x": bx["x"], "y": est["y"] - 12, "width": bx["width"], "height": fb["y"] + fb["height"] - est["y"] + 34})
    a, b = Image.open(io.BytesIO(cab)), Image.open(io.BytesIO(cue))
    lienzo = Image.new("RGB", (a.width, a.height + b.height), "white")
    lienzo.paste(a, (0, 0)); lienzo.paste(b, (0, a.height)); lienzo.save(salida)
    return info


def servicio_de(atributos):
    m = re.search(r"Servicios\s*\n(.+)", atributos or "")
    p = re.search(r"Tipo de plaga\s*\n(.+)", atributos or "")
    return ((m.group(1) if m else "") + (" · " + p.group(1) if p else "")).strip(" ·")


