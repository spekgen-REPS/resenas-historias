"""Diseños de historia de reseña ANIMADOS (MP4 1080x1920) sobre el screenshot real de Google Maps.

Cada diseño es una función que recibe URIs de capturas y devuelve (html_body, duración).
Para cada cuadro se pausan las animaciones CSS, se ponen en el tiempo t y se toma
screenshot; ffmpeg (de imageio-ffmpeg) arma el MP4. Ningún texto de la reseña se
reescribe: la reseña es siempre la captura de Google.

Cada cliente tiene su tema (temas/<cod>.json) con su single y su múltiple, para que
ningún cliente repita el template de otro.
"""
import pathlib, subprocess, sys, imageio_ffmpeg
from playwright.sync_api import sync_playwright

AQUI = pathlib.Path(__file__).parent.resolve()
u = lambda p: (AQUI / p).as_uri()
FPS = 30

HEAD = """<!doctype html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Archivo+Black&family=Poppins:wght@500;600;800&family=Caveat:wght@700&family=Oswald:wght@600;700&display=block" rel="stylesheet">
<style>*{box-sizing:border-box;margin:0}html,body{width:1080px;height:1920px;overflow:hidden}
body{position:relative;font-family:Poppins,sans-serif}.abs{position:absolute}
.card{border-radius:30px;overflow:hidden;background:#fff;box-shadow:0 30px 60px rgba(0,0,0,.28),0 6px 14px rgba(0,0,0,.12)}
.card img{display:block;width:100%}
.stack{position:absolute;left:0;right:0;display:flex;flex-direction:column;align-items:center;justify-content:center}
%CSS%</style></head><body>%BODY%
<script>function fit(){document.querySelectorAll('.fitme').forEach(st=>{const max=+st.dataset.max;let w=+st.dataset.w;const cs=[...st.children];
const cs2=cs.filter(c=>c.querySelector('.card')||c.classList.contains('fr')||c.classList.contains('card'));
while(st.scrollHeight>max&&w>400){w-=20;cs2.forEach(c=>c.style.width=w+'px')}})}</script></body></html>"""


# ------------------------------------------------------------------ piezas

def corazon(i, x, y, r, c1, c2, blur=0, dur=4, amp=16, delay=0):
    return f"""<div class="abs" style="left:{x-r}px;top:{y-r}px;width:{2*r}px;height:{2*r}px;animation:flota{i} {dur}s ease-in-out {delay}s infinite alternate;filter:blur({blur}px) drop-shadow(0 18px 24px rgba(0,0,0,.25))">
<style>@keyframes flota{i}{{from{{transform:translate(0,0) rotate(-5deg)}}to{{transform:translate({amp//2}px,-{amp}px) rotate(6deg)}}}}</style>
<svg width="100%" height="100%" viewBox="0 0 100 100"><defs><radialGradient id="g{i}" cx="35%" cy="30%" r="75%"><stop offset="0" stop-color="#fff" stop-opacity=".6"/><stop offset=".25" stop-color="{c1}"/><stop offset="1" stop-color="{c2}"/></radialGradient></defs>
<circle cx="50" cy="50" r="48" fill="url(#g{i})"/><path d="M50 74 C20 54 22 32 36 30 C44 29 48 34 50 39 C52 34 56 29 64 30 C78 32 80 54 50 74Z" fill="#fff"/></svg></div>"""


def cucaracha(i, path, dur, delay, escala=1.0, color="#4a2a14"):
    """Cucaracha vista desde arriba que camina por un path (offset-path), mirando hacia donde va."""
    return f"""<div class="abs" style="left:0;top:0;offset-path:path('{path}');offset-rotate:auto;animation:camina{i} {dur}s linear {delay}s both">
<style>@keyframes camina{i}{{0%{{offset-distance:0%;opacity:0}}6%{{opacity:1}}100%{{offset-distance:100%;opacity:1}}}}</style>
<svg width="{int(90*escala)}" height="{int(60*escala)}" viewBox="-45 -30 90 60" style="transform:translate(-50%,-50%);display:block;animation:patas 0.18s linear infinite alternate">
<g stroke="{color}" stroke-width="2.6" stroke-linecap="round" fill="none">
<path d="M-8 -9 L-18 -24 M4 -10 L2 -27 M14 -9 L24 -24 M-8 9 L-18 24 M4 10 L2 27 M14 9 L24 24"/>
<path d="M30 -4 Q44 -16 52 -26 M30 4 Q44 16 52 26"/></g>
<ellipse cx="0" cy="0" rx="26" ry="13" fill="{color}"/><ellipse cx="27" cy="0" rx="8" ry="7" fill="#2b170a"/>
<path d="M-24 0 L20 0" stroke="#2b170a" stroke-width="1.5" opacity=".6"/></svg></div>"""


