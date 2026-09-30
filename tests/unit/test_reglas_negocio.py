"""Pruebas UNITARIAS: reglas de negocio puras, sin base de datos ni red."""
import pytest

from src.ms_auth import logic as auth
from src.ms_catalogo import logic as red
from src.ms_pedidos import logic as soporte
from src.ms_pagos import logic as pagos

pytestmark = pytest.mark.unit


@pytest.mark.caso("CP-01", "Validación de NIT/DPI del suscriptor")
@pytest.mark.parametrize("nit,esperado", [
    ("12345679", True), ("1234567-9", True), ("CF", True), ("1234567890101", True),
    ("12345678", False), ("ABC", False), ("", False), ("123456789012345", False),
])
def test_validar_nit(nit, esperado):
    assert auth.validar_nit(nit) is esperado


@pytest.mark.caso("CP-02", "Política de contraseñas y hash bcrypt")
def test_politica_password_y_hash():
    assert auth.validar_password("Fiver2026x")
    for debil in ("corta1A", "sinmayuscula1", "SINMINUSCULA1", "SinNumeros"):
        assert not auth.validar_password(debil)
    h = auth.hash_password("Fiver2026x")
    assert h.startswith("$2b$") and "Fiver2026x" not in h
    assert auth.verificar_password("Fiver2026x", h)
    assert not auth.verificar_password("otra", h)


@pytest.mark.caso("CP-03", "Transiciones válidas del estado de servicio")
def test_transiciones_estado():
    assert auth.transicion_valida("Activo", "Moroso")
    assert auth.transicion_valida("Moroso", "Activo")
    assert not auth.transicion_valida("Inactivo", "Moroso")
    assert not auth.transicion_valida("Activo", "Activo")


@pytest.mark.caso("CP-04", "Normalización y validación de dirección MAC de la ONU")
def test_normalizar_mac():
    assert red.normalizar_mac("48-57-dd-a1-b2-c3") == "48:57:DD:A1:B2:C3"
    assert red.normalizar_mac("4857DDA1B2C3") == "48:57:DD:A1:B2:C3"
    for mala in ("48:57:DD:A1:B2", "ZZ:57:DD:A1:B2:C3", "48:57-DD:A1:B2:C3", ""):
        with pytest.raises(ValueError):
            red.normalizar_mac(mala)


@pytest.mark.caso("CP-05", "Clasificación de potencia óptica según umbrales GPON")
@pytest.mark.parametrize("dbm,clase", [
    (-19.5, "Normal"), (-26.0, "Advertencia"), (-28.2, "Critica_Baja"),
    (-7.5, "Critica_Alta"), (-27.0, "Advertencia"), (None, "Sin_Lectura"),
])
def test_clasificar_senal(dbm, clase):
    assert red.clasificar_senal(dbm) == clase


@pytest.mark.caso("CP-06", "Prioridad automática de tickets y SLA")
def test_prioridad_y_sla():
    assert soporte.sugerir_prioridad("Falla", "Cliente sin internet desde ayer") == "Critica"
    assert soporte.sugerir_prioridad("Señal baja", "navegación lenta") == "Alta"
    assert soporte.sugerir_prioridad("Consulta", "información de planes") == "Baja"
    assert soporte.sugerir_prioridad("Cambio", "cambio de clave wifi") == "Media"
    assert soporte.sla_horas("Critica") == 4 and soporte.sla_horas("Baja") == 72
    with pytest.raises(ValueError):
        soporte.sla_horas("Urgentisima")


@pytest.mark.caso("CP-07", "Validación del monto cobrado en campo")
def test_validar_monto():
    assert str(pagos.validar_monto(299, "299.00")) == "299.00"
    for pagado in (150, 300, 0, -5, "abc"):
        with pytest.raises(ValueError):
            pagos.validar_monto(pagado, "299.00")


@pytest.mark.caso("CP-08", "Identificador de transacción único y método de pago permitido")
def test_id_transaccion_y_metodo():
    ids = {pagos.generar_id_transaccion() for _ in range(500)}
    assert len(ids) == 500
    assert all(i.startswith("FC-") for i in ids)
    assert pagos.validar_metodo("Efectivo") and not pagos.validar_metodo("Bitcoin")
    assert pagos.requiere_autorizacion("Tarjeta") and not pagos.requiere_autorizacion("Efectivo")
