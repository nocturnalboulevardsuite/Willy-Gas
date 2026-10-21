"""
estilos.py — CSS inyectado para que Streamlit se vea y se use como una app
para personas mayores: letra grande, botones enormes, alto contraste.

Paleta (inspirada en los cilindros de gas chilenos):
  tinta   #14213D  textos y bordes (azul casi negro, contraste 15:1 sobre blanco)
  naranjo #D9480F  acción principal: "Agregar pedido"
  verde   #1E7B34  entregado / ya pagó
  rojo    #B42318  no entregado / deuda atrasada
  ámbar   #F2B705  fiado
  azul    #0B57D0  ir en el mapa

Tipografía: Atkinson Hyperlegible, diseñada por el Braille Institute para
personas con baja visión (letras como I, l y 1 no se confunden).

Los selectores `div[class*="st-key-..."]` funcionan porque Streamlit (>=1.40)
agrega la clase `st-key-<key>` a cada st.container(key=...).
"""
import streamlit as st

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Atkinson+Hyperlegible:wght@400;700&display=swap');

:root {
  --tinta: #14213D;
  --naranjo: #D9480F;
  --verde: #1E7B34;
  --rojo: #B42318;
  --ambar: #F2B705;
  --azul: #0B57D0;
  --papel: #FFFFFF;
  --gris: #EEF1F6;
}

/* ---------- Base: letra grande y legible ---------- */
html, body, .stApp, .stApp p, .stApp li, .stApp label, .stApp input, .stApp button {
  font-family: 'Atkinson Hyperlegible', system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif !important;
}
.stApp { background: var(--papel); color: var(--tinta); }
.stApp p, .stApp li { font-size: 21px; line-height: 1.4; }

/* ---------- Sin menús ocultos: se esconde todo el "cromo" de Streamlit ---------- */
#MainMenu, footer, header[data-testid="stHeader"],
[data-testid="stToolbar"], [data-testid="stDecoration"],
[data-testid="stStatusWidget"], [data-testid="stSidebar"],
[data-testid="collapsedControl"] { display: none !important; }

/* Contenido angosto, pensado para el celular */
.block-container, [data-testid="stMainBlockContainer"] {
  padding: 0.8rem 0.9rem 9.5rem !important;  /* espacio para el botón flotante */
  max-width: 560px !important;
}

/* ---------- Columnas: en el celular Streamlit las apila; aquí las forzamos lado a lado ---------- */
[data-testid="stHorizontalBlock"] {
  flex-wrap: nowrap !important;
  gap: 0.6rem !important;
  align-items: stretch;
}
[data-testid="stHorizontalBlock"] > [data-testid="stColumn"],
[data-testid="stHorizontalBlock"] > [data-testid="column"] {
  min-width: 0 !important;
  width: auto !important;
  flex: 1 1 0% !important;
}

/* ---------- Botones gigantes ---------- */
/* Streamlit encoge los botones al ancho del texto: se fuerza el ancho completo */
[data-testid="stElementContainer"]:has(.stButton),
[data-testid="stElementContainer"]:has(.stLinkButton),
[data-testid="stElementContainer"]:has(.stDownloadButton),
.stButton, .stLinkButton, .stDownloadButton,
.stButton > div, .stLinkButton > div {
  width: 100% !important;
  max-width: 100% !important;
}
.stButton > button, .stLinkButton > a, .stDownloadButton > button, .stFormSubmitButton > button {
  width: 100% !important;
  min-height: 76px;
  border-radius: 18px !important;
  border: 3px solid var(--tinta) !important;
  background: var(--papel) !important;
  color: var(--tinta) !important;
  padding: 0.4rem 0.6rem !important;
  box-shadow: 0 4px 0 var(--tinta);
  transition: transform 80ms ease, box-shadow 80ms ease;
}
.stButton > button p, .stLinkButton > a p, .stLinkButton > a span,
.stDownloadButton > button p {
  font-size: 24px !important;
  font-weight: 700 !important;
  line-height: 1.15 !important;
  white-space: normal !important;
  overflow-wrap: normal !important;
  word-break: keep-all !important;   /* nunca cortar una palabra a la mitad */
  color: inherit !important;
}
/* Navegación: tres botones en una fila, letra un poco menor para que quepan */
/* Streamlit recorta los textos largos con "…": se desactiva para que todo se lea */
.stButton [data-testid="stMarkdownContainer"],
.stLinkButton [data-testid="stMarkdownContainer"] {
  white-space: normal !important; overflow: visible !important; text-overflow: clip !important;
}
/* Botones lado a lado (navegación, No entregué / Fiado): letra un poco menor para que quepan */
[data-testid="stHorizontalBlock"] .stButton > button { padding: 0.3rem 0.25rem !important; }
[data-testid="stHorizontalBlock"] .stButton > button p { font-size: 20px !important; }
/* Sensación de "botón físico" al tocar */
.stButton > button:active, .stLinkButton > a:active {
  transform: translateY(4px);
  box-shadow: 0 0 0 var(--tinta);
}
.stButton > button:focus-visible, .stLinkButton > a:focus-visible {
  outline: 4px solid var(--azul) !important;
  outline-offset: 3px;
}

