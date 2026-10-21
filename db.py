"""
db.py — Capa de PERSISTENCIA de Willy Gas.

Este archivo NO importa Streamlit: solo guarda y lee datos.
Hay dos "motores" intercambiables que exponen exactamente los mismos métodos:

  • SQLiteRepo  → archivo local `willy_gas.db`
                  (PC de la casa, Raspberry Pi o servidor con disco permanente)
  • SheetsRepo  → una planilla de Google Sheets
                  (lo ideal si la app vive en Streamlit Community Cloud,
                   cuyo disco se borra cada vez que la app se reinicia)

La interfaz (app.py) no sabe cuál de los dos está usando.
"""
from __future__ import annotations

import sqlite3
import threading
import time
from contextlib import closing

# ──────────────────────────────────────────────────────────────────────────────
# Constantes del dominio
# ──────────────────────────────────────────────────────────────────────────────
PENDIENTE = "PENDIENTE"        # recién anotado, falta ir
ENTREGADO = "ENTREGADO"        # entregado y pagado al contado
NO_ENTREGADO = "NO_ENTREGADO"  # no se pudo entregar / cancelado
POR_COBRAR = "POR_COBRAR"      # entregado, pero quedó fiado
PAGADO = "PAGADO"              # era fiado y ya se cobró

TAMANOS = (5, 11, 15, 45)  # kg de los cilindros

# Precios iniciales (CLP). Se cambian desde la app en "⚙️ Ajustes".
PRECIOS_POR_DEFECTO = {5: 13000, 11: 21000, 15: 28000, 45: 80000}
# Se agrega a cada dirección al abrir Maps. Cámbiela en ⚙️ Ajustes por "Su comuna, Chile".
CIUDAD_POR_DEFECTO = "Chile"

# Orden de columnas de un pedido (también es el orden de la hoja de Google)
CAMPOS_PEDIDO = [
    "id", "creado_en", "fecha_jornada", "direccion", "nota",
    "c5", "c11", "c15", "c45",
    "estado", "monto_venta", "monto_deuda",
    "fecha_cobro", "fecha_cierre", "fecha_pago",
]
CAMPOS_ENTEROS = {"id", "c5", "c11", "c15", "c45", "monto_venta", "monto_deuda"}
CAMPOS_EDITABLES = set(CAMPOS_PEDIDO) - {"id"}


def _normalizar(fila: dict) -> dict:
    """Deja cualquier fila (venga de SQLite o de Sheets) con tipos uniformes:
    números como int y todo lo demás como texto ('' si está vacío)."""
    pedido = {}
    for campo in CAMPOS_PEDIDO:
        valor = fila.get(campo, "")
        if campo in CAMPOS_ENTEROS:
            try:
                valor = int(float(valor)) if valor not in ("", None) else 0
            except (TypeError, ValueError):
                valor = 0
        else:
            valor = "" if valor is None else str(valor)
        pedido[campo] = valor
    return pedido


