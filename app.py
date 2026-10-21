"""
app.py — Interfaz de "Willy Gas" (Streamlit, pensada para celular).

Ejecutar en el computador:   streamlit run app.py

Estructura del proyecto:
  app.py      → pantallas y botones (este archivo)
  estilos.py  → CSS inyectado (botones gigantes, alto contraste)
  logica.py   → cálculos del negocio (precios, resumen del día)
  db.py       → guardar/leer datos (SQLite local o Google Sheets)
"""
from __future__ import annotations

import csv
import hmac
import html
import io
import os
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import streamlit as st

import db
import logica
from estilos import inyectar_css

# ══════════════════════════════════════════════════════════════════════════════
# 1. CONFIGURACIÓN DE LA PÁGINA
# ══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Willy Gas",
    page_icon="🛢️",
    layout="centered",
    initial_sidebar_state="collapsed",
)
inyectar_css()

# Los servidores en la nube usan hora UTC: se fuerza la hora de Chile para que
# "hoy" cambie a medianoche en Santiago y no a las 21:00.
ZONA = ZoneInfo(os.getenv("WILLY_TZ", "America/Santiago"))
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


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
    return "$" + f"{int(monto):,}".replace(",", ".")


def esc(texto: str) -> str:
    """Escapa lo que escribe el usuario antes de meterlo en HTML."""
    return html.escape(str(texto))


# ══════════════════════════════════════════════════════════════════════════════
# 2. CONEXIÓN A LA BASE DE DATOS
#    Si hay credenciales de Google en .streamlit/secrets.toml → Google Sheets.
#    Si no → SQLite local (archivo willy_gas.db).
# ══════════════════════════════════════════════════════════════════════════════
def _secreto(seccion: str):
    try:
        return st.secrets[seccion]
    except Exception:
        return None


@st.cache_resource(show_spinner="Conectando… ⏳")
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
        st.markdown("<div class='vacio'>🔒 Abra Willy Gas desde el ícono de su celular.</div>",
                    unsafe_allow_html=True)
        st.stop()

try:
    repo = obtener_repo()
except Exception as e:  # sin internet o credenciales malas
    st.markdown(
        "<div class='aviso error'>⚠️ No se pudo conectar con los datos. "
        "Revise que haya internet y vuelva a abrir la app.</div>",
        unsafe_allow_html=True,
    )
    st.caption(f"Detalle técnico: {e}")
    st.stop()


