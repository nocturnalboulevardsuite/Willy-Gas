"""
logica.py — Reglas del negocio (cálculos). Sin Streamlit y sin base de datos:
recibe listas de pedidos y devuelve números. Fácil de probar y de reutilizar
si mañana la interfaz se reescribe como app nativa.
"""
from __future__ import annotations

from db import (
    CIUDAD_POR_DEFECTO, ENTREGADO, NO_ENTREGADO, PAGADO, PENDIENTE,
    POR_COBRAR, PRECIOS_POR_DEFECTO, TAMANOS,
)
from urllib.parse import quote_plus


def precios_desde_config(config: dict) -> dict[int, int]:
    precios = {}
    for t in TAMANOS:
        try:
            precios[t] = int(float(config.get(f"precio_{t}", PRECIOS_POR_DEFECTO[t])))
        except ValueError:
            precios[t] = PRECIOS_POR_DEFECTO[t]
    return precios


def ciudad_desde_config(config: dict) -> str:
    return config.get("ciudad", CIUDAD_POR_DEFECTO)


def valor_pedido(pedido: dict, precios: dict[int, int]) -> int:
    """Precio total de los cilindros de un pedido."""
    return sum(int(pedido.get(f"c{t}", 0)) * precios[t] for t in TAMANOS)


def cilindros_de(pedido: dict) -> dict[int, int]:
    """{11: 2, 45: 1} — solo los tamaños con cantidad > 0."""
    return {t: int(pedido[f"c{t}"]) for t in TAMANOS if int(pedido.get(f"c{t}", 0)) > 0}


def url_google_maps(direccion: str, ciudad: str) -> str:
    """Enlace que abre Google Maps con la ruta hacia la dirección.
    Se agrega la ciudad para que Maps no confunda calles con el mismo nombre."""
    destino = direccion.strip()
    if ciudad and ciudad.split(",")[0].strip().lower() not in destino.lower():
        destino = f"{destino}, {ciudad}"
    return (
        "https://www.google.com/maps/dir/?api=1"
        f"&destination={quote_plus(destino)}&travelmode=driving"
    )


def resumen_del_dia(pedidos: list[dict], fecha_iso: str) -> dict:
    """Totales de un día. Reglas:
    - Cilindros vendidos = entregados al contado + entregados fiados ese día.
    - Plata en mano = ventas al contado del día + deudas cobradas ese día.
    - Por cobrar = TODAS las deudas abiertas, sin importar el día.
    """
    cerrados = [p for p in pedidos if p["fecha_cierre"] == fecha_iso]
    vendidos = [p for p in cerrados if p["estado"] in (ENTREGADO, POR_COBRAR, PAGADO)]

    por_tamano = {t: sum(p[f"c{t}"] for p in vendidos) for t in TAMANOS}
    ventas_contado = sum(p["monto_venta"] for p in cerrados if p["estado"] == ENTREGADO)
    cobros_de_deudas = sum(
        p["monto_deuda"] for p in pedidos
        if p["estado"] == PAGADO and p["fecha_pago"] == fecha_iso
    )
    fiado_del_dia = sum(p["monto_deuda"] for p in cerrados if p["estado"] in (POR_COBRAR, PAGADO))

    return {
        "por_tamano": por_tamano,
        "total_cilindros": sum(por_tamano.values()),
        "entregas": len(vendidos),
        "ventas_contado": ventas_contado,
        "cobros_de_deudas": cobros_de_deudas,
        "plata_en_mano": ventas_contado + cobros_de_deudas,
        "fiado_del_dia": fiado_del_dia,
        "no_entregados": sum(1 for p in cerrados if p["estado"] == NO_ENTREGADO),
        "pendientes": sum(1 for p in pedidos if p["estado"] == PENDIENTE),
        "por_cobrar_total": sum(p["monto_deuda"] for p in pedidos if p["estado"] == POR_COBRAR),
        "deudores": sum(1 for p in pedidos if p["estado"] == POR_COBRAR),
    }