CSS_COMUN = """
@keyframes entra{from{opacity:0;transform:translateY(60px) scale(.94)}to{opacity:1;transform:none}}
@keyframes flotaCard{from{transform:translateY(0)}to{transform:translateY(-10px)}}
@keyframes titulo{from{opacity:0;letter-spacing:22px}to{opacity:1;letter-spacing:1px}}
@keyframes pulso{0%{transform:scale(.96);opacity:.0}25%{opacity:.75}100%{transform:scale(1.08);opacity:0}}
@keyframes deriva{from{transform:translate(-80px,-60px)}to{transform:translate(80px,70px)}}
@keyframes patas{from{transform:translate(-50%,-50%) scaleY(1)}to{transform:translate(-50%,-50%) scaleY(.92)}}
@keyframes sello{0%{opacity:0;transform:scale(2.4) rotate(-30deg)}70%{opacity:1;transform:scale(.92) rotate(-12deg)}100%{opacity:1;transform:scale(1) rotate(-12deg)}}
@keyframes cinta{from{background-position:0 0}to{background-position:160px 0}}
@keyframes check{from{stroke-dashoffset:60}to{stroke-dashoffset:0}}
@keyframes reticula{from{background-position:0 0}to{background-position:90px 90px}}
@keyframes reticula2{from{background-position:0 0,0 0,0 0,0 0}to{background-position:0 150px,0 150px,0 150px,0 150px}}
@keyframes pop{0%{transform:scale(0)}70%{transform:scale(1.15)}100%{transform:scale(1)}}
"""


def card_animada(img, ancho, delay=0.35):
    return f"""<div style="width:{ancho}px;animation:entra .9s cubic-bezier(.2,.9,.25,1.15) {delay}s both"><div class="card" style="animation:flotaCard 2s ease-in-out 1.3s infinite alternate"><img src="{img}"></div></div>"""


# ------------------------------------------------------------------ diseños

def spk_s1(img):
    """SPK · Customer Review animado: fondo que respira, anillos pulsando, corazones flotando."""
    c1, c2 = "#4C72F5", "#1B3FC9"
    anillos = "".join(
        f'<div class="abs" style="left:{540-r}px;top:{880-r}px;width:{2*r}px;height:{2*r}px;border-radius:50%;border:3px solid rgba(255,255,255,.8);animation:pulso 4s ease-out {-(k*0.66):.2f}s infinite"></div>'
        for k, r in enumerate((180, 300, 420, 540, 660, 780)))
    fijos = "".join(f'<div class="abs" style="left:{540-r}px;top:{880-r}px;width:{2*r}px;height:{2*r}px;border-radius:50%;border:2px solid rgba(255,255,255,.35)"></div>' for r in (240, 400, 560, 720, 900))
    hearts = (corazon(1, 80, 130, 110, c1, c2, 2, 4, 18) + corazon(2, 560, 70, 55, c1, c2, 0, 2, 10, .3) +
              corazon(3, 1000, 330, 150, c1, c2, 0, 4, 22, .5) + corazon(4, 70, 1500, 170, c1, c2, 6, 4, 26, .2) +
              corazon(5, 990, 1420, 62, c1, c2, 0, 2, 12, .7) + corazon(6, 1030, 1870, 120, c1, c2, 4, 4, 18) +
              corazon(7, 320, 1880, 72, c1, c2, 3, 2, 12, .4))
    body = f"""<div class="abs" style="inset:0;background:radial-gradient(circle at 50% 46%,#f2f2f3 0,#d6d6d9 45%,#a9a9ae 100%)"></div>
<div class="abs" style="left:-200px;top:300px;width:1480px;height:1300px;background:radial-gradient(circle,rgba(255,255,255,.55),transparent 60%);animation:deriva 4s ease-in-out infinite alternate"></div>
{fijos}{anillos}{hearts}
<div class="stack" style="top:280px;height:1080px;gap:44px">
<div style="font-family:'Archivo Black';font-size:82px;color:{c2};white-space:nowrap;animation:titulo 1s ease-out .1s both">CUSTOMER REVIEW</div>
{card_animada(img, 940)}</div>
<img class="abs" src="{u('assets/spk_negro_c.png')}" style="left:50%;transform:translateX(-50%);top:1410px;height:60px;animation:entra .8s ease-out 1s both">"""
    return body, 8


def ssi_a_plagas(img, servicio):
    """SSI · Plagas fuera: las cucarachas huyen de la tarjeta cuando llega la reseña."""
    rutas = [("M540 900 C420 700 200 620 -120 560", 2.6, .5), ("M560 950 C700 760 900 700 1220 640", 2.4, .6),
             ("M520 1000 C380 1200 200 1350 -120 1500", 2.8, .55), ("M580 980 C760 1150 900 1300 1220 1460", 2.5, .7),
             ("M540 880 C560 600 520 400 560 -120", 2.7, .65), ("M500 1050 C480 1300 560 1600 520 2050", 3.0, .6),
             ("M600 930 C850 900 1000 1000 1220 1050", 2.2, .8), ("M480 940 C250 960 100 900 -120 950", 2.3, .75)]
    bichos = "".join(cucaracha(i, p, d, de + .75, 1.15 if i % 2 else .9) for i, (p, d, de) in enumerate(rutas))
    body = f"""<div class="abs" style="inset:0;background:#faf8f1"></div>
<div class="abs" style="inset:0;background:repeating-linear-gradient(135deg,rgba(139,195,74,.08) 0 40px,transparent 40px 80px)"></div>
{bichos}
<div class="stack" style="top:270px;height:1100px;gap:36px">
<div style="text-align:center;animation:entra .8s ease-out .2s both">
 <div style="font-family:Oswald;font-weight:700;font-size:96px;color:#1a1a1a;line-height:1">RESEÑA DE CLIENTE</div>
 <div style="display:inline-block;margin-top:18px;background:#8BC34A;color:#1a1a1a;font-weight:600;font-size:32px;padding:8px 26px;border-radius:40px">Servicio: {servicio}</div></div>
{card_animada(img, 930, .3)}</div>
<img class="abs" src="{u('assets/logo_ssicma.png')}" style="left:50%;transform:translateX(-50%);top:1370px;height:120px;animation:entra .8s ease-out 1.4s both">"""
    return body, 7