# ══════════════════════════════════════════════════════════════════════════════
# 3. ESTADO DE LA SESIÓN (solo cosas de pantalla; los datos viven en la BD)
# ══════════════════════════════════════════════════════════════════════════════
def iniciar_estado() -> None:
    por_defecto = {
        "vista": "pedidos",       # pedidos | resumen | deudas
        "mostrar_form": False,    # formulario de nuevo pedido abierto
        "fiado_id": None,         # pedido con el panel de fiado abierto
        "deshacer": None,         # última acción, para poder revertirla
        "aviso": None,            # mensaje verde grande
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
# 4. ACCIONES (callbacks). Se ejecutan ANTES de redibujar la pantalla,
#    así un solo toque basta y la pantalla siempre muestra el dato guardado.
# ══════════════════════════════════════════════════════════════════════════════
ERROR_RED = "⚠️ No se pudo guardar. Revise internet y toque de nuevo."


def _registrar_deshacer(pedido_antes: dict, cambios: dict, texto: str) -> None:
    st.session_state.deshacer = {
        "id": pedido_antes["id"],
        "antes": {k: pedido_antes[k] for k in cambios},
        "texto": texto,
    }


def cb_iniciar_dia() -> None:
    repo.iniciar_jornada(hoy().isoformat(), ahora().isoformat(timespec="seconds"))
    st.session_state.aviso = "☀️ ¡Buen día! Ya puede anotar pedidos."


def cb_ir_a(vista: str) -> None:
    st.session_state.vista = vista
    st.session_state.fiado_id = None
    st.session_state.mostrar_form = False


def cb_abrir_form() -> None:
    st.session_state.mostrar_form = True
    st.session_state.deshacer = None


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
        st.session_state.error_form = "🛢️ Toque ➕ en al menos un cilindro."
        return
    if not direccion:
        st.session_state.error_form = "📍 Falta la dirección. Toque el cuadro y hable 🎤"
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
    st.session_state.aviso = "✅ Pedido guardado"


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
        st.session_state.aviso = ERROR_RED
        return
    texto = "✅ Marcado como entregado" if estado == db.ENTREGADO else "❌ Marcado como no entregado"
    _registrar_deshacer(antes, cambios, texto)
    st.session_state.aviso = None


def cb_abrir_fiado(pedido_id: int) -> None:
    st.session_state.fiado_id = pedido_id
    st.session_state.deshacer = None


def cb_cerrar_fiado() -> None:
    st.session_state.fiado_id = None


def cb_confirmar_fiado(pedido_id: int) -> None:
    monto = int(st.session_state.get(f"monto_{pedido_id}", 0) or 0)
    cuando: date = st.session_state.get(f"cuando_{pedido_id}", hoy())
    if monto <= 0:
        st.session_state.aviso = "💰 Escriba cuánto le deben."
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
        st.session_state.aviso = ERROR_RED
        return
    _registrar_deshacer(antes, cambios, f"💰 Fiado anotado: {pesos(monto)}")
    st.session_state.fiado_id = None
    st.session_state.aviso = None


def cb_ya_pago(pedido_id: int) -> None:
    antes = repo.obtener_pedido(pedido_id)
    cambios = {"estado": db.PAGADO, "fecha_pago": hoy().isoformat()}
    try:
        repo.actualizar_pedido(pedido_id, cambios)
    except Exception:
        st.session_state.aviso = ERROR_RED
        return
    _registrar_deshacer(antes, cambios, f"💵 Cobrado: {pesos(antes['monto_deuda'])}")
    st.session_state.aviso = None


def cb_deshacer() -> None:
    d = st.session_state.deshacer
    if d:
        repo.actualizar_pedido(d["id"], d["antes"])
        st.session_state.aviso = "↩️ Listo, quedó como antes."
    st.session_state.deshacer = None


def cb_guardar_ajustes() -> None:
    valores = {f"precio_{t}": int(st.session_state[f"aj_precio_{t}"]) for t in db.TAMANOS}
    valores["ciudad"] = st.session_state.aj_ciudad.strip()
    repo.guardar_config(valores)
    st.session_state.aviso = "⚙️ Ajustes guardados"


# ══════════════════════════════════════════════════════════════════════════════
# 5. PIEZAS DE PANTALLA
# ══════════════════════════════════════════════════════════════════════════════
def boton(texto: str, zona: str, **kwargs) -> None:
    """Botón dentro de un contenedor con key, para poder pintarlo con CSS."""
    with st.container(key=zona):
        st.button(texto, key=f"btn_{zona}", **kwargs)


def encabezado() -> None:
    st.markdown(
        f"<div class='marca'><h1>🛢️ Willy Gas</h1></div>"
        f"<p class='fecha-hoy'>📅 {fecha_larga(hoy())}</p>",
        unsafe_allow_html=True,
    )


def mostrar_avisos() -> None:
    if st.session_state.aviso:
        st.markdown(f"<div class='aviso'>{esc(st.session_state.aviso)}</div>",
                    unsafe_allow_html=True)
        st.session_state.aviso = None  # se muestra una sola vez
    if st.session_state.deshacer:
        st.markdown(f"<div class='aviso'>{esc(st.session_state.deshacer['texto'])}</div>",
                    unsafe_allow_html=True)
        boton("↩️ Me equivoqué, deshacer", "zona_deshacer", on_click=cb_deshacer)


def navegacion() -> None:
    """Tres botones siempre visibles: nada escondido en menús."""
    vista = st.session_state.vista
    opciones = [("pedidos", "📋 Pedidos"), ("resumen", "📊 Hoy"), ("deudas", "💰 Deben")]
    columnas = st.columns(3)
    for col, (clave, texto) in zip(columnas, opciones):
        with col:
            st.button(
                texto, key=f"nav_{clave}",
                type="primary" if vista == clave else "secondary",
                on_click=cb_ir_a, args=(clave,),
            )


def chips_cilindros(pedido: dict) -> str:
    chips = "".join(
        f"<span class='chip'>{n} × 🛢️ {t} kg</span>"
        for t, n in logica.cilindros_de(pedido).items()
    )
    return f"<div class='cilindros'>{chips}</div>"


def boton_mapa(pedido: dict) -> None:
    with st.container(key=f"zona_ir_{pedido['id']}"):
        st.link_button("🗺️ Ir", logica.url_google_maps(pedido["direccion"], CIUDAD))


# ══════════════════════════════════════════════════════════════════════════════
# 6. PANTALLAS
# ══════════════════════════════════════════════════════════════════════════════
def pantalla_comenzar_dia(pedidos: list[dict]) -> None:
    pendientes = sum(1 for p in pedidos if p["estado"] == db.PENDIENTE)
    deudas = sum(1 for p in pedidos if p["estado"] == db.POR_COBRAR)
    st.markdown("<p class='titulo-seccion'>☀️ ¡Buenos días, Willy!</p>", unsafe_allow_html=True)
    boton("☀️ Comenzar nuevo día", "zona_dia", on_click=cb_iniciar_dia)
    if pendientes or deudas:
        partes = []
        if pendientes:
            partes.append(f"⏳ Quedaron <b>{pendientes}</b> pedidos sin entregar.")
        if deudas:
            partes.append(f"💰 Hay <b>{deudas}</b> clientes que deben.")
        st.markdown(f"<div class='vacio'>{'<br>'.join(partes)}</div>", unsafe_allow_html=True)


def formulario_pedido() -> None:
    st.markdown("<p class='titulo-seccion'>➕ Nuevo pedido</p>", unsafe_allow_html=True)

    # --- Selector de cilindros: ➖ cantidad ➕ (botones grandes, sin teclado) ---
    for t in db.TAMANOS:
        n = st.session_state[f"cant_{t}"]
        st.markdown(f"<p class='nombre-cil'>🛢️ {t} kg</p>", unsafe_allow_html=True)
        menos, cantidad, mas = st.columns(3)
        with menos:
            boton("➖", f"zona_menos_{t}", on_click=cb_cantidad, args=(t, -1))
        with cantidad:
            clase = "contador activo" if n else "contador"
            st.markdown(f"<div class='{clase}'>{n}</div>", unsafe_allow_html=True)
        with mas:
            boton("➕", f"zona_mas_{t}", on_click=cb_cantidad, args=(t, +1))

    # --- Dirección: un text_input normal deja usar el 🎤 del teclado del celular ---
    st.text_input(
        "📍 Dirección",
        key="dir_nueva",
        placeholder="Toque aquí y hable 🎤",
        autocomplete="street-address",
    )
    st.text_input(
        "👤 Nombre o seña (opcional)",
        key="nota_nueva",
        placeholder="Ej: Sra. Rosa, casa verde",
    )

    total = sum(st.session_state[f"cant_{t}"] * PRECIOS[t] for t in db.TAMANOS)
    if total:
        st.markdown(f"<div class='total-form'>💵 Valor: {pesos(total)}</div>",
                    unsafe_allow_html=True)

    if st.session_state.error_form:
        st.markdown(f"<div class='aviso error'>{esc(st.session_state.error_form)}</div>",
                    unsafe_allow_html=True)

    boton("💾 Guardar pedido", "zona_guardar", on_click=cb_guardar_pedido)
    boton("✖️ Cancelar", "zona_cancelar", on_click=cb_cerrar_form)


def tarjeta_pedido(p: dict) -> None:
    pid = p["id"]
    es_viejo = p["fecha_jornada"] != hoy().isoformat()
    with st.container(key=f"card_viejo_{pid}" if es_viejo else f"card_{pid}"):
        hora = p["creado_en"][11:16]
        etiqueta = (f"<span class='etiqueta-vieja'>📅 Del {fecha_corta(p['fecha_jornada'])}</span> "
                    if es_viejo else "")
        nota = f"<p class='nota'>👤 {esc(p['nota'])}</p>" if p["nota"] else ""
        st.markdown(
            f"<p class='direccion'>📍 {esc(p['direccion'])}</p>{nota}"
            f"{chips_cilindros(p)}"
            f"<p class='meta'>{etiqueta}🕐 {hora} · 💵 {pesos(logica.valor_pedido(p, PRECIOS))}</p>",
            unsafe_allow_html=True,
        )
        boton_mapa(p)

        if st.session_state.fiado_id == pid:
            # --- Menú rápido de fiado ---
            st.number_input(
                "💰 ¿Cuánto debe?",
                min_value=0, step=1000,
                value=logica.valor_pedido(p, PRECIOS),
                key=f"monto_{pid}",
            )
            st.date_input(
                "📅 ¿Cuándo cobrar?",
                value=hoy() + timedelta(days=7),
                min_value=hoy(),
                format="DD/MM/YYYY",
                key=f"cuando_{pid}",
            )
            boton("✅ Anotar fiado", f"zona_confirma_{pid}", on_click=cb_confirmar_fiado, args=(pid,))
            boton("↩️ Volver", f"zona_volver_{pid}", on_click=cb_cerrar_fiado)
        else:
            # --- Acciones: la más usada (Entregado) ocupa todo el ancho ---
            boton("✅ Entregado", f"zona_ok_{pid}",
                  on_click=cb_cambiar_estado, args=(pid, db.ENTREGADO))
            izq, der = st.columns(2)
            with izq:
                boton("❌ No entregué", f"zona_no_{pid}",
                      on_click=cb_cambiar_estado, args=(pid, db.NO_ENTREGADO))
            with der:
                boton("💰 Fiado", f"zona_fia_{pid}", on_click=cb_abrir_fiado, args=(pid,))


def vista_pedidos(pedidos: list[dict]) -> None:
    if st.session_state.mostrar_form:
        formulario_pedido()
        return  # mientras anota, no se muestra nada más: cero distracciones

    pendientes = [p for p in pedidos if p["estado"] == db.PENDIENTE]
    st.markdown(f"<p class='titulo-seccion'>⏳ Por entregar: {len(pendientes)}</p>",
                unsafe_allow_html=True)
    if not pendientes:
        st.markdown("<div class='vacio'>🎉 No hay pedidos pendientes.<br>"
                    "Toque <b>➕ Agregar pedido</b> (abajo) cuando lo llamen.</div>",
                    unsafe_allow_html=True)
    for p in pendientes:
        tarjeta_pedido(p)

    # Botón flotante (el CSS lo fija abajo de la pantalla). Va al final del
    # código para que no empuje las tarjetas, pero siempre se ve.
    boton("➕ Agregar pedido", "zona_agregar", on_click=cb_abrir_form)


def vista_resumen(pedidos: list[dict]) -> None:
    dia = st.date_input("📅 Ver el día", value=hoy(), max_value=hoy(),
                        format="DD/MM/YYYY", key="dia_resumen")
    r = logica.resumen_del_dia(pedidos, dia.isoformat())

    detalle_cil = " · ".join(f"{t}kg: {n}" for t, n in r["por_tamano"].items() if n) or "ninguno"
    tarjetas = f"""
        <div class='grilla'>
          <div class='dato ancho verde'>
            <div class='icono'>💵</div>
            <div class='valor'>{pesos(r['plata_en_mano'])}</div>
            <div class='texto'>Plata recibida ({pesos(r['ventas_contado'])} ventas
              + {pesos(r['cobros_de_deudas'])} deudas cobradas)</div>
          </div>
          <div class='dato ancho'>
            <div class='icono'>🛢️</div>
            <div class='valor'>{r['total_cilindros']} cilindros</div>
            <div class='texto'>{detalle_cil}</div>
          </div>
          <div class='dato ambar'>
            <div class='icono'>📝</div>
            <div class='valor'>{pesos(r['fiado_del_dia'])}</div>
            <div class='texto'>Fiado este día</div>
          </div>
          <div class='dato rojo'>
            <div class='icono'>🔴</div>
            <div class='valor'>{pesos(r['por_cobrar_total'])}</div>
            <div class='texto'>Le deben en total ({r['deudores']})</div>
          </div>
          <div class='dato'>
            <div class='icono'>❌</div>
            <div class='valor'>{r['no_entregados']}</div>
            <div class='texto'>No entregados</div>
          </div>
          <div class='dato'>
            <div class='icono'>⏳</div>
            <div class='valor'>{r['pendientes']}</div>
            <div class='texto'>Pendientes ahora</div>
          </div>
        </div>
        """
    # Se quita la sangría: en Markdown, 4 espacios al inicio = bloque de código
    st.markdown(" ".join(linea.strip() for linea in tarjetas.splitlines()),
                unsafe_allow_html=True)

    # Ajustes para el hijo/a (precios, ciudad, respaldo). Plegado para no molestar.
    with st.expander("⚙️ Ajustes (precios y respaldo)"):
        for t in db.TAMANOS:
            st.number_input(f"Precio 🛢️ {t} kg", min_value=0, step=500,
                            value=PRECIOS[t], key=f"aj_precio_{t}")
        st.text_input("Ciudad para el mapa", value=CIUDAD, key="aj_ciudad")
        boton("💾 Guardar ajustes", "zona_guardar_ajustes", on_click=cb_guardar_ajustes)

        st.download_button(
            "📥 Descargar respaldo (Excel)",
            data=csv_respaldo(pedidos),
            file_name=f"willy_gas_{hoy().isoformat()}.csv",
            mime="text/csv",
        )
        st.caption(f"Datos guardados en: {repo.nombre}")


def vista_deudas(pedidos: list[dict]) -> None:
    deudas = sorted((p for p in pedidos if p["estado"] == db.POR_COBRAR),
                    key=lambda p: (p["fecha_cobro"], p["id"]))
    total = sum(p["monto_deuda"] for p in deudas)
    st.markdown(f"<p class='titulo-seccion'>💰 Le deben: {pesos(total)}</p>",
                unsafe_allow_html=True)
    if not deudas:
        st.markdown("<div class='vacio'>🎉 Nadie le debe plata.</div>", unsafe_allow_html=True)
        return

    hoy_iso = hoy().isoformat()
    for p in deudas:
        pid = p["id"]
        atrasado = p["fecha_cobro"] and p["fecha_cobro"] < hoy_iso
        if atrasado:
            estado = "🔴 Atrasado"
        elif p["fecha_cobro"] == hoy_iso:
            estado = "🟡 Cobrar hoy"
        else:
            estado = "🟢 Al día"
        with st.container(key=f"card_atrasado_{pid}" if atrasado else f"card_deuda_{pid}"):
            nota = f"<p class='nota'>👤 {esc(p['nota'])}</p>" if p["nota"] else ""
            st.markdown(
                f"<p class='direccion'>📍 {esc(p['direccion'])}</p>{nota}"
                f"<p class='monto-deuda'>{pesos(p['monto_deuda'])}</p>"
                f"<p class='meta'>{estado} · 📅 Cobrar el {fecha_corta(p['fecha_cobro'])}<br>"
                f"🛢️ Se fió el {fecha_corta(p['fecha_cierre'])}</p>",
                unsafe_allow_html=True,
            )
            boton("💵 Ya pagó", f"zona_pago_{pid}", on_click=cb_ya_pago, args=(pid,))
            boton_mapa(p)


def csv_respaldo(pedidos: list[dict]) -> bytes:
    buffer = io.StringIO()
    escritor = csv.DictWriter(buffer, fieldnames=db.CAMPOS_PEDIDO)
    escritor.writeheader()
    escritor.writerows(pedidos)
    return buffer.getvalue().encode("utf-8-sig")  # utf-8-sig: Excel muestra bien las tildes


# ══════════════════════════════════════════════════════════════════════════════
# 7. FLUJO PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════
encabezado()
PEDIDOS = repo.listar_pedidos()

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
else:
    vista_pedidos(PEDIDOS)
