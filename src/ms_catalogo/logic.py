"""Reglas de negocio puras de ms_catalogo (Agente OLT / Provisionamiento)."""
import re

ESTADOS_ONU = {"Online", "Offline", "Corta_Velocidad", "Suspendido"}
UMBRAL_BAJO_DBM = -27.00   # por debajo: señal débil (fibra dañada / conector sucio)
UMBRAL_ALTO_DBM = -8.00    # por encima: saturación del receptor

_MAC = re.compile(r"^[0-9A-F]{2}([:-]?)[0-9A-F]{2}(\1[0-9A-F]{2}){4}$")


def normalizar_mac(mac: str) -> str:
    """Devuelve la MAC en formato AA:BB:CC:DD:EE:FF o lanza ValueError."""
    if not mac:
        raise ValueError("MAC vacía")
    m = mac.strip().upper()
    if not _MAC.match(m):
        raise ValueError("Formato de MAC inválido")
    limpia = re.sub(r"[:-]", "", m)
    return ":".join(limpia[i:i + 2] for i in range(0, 12, 2))


def clasificar_senal(potencia_dbm: float | None) -> str:
    """Clasifica la potencia óptica recibida por la ONU."""
    if potencia_dbm is None:
        return "Sin_Lectura"
    if potencia_dbm < UMBRAL_BAJO_DBM:
        return "Critica_Baja"
    if potencia_dbm > UMBRAL_ALTO_DBM:
        return "Critica_Alta"
    if potencia_dbm < -25.0:
        return "Advertencia"
    return "Normal"


def validar_puerto_olt(puerto: str) -> bool:
    return bool(re.fullmatch(r"Slot\d{1,2}/Pon\d{1,2}", puerto or ""))