def ssi_b_sello(img, servicio):
    """SSI · Sello: carbón, cinta de seguridad que corre y un sello que cae sobre la reseña."""
    cinta = "background:repeating-linear-gradient(45deg,#8BC34A 0 40px,#1a1a1a 40px 80px);animation:cinta 1.2s linear infinite"
    body = f"""<div class="abs" style="inset:0;background:radial-gradient(circle at 50% 40%,#2c2c2c,#121212 70%)"></div>
<div class="abs" style="left:0;right:0;top:170px;height:46px;{cinta}"></div>
<div class="abs" style="left:0;right:0;top:1560px;height:46px;{cinta};animation-direction:reverse"></div>
<div class="stack" style="top:300px;height:1060px;gap:40px">
<div style="text-align:center;animation:entra .8s ease-out .1s both"><div style="font-family:Oswald;font-weight:700;font-size:88px;color:#fff;line-height:1">LO QUE DICEN</div>
<div style="font-family:Oswald;font-weight:700;font-size:88px;color:#8BC34A;line-height:1.05">NUESTROS CLIENTES</div></div>
<div style="position:relative">{card_animada(img, 930, .6)}
<div class="abs" style="right:-40px;bottom:-200px;width:250px;height:250px;animation:sello .55s cubic-bezier(.3,1.4,.5,1) 1.7s both">
<svg viewBox="0 0 200 200" width="250" height="250"><defs><path id="arc" d="M100 100 m-72 0 a72 72 0 1 1 144 0 a72 72 0 1 1 -144 0"/></defs>
<circle cx="100" cy="100" r="92" fill="#8BC34A" opacity=".96"/><circle cx="100" cy="100" r="80" fill="none" stroke="#1a1a1a" stroke-width="3" stroke-dasharray="4 5"/>
<text font-family="Oswald" font-weight="700" font-size="20" fill="#1a1a1a" letter-spacing="3"><textPath href="#arc">CLIENTE SATISFECHO · CLIENTE SATISFECHO ·</textPath></text>
<text x="100" y="98" text-anchor="middle" font-family="Oswald" font-weight="700" font-size="44" fill="#1a1a1a">5.0</text>
<text x="100" y="128" text-anchor="middle" font-size="22" fill="#1a1a1a">★★★★★</text></svg></div></div></div>
<img class="abs" src="{u('assets/logo_ssicma_claro.png')}" style="left:50%;transform:translateX(-50%);top:1410px;height:110px;animation:entra .8s ease-out 2s both">"""
    return body, 7


def ssi_c_bitacora(img, servicio):
    """SSI · Bitácora: la reseña sujeta a una tabla de servicio con su palomita."""
    body = f"""<div class="abs" style="inset:0;background:linear-gradient(170deg,#8BC34A,#5E8F2A)"></div>
<div class="abs" style="inset:0;background-image:radial-gradient(rgba(255,255,255,.18) 2px,transparent 2px);background-size:36px 36px"></div>
<div class="abs" style="left:60px;top:400px;width:960px;height:880px;border-radius:36px;background:#7a5230;box-shadow:0 40px 70px rgba(0,0,0,.35);animation:entra .8s ease-out .1s both">
 <div class="abs" style="left:40px;right:40px;top:70px;bottom:40px;background:#faf8f1;border-radius:14px"></div>
 <div class="abs" style="left:50%;top:-40px;transform:translateX(-50%);width:300px;height:110px;border-radius:24px;background:linear-gradient(#d9d9d9,#9a9a9a);box-shadow:0 6px 12px rgba(0,0,0,.3)"></div>
 <div class="abs" style="left:90px;right:90px;top:140px;display:flex;justify-content:space-between;align-items:center;font-family:Oswald;font-weight:700;color:#1a1a1a">
  <span style="font-size:52px">BITÁCORA DE SERVICIO</span>
  <svg width="74" height="74" viewBox="0 0 40 40" style="animation:pop .5s ease-out 1.6s both"><circle cx="20" cy="20" r="19" fill="#8BC34A"/><path d="M11 21 l6 6 l12-14" fill="none" stroke="#1a1a1a" stroke-width="4" stroke-linecap="round" stroke-dasharray="60" style="animation:check .5s ease-out 1.9s both"/></svg></div>
 <div class="abs" style="left:90px;right:90px;top:225px;height:3px;background:#1a1a1a;opacity:.15"></div>
 <div class="abs" style="left:90px;top:250px;font-size:30px;color:#555">Servicio: <b style="color:#1a1a1a">{servicio}</b></div>
 <div class="abs" style="left:60px;right:60px;top:320px">{card_animada(img, 840, .8)}</div>
 <img class="abs" src="{u('assets/logo_ssicma.png')}" style="left:50%;transform:translateX(-50%);bottom:70px;height:100px">
</div>"""
    return body, 7