# ──────────────────────────────────────────────────────────────────────────────
# Motor 1: SQLite (archivo local)
# ──────────────────────────────────────────────────────────────────────────────
class SQLiteRepo:
    """Guarda todo en un único archivo .db. Cero configuración."""

    nombre = "SQLite (archivo local)"

    def __init__(self, ruta: str = "willy_gas.db"):
        self.ruta = ruta
        self._lock = threading.Lock()
        self._crear_tablas()

    def _conectar(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.ruta, timeout=10, check_same_thread=False)
        con.row_factory = sqlite3.Row
        return con

    def _crear_tablas(self) -> None:
        with closing(self._conectar()) as con:
            # WAL = escrituras más seguras si la app se corta a mitad de camino
            con.execute("PRAGMA journal_mode=WAL")
            with con:
                con.execute(
                    """
                    CREATE TABLE IF NOT EXISTS pedidos (
                        id            INTEGER PRIMARY KEY AUTOINCREMENT,
                        creado_en     TEXT NOT NULL,
                        fecha_jornada TEXT NOT NULL,
                        direccion     TEXT NOT NULL,
                        nota          TEXT DEFAULT '',
                        c5  INTEGER DEFAULT 0,
                        c11 INTEGER DEFAULT 0,
                        c15 INTEGER DEFAULT 0,
                        c45 INTEGER DEFAULT 0,
                        estado        TEXT NOT NULL DEFAULT 'PENDIENTE',
                        monto_venta   INTEGER DEFAULT 0,
                        monto_deuda   INTEGER DEFAULT 0,
                        fecha_cobro   TEXT DEFAULT '',
                        fecha_cierre  TEXT DEFAULT '',
                        fecha_pago    TEXT DEFAULT ''
                    )
                    """
                )
                con.execute("CREATE INDEX IF NOT EXISTS ix_estado ON pedidos(estado)")
                con.execute(
                    "CREATE TABLE IF NOT EXISTS jornadas (fecha TEXT PRIMARY KEY, iniciada_en TEXT)"
                )
                con.execute(
                    "CREATE TABLE IF NOT EXISTS config (clave TEXT PRIMARY KEY, valor TEXT)"
                )

    # --- Jornadas -------------------------------------------------------------
    def jornada_existe(self, fecha: str) -> bool:
        with closing(self._conectar()) as con:
            fila = con.execute("SELECT 1 FROM jornadas WHERE fecha = ?", (fecha,)).fetchone()
        return fila is not None

    def iniciar_jornada(self, fecha: str, iniciada_en: str) -> None:
        with self._lock, closing(self._conectar()) as con, con:
            con.execute(
                "INSERT OR IGNORE INTO jornadas (fecha, iniciada_en) VALUES (?, ?)",
                (fecha, iniciada_en),
            )

    # --- Pedidos --------------------------------------------------------------
    def listar_pedidos(self) -> list[dict]:
        with closing(self._conectar()) as con:
            filas = con.execute("SELECT * FROM pedidos ORDER BY id").fetchall()
        return [_normalizar(dict(f)) for f in filas]

    def obtener_pedido(self, pedido_id: int) -> dict | None:
        with closing(self._conectar()) as con:
            fila = con.execute("SELECT * FROM pedidos WHERE id = ?", (pedido_id,)).fetchone()
        return _normalizar(dict(fila)) if fila else None

    def crear_pedido(self, datos: dict) -> int:
        fila = _normalizar(datos)
        campos = [c for c in CAMPOS_PEDIDO if c != "id"]
        marcas = ", ".join("?" for _ in campos)
        with self._lock, closing(self._conectar()) as con, con:
            cur = con.execute(
                f"INSERT INTO pedidos ({', '.join(campos)}) VALUES ({marcas})",
                [fila[c] for c in campos],
            )
            return int(cur.lastrowid)

    def actualizar_pedido(self, pedido_id: int, cambios: dict) -> None:
        cambios = {k: v for k, v in cambios.items() if k in CAMPOS_EDITABLES}
        if not cambios:
            return
        asignaciones = ", ".join(f"{k} = ?" for k in cambios)
        with self._lock, closing(self._conectar()) as con, con:
            con.execute(
                f"UPDATE pedidos SET {asignaciones} WHERE id = ?",
                [*cambios.values(), pedido_id],
            )

    # --- Configuración (precios, ciudad) -------------------------------------
    def leer_config(self) -> dict:
        with closing(self._conectar()) as con:
            filas = con.execute("SELECT clave, valor FROM config").fetchall()
        return {f["clave"]: f["valor"] for f in filas}

    def guardar_config(self, valores: dict) -> None:
        with self._lock, closing(self._conectar()) as con, con:
            con.executemany(
                "INSERT INTO config (clave, valor) VALUES (?, ?) "
                "ON CONFLICT(clave) DO UPDATE SET valor = excluded.valor",
                [(k, str(v)) for k, v in valores.items()],
            )