/* Botón "activo" de la navegación (type="primary") */
.stButton > button[kind="primary"],
.stButton > button[data-testid="stBaseButton-primary"] {
  background: var(--tinta) !important;
  color: #FFFFFF !important;
}

/* Colores por acción (cada botón vive en un contenedor con key) */
/* ➕ Agregar pedido: FLOTANTE, fijo abajo, siempre al alcance del pulgar */
div[class*="st-key-zona_agregar"] {
  position: fixed !important;
  left: 0; right: 0; bottom: 0;
  z-index: 1000;
  max-width: 560px; margin: 0 auto;
  padding: 10px 12px calc(12px + env(safe-area-inset-bottom)) !important;
  background: rgba(255, 255, 255, 0.97);
  border-top: 3px solid var(--tinta);
}
div[class*="st-key-zona_agregar"] button {
  background: var(--naranjo) !important; color: #FFF !important;
  min-height: 100px !important; border-color: #7A2606 !important;
  box-shadow: 0 6px 0 #7A2606 !important;
}
div[class*="st-key-zona_agregar"] button p { font-size: 32px !important; }
div[class*="st-key-zona_dia"] button {
  background: var(--naranjo) !important; color: #FFF !important;
  min-height: 140px !important; border-color: #7A2606 !important;
  box-shadow: 0 6px 0 #7A2606 !important;
}
div[class*="st-key-zona_dia"] button p { font-size: 32px !important; }
div[class*="st-key-zona_guardar"] button,
div[class*="st-key-zona_ok"] button,
div[class*="st-key-zona_pago"] button,
div[class*="st-key-zona_confirma"] button {
  background: var(--verde) !important; color: #FFF !important;
  border-color: #0E3F1A !important; box-shadow: 0 4px 0 #0E3F1A !important;
}
div[class*="st-key-zona_guardar"] button { min-height: 96px !important; }
div[class*="st-key-zona_guardar"] button p { font-size: 30px !important; }
div[class*="st-key-zona_no"] button {
  background: var(--rojo) !important; color: #FFF !important;
  border-color: #5E120C !important; box-shadow: 0 4px 0 #5E120C !important;
}
div[class*="st-key-zona_fia"] button {
  background: var(--ambar) !important; color: var(--tinta) !important;
}
div[class*="st-key-zona_ir"] a {
  background: var(--azul) !important; color: #FFF !important;
  border-color: #062E6F !important; box-shadow: 0 4px 0 #062E6F !important;
  text-decoration: none !important;
}
div[class*="st-key-zona_mas"] .stButton > button p,
div[class*="st-key-zona_menos"] .stButton > button p { font-size: 34px !important; }