import re
PLAGAS = re.compile(r"cucarach|plaga|fumig|roedor|rata|termita|hormiga|mosc|chinche|alacr|ara[nñ]a|exterminaci|garrapat|pulga", re.I)


def chispa(i, path, dur, delay):
    """Palomita lima que sale disparada de la tarjeta (adorno para reseñas que no son de plagas)."""
    return f"""<div class="abs" style="left:0;top:0;offset-path:path('{path}');offset-rotate:0deg;animation:camina{i} {dur}s cubic-bezier(.2,.7,.3,1) {delay}s both">
<style>@keyframes camina{i}{{0%{{offset-distance:0%;opacity:0;transform:scale(.4)}}10%{{opacity:1}}70%{{opacity:1}}100%{{offset-distance:100%;opacity:0;transform:scale(1.1)}}}}</style>
<svg width="70" height="70" viewBox="0 0 40 40" style="transform:translate(-50%,-50%);display:block"><circle cx="20" cy="20" r="18" fill="#8BC34A"/><path d="M11 21l6 6 12-14" fill="none" stroke="#1a1a1a" stroke-width="4" stroke-linecap="round"/></svg></div>"""


def ssi_a(img, servicio=""):
    """SSI · A con adorno según el servicio: cucarachas que huyen si es de plagas; si no, palomitas que salen."""
    # etiqueta corta: Google a veces lista 4 o 5 servicios y plagas en una sola reseña
    if PLAGAS.search(servicio or ""):
        return ssi_a_plagas(img, "Control de plagas")
    servicio = (servicio or "").split(" · ")[0].split(",")[0].strip()[:40]
    body, dur = ssi_a_plagas(img, servicio)
    rutas = [("M540 900 C420 700 200 620 60 560", 2.2, .9), ("M560 950 C700 760 900 700 1020 640", 2.0, 1.0),
             ("M520 1000 C380 1200 200 1350 80 1450", 2.4, 1.1), ("M580 980 C760 1150 900 1300 1000 1400", 2.1, 1.2),
             ("M600 930 C850 900 1000 1000 1040 1050", 1.9, 1.3), ("M480 940 C250 960 100 900 40 950", 2.0, 1.4)]
    chispas = "".join(chispa(i, p, d, de) for i, (p, d, de) in enumerate(rutas))
    body = re.sub(r'<div class="abs" style="left:0;top:0;offset-path.*?</svg></div>', "", body, flags=re.S)
    body = body.replace('<div class="stack"', chispas + '<div class="stack"', 1)
    if not servicio:
        body = re.sub(r'<div style="display:inline-block;margin-top:18px;background:#8BC34A.*?</div>', "", body, flags=re.S)
    return body, dur


def _entra_rot(img, ancho, dx, rot, delay):
    return (f'<div style="width:{ancho}px;transform:translateX({dx}px);animation:entra .8s cubic-bezier(.2,.9,.25,1.15) {delay}s both">'
            f'<div class="card" style="transform:rotate({rot}deg)"><img src="{img}"></div></div>')


def spk_m2(imgs, total):
    """SPK · M2 animado: la cuadrícula avanza, las tarjetas caen una por una y los pulgares se mecen."""
    grid = ("background-color:#0d1330;background-image:linear-gradient(rgba(255,255,255,.07) 2px,transparent 2px),"
            "linear-gradient(90deg,rgba(255,255,255,.07) 2px,transparent 2px);background-size:90px 90px;animation:reticula 6s linear infinite")
    pulgar = lambda i, x, y, r: (f'<div class="abs" style="left:{x}px;top:{y}px;animation:meceP{i} 1.5s ease-in-out infinite alternate">'
        f'<style>@keyframes meceP{i}{{from{{transform:rotate({r-8}deg) translateY(0)}}to{{transform:rotate({r+8}deg) translateY(-12px)}}}}</style>'
        '<svg width="110" height="110" viewBox="0 0 24 24" fill="none" stroke="#3E64F0" stroke-width="1.3" stroke-linejoin="round">'
        '<path d="M7 10v11H3V10h4zm0 0l4-8c1.7 0 3 1.3 3 3v4h5.5c1.2 0 2.1 1.1 1.9 2.3l-1.4 8c-.2 1-1 1.7-2 1.7H7"/></svg></div>')
    cards = "".join(_entra_rot(s, 820, dx, r, .4 + .35 * k) for k, (s, dx, r) in enumerate(zip(imgs, (30, -25, 20, -20), (-3, 2, -1.5, 2.5))))
    body = f"""<div class="abs" style="inset:0;{grid}"></div>
<div class="abs" style="left:0;right:0;top:290px;text-align:center;color:#fff;font-weight:800;font-size:64px;animation:titulo .9s ease-out 0s both">Opiniones reales</div>
<div class="abs" style="left:0;right:0;top:385px;text-align:center;color:#3E64F0;font-weight:600;font-size:34px;animation:entra .7s ease-out .2s both">★★★★★ {total}</div>
<div class="stack fitme" style="top:480px;height:960px;gap:36px" data-max="960" data-w="820">{cards}</div>
{pulgar(1, 30, 700, -15)}{pulgar(2, 950, 980, 12)}{pulgar(3, 40, 1300, -8)}
<img class="abs" src="{u('assets/spk_blanco_c.png')}" style="left:50%;transform:translateX(-50%);top:1470px;height:52px;animation:entra .8s ease-out 1.6s both">"""
    return body, 7


