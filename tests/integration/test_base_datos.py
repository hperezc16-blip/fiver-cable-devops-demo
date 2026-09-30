"""Pruebas de INTEGRACIÓN con PostgreSQL: triggers, procedimientos, vistas y restricciones
creados por el script del Entregable 8. Cada prueba se revierte al finalizar."""
import psycopg
import pytest

pytestmark = pytest.mark.integration


@pytest.mark.caso("CP-09", "Trigger trg_auditar_cliente registra el cambio de estado")
def test_trigger_auditoria(db):
    db.execute("UPDATE usuarios_db.clientes SET estado_servicio = 'Moroso' WHERE id_cliente = 2")
    fila = db.execute("""SELECT accion, detalles FROM usuarios_db.auditoria_usuarios
                         WHERE id_cliente = 2 ORDER BY id_auditoria DESC LIMIT 1""").fetchone()
    assert fila["accion"] == "CAMBIO_ESTADO_SERVICIO"
    assert fila["detalles"] == {"estado_anterior": "Activo", "estado_nuevo": "Moroso"}


@pytest.mark.caso("CP-10", "Trigger trg_procesar_pago_exitoso marca la factura como Pagado")
def test_trigger_pago_exitoso(db):
    id_f = db.execute("""INSERT INTO billing_db.facturas_fel (id_cliente_ref, uuid_sat, serie_fel, numero_fel, monto_total)
                         VALUES (1, 'INT-TEST-0001', 'FEL-T', '9001', 199.00) RETURNING id_factura""").fetchone()["id_factura"]
    db.execute("""INSERT INTO billing_db.pagos (id_factura, id_transaccion_pasarela, monto_pagado, metodo_pago)
                  VALUES (%s, 'TX-INT-1', 199.00, 'Efectivo')""", (id_f,))
    estado = db.execute("SELECT estado_pago FROM billing_db.facturas_fel WHERE id_factura = %s", (id_f,)).fetchone()
    assert estado["estado_pago"] == "Pagado"


@pytest.mark.caso("CP-11", "Restricción UNIQUE impide asignar una MAC a dos suscriptores")
def test_mac_unica(db):
    with pytest.raises(psycopg.errors.UniqueViolation):
        db.execute("""INSERT INTO red_db.dispositivos_onu (id_cliente_ref, mac_address, serial_number, puerto_olt)
                      VALUES (2, '48:57:DD:A1:B2:C3', 'HWTC00000000', 'Slot2/Pon1')""")


@pytest.mark.caso("CP-12", "sp_cerrar_ticket cierra el ticket y la vista de pendientes lo excluye")
def test_sp_cerrar_ticket(db):
    id_t = db.execute("""INSERT INTO soporte_db.tickets_soporte (id_cliente_ref, tipo_incidencia, descripcion_falla)
                         VALUES (1, 'Prueba', 'Ticket de prueba de integración') RETURNING id_ticket""").fetchone()["id_ticket"]
    db.execute("CALL soporte_db.sp_cerrar_ticket(%s, %s)", (id_t, 3))
    t = db.execute("SELECT * FROM soporte_db.tickets_soporte WHERE id_ticket = %s", (id_t,)).fetchone()
    assert t["estado_ticket"] == "Cerrado" and t["fecha_cierre"] is not None and t["id_tecnico_asignado"] == 3
    pend = db.execute("SELECT 1 FROM soporte_db.vw_tickets_pendientes WHERE id_ticket = %s", (id_t,)).fetchone()
    assert pend is None


@pytest.mark.caso("CP-13", "Vista vw_onus_senal_critica y sp_actualizar_estado_onu")
def test_vista_senal_critica_y_sp_onu(db):
    macs = {f["mac_address"] for f in db.execute("SELECT mac_address FROM red_db.vw_onus_senal_critica").fetchall()}
    assert "48:57:DD:F4:E5:D6" in macs          # -28.20 dBm
    assert "48:57:DD:A1:B2:C3" not in macs      # -19.50 dBm (normal)
    db.execute("CALL red_db.sp_actualizar_estado_onu(%s, %s)", (2, "Online"))
    est = db.execute("SELECT estado_conexion FROM red_db.dispositivos_onu WHERE id_cliente_ref = 2").fetchone()
    assert est["estado_conexion"] == "Online"
