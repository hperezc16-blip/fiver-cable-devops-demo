"""Reglas de negocio puras de ms_pedidos (Tickets y Soporte)."""

PRIORIDADES = ("Baja", "Media", "Alta", "Critica")
# Tiempo máximo de atención (SLA) en horas según prioridad
SLA_HORAS = {"Critica": 4, "Alta": 8, "Media": 24, "Baja": 72}

_PALABRAS_CRITICAS = ("sin servicio", "sin internet", "fibra cortada", "corte total", "caida masiva")
_PALABRAS_ALTAS = ("lento", "intermitente", "señal baja", "senal baja", "potencia")


def sugerir_prioridad(tipo_incidencia: str, descripcion: str) -> str:
    """Asigna prioridad inicial a partir del texto del reporte."""
    texto = f"{tipo_incidencia} {descripcion}".lower()
    if any(p in texto for p in _PALABRAS_CRITICAS):
        return "Critica"
    if any(p in texto for p in _PALABRAS_ALTAS):
        return "Alta"
    if "consulta" in texto or "información" in texto or "informacion" in texto:
        return "Baja"
    return "Media"


def sla_horas(prioridad: str) -> int:
    if prioridad not in SLA_HORAS:
        raise ValueError("Prioridad inválida")
    return SLA_HORAS[prioridad]