def ssi_m2b(imgs, total):
    """SSI · Plano técnico animado: retícula que avanza, cintas de seguridad corriendo, tarjetas que caen, íconos flotando."""
    L, C = "#8BC34A", "#1a1a1a"
    grid = ("background-color:#151a14;background-image:linear-gradient(rgba(139,195,74,.10) 1px,transparent 1px),"
            "linear-gradient(90deg,rgba(139,195,74,.10) 1px,transparent 1px),linear-gradient(rgba(139,195,74,.18) 2px,transparent 2px),"
            "linear-gradient(90deg,rgba(139,195,74,.18) 2px,transparent 2px);background-size:30px 30px,30px 30px,150px 150px,150px 150px;"
            "animation:reticula2 6s linear infinite")
    cinta = f"background:repeating-linear-gradient(90deg,{L} 0 40px,{C} 40px 80px);background-size:160px 46px;animation:cinta 1.2s linear infinite"
    ICON = {"extintor": '<path d="M9 8h6v13H9z M10 8V5h4v3 M14 5l4-2 M8 12h-2v4"/>',
            "casco": '<path d="M3 17h18 M5 17a7 7 0 0 1 14 0 M12 10V6 M9 11V8 M15 11V8"/>',
            "escudo": '<path d="M12 3l8 3v6c0 5-4 8-8 9-4-1-8-4-8-9V6z M8.5 12l2.5 2.5 5-5"/>'}
    ic = lambda i, k, x, y, r, s=120: (f'<div class="abs" style="left:{x}px;top:{y}px;animation:meceI{i} 2s ease-in-out infinite alternate">'
        f'<style>@keyframes meceI{i}{{from{{transform:rotate({r-6}deg) translateY(0)}}to{{transform:rotate({r+6}deg) translateY(-14px)}}}}</style>'
        f'<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="{L}" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round">{ICON[k]}</svg></div>')
    cards = "".join(_entra_rot(s, 820, dx, r, .4 + .35 * k) for k, (s, dx, r) in enumerate(zip(imgs, (25, -25, 20, -20), (-2.5, 2, -1.5, 2))))
    body = f"""<div class="abs" style="inset:0;{grid}"></div>
<div class="abs" style="left:-140px;top:130px;width:640px;height:46px;transform:rotate(-35deg)"><div style="width:100%;height:100%;{cinta}"></div></div>
<div class="abs" style="right:-140px;top:1700px;width:640px;height:46px;transform:rotate(-35deg)"><div style="width:100%;height:100%;{cinta};animation-direction:reverse"></div></div>
<div class="abs" style="left:0;right:0;top:280px;text-align:center;font-family:Oswald;font-weight:700;font-size:84px;color:#fff;letter-spacing:2px;animation:titulo .9s ease-out 0s both">CLIENTES <span style="color:{L}">SATISFECHOS</span></div>
<div class="abs" style="left:0;right:0;top:395px;text-align:center;color:{L};font-weight:600;font-size:32px;animation:entra .7s ease-out .2s both">★★★★★ {total}</div>
<div class="stack fitme" style="top:480px;height:960px;gap:36px" data-max="960" data-w="820">{cards}</div>
{ic(1, 'extintor', 20, 640, -12)}{ic(2, 'casco', 950, 930, 10, 110)}{ic(3, 'escudo', 30, 1280, -6, 110)}
<img class="abs" src="{u('assets/logo_ssicma_claro.png')}" style="left:50%;transform:translateX(-50%);top:1460px;height:96px;animation:entra .8s ease-out 1.6s both">"""
    return body, 7




# ------------------------------------------------------------------ v5 (19-nov-2026): 5 s con cierre
# Gibran: 5 s, logos centrados que no salgan «de la nada», cierre propio. Single = gracias; múltiple = sólo salida.
# El logo vive SIEMPRE en un contenedor flex que lo centra; la animación va en la imagen (así no pisa el centrado).

