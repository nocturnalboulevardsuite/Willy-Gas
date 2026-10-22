"""
app.py — Interfaz de "Willy Gas" (Streamlit, pensada para celular).

Ejecutar en el computador:   streamlit run app.py

Estructura del proyecto:
  app.py      → pantallas, botones, dibujos y estilos (este archivo)
  logica.py   → cálculos del negocio (precios, resumen del día)
  db.py       → guardar/leer datos (SQLite local o Google Sheets)
  imagenes/   → (opcional) fotos reales de los cilindros. Si existe, por ejemplo,
                imagenes/cilindro_15.jpg, se usa esa foto en vez del dibujo.
                Formatos: .png .jpg .jpeg .webp

Nota: los estilos ahora viven al final de la sección 1 de este archivo,
así que estilos.py ya no se usa.
"""
from __future__ import annotations

import base64
import csv
import hmac
import html
import io
import os
from datetime import date, datetime, timedelta
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

import streamlit as st

import db
import logica

# ══════════════════════════════════════════════════════════════════════════════
# 1. CONFIGURACIÓN DE LA PÁGINA Y ESTILOS
# ══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Willy Gas",
    page_icon=":material/propane_tank:",
    layout="centered",
    initial_sidebar_state="collapsed",
)

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Atkinson+Hyperlegible:wght@400;700&display=swap');

:root{
  --tinta:#18212B; --suave:#56616E; --fondo:#F1F3F5; --papel:#FFFFFF; --linea:#D5DBE1;
  --azul:#1D4C86; --verde:#1B7A45; --rojo:#B3261E; --ambar:#8F5B00;
}

/* ---------- Base: fondo claro siempre, letra grande y legible ---------- */
html, body, .stApp, [data-testid="stAppViewContainer"]{
  background:var(--fondo)!important; color:var(--tinta)!important;
}
.stApp p, .stApp label, .stApp input, .stApp button, .stApp a, .stApp div{
  font-family:'Atkinson Hyperlegible', system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif;
}
header[data-testid="stHeader"], footer, #MainMenu, [data-testid="stToolbar"],
[data-testid="stDecoration"]{display:none!important;}
.block-container, [data-testid="stMainBlockContainer"]{
  padding:14px 14px 130px!important; max-width:560px!important;
}
[data-testid="stVerticalBlock"]{gap:.65rem;}

/* Columnas lado a lado también en el celular */
[data-testid="stHorizontalBlock"]{flex-wrap:nowrap!important; gap:10px!important;}
[data-testid="stColumn"], [data-testid="column"]{
  min-width:0!important; width:auto!important; flex:1 1 0%!important;
}

/* ---------- Botones grandes ---------- */
.stButton, .stLinkButton, .stDownloadButton,
[data-testid="stElementContainer"]:has(.stButton),
[data-testid="stElementContainer"]:has(.stLinkButton),
[data-testid="stElementContainer"]:has(.stDownloadButton){width:100%!important;}
.stButton button, .stLinkButton a, .stDownloadButton button{
  width:100%!important; min-height:64px; border-radius:16px!important;
  border:2px solid var(--linea)!important; background:var(--papel)!important;
  color:var(--tinta)!important; box-shadow:none!important; padding:8px 10px!important;
}
.stButton button p, .stLinkButton a p, .stDownloadButton button p{
  font-size:20px!important; font-weight:700!important; color:inherit!important; line-height:1.15;
}
.stButton button [data-testid="stIconMaterial"],
.stLinkButton a [data-testid="stIconMaterial"],
.stDownloadButton button [data-testid="stIconMaterial"]{font-size:28px!important; color:inherit!important;}
.stButton button [data-testid="stMarkdownContainer"],
.stLinkButton a [data-testid="stMarkdownContainer"]{overflow:visible!important; max-width:none!important;}
.stButton button p, .stLinkButton a p{white-space:normal!important; text-overflow:clip!important;}
.stButton button:active{transform:scale(.98);}
.stButton button:focus-visible, .stLinkButton a:focus-visible{
  outline:3px solid var(--azul)!important; outline-offset:2px;
}