# ──────────────────────────────────────────────────────────────────────────────
# Motor 2: Google Sheets (en la nube)
# ──────────────────────────────────────────────────────────────────────────────
class SheetsRepo:
    """Guarda todo en una planilla de Google con 3 hojas: pedidos, jornadas, config.

    Para no gastar la cuota de la API de Google (Streamlit recarga la página en
    cada toque), las lecturas se guardan en memoria unos segundos y se refrescan
    apenas hay una escritura.
    """

    nombre = "Google Sheets (nube)"
    HOJAS = {
        "pedidos": CAMPOS_PEDIDO,
        "jornadas": ["fecha", "iniciada_en"],
        "config": ["clave", "valor"],
    }

    def __init__(self, credenciales: dict, spreadsheet_key: str, ttl_segundos: int = 20):
        import gspread  # se importa aquí para que SQLite funcione sin gspread instalado

        self._gspread = gspread
        cliente = gspread.service_account_from_dict(credenciales)
        self.libro = cliente.open_by_key(spreadsheet_key)
        self.ttl = ttl_segundos
        self._lock = threading.Lock()
        self._cache: dict[str, tuple[float, list[dict]]] = {}
        self.ws = {nombre: self._asegurar_hoja(nombre, enc) for nombre, enc in self.HOJAS.items()}

    def _asegurar_hoja(self, nombre: str, encabezados: list[str]):
        """Crea la hoja y sus encabezados si todavía no existen."""
        try:
            ws = self.libro.worksheet(nombre)
        except self._gspread.WorksheetNotFound:
            ws = self.libro.add_worksheet(title=nombre, rows=1000, cols=len(encabezados))
        if not ws.row_values(1):
            ws.update(range_name="A1", values=[encabezados], value_input_option="RAW")
        return ws

    def _registros(self, hoja: str, forzar: bool = False) -> list[dict]:
        ahora = time.monotonic()
        guardado = self._cache.get(hoja)
        if not forzar and guardado and ahora - guardado[0] < self.ttl:
            return guardado[1]
        filas = self.ws[hoja].get_all_records(default_blank="")
        self._cache[hoja] = (ahora, filas)
        return filas

    def _invalidar(self, hoja: str) -> None:
        self._cache.pop(hoja, None)

    def _numero_fila(self, hoja: str, clave: str) -> int | None:
        """Número de fila (1 = encabezados) cuyo valor en la columna A es `clave`."""
        valores = self.ws[hoja].col_values(1)
        try:
            return valores.index(str(clave)) + 1
        except ValueError:
            return None

    # --- Jornadas -------------------------------------------------------------
    def jornada_existe(self, fecha: str) -> bool:
        return any(str(r.get("fecha")) == fecha for r in self._registros("jornadas"))

    def iniciar_jornada(self, fecha: str, iniciada_en: str) -> None:
        with self._lock:
            if any(str(r.get("fecha")) == fecha for r in self._registros("jornadas", forzar=True)):
                return
            self.ws["jornadas"].append_row([fecha, iniciada_en], value_input_option="RAW")
            self._invalidar("jornadas")

    # --- Pedidos --------------------------------------------------------------
    def listar_pedidos(self) -> list[dict]:
        return [_normalizar(r) for r in self._registros("pedidos")]

    def obtener_pedido(self, pedido_id: int) -> dict | None:
        for r in self._registros("pedidos", forzar=True):
            p = _normalizar(r)
            if p["id"] == int(pedido_id):
                return p
        return None

    def crear_pedido(self, datos: dict) -> int:
        with self._lock:
            existentes = [_normalizar(r)["id"] for r in self._registros("pedidos", forzar=True)]
            nuevo_id = max(existentes, default=0) + 1
            fila = _normalizar({**datos, "id": nuevo_id})
            self.ws["pedidos"].append_row(
                [fila[c] for c in CAMPOS_PEDIDO], value_input_option="RAW"
            )
            self._invalidar("pedidos")
            return nuevo_id

    def actualizar_pedido(self, pedido_id: int, cambios: dict) -> None:
        cambios = {k: v for k, v in cambios.items() if k in CAMPOS_EDITABLES}
        if not cambios:
            return
        with self._lock:
            actual = self.obtener_pedido(pedido_id)
            numero = self._numero_fila("pedidos", pedido_id)
            if actual is None or numero is None:
                raise KeyError(f"No existe el pedido {pedido_id}")
            fila = _normalizar({**actual, **cambios})
            self.ws["pedidos"].update(
                range_name=f"A{numero}",
                values=[[fila[c] for c in CAMPOS_PEDIDO]],
                value_input_option="RAW",
            )
            self._invalidar("pedidos")

    # --- Configuración --------------------------------------------------------
    def leer_config(self) -> dict:
        return {str(r["clave"]): str(r["valor"]) for r in self._registros("config")}

    def guardar_config(self, valores: dict) -> None:
        with self._lock:
            for clave, valor in valores.items():
                numero = self._numero_fila("config", clave)
                if numero:
                    self.ws["config"].update(
                        range_name=f"B{numero}", values=[[str(valor)]], value_input_option="RAW"
                    )
                else:
                    self.ws["config"].append_row([clave, str(valor)], value_input_option="RAW")
            self._invalidar("config")