CSS_V5 = """
@keyframes sube{from{opacity:0;transform:translateY(70px) scale(.94)}to{opacity:1;transform:none}}
@keyframes sale{to{opacity:0;transform:translateY(-160px) scale(.9)}}
@keyframes saleIzq{to{opacity:0;transform:translate(-900px,-120px) rotate(-14deg)}}
@keyframes saleDer{to{opacity:0;transform:translate(900px,-120px) rotate(14deg)}}
@keyframes lockup{0%{opacity:0;transform:scale(.82)}60%{opacity:1;transform:scale(1.04)}100%{opacity:1;transform:scale(1)}}
@keyframes linea{from{transform:scaleX(0)}to{transform:scaleX(1)}}
"""
SALIDA = 2.9      # empieza la salida del single
CIERRE = 3.45     # entra el mensaje de gracias / el logo


def _logo(src, top, alto, delay):
    return (f'<div class="abs" style="left:0;right:0;top:{top}px;display:flex;justify-content:center">'
            f'<img src="{src}" style="height:{alto}px;animation:lockup .7s cubic-bezier(.2,.9,.25,1.1) {delay}s both"></div>')


def _gracias(t1, t2, color1, color2, fuente, logo, logo_alto, acento):
    return f"""<div class="abs" style="left:0;right:0;top:640px;display:flex;flex-direction:column;align-items:center;gap:26px;text-align:center;padding:0 90px">
<div style="font-family:{fuente};font-size:96px;line-height:1.02;color:{color1};animation:lockup .7s cubic-bezier(.2,.9,.25,1.1) {CIERRE}s both">{t1}</div>
<div style="width:220px;height:8px;border-radius:8px;background:{acento};transform-origin:center;animation:linea .5s ease-out {CIERRE + .25}s both"></div>
<div style="font-size:44px;font-weight:600;color:{color2};animation:sube .6s ease-out {CIERRE + .35}s both">{t2}</div></div>
{_logo(logo, 1230, logo_alto, CIERRE + .6)}"""


def spk_s1_v5(img, servicio=""):
    c1, c2 = "#4C72F5", "#1B3FC9"
    anillos = "".join(
        f'<div class="abs" style="left:{540-r}px;top:{880-r}px;width:{2*r}px;height:{2*r}px;border-radius:50%;border:3px solid rgba(255,255,255,.8);animation:pulso 4s ease-out {-(k*0.66):.2f}s infinite"></div>'
        for k, r in enumerate((180, 300, 420, 540, 660, 780)))
    fijos = "".join(f'<div class="abs" style="left:{540-r}px;top:{880-r}px;width:{2*r}px;height:{2*r}px;border-radius:50%;border:2px solid rgba(255,255,255,.35)"></div>' for r in (240, 400, 560, 720, 900))
    hearts = (corazon(1, 80, 130, 110, c1, c2, 2, 2.5, 18) + corazon(2, 560, 70, 55, c1, c2, 0, 1.25, 10, .3) +
              corazon(3, 1000, 330, 150, c1, c2, 0, 2.5, 22, .5) + corazon(4, 70, 1500, 170, c1, c2, 6, 2.5, 26, .2) +
              corazon(5, 990, 1420, 62, c1, c2, 0, 1.25, 12, .7) + corazon(6, 1030, 1870, 120, c1, c2, 4, 2.5, 18) +
              corazon(7, 320, 1880, 72, c1, c2, 3, 1.25, 12, .4))
    body = f"""<div class="abs" style="inset:0;background:radial-gradient(circle at 50% 46%,#f2f2f3 0,#d6d6d9 45%,#a9a9ae 100%)"></div>
<div class="abs" style="left:-200px;top:300px;width:1480px;height:1300px;background:radial-gradient(circle,rgba(255,255,255,.55),transparent 60%);animation:deriva 2.5s ease-in-out infinite alternate"></div>
{fijos}{anillos}{hearts}
<div class="stack fitme" data-max="1080" data-w="940" style="top:280px;height:1080px;gap:44px;animation:sale .55s ease-in {SALIDA}s forwards">
<div style="font-family:'Archivo Black';font-size:74px;color:{c2};white-space:nowrap;animation:titulo .8s ease-out 0s both">CUSTOMER REVIEW</div>
{card_animada(img, 940, .25)}</div>
{_gracias("¡Gracias por tu reseña!", "Seguimos trabajando para ti.", c2, "#2b2f3a", "'Archivo Black'", u('assets/spk_negro_c.png'), 64, c1)}"""
    return body, 5