/* Acción principal: azul */
.st-key-zona_dia button, .st-key-zona_guardar button, .st-key-zona_agregar button{
  background:var(--azul)!important; border-color:var(--azul)!important; color:#fff!important; min-height:72px;
}
/* Entregado / Ya pagó: verde */
[class*="st-key-zona_ok_"] button, [class*="st-key-zona_pago_"] button,
[class*="st-key-zona_confirma_"] button{
  background:var(--verde)!important; border-color:var(--verde)!important; color:#fff!important; min-height:72px;
}
/* Borrar: rojo suave; Confirmar borrado: rojo lleno */
[class*="st-key-zona_borrar_"] button{color:var(--rojo)!important; border-color:#EBC3BF!important;}
[class*="st-key-zona_si_"] button{
  background:var(--rojo)!important; border-color:var(--rojo)!important; color:#fff!important;
}
/* − y + del formulario */
[class*="st-key-zona_menos_"] button, [class*="st-key-zona_mas_"] button{min-height:68px;}
[class*="st-key-zona_menos_"] [data-testid="stIconMaterial"],
[class*="st-key-zona_mas_"] [data-testid="stIconMaterial"]{font-size:38px!important;}

/* Botón "Agregar pedido" fijo abajo */
.st-key-zona_agregar{
  position:fixed; left:14px; right:14px; bottom:calc(14px + env(safe-area-inset-bottom));
  z-index:999; max-width:532px; margin:0 auto; width:auto!important;
}
.st-key-zona_agregar button{min-height:76px; box-shadow:0 8px 22px rgba(24,33,43,.28)!important;}

/* Navegación: ícono arriba, texto abajo */
.st-key-navegacion button{min-height:78px; padding:6px 2px!important;}
.st-key-navegacion button > div > span{flex-direction:column!important; gap:2px!important;}
.st-key-navegacion button p{font-size:16px!important; white-space:nowrap!important;}
.st-key-navegacion [data-testid="stBaseButton-primary"]{
  background:var(--tinta)!important; border-color:var(--tinta)!important; color:#fff!important;
}

/* ---------- Tarjetas ---------- */
[class*="st-key-card_"]{
  background:var(--papel); border:1.5px solid var(--linea); border-radius:20px; padding:16px!important;
}
[class*="st-key-card_viejo_"]{border-left:7px solid var(--ambar);}
[class*="st-key-card_atrasado_"]{border-left:7px solid var(--rojo);}
[class*="st-key-fila_"]{border-top:1.5px solid var(--linea); padding-top:12px!important;}

/* ---------- Campos de texto ---------- */
[data-baseweb="input"]{border:2px solid var(--linea)!important; border-radius:14px!important; background:#fff!important;}
[data-baseweb="input"]:focus-within{border-color:var(--azul)!important;}
.stTextInput input, .stNumberInput input, .stDateInput input, [data-testid="stDateInput"] input{
  font-size:22px!important; min-height:60px; color:var(--tinta)!important; background:#fff!important;
}
[data-testid="stWidgetLabel"] p{font-size:18px!important; font-weight:700!important; color:var(--tinta)!important;}
[data-testid="stExpander"]{background:var(--papel); border-radius:16px!important;}
[data-testid="stExpander"] summary p{font-size:19px!important; font-weight:700!important;}
[class*="st-key-card_precio_"] [data-testid="stNumberInputStepDown"],
[class*="st-key-card_precio_"] [data-testid="stNumberInputStepUp"]{display:none!important;}

/* ---------- Textos ---------- */
.stApp .ico{width:22px; height:22px; vertical-align:-4px; margin-right:6px;}
.stApp .marca{display:flex; align-items:center; gap:12px; margin-bottom:4px;}
.stApp .marca .nombre{font-size:30px; font-weight:700; line-height:1;}
.stApp .fecha-hoy{font-size:18px; color:var(--suave); margin:4px 0 0;}
.stApp .titulo-seccion{font-size:25px; font-weight:700; margin:6px 0 2px;}
.stApp .subtitulo{font-size:17px; color:var(--suave); margin:0;}
.stApp .direccion{font-size:24px; font-weight:700; line-height:1.25; margin:0 0 4px;}
.stApp .nota{font-size:19px; color:var(--suave); margin:0 0 6px;}
.stApp .meta{font-size:18px; color:var(--suave); margin:8px 0 2px; display:flex; flex-wrap:wrap; gap:4px 16px;}
.stApp .meta span{white-space:nowrap;}
.stApp .etiqueta-vieja{color:var(--ambar); font-weight:700;}
.stApp .cilindros{display:flex; flex-wrap:wrap; gap:8px; margin:8px 0 2px;}
.stApp .chip{display:inline-flex; align-items:center; gap:8px; background:var(--fondo);
  border-radius:14px; padding:6px 14px 6px 8px; font-size:20px; font-weight:700;}
.stApp .fila-cil{display:flex; align-items:flex-end; gap:14px; margin:10px 0 8px;}
.stApp .nombre-cil{font-size:24px; font-weight:700; line-height:1.1;}
.stApp .precio-cil{font-size:18px; color:var(--suave);}
.stApp .contador{font-size:40px; font-weight:700; text-align:center; line-height:64px;
  background:var(--papel); border:2px solid var(--linea); border-radius:16px; color:var(--suave);}
.stApp .contador.activo{color:var(--azul); border-color:var(--azul);}
.stApp .total-form{font-size:28px; font-weight:700; text-align:center; margin:6px 0;}
.stApp .aviso{background:#E5F2EA; color:#12502D; border-radius:16px; padding:14px 16px;
  font-size:20px; font-weight:700;}
.stApp .aviso.error{background:#FBE8E6; color:var(--rojo);}
.stApp .vacio{text-align:center; color:var(--suave); font-size:20px; padding:30px 16px;
  border:2px dashed var(--linea); border-radius:20px; line-height:1.5;}
.stApp .confirmar{background:#FBE8E6; color:var(--rojo); border-radius:16px; padding:14px;
  font-size:21px; font-weight:700; text-align:center;}
.stApp .confirmar small{display:block; font-size:17px; font-weight:400; color:var(--tinta); margin-top:4px;}
.stApp .grilla{display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-bottom:8px;}
.stApp .dato{background:var(--papel); border:1.5px solid var(--linea); border-radius:18px; padding:14px;}
.stApp .dato.ancho{grid-column:span 2;}
.stApp .dato .icono img{width:28px; height:28px;}
.stApp .dato .valor{font-size:27px; font-weight:700; margin-top:4px;}
.stApp .dato .texto{font-size:16px; color:var(--suave);}
.stApp .dato.verde .valor{color:var(--verde);} .stApp .dato.ambar .valor{color:var(--ambar);} .stApp .dato.rojo .valor{color:var(--rojo);}
.stApp .monto-deuda{font-size:34px; font-weight:700; color:var(--rojo); margin:2px 0;}
.stApp .punto{display:inline-block; width:14px; height:14px; border-radius:50%; margin-right:6px; vertical-align:-1px;}
.stApp .precio-grande{font-size:36px; font-weight:700; line-height:1.1;}
.stApp .guardado{color:var(--verde); font-size:18px; font-weight:700;}
.stApp .fila-pedido{font-size:19px; line-height:1.35;}
.stApp .fila-pedido b{font-size:20px;}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# Los servidores en la nube usan hora UTC: se fuerza la hora de Chile para que
# "hoy" cambie a medianoche en Santiago y no a las 21:00.
ZONA = ZoneInfo(os.getenv("WILLY_TZ", "America/Santiago"))
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

# Estado para pedidos borrados. Se marcan en vez de desaparecer de la base,
# así "Deshacer" funciona y el respaldo los conserva.
ELIMINADO = getattr(db, "ELIMINADO", "eliminado")


def ahora() -> datetime:
    return datetime.now(ZONA)


def hoy() -> date:
    return ahora().date()


def fecha_larga(d: date) -> str:
    return f"{DIAS[d.weekday()].capitalize()} {d.day} de {MESES[d.month - 1]}"


def fecha_corta(iso: str) -> str:
    if not iso:
        return ""
    d = date.fromisoformat(iso[:10])
    return f"{DIAS[d.weekday()][:3]} {d.day:02d}/{d.month:02d}"


def pesos(monto: int) -> str:
    """21000 → $21.000 (formato chileno)."""
    return "$" + f"{int(monto or 0):,}".replace(",", ".")


def esc(texto: str) -> str:
    """Escapa lo que escribe el usuario antes de meterlo en HTML."""
    return html.escape(str(texto))


# ══════════════════════════════════════════════════════════════════════════════
# 2. DIBUJOS (reemplazan a los emojis)
# ══════════════════════════════════════════════════════════════════════════════
def _data_uri(svg: str) -> str:
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()


_TRAZOS = {
    "pin": '<path d="M12 21s-7-6.3-7-11.5a7 7 0 0 1 14 0C19 14.7 12 21 12 21z"/><circle cx="12" cy="9.5" r="2.5"/>',
    "persona": '<circle cx="12" cy="8" r="4"/><path d="M4 21c0-4.4 3.6-7 8-7s8 2.6 8 7"/>',
    "reloj": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3.5 2"/>',
    "billete": '<rect x="2.5" y="6" width="19" height="12" rx="2"/><circle cx="12" cy="12" r="2.8"/><path d="M6 9.5v5M18 9.5v5"/>',
    "calendario": '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/>',
    "alerta": '<path d="M12 3.5 2.5 20h19z"/><path d="M12 10v4.5M12 17.2v.3"/>',
    "check": '<circle cx="12" cy="12" r="9"/><path d="m7.5 12.5 3 3 6-6.5"/>',
    "x": '<circle cx="12" cy="12" r="9"/><path d="m9 9 6 6M15 9l-6 6"/>',
    "candado": '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V7.5a4 4 0 0 1 8 0V11"/>',
    "libreta": '<rect x="5" y="3" width="14" height="18" rx="2"/><path d="M9 8h6M9 12h6M9 16h3"/>',
    "sol": '<circle cx="12" cy="12" r="4"/><path d="M12 2.5V5M12 19v2.5M2.5 12H5M19 12h2.5M5.3 5.3l1.8 1.8M16.9 16.9l1.8 1.8M5.3 18.7l1.8-1.8M16.9 7.1l1.8-1.8"/>',
    "deshacer": '<path d="M9 14 4 9l5-5"/><path d="M4 9h10.5a5.5 5.5 0 0 1 0 11H11"/>',
    "basura": '<path d="M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3"/>',
    "pila": '<ellipse cx="12" cy="6" rx="7" ry="3"/><path d="M5 6v6c0 1.7 3.1 3 7 3s7-1.3 7-3V6M5 12v6c0 1.7 3.1 3 7 3s7-1.3 7-3v-6"/>',
}


@lru_cache(maxsize=None)
def _uri_icono(nombre: str, color: str) -> str:
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
           f'stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
           f'{_TRAZOS[nombre]}</svg>')
    return _data_uri(svg)


def icono(nombre: str, color: str = "#56616E") -> str:
    return f"<img class='ico' src='{_uri_icono(nombre, color)}' alt=''>"


# --- Cilindros de gas: dibujo con volumen (metal, collarín, válvula, base) ---
# Ancho y alto del cuerpo según el tamaño, para que se reconozcan de un vistazo.
_FORMAS = {5: (62, 74), 11: (74, 110), 15: (78, 132), 45: (70, 198)}


def _rect_redondeado(x: float, y: float, w: float, h: float, r: float) -> str:
    return (f"M{x + r},{y} h{w - 2 * r} a{r},{r} 0 0 1 {r},{r} v{h - 2 * r} "
            f"a{r},{r} 0 0 1 -{r},{r} h-{w - 2 * r} a{r},{r} 0 0 1 -{r},-{r} "
            f"v-{h - 2 * r} a{r},{r} 0 0 1 {r},-{r} z")


@lru_cache(maxsize=None)
def _svg_cilindro(kg: int) -> str:
    w, h = _FORMAS.get(kg, (74, min(200, 70 + kg * 3)))
    ancho_total, arriba = 100, 34
    x0 = (ancho_total - w) / 2
    alto_total = arriba + h + 10
    ry = min(20, h * 0.2)
    g = f"m{kg}"
    cw = w * 0.62
    cx = (ancho_total - cw) / 2
    collar = (_rect_redondeado(cx, 4, cw, 38, 8) + " "
              + _rect_redondeado(cx + 7, 10, cw - 14, 14, 7))
    eti_h = min(30, h * 0.26)
    eti_y = arriba + h * 0.24
    letra = min(19, eti_h * 0.62)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {ancho_total} {alto_total}">
<defs>
 <linearGradient id="{g}" x1="0" x2="1">
  <stop offset="0" stop-color="#7A3210"/><stop offset=".16" stop-color="#C8561A"/>
  <stop offset=".36" stop-color="#F7A866"/><stop offset=".52" stop-color="#E5712A"/>
  <stop offset=".84" stop-color="#B0501A"/><stop offset="1" stop-color="#6E2C0E"/>
 </linearGradient>
 <linearGradient id="{g}b" x1="0" x2="1">
  <stop offset="0" stop-color="#7A5A12"/><stop offset=".45" stop-color="#EBCB6A"/><stop offset="1" stop-color="#8A6A18"/>
 </linearGradient>
 <linearGradient id="{g}p" x1="0" x2="1">
  <stop offset="0" stop-color="#2B3036"/><stop offset=".4" stop-color="#7E868E"/><stop offset="1" stop-color="#262A2F"/>
 </linearGradient>
 <linearGradient id="{g}s" x1="0" y1="0" x2="0" y2="1">
  <stop offset="0" stop-color="#fff" stop-opacity=".35"/><stop offset=".25" stop-color="#fff" stop-opacity="0"/>
  <stop offset=".85" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".3"/>
 </linearGradient>
</defs>
<rect x="{x0 + w * .08}" y="{arriba + h - 8}" width="{w * .84}" height="16" rx="3" fill="url(#{g}p)"/>
<rect x="{x0}" y="{arriba}" width="{w}" height="{h}" rx="{w / 2}" ry="{ry}" fill="url(#{g})"/>
<rect x="{x0}" y="{arriba}" width="{w}" height="{h}" rx="{w / 2}" ry="{ry}" fill="url(#{g}s)"/>
<path d="M{x0 + 1} {arriba + h * .58} H{x0 + w - 1}" stroke="#000" stroke-opacity=".22" stroke-width="1.4"/>
<rect x="{x0 + w * .15}" y="{eti_y}" width="{w * .7}" height="{eti_h}" rx="4" fill="#fff" fill-opacity=".94"/>
<text x="50" y="{eti_y + eti_h * .7}" text-anchor="middle" font-family="Arial, Helvetica, sans-serif"
 font-weight="700" font-size="{letra}" fill="#18212B">{kg} kg</text>
<rect x="44" y="16" width="12" height="22" rx="2" fill="url(#{g}b)"/>
<rect x="39" y="12" width="22" height="7" rx="3.5" fill="#3A3F45"/>
<path d="{collar}" fill="url(#{g})" fill-rule="evenodd" stroke="#5E260B" stroke-opacity=".35"/>
</svg>"""


def _foto_real(kg: int) -> str | None:
    """Si existe imagenes/cilindro_<kg>.(png|jpg|jpeg|webp) se usa esa foto."""
    carpeta = Path(__file__).parent / "imagenes"
    for ext, mime in (("png", "png"), ("jpg", "jpeg"), ("jpeg", "jpeg"), ("webp", "webp")):
        ruta = carpeta / f"cilindro_{kg}.{ext}"
        if ruta.exists():
            return f"data:image/{mime};base64," + base64.b64encode(ruta.read_bytes()).decode()
    return None


@lru_cache(maxsize=None)
def _src_cilindro(kg: int) -> str:
    return _foto_real(kg) or _data_uri(_svg_cilindro(kg))


def img_cilindro(kg: int, alto: int | None = None, ancho: int | None = None) -> str:
    medida = f"height:{alto}px;width:auto;" if alto else f"width:{ancho or 56}px;height:auto;"
    return (f"<img src='{_src_cilindro(kg)}' alt='Cilindro de {kg} kg' "
            f"style='{medida}object-fit:contain;flex:none;'>")


# ══════════════════════════════════════════════════════════════════════════════
# 3. CONEXIÓN A LA BASE DE DATOS
#    Si hay credenciales de Google en .streamlit/secrets.toml → Google Sheets.
#    Si no → SQLite local (archivo willy_gas.db).
# ══════════════════════════════════════════════════════════════════════════════
def _secreto(seccion: str):
    try:
        return st.secrets[seccion]
    except Exception:
        return None


@st.cache_resource(show_spinner="Conectando…")
def obtener_repo():
    credenciales = _secreto("gcp_service_account")
    hoja = _secreto("google_sheets")
    if credenciales and hoja:
        return db.SheetsRepo(dict(credenciales), hoja["spreadsheet_key"])
    return db.SQLiteRepo(os.getenv("WILLY_DB", "willy_gas.db"))


# Candado opcional: si en secrets hay [acceso] clave = "...", la app solo abre
# con el enlace https://...streamlit.app/?k=ESA_CLAVE (se guarda en el ícono
# del celular, así el papá nunca tiene que escribir nada).
acceso = _secreto("acceso")
if acceso and acceso.get("clave"):
    if not hmac.compare_digest(str(st.query_params.get("k", "")), str(acceso["clave"])):
        st.markdown(f"<div class='vacio'>{icono('candado')}Abra Willy Gas desde el ícono de su celular.</div>",
                    unsafe_allow_html=True)
        st.stop()

try:
    repo = obtener_repo()
except Exception as e:  # sin internet o credenciales malas
    st.markdown(
        f"<div class='aviso error'>{icono('alerta', '#B3261E')}No se pudo conectar con los datos. "
        "Revise que haya internet y vuelva a abrir la app.</div>",
        unsafe_allow_html=True,
    )
    st.caption(f"Detalle técnico: {e}")
    st.stop()


# ══════════════════════════════════════════════════════════════════════════════
# 4. ESTADO DE LA SESIÓN (solo cosas de pantalla; los datos viven en la BD)
# ══════════════════════════════════════════════════════════════════════════════
def iniciar_estado() -> None:
    por_defecto = {
        "vista": "pedidos",       # pedidos | resumen | deudas | precios
        "mostrar_form": False,    # formulario de nuevo pedido abierto
        "fiado_id": None,         # pedido con el panel de fiado abierto
        "borrar_id": None,        # pedido que está pidiendo confirmación para borrar
        "borrar_dia": None,       # día (iso) que está pidiendo confirmación para borrar
        "deshacer": None,         # última acción, para poder revertirla
        "aviso": None,            # (texto, es_error)
        "precio_ok": None,        # tamaño cuyo precio se acaba de guardar
        "error_form": None,       # mensaje rojo del formulario
        "dir_nueva": "",
        "nota_nueva": "",
        **{f"cant_{t}": 0 for t in db.TAMANOS},
    }
    for clave, valor in por_defecto.items():
        st.session_state.setdefault(clave, valor)


iniciar_estado()
CONFIG = repo.leer_config()
PRECIOS = logica.precios_desde_config(CONFIG)
CIUDAD = logica.ciudad_desde_config(CONFIG)


# ══════════════════════════════════════════════════════════════════════════════
# 5. ACCIONES (callbacks). Se ejecutan ANTES de redibujar la pantalla,
#    así un solo toque basta y la pantalla siempre muestra el dato guardado.
# ══════════════════════════════════════════════════════════════════════════════
ERROR_RED = "No se pudo guardar. Revise internet y toque de nuevo."


def avisar(texto: str, error: bool = False) -> None:
    st.session_state.aviso = (texto, error)


def _cerrar_paneles() -> None:
    st.session_state.fiado_id = None
    st.session_state.borrar_id = None
    st.session_state.borrar_dia = None


def _registrar_deshacer(pedidos_antes: dict | list[dict], cambios: dict, texto: str) -> None:
    if isinstance(pedidos_antes, dict):
        pedidos_antes = [pedidos_antes]
    st.session_state.deshacer = {
        "items": [{"id": p["id"], "antes": {k: p.get(k) for k in cambios}} for p in pedidos_antes],
        "texto": texto,
    }


def cb_iniciar_dia() -> None:
    repo.iniciar_jornada(hoy().isoformat(), ahora().isoformat(timespec="seconds"))
    avisar("¡Buen día! Ya puede anotar pedidos.")


def cb_ir_a(vista: str) -> None:
    st.session_state.vista = vista
    st.session_state.mostrar_form = False
    _cerrar_paneles()


def cb_abrir_form() -> None:
    st.session_state.mostrar_form = True
    st.session_state.deshacer = None
    _cerrar_paneles()


def cb_cerrar_form() -> None:
    for t in db.TAMANOS:
        st.session_state[f"cant_{t}"] = 0
    st.session_state.dir_nueva = ""
    st.session_state.nota_nueva = ""
    st.session_state.error_form = None
    st.session_state.mostrar_form = False


def cb_cantidad(tamano: int, delta: int) -> None:
    clave = f"cant_{tamano}"
    st.session_state[clave] = max(0, min(20, st.session_state[clave] + delta))
    st.session_state.error_form = None


def cb_guardar_pedido() -> None:
    direccion = st.session_state.dir_nueva.strip()
    cantidades = {t: st.session_state[f"cant_{t}"] for t in db.TAMANOS}
    if sum(cantidades.values()) == 0:
        st.session_state.error_form = "Toque el botón + en al menos un cilindro."
        return
    if not direccion:
        st.session_state.error_form = "Falta la dirección. Toque el cuadro y hable con el micrófono."
        return
    try:
        repo.crear_pedido({
            "creado_en": ahora().isoformat(timespec="seconds"),
            "fecha_jornada": hoy().isoformat(),
            "direccion": direccion,
            "nota": st.session_state.nota_nueva.strip(),
            **{f"c{t}": n for t, n in cantidades.items()},
            "estado": db.PENDIENTE,
        })
    except Exception:
        st.session_state.error_form = ERROR_RED
        return
    cb_cerrar_form()
    avisar("Pedido guardado")


def cb_cambiar_estado(pedido_id: int, estado: str) -> None:
    antes = repo.obtener_pedido(pedido_id)
    if not antes:
        return
    cambios = {"estado": estado, "fecha_cierre": hoy().isoformat()}
    if estado == db.ENTREGADO:
        # El precio se "congela" al entregar: si mañana sube el gas, no cambia la historia
        cambios["monto_venta"] = logica.valor_pedido(antes, PRECIOS)
    try:
        repo.actualizar_pedido(pedido_id, cambios)
    except Exception:
        avisar(ERROR_RED, error=True)
        return
    texto = "Marcado como entregado" if estado == db.ENTREGADO else "Marcado como no entregado"
    _registrar_deshacer(antes, cambios, texto)
    st.session_state.aviso = None


def cb_abrir_fiado(pedido_id: int) -> None:
    _cerrar_paneles()
    st.session_state.fiado_id = pedido_id
    st.session_state.deshacer = None


def cb_cerrar_fiado() -> None:
    st.session_state.fiado_id = None


def cb_confirmar_fiado(pedido_id: int) -> None:
    monto = int(st.session_state.get(f"monto_{pedido_id}", 0) or 0)
    cuando: date = st.session_state.get(f"cuando_{pedido_id}", hoy())
    if monto <= 0:
        avisar("Escriba cuánto le deben.", error=True)
        return
    antes = repo.obtener_pedido(pedido_id)
    cambios = {
        "estado": db.POR_COBRAR,
        "monto_deuda": monto,
        "monto_venta": 0,
        "fecha_cobro": cuando.isoformat(),
        "fecha_cierre": hoy().isoformat(),
    }
    try:
        repo.actualizar_pedido(pedido_id, cambios)
    except Exception:
        avisar(ERROR_RED, error=True)
        return
    _registrar_deshacer(antes, cambios, f"Fiado anotado: {pesos(monto)}")
    st.session_state.fiado_id = None
    st.session_state.aviso = None


def cb_ya_pago(pedido_id: int) -> None:
    antes = repo.obtener_pedido(pedido_id)
    cambios = {"estado": db.PAGADO, "fecha_pago": hoy().isoformat()}
    try:
        repo.actualizar_pedido(pedido_id, cambios)
    except Exception:
        avisar(ERROR_RED, error=True)
        return
    _registrar_deshacer(antes, cambios, f"Cobrado: {pesos(antes['monto_deuda'])}")
    st.session_state.aviso = None


# --- Borrar un pedido (pide confirmación y se puede deshacer) ---
def cb_pedir_borrar(pedido_id: int) -> None:
    _cerrar_paneles()
    st.session_state.borrar_id = pedido_id
    st.session_state.deshacer = None


def cb_cancelar_borrar() -> None:
    st.session_state.borrar_id = None
    st.session_state.borrar_dia = None


def cb_borrar_pedido(pedido_id: int) -> None:
    antes = repo.obtener_pedido(pedido_id)
    st.session_state.borrar_id = None
    if not antes:
        return
    cambios = {"estado": ELIMINADO}
    try:
        repo.actualizar_pedido(pedido_id, cambios)
    except Exception:
        avisar(ERROR_RED, error=True)
        return
    _registrar_deshacer(antes, cambios, "Pedido borrado")
    st.session_state.aviso = None


# --- Borrar un día completo (todos sus pedidos) ---
def cb_pedir_borrar_dia(dia_iso: str) -> None:
    _cerrar_paneles()
    st.session_state.borrar_dia = dia_iso
    st.session_state.deshacer = None


def cb_borrar_dia(dia_iso: str) -> None:
    st.session_state.borrar_dia = None
    del_dia = [p for p in repo.listar_pedidos()
               if p["fecha_jornada"] == dia_iso and p["estado"] != ELIMINADO]
    cambios = {"estado": ELIMINADO}
    hechos: list[dict] = []
    try:
        for p in del_dia:
            repo.actualizar_pedido(p["id"], cambios)
            hechos.append(p)
    except Exception:
        avisar(ERROR_RED, error=True)
    if hechos:
        d = date.fromisoformat(dia_iso)
        _registrar_deshacer(hechos, cambios, f"Se borró el {fecha_larga(d).lower()}")


def cb_deshacer() -> None:
    d = st.session_state.deshacer
    if d:
        try:
            for item in d["items"]:
                repo.actualizar_pedido(item["id"], item["antes"])
            avisar("Listo, quedó como antes.")
        except Exception:
            avisar(ERROR_RED, error=True)
    st.session_state.deshacer = None


# --- Precios: se guardan al instante, sin botón "Guardar" ---
def _guardar_config(**cambios) -> None:
    """Lee la configuración recién guardada y cambia solo lo pedido."""
    cfg = repo.leer_config()
    precios = logica.precios_desde_config(cfg)
    valores = {f"precio_{t}": int(precios[t]) for t in db.TAMANOS}
    valores["ciudad"] = logica.ciudad_desde_config(cfg)
    valores.update(cambios)
    repo.guardar_config(valores)


def cb_precio_paso(tamano: int, delta: int) -> None:
    try:
        actual = logica.precios_desde_config(repo.leer_config())[tamano]
        _guardar_config(**{f"precio_{tamano}": max(0, int(actual) + delta)})
    except Exception:
        avisar(ERROR_RED, error=True)
        return
    st.session_state.precio_ok = tamano


def cb_precio_escrito(tamano: int) -> None:
    valor = int(st.session_state.get(f"pr_{tamano}") or 0)
    try:
        _guardar_config(**{f"precio_{tamano}": max(0, valor)})
    except Exception:
        avisar(ERROR_RED, error=True)
        return
    st.session_state.precio_ok = tamano


def cb_guardar_ciudad() -> None:
    try:
        _guardar_config(ciudad=st.session_state.aj_ciudad.strip())
    except Exception:
        avisar(ERROR_RED, error=True)
        return
    avisar("Ciudad guardada")


# ══════════════════════════════════════════════════════════════════════════════
# 6. PIEZAS DE PANTALLA
# ══════════════════════════════════════════════════════════════════════════════
def boton(texto: str, zona: str, icono_m: str | None = None, **kwargs) -> None:
    """Botón dentro de un contenedor con key, para poder pintarlo con CSS."""
    with st.container(key=zona):
        st.button(texto, key=f"btn_{zona}", icon=icono_m, **kwargs)


def html_limpio(texto: str) -> None:
    """Quita la sangría: en Markdown, 4 espacios al inicio = bloque de código."""
    st.markdown(" ".join(linea.strip() for linea in texto.splitlines()), unsafe_allow_html=True)


def encabezado() -> None:
    tamanos = list(db.TAMANOS)
    logo = 11 if 11 in tamanos else tamanos[0]
    html_limpio(f"""
        <div class='marca'>{img_cilindro(logo, alto=58)}
          <div><div class='nombre'>Willy Gas</div>
          <p class='fecha-hoy'>{fecha_larga(hoy())}</p></div>
        </div>""")


def mostrar_avisos() -> None:
    if st.session_state.aviso:
        texto, es_error = st.session_state.aviso
        clase, ico = ("aviso error", icono("alerta", "#B3261E")) if es_error else ("aviso", icono("check", "#12502D"))
        st.markdown(f"<div class='{clase}'>{ico}{esc(texto)}</div>", unsafe_allow_html=True)
        st.session_state.aviso = None  # se muestra una sola vez
    if st.session_state.deshacer:
        st.markdown(f"<div class='aviso'>{icono('check', '#12502D')}"
                    f"{esc(st.session_state.deshacer['texto'])}</div>", unsafe_allow_html=True)
        boton("Me equivoqué, deshacer", "zona_deshacer", ":material/undo:", on_click=cb_deshacer)


def navegacion() -> None:
    """Cuatro botones siempre visibles: nada escondido en menús."""
    vista = st.session_state.vista
    opciones = [
        ("pedidos", "Pedidos", ":material/list_alt:"),
        ("resumen", "Días", ":material/calendar_month:"),
        ("deudas", "Deben", ":material/account_balance_wallet:"),
        ("precios", "Precios", ":material/sell:"),
    ]
    with st.container(key="navegacion"):
        columnas = st.columns(len(opciones))
        for col, (clave, texto, ico) in zip(columnas, opciones):
            with col:
                st.button(
                    texto, key=f"nav_{clave}", icon=ico,
                    type="primary" if vista == clave else "secondary",
                    on_click=cb_ir_a, args=(clave,),
                )


def chips_cilindros(pedido: dict) -> str:
    chips = "".join(
        f"<span class='chip'>{img_cilindro(t, alto=42)}{n} × {t} kg</span>"
        for t, n in logica.cilindros_de(pedido).items()
    )
    return f"<div class='cilindros'>{chips}</div>"


def boton_mapa(pedido: dict) -> None:
    with st.container(key=f"zona_ir_{pedido['id']}"):
        st.link_button("Mapa", logica.url_google_maps(pedido["direccion"], CIUDAD),
                       icon=":material/directions:")


def confirmar_borrado(pid: int, pregunta: str, detalle: str = "") -> None:
    extra = f"<small>{detalle}</small>" if detalle else ""
    st.markdown(f"<div class='confirmar'>{pregunta}{extra}</div>", unsafe_allow_html=True)
    si, no = st.columns(2)
    with si:
        boton("Sí, borrar", f"zona_si_{pid}", ":material/delete:",
              on_click=cb_borrar_pedido, args=(pid,))
    with no:
        boton("No", f"zona_no_borrar_{pid}", ":material/close:", on_click=cb_cancelar_borrar)


def fila_mapa_borrar(p: dict) -> None:
    izq, der = st.columns(2)
    with izq:
        boton_mapa(p)
    with der:
        boton("Borrar", f"zona_borrar_{p['id']}", ":material/delete:",
              on_click=cb_pedir_borrar, args=(p["id"],))


# ══════════════════════════════════════════════════════════════════════════════
# 7. PANTALLAS
# ══════════════════════════════════════════════════════════════════════════════
def pantalla_comenzar_dia(pedidos: list[dict]) -> None:
    pendientes = sum(1 for p in pedidos if p["estado"] == db.PENDIENTE)
    deudas = sum(1 for p in pedidos if p["estado"] == db.POR_COBRAR)
    st.markdown(f"<p class='titulo-seccion'>{icono('sol', '#8F5B00')}¡Buenos días, Willy!</p>",
                unsafe_allow_html=True)
    boton("Comenzar el día", "zona_dia", ":material/wb_sunny:", on_click=cb_iniciar_dia)
    if pendientes or deudas:
        partes = []
        if pendientes:
            partes.append(f"{icono('reloj')}Quedaron <b>{pendientes}</b> pedidos sin entregar.")
        if deudas:
            partes.append(f"{icono('libreta')}Hay <b>{deudas}</b> clientes que deben.")
        st.markdown(f"<div class='vacio'>{'<br>'.join(partes)}</div>", unsafe_allow_html=True)


def formulario_pedido() -> None:
    st.markdown("<p class='titulo-seccion'>Nuevo pedido</p>", unsafe_allow_html=True)

    # --- Selector de cilindros: − cantidad + (botones grandes, sin teclado) ---
    for t in db.TAMANOS:
        n = st.session_state[f"cant_{t}"]
        html_limpio(f"""
            <div class='fila-cil'>{img_cilindro(t, ancho=46)}
              <div><div class='nombre-cil'>{t} kg</div>
              <div class='precio-cil'>{pesos(PRECIOS[t])} cada uno</div></div>
            </div>""")
        menos, cantidad, mas = st.columns(3)
        with menos:
            boton("", f"zona_menos_{t}", ":material/remove:", on_click=cb_cantidad, args=(t, -1),
                  help=f"Quitar uno de {t} kg")
        with cantidad:
            clase = "contador activo" if n else "contador"
            st.markdown(f"<div class='{clase}'>{n}</div>", unsafe_allow_html=True)
        with mas:
            boton("", f"zona_mas_{t}", ":material/add:", on_click=cb_cantidad, args=(t, +1),
                  help=f"Sumar uno de {t} kg")

    # --- Dirección: un text_input normal deja usar el micrófono del teclado ---
    st.text_input(
        ":material/location_on: Dirección",
        key="dir_nueva",
        placeholder="Toque aquí y hable",
        autocomplete="street-address",
    )
    st.text_input(
        ":material/person: Nombre o seña (opcional)",
        key="nota_nueva",
        placeholder="Ej: Sra. Rosa, casa verde",
    )

    total = sum(st.session_state[f"cant_{t}"] * PRECIOS[t] for t in db.TAMANOS)
    if total:
        st.markdown(f"<div class='total-form'>Valor: {pesos(total)}</div>", unsafe_allow_html=True)

    if st.session_state.error_form:
        st.markdown(f"<div class='aviso error'>{icono('alerta', '#B3261E')}"
                    f"{esc(st.session_state.error_form)}</div>", unsafe_allow_html=True)

    boton("Guardar pedido", "zona_guardar", ":material/check:", on_click=cb_guardar_pedido)
    boton("Cancelar", "zona_cancelar", ":material/close:", on_click=cb_cerrar_form)


def tarjeta_pedido(p: dict) -> None:
    pid = p["id"]
    es_viejo = p["fecha_jornada"] != hoy().isoformat()
    with st.container(key=f"card_viejo_{pid}" if es_viejo else f"card_{pid}"):
        hora = p["creado_en"][11:16]
        etiqueta = (f"<span class='etiqueta-vieja'>{icono('calendario', '#8F5B00')}"
                    f"Del {fecha_corta(p['fecha_jornada'])}</span>" if es_viejo else "")
        nota = f"<p class='nota'>{icono('persona')}{esc(p['nota'])}</p>" if p["nota"] else ""
        st.markdown(
            f"<p class='direccion'>{icono('pin', '#18212B')}{esc(p['direccion'])}</p>{nota}"
            f"{chips_cilindros(p)}"
            f"<div class='meta'>{etiqueta}<span>{icono('reloj')}{hora}</span>"
            f"<span>{icono('billete')}{pesos(logica.valor_pedido(p, PRECIOS))}</span></div>",
            unsafe_allow_html=True,
        )

        if st.session_state.borrar_id == pid:
            confirmar_borrado(pid, "¿Borrar este pedido?")
        elif st.session_state.fiado_id == pid:
            # --- Menú rápido de fiado ---
            st.number_input(
                ":material/payments: ¿Cuánto debe?",
                min_value=0, step=1000,
                value=logica.valor_pedido(p, PRECIOS),
                key=f"monto_{pid}",
            )
            st.date_input(
                ":material/calendar_today: ¿Cuándo cobrar?",
                value=hoy() + timedelta(days=7),
                min_value=hoy(),
                format="DD/MM/YYYY",
                key=f"cuando_{pid}",
            )
            boton("Anotar fiado", f"zona_confirma_{pid}", ":material/check:",
                  on_click=cb_confirmar_fiado, args=(pid,))
            boton("Volver", f"zona_volver_{pid}", ":material/arrow_back:", on_click=cb_cerrar_fiado)
        else:
            # --- Acciones: la más usada (Entregado) ocupa todo el ancho ---
            boton("Entregado", f"zona_ok_{pid}", ":material/check_circle:",
                  on_click=cb_cambiar_estado, args=(pid, db.ENTREGADO))
            izq, der = st.columns(2)
            with izq:
                boton("No entregué", f"zona_no_{pid}", ":material/cancel:",
                      on_click=cb_cambiar_estado, args=(pid, db.NO_ENTREGADO))
            with der:
                boton("Fiado", f"zona_fia_{pid}", ":material/payments:",
                      on_click=cb_abrir_fiado, args=(pid,))
            fila_mapa_borrar(p)


def vista_pedidos(pedidos: list[dict]) -> None:
    if st.session_state.mostrar_form:
        formulario_pedido()
        return  # mientras anota, no se muestra nada más: cero distracciones

    pendientes = [p for p in pedidos if p["estado"] == db.PENDIENTE]
    st.markdown(f"<p class='titulo-seccion'>Por entregar: {len(pendientes)}</p>",
                unsafe_allow_html=True)
    if not pendientes:
        st.markdown(f"<div class='vacio'>{icono('check', '#1B7A45')}No hay pedidos pendientes.<br>"
                    "Toque <b>Agregar pedido</b> (abajo) cuando lo llamen.</div>",
                    unsafe_allow_html=True)
    for p in pendientes:
        tarjeta_pedido(p)

    # Botón flotante (el CSS lo fija abajo de la pantalla). Va al final del
    # código para que no empuje las tarjetas, pero siempre se ve.
    boton("Agregar pedido", "zona_agregar", ":material/add_circle:", on_click=cb_abrir_form)


NOMBRE_ESTADO = {
    db.PENDIENTE: ("Por entregar", "#56616E"),
    db.ENTREGADO: ("Entregado", "#1B7A45"),
    db.NO_ENTREGADO: ("No entregado", "#56616E"),
    db.POR_COBRAR: ("Fiado", "#8F5B00"),
    db.PAGADO: ("Fiado ya pagado", "#1B7A45"),
}


def vista_resumen(pedidos: list[dict]) -> None:
    dia = st.date_input(":material/calendar_today: Ver el día", value=hoy(), max_value=hoy(),
                        format="DD/MM/YYYY", key="dia_resumen")
    dia_iso = dia.isoformat()
    r = logica.resumen_del_dia(pedidos, dia_iso)

    detalle_cil = "  ".join(f"{t} kg: {n}" for t, n in r["por_tamano"].items() if n) or "ninguno"
    html_limpio(f"""
        <div class='grilla'>
          <div class='dato ancho verde'>
            <div class='icono'><img src='{_uri_icono("billete", "#1B7A45")}' alt=''></div>
            <div class='valor'>{pesos(r['plata_en_mano'])}</div>
            <div class='texto'>Plata recibida ({pesos(r['ventas_contado'])} ventas
              + {pesos(r['cobros_de_deudas'])} deudas cobradas)</div>
          </div>
          <div class='dato ancho'>
            <div class='icono'><img src='{_uri_icono("pila", "#18212B")}' alt=''></div>
            <div class='valor'>{r['total_cilindros']} cilindros</div>
            <div class='texto'>{detalle_cil}</div>
          </div>
          <div class='dato ambar'>
            <div class='icono'><img src='{_uri_icono("libreta", "#8F5B00")}' alt=''></div>
            <div class='valor'>{pesos(r['fiado_del_dia'])}</div>
            <div class='texto'>Fiado este día</div>
          </div>
          <div class='dato rojo'>
            <div class='icono'><img src='{_uri_icono("alerta", "#B3261E")}' alt=''></div>
            <div class='valor'>{pesos(r['por_cobrar_total'])}</div>
            <div class='texto'>Le deben en total ({r['deudores']})</div>
          </div>
          <div class='dato'>
            <div class='icono'><img src='{_uri_icono("x", "#56616E")}' alt=''></div>
            <div class='valor'>{r['no_entregados']}</div>
            <div class='texto'>No entregados</div>
          </div>
          <div class='dato'>
            <div class='icono'><img src='{_uri_icono("reloj", "#56616E")}' alt=''></div>
            <div class='valor'>{r['pendientes']}</div>
            <div class='texto'>Pendientes ahora</div>
          </div>
        </div>""")

    # --- Pedidos del día, cada uno con su botón Borrar ---
    del_dia = [p for p in pedidos if p["fecha_jornada"] == dia_iso]
    if not del_dia:
        return
    with st.expander(f"Pedidos de este día ({len(del_dia)})", icon=":material/list_alt:",
                     expanded=st.session_state.borrar_id in {p["id"] for p in del_dia}):
        for p in del_dia:
            pid = p["id"]
            nombre, color = NOMBRE_ESTADO.get(p["estado"], (p["estado"], "#56616E"))
            cil = ", ".join(f"{n} × {t} kg" for t, n in logica.cilindros_de(p).items())
            with st.container(key=f"fila_{pid}"):
                st.markdown(
                    f"<div class='fila-pedido'><b>{esc(p['direccion'])}</b><br>{cil}<br>"
                    f"<span class='punto' style='background:{color}'></span>{nombre}</div>",
                    unsafe_allow_html=True,
                )
                if st.session_state.borrar_id == pid:
                    confirmar_borrado(pid, "¿Borrar este pedido?")
                else:
                    boton("Borrar pedido", f"zona_borrar_{pid}", ":material/delete:",
                          on_click=cb_pedir_borrar, args=(pid,))

    # --- Borrar el día completo ---
    if st.session_state.borrar_dia == dia_iso:
        fiados = sum(1 for p in del_dia if p["estado"] == db.POR_COBRAR)
        n = len(del_dia)
        detalle = "Se borrará 1 pedido." if n == 1 else f"Se borrarán {n} pedidos."
        if fiados:
            detalle += f" Incluye {fiados} fiado(s) sin cobrar."
        st.markdown(f"<div class='confirmar'>¿Borrar todo el {fecha_larga(dia).lower()}?"
                    f"<small>{detalle}</small></div>", unsafe_allow_html=True)
        si, no = st.columns(2)
        with si:
            boton("Sí, borrar", "zona_si_dia", ":material/delete:",
                  on_click=cb_borrar_dia, args=(dia_iso,))
        with no:
            boton("No", "zona_no_dia", ":material/close:", on_click=cb_cancelar_borrar)
    else:
        boton("Borrar este día", "zona_borrar_dia", ":material/delete_sweep:",
              on_click=cb_pedir_borrar_dia, args=(dia_iso,))


def vista_deudas(pedidos: list[dict]) -> None:
    deudas = sorted((p for p in pedidos if p["estado"] == db.POR_COBRAR),
                    key=lambda p: (p["fecha_cobro"], p["id"]))
    total = sum(p["monto_deuda"] for p in deudas)
    st.markdown(f"<p class='titulo-seccion'>Le deben: {pesos(total)}</p>", unsafe_allow_html=True)
    if not deudas:
        st.markdown(f"<div class='vacio'>{icono('check', '#1B7A45')}Nadie le debe plata.</div>",
                    unsafe_allow_html=True)
        return

    hoy_iso = hoy().isoformat()
    for p in deudas:
        pid = p["id"]
        atrasado = p["fecha_cobro"] and p["fecha_cobro"] < hoy_iso
        if atrasado:
            estado, color = "Atrasado", "#B3261E"
        elif p["fecha_cobro"] == hoy_iso:
            estado, color = "Cobrar hoy", "#C98A00"
        else:
            estado, color = "Al día", "#1B7A45"
        with st.container(key=f"card_atrasado_{pid}" if atrasado else f"card_deuda_{pid}"):
            nota = f"<p class='nota'>{icono('persona')}{esc(p['nota'])}</p>" if p["nota"] else ""
            st.markdown(
                f"<p class='direccion'>{icono('pin', '#18212B')}{esc(p['direccion'])}</p>{nota}"
                f"<p class='monto-deuda'>{pesos(p['monto_deuda'])}</p>"
                f"<div class='meta'><span><span class='punto' style='background:{color}'></span>{estado}</span>"
                f"<span>{icono('calendario')}Cobrar el {fecha_corta(p['fecha_cobro'])}</span>"
                f"<span>{icono('libreta')}Se fió el {fecha_corta(p['fecha_cierre'])}</span></div>",
                unsafe_allow_html=True,
            )
            if st.session_state.borrar_id == pid:
                confirmar_borrado(pid, "¿Borrar esta deuda?", "Desaparece de la lista de los que deben.")
            else:
                boton("Ya pagó", f"zona_pago_{pid}", ":material/payments:",
                      on_click=cb_ya_pago, args=(pid,))
                fila_mapa_borrar(p)


def vista_precios(todos: list[dict]) -> None:
    st.markdown("<p class='titulo-seccion'>Precios</p>"
                "<p class='subtitulo'>Los cambios se guardan solos, al instante.</p>",
                unsafe_allow_html=True)
    for t in db.TAMANOS:
        # El cuadro siempre muestra el precio guardado
        st.session_state[f"pr_{t}"] = int(PRECIOS[t])
        with st.container(key=f"card_precio_{t}"):
            guardado = ("<div class='guardado'>" + icono("check", "#1B7A45") + "Guardado</div>"
                        if st.session_state.precio_ok == t else "")
            html_limpio(f"""
                <div class='fila-cil'>{img_cilindro(t, ancho=62)}
                  <div><div class='nombre-cil'>Cilindro {t} kg</div>
                  <div class='precio-grande'>{pesos(PRECIOS[t])}</div>{guardado}</div>
                </div>""")
            bajar, subir = st.columns(2)
            with bajar:
                boton("$500", f"zona_bajar_{t}", ":material/remove:",
                      on_click=cb_precio_paso, args=(t, -500))
            with subir:
                boton("$500", f"zona_subir_{t}", ":material/add:",
                      on_click=cb_precio_paso, args=(t, +500))
            st.number_input("Escribir otro precio", min_value=0, step=500,
                            key=f"pr_{t}", on_change=cb_precio_escrito, args=(t,))
    st.session_state.precio_ok = None

    with st.expander("Más ajustes", icon=":material/settings:"):
        st.text_input("Ciudad para el mapa", value=CIUDAD, key="aj_ciudad")
        boton("Guardar ciudad", "zona_guardar_ciudad", ":material/check:", on_click=cb_guardar_ciudad)
        st.download_button(
            "Descargar respaldo (Excel)",
            data=csv_respaldo(todos),
            file_name=f"willy_gas_{hoy().isoformat()}.csv",
            mime="text/csv",
            icon=":material/download:",
        )
        st.caption(f"Datos guardados en: {repo.nombre}")


def csv_respaldo(pedidos: list[dict]) -> bytes:
    buffer = io.StringIO()
    escritor = csv.DictWriter(buffer, fieldnames=db.CAMPOS_PEDIDO, extrasaction="ignore")
    escritor.writeheader()
    escritor.writerows(pedidos)
    return buffer.getvalue().encode("utf-8-sig")  # utf-8-sig: Excel muestra bien las tildes


# ══════════════════════════════════════════════════════════════════════════════
# 8. FLUJO PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════
encabezado()
TODOS = repo.listar_pedidos()                                  # incluye borrados (para el respaldo)
PEDIDOS = [p for p in TODOS if p.get("estado") != ELIMINADO]   # lo que se ve en pantalla

if not repo.jornada_existe(hoy().isoformat()):
    pantalla_comenzar_dia(PEDIDOS)
    st.stop()

if not st.session_state.mostrar_form:
    navegacion()
mostrar_avisos()

if st.session_state.vista == "resumen":
    vista_resumen(PEDIDOS)
elif st.session_state.vista == "deudas":
    vista_deudas(PEDIDOS)
elif st.session_state.vista == "precios":
    vista_precios(TODOS)
else:
    vista_pedidos(PEDIDOS)