/* ---------- Campos de texto, número y fecha ---------- */
.stTextInput input, .stNumberInput input, .stDateInput input, .stTextArea textarea,
[data-testid="stDateInput"] input, [data-testid="stNumberInput"] input {
  font-size: 26px !important;
  min-height: 66px;
  border: 3px solid var(--tinta) !important;
  border-radius: 14px !important;
  color: var(--tinta) !important;
  background: #FFFFFF !important;
}
/* Fecha: las versiones nuevas de Streamlit usan un campo por segmentos (día/mes/año) */
[data-testid="stDateInputField"] {
  min-height: 66px !important;
  border: 3px solid var(--tinta) !important;
  border-radius: 14px !important;
  background: #FFFFFF !important;
}
[data-testid="stDateInputField"] [data-type] {
  font-size: 26px !important; font-weight: 700 !important; color: var(--tinta) !important;
}
/* Número: el contenedor tiene alto fijo y cortaba los botones − y + */
[data-testid="stNumberInputContainer"], .stNumberInput [data-baseweb="input"] {
  height: auto !important; min-height: 66px !important;
}
.stTextInput input::placeholder { color: #5B6478 !important; }
[data-testid="stWidgetLabel"] p, .stTextInput label p, .stNumberInput label p, .stDateInput label p {
  font-size: 23px !important;
  font-weight: 700 !important;
  color: var(--tinta) !important;
}
/* Los +/- diminutos de st.number_input se agrandan */
[data-testid="stNumberInputStepDown"], [data-testid="stNumberInputStepUp"] {
  min-width: 58px !important; min-height: 66px !important;
}
[data-testid="stNumberInputStepDown"] svg, [data-testid="stNumberInputStepUp"] svg {
  width: 28px !important; height: 28px !important;
}

/* ---------- Tarjetas de pedido ---------- */
div[class*="st-key-card_"] {
  border: 3px solid var(--tinta);
  border-radius: 20px;
  padding: 16px 14px 18px;
  background: #FFFFFF;
  margin-bottom: 14px;
}
div[class*="st-key-card_viejo"] { border-left: 12px solid var(--ambar); }
div[class*="st-key-card_atrasado"] { border-left: 12px solid var(--rojo); }

.direccion { font-size: 27px; font-weight: 700; line-height: 1.2; margin: 0 0 6px; }
.nota { font-size: 21px; margin: 0 0 8px; color: #33405C; }
.cilindros { display: flex; flex-wrap: wrap; gap: 8px; margin: 6px 0 10px; }
.chip {
  font-size: 23px; font-weight: 700; padding: 6px 12px;
  border-radius: 12px; background: var(--gris); border: 2px solid var(--tinta);
}
.meta { font-size: 19px; color: #33405C; margin: 0 0 10px; }
.etiqueta-vieja {
  display: inline-block; background: var(--ambar); color: var(--tinta);
  font-weight: 700; font-size: 19px; padding: 2px 10px; border-radius: 8px;
}

/* ---------- Encabezado ---------- */
.marca { display: flex; align-items: baseline; gap: 10px; margin: 0 0 2px; }
.marca h1 { font-size: 38px !important; margin: 0 !important; padding: 0 !important; color: var(--tinta); }
.fecha-hoy { font-size: 22px; margin: 0 0 12px; color: #33405C; }
.titulo-seccion { font-size: 28px; font-weight: 700; margin: 18px 0 10px; }

/* ---------- Contador de cilindros ---------- */
.nombre-cil { font-size: 26px; font-weight: 700; margin: 14px 0 6px; }
.contador {
  height: 76px; display: flex; align-items: center; justify-content: center;
  font-size: 40px; font-weight: 700; border-radius: 18px;
  background: var(--gris); border: 3px dashed #8A93A6;
}
.contador.activo { background: #FFE8D9; border: 3px solid var(--naranjo); color: #7A2606; }
.total-form {
  font-size: 24px; font-weight: 700; margin: 14px 0 4px; padding: 12px;
  background: var(--gris); border-radius: 14px; text-align: center;
}

/* ---------- Avisos ---------- */
.aviso {
  font-size: 23px; font-weight: 700; padding: 14px 16px; border-radius: 16px;
  background: #E3F4E7; border: 3px solid var(--verde); margin: 6px 0 10px;
}
.aviso.error { background: #FDE7E5; border-color: var(--rojo); }
.vacio {
  text-align: center; font-size: 24px; padding: 28px 12px; border-radius: 20px;
  background: var(--gris); margin-top: 8px;
}

/* ---------- Resumen del día ---------- */
.grilla { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin: 8px 0 16px; }
.dato {
  border: 3px solid var(--tinta); border-radius: 18px; padding: 14px 12px; background: #FFF;
}
.dato.ancho { grid-column: 1 / -1; }
.dato .icono { font-size: 30px; }
.dato .valor { font-size: 34px; font-weight: 700; line-height: 1.1; margin: 4px 0; }
.dato .texto { font-size: 19px; color: #33405C; }
.dato.verde { background: #E3F4E7; border-color: var(--verde); }
.dato.rojo  { background: #FDE7E5; border-color: var(--rojo); }
.dato.ambar { background: #FFF6D6; border-color: #B88600; }

.monto-deuda { font-size: 36px; font-weight: 700; color: var(--rojo); margin: 4px 0; }

/* Expander de ajustes con letra grande */
[data-testid="stExpander"] summary p { font-size: 22px !important; font-weight: 700; }

@media (prefers-reduced-motion: reduce) {
  .stButton > button, .stLinkButton > a { transition: none; }
}
</style>
"""


def inyectar_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