def ssi_a_v5(img, servicio=""):
    plagas = bool(PLAGAS.search(servicio or ""))
    etiqueta = "Control de plagas" if plagas else (servicio or "").split(" · ")[0].split(",")[0].strip()[:40]
    if plagas:
        rutas = [("M540 900 C420 700 200 620 -120 560", 1.8), ("M560 950 C700 760 900 700 1220 640", 1.7),
                 ("M520 1000 C380 1200 200 1350 -120 1500", 2.0), ("M580 980 C760 1150 900 1300 1220 1460", 1.8),
                 ("M540 880 C560 600 520 400 560 -120", 1.9), ("M500 1050 C480 1300 560 1600 520 2050", 2.1),
                 ("M600 930 C850 900 1000 1000 1220 1050", 1.6), ("M480 940 C250 960 100 900 -120 950", 1.7)]
        adorno = "".join(cucaracha(i, p, d, .85 + .05 * i, 1.15 if i % 2 else .9) for i, (p, d) in enumerate(rutas))
    else:
        rutas = [("M540 900 C420 700 200 620 60 560", 1.6), ("M560 950 C700 760 900 700 1020 640", 1.5),
                 ("M520 1000 C380 1200 200 1350 80 1450", 1.7), ("M580 980 C760 1150 900 1300 1000 1400", 1.6)]
        adorno = "".join(chispa(i, p, d, .85 + .1 * i) for i, (p, d) in enumerate(rutas))
    chip = (f'<div style="display:inline-block;margin-top:18px;background:#8BC34A;color:#1a1a1a;font-weight:600;font-size:32px;'
            f'padding:8px 26px;border-radius:40px">Servicio: {etiqueta}</div>') if etiqueta else ""
    body = f"""<div class="abs" style="inset:0;background:#faf8f1"></div>
<div class="abs" style="inset:0;background:repeating-linear-gradient(135deg,rgba(139,195,74,.08) 0 40px,transparent 40px 80px)"></div>
{adorno}
<div class="stack fitme" data-max="1100" data-w="930" style="top:270px;height:1100px;gap:36px;animation:sale .55s ease-in {SALIDA}s forwards">
<div style="text-align:center;animation:sube .7s ease-out 0s both">
 <div style="font-family:Oswald;font-weight:700;font-size:96px;color:#1a1a1a;line-height:1">RESEÑA DE CLIENTE</div>{chip}</div>
{card_animada(img, 930, .2)}</div>
{_gracias("Gracias por tu confianza", "Seguimos cuidando tu negocio.", "#1a1a1a", "#3b4a2a", "Oswald;font-weight:700", u('assets/logo_ssicma.png'), 120, "#8BC34A")}"""
    return body, 5


def _multi_v5(imgs, dxs, rots, salida=3.35, cierre=3.95):
    out = []
    for k, (s, dx, r) in enumerate(zip(imgs, dxs, rots)):
        sal = "saleIzq" if k % 2 else "saleDer"
        out.append(f'<div style="width:820px;transform:translateX({dx}px);animation:entra .7s cubic-bezier(.2,.9,.25,1.15) {.3 + .25 * k}s both,'
                   f'{sal} .5s cubic-bezier(.5,0,.9,.6) {salida + .1 * k}s forwards"><div class="card" style="transform:rotate({r}deg)"><img src="{s}"></div></div>')
    return "".join(out)


def spk_m2_v5(imgs, total):
    grid = ("background-color:#0d1330;background-image:linear-gradient(rgba(255,255,255,.07) 2px,transparent 2px),"
            "linear-gradient(90deg,rgba(255,255,255,.07) 2px,transparent 2px);background-size:90px 90px;animation:reticula 3s linear infinite")
    pulgar = lambda i, x, y, r: (f'<div class="abs" style="left:{x}px;top:{y}px;animation:meceP{i} 1.25s ease-in-out infinite alternate">'
        f'<style>@keyframes meceP{i}{{from{{transform:rotate({r-8}deg) translateY(0)}}to{{transform:rotate({r+8}deg) translateY(-12px)}}}}</style>'
        '<svg width="110" height="110" viewBox="0 0 24 24" fill="none" stroke="#3E64F0" stroke-width="1.3" stroke-linejoin="round">'
        '<path d="M7 10v11H3V10h4zm0 0l4-8c1.7 0 3 1.3 3 3v4h5.5c1.2 0 2.1 1.1 1.9 2.3l-1.4 8c-.2 1-1 1.7-2 1.7H7"/></svg></div>')
    body = f"""<div class="abs" style="inset:0;{grid}"></div>
<div class="abs" style="left:0;right:0;top:290px;text-align:center;animation:sale .5s ease-in 3.3s forwards">
 <div style="color:#fff;font-weight:800;font-size:64px;animation:titulo .8s ease-out 0s both">Opiniones reales</div>
 <div style="margin-top:14px;color:#3E64F0;font-weight:600;font-size:34px;animation:sube .6s ease-out .15s both">★★★★★ {total}</div></div>
<div class="stack fitme" style="top:480px;height:960px;gap:36px" data-max="960" data-w="820">{_multi_v5(imgs, (30, -25, 20, -20), (-3, 2, -1.5, 2.5))}</div>
<div style="animation:sale .4s ease-in 3.35s forwards">{pulgar(1, 30, 700, -15)}{pulgar(2, 950, 980, 12)}{pulgar(3, 40, 1300, -8)}</div>
{_logo(u('assets/spk_blanco_c.png'), 880, 130, 3.95)}"""
    return body, 5


