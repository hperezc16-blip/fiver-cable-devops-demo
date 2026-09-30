"""Reglas de negocio puras de ms_pagos (Billing / cobro digital en campo)."""
import secrets
from datetime import datetime
from decimal import Decimal, InvalidOperation

METODOS_PAGO = {"Tarjeta", "Transferencia", "Efectivo", "Agente_Autorizado"}


def validar_monto(monto_pagado, monto_factura) -> Decimal:
    """El cobro en campo liquida la factura completa: el monto debe coincidir exactamente."""
    try:
        pagado = Decimal(str(monto_pagado)).quantize(Decimal("0.01"))
        total = Decimal(str(monto_factura)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        raise ValueError("Monto con formato inválido")
    if pagado <= 0:
        raise ValueError("El monto debe ser mayor a cero")
    if pagado != total:
        raise ValueError(f"El monto Q{pagado} no coincide con el total de la factura Q{total}")
    return pagado


def validar_metodo(metodo: str) -> bool:
    return metodo in METODOS_PAGO


def generar_id_transaccion(prefijo: str = "FC") -> str:
    """Identificador único y no predecible de la transacción de cobro."""
    return f"{prefijo}-{datetime.now():%Y%m%d%H%M%S}-{secrets.token_hex(4).upper()}"


def requiere_autorizacion(metodo: str) -> bool:
    return metodo in {"Tarjeta", "Transferencia"}