def ssi_m2b_v5(imgs, total):
    L, C = "#8BC34A", "#1a1a1a"
    grid = ("background-color:#151a14;background-image:linear-gradient(rgba(139,195,74,.10) 1px,transparent 1px),"
            "linear-gradient(90deg,rgba(139,195,74,.10) 1px,transparent 1px),linear-gradient(rgba(139,195,74,.18) 2px,transparent 2px),"
            "linear-gradient(90deg,rgba(139,195,74,.18) 2px,transparent 2px);background-size:30px 30px,30px 30px,150px 150px,150px 150px;"
            "animation:reticula2 3s linear infinite")
    cinta = f"background:repeating-linear-gradient(90deg,{L} 0 40px,{C} 40px 80px);background-size:160px 46px;animation:cinta 1.2s linear infinite"
    ICON = {"extintor": '<path d="M9 8h6v13H9z M10 8V5h4v3 M14 5l4-2 M8 12h-2v4"/>',
            "casco": '<path d="M3 17h18 M5 17a7 7 0 0 1 14 0 M12 10V6 M9 11V8 M15 11V8"/>',
            "escudo": '<path d="M12 3l8 3v6c0 5-4 8-8 9-4-1-8-4-8-9V6z M8.5 12l2.5 2.5 5-5"/>'}
    ic = lambda i, k, x, y, r, s=120: (f'<div class="abs" style="left:{x}px;top:{y}px;animation:meceI{i} 1.25s ease-in-out infinite alternate">'
        f'<style>@keyframes meceI{i}{{from{{transform:rotate({r-6}deg) translateY(0)}}to{{transform:rotate({r+6}deg) translateY(-14px)}}}}</style>'
        f'<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="{L}" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round">{ICON[k]}</svg></div>')
    body = f"""<div class="abs" style="inset:0;{grid}"></div>
<div class="abs" style="left:-140px;top:130px;width:640px;height:46px;transform:rotate(-35deg)"><div style="width:100%;height:100%;{cinta}"></div></div>
<div class="abs" style="right:-140px;top:1700px;width:640px;height:46px;transform:rotate(-35deg)"><div style="width:100%;height:100%;{cinta};animation-direction:reverse"></div></div>
<div class="abs" style="left:0;right:0;top:280px;text-align:center;animation:sale .5s ease-in 3.3s forwards">
 <div style="font-family:Oswald;font-weight:700;font-size:84px;color:#fff;letter-spacing:2px;animation:titulo .8s ease-out 0s both">CLIENTES <span style="color:{L}">SATISFECHOS</span></div>
 <div style="margin-top:10px;color:{L};font-weight:600;font-size:32px;animation:sube .6s ease-out .15s both">★★★★★ {total}</div></div>
<div class="stack fitme" style="top:480px;height:960px;gap:36px" data-max="960" data-w="820">{_multi_v5(imgs, (25, -25, 20, -20), (-2.5, 2, -1.5, 2))}</div>
<div style="animation:sale .4s ease-in 3.35s forwards">{ic(1, 'extintor', 20, 640, -12)}{ic(2, 'casco', 950, 930, 10, 110)}{ic(3, 'escudo', 30, 1280, -6, 110)}</div>
{_logo(u('assets/logo_ssicma_claro.png'), 880, 170, 3.95)}"""
    return body, 5


CSS_COMUN += CSS_V5

SINGLES_V4 = {"spk_s1": lambda img, servicio="": spk_s1(img), "ssi_a": ssi_a}
SINGLES = {"spk_s1": spk_s1_v5, "ssi_a": ssi_a_v5,
           "ssi_b": ssi_b_sello, "ssi_c": ssi_c_bitacora}
MULTIS = {"spk_m2": spk_m2_v5, "ssi_m2b": ssi_m2b_v5}
_VIEJO = {"spk_s1": lambda img, servicio="": spk_s1(img), "ssi_a": ssi_a,
           "ssi_b": ssi_b_sello, "ssi_c": ssi_c_bitacora}
MULTIS_V4 = {"spk_m2": spk_m2, "ssi_m2b": ssi_m2b}


def render(salida, body, dur, pg, cuadro_s=2.6):
    """Renderiza body a MP4 en `salida` (Path). Deja también un PNG del cuadro en cuadro_s."""
    import tempfile
    html = HEAD.replace("%CSS%", CSS_COMUN).replace("%BODY%", body)
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8", dir=AQUI) as t:
        t.write(html); tmp = pathlib.Path(t.name)
    try:
        pg.goto(tmp.as_uri()); pg.wait_for_load_state("networkidle"); pg.evaluate("document.fonts.ready")
        pg.evaluate("fit()"); pg.evaluate("document.getAnimations().forEach(a=>a.pause())")
        ff = subprocess.Popen([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-f", "image2pipe",
                               "-framerate", str(FPS), "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
                               "-preset", "medium", "-movflags", "+faststart", str(salida)], stdin=subprocess.PIPE)
        for f in range(int(dur * FPS)):
            pg.evaluate(f"document.getAnimations().forEach(a=>{{a.currentTime={f * 1000 / FPS}}})")
            png = pg.screenshot(type="png"); ff.stdin.write(png)
            if f == int(cuadro_s * FPS):
                salida.with_name(salida.stem + "_cuadro.png").write_bytes(png)
        ff.stdin.close(); ff.wait()
    finally:
        tmp.unlink(missing_ok=True)
