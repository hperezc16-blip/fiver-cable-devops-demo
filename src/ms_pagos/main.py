"""ms_pagos -> esquema billing_db. Facturas FEL, pagos y portal web de Fiver Cable."""
import os
import uuid
from pathlib import Path

from fastapi import Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, Field

from src.common.base import COBRADORES, PERSONAL, crear_app, get_conn, requiere_rol, usuario_actual
from src.ms_pagos import logic

ESQUEMA = "billing_db"
app = crear_app("ms_pagos", ESQUEMA)
PORTAL_HTML = (Path(__file__).parent / "portal.html").read_text(encoding="utf-8")


class NuevoPago(BaseModel):
    id_factura: int = Field(gt=0)
    monto_pagado: float
    metodo_pago: str
    codigo_autorizacion: str | None = Field(default=None, max_length=50)


class NuevaFactura(BaseModel):
    id_cliente_ref: int = Field(gt=0)
    monto_total: float = Field(gt=0, le=100000)


@app.get("/api/facturas")
def facturas(id_cliente: int | None = None, estado: str | None = None, user: dict = Depends(usuario_actual)):
    if user["rol"] == "Suscriptor":
        if id_cliente is not None and int(user["sub"]) != id_cliente:
            raise HTTPException(403, "Solo puede consultar sus propias facturas")
        id_cliente = int(user["sub"])
    elif user["rol"] not in PERSONAL:
        raise HTTPException(403, "Rol sin permiso para esta operación")
    sql = "SELECT * FROM facturas_fel WHERE TRUE"
    params: list = []
    if id_cliente is not None:
        sql += " AND id_cliente_ref = %s"
        params.append(id_cliente)
    if estado:
        sql += " AND estado_pago = %s"
        params.append(estado)
    with get_conn(ESQUEMA) as c:
        return c.execute(sql + " ORDER BY fecha_emision, id_factura LIMIT 200", params).fetchall()


@app.post("/api/facturas", status_code=201)
def emitir_factura(datos: NuevaFactura, user: dict = Depends(requiere_rol("Administrador", "Secretaria"))):
    with get_conn(ESQUEMA) as c:
        siguiente = c.execute(
            """SELECT COALESCE(MAX(CAST(numero_fel AS INT)), 1000) + 1 AS n FROM facturas_fel
               WHERE serie_fel = 'FEL-A' AND numero_fel ~ '^[0-9]+$'""").fetchone()["n"]
        return c.execute(
            """INSERT INTO facturas_fel (id_cliente_ref, uuid_sat, serie_fel, numero_fel, monto_total)
               VALUES (%s, %s, 'FEL-A', %s, %s) RETURNING *""",
            (datos.id_cliente_ref, str(uuid.uuid4()).upper(), str(siguiente),
             round(datos.monto_total, 2))).fetchone()


@app.post("/api/pagos", status_code=201)
def registrar_pago(datos: NuevoPago, user: dict = Depends(requiere_rol(*COBRADORES))):
    if not logic.validar_metodo(datos.metodo_pago):
        raise HTTPException(422, "Método de pago no permitido")
    if logic.requiere_autorizacion(datos.metodo_pago) and not datos.codigo_autorizacion:
        raise HTTPException(422, "El método de pago requiere código de autorización")
    with get_conn(ESQUEMA) as c:
        factura = c.execute("SELECT * FROM facturas_fel WHERE id_factura = %s FOR UPDATE",
                            (datos.id_factura,)).fetchone()
        if not factura:
            raise HTTPException(404, "Factura no encontrada")
        if factura["estado_pago"] != "Pendiente":
            raise HTTPException(409, f"La factura ya está en estado {factura['estado_pago']}")
        try:
            monto = logic.validar_monto(datos.monto_pagado, factura["monto_total"])
        except ValueError as e:
            raise HTTPException(422, str(e))
        pago = c.execute(
            """INSERT INTO pagos (id_factura, id_transaccion_pasarela, monto_pagado, metodo_pago,
                                  codigo_autorizacion, registrado_por)
               VALUES (%s,%s,%s,%s,%s,%s) RETURNING *""",
            (datos.id_factura, logic.generar_id_transaccion(), monto, datos.metodo_pago,
             datos.codigo_autorizacion, user["correo"])).fetchone()
        # El trigger trg_procesar_pago_exitoso marca la factura como 'Pagado'
        estado = c.execute("SELECT estado_pago FROM facturas_fel WHERE id_factura = %s",
                           (datos.id_factura,)).fetchone()["estado_pago"]
    pago["estado_factura"] = estado
    pago["cobrado_por"] = user["correo"]
    pago["id_cliente_ref"] = factura["id_cliente_ref"]
    pago["factura"] = f"{factura['serie_fel']}-{factura['numero_fel']}"
    return pago


@app.get("/api/pagos")
def pagos_recientes(limite: int = Query(default=50, ge=1, le=200), user: dict = Depends(requiere_rol(*PERSONAL))):
    with get_conn(ESQUEMA) as c:
        return c.execute(
            """SELECT p.id_pago, p.id_transaccion_pasarela, p.monto_pagado, p.fecha_pago, p.metodo_pago,
                      p.registrado_por, f.id_factura, f.id_cliente_ref, f.serie_fel || '-' || f.numero_fel AS factura
               FROM pagos p JOIN facturas_fel f ON f.id_factura = p.id_factura
               ORDER BY p.fecha_pago DESC LIMIT %s""", (limite,)).fetchall()


@app.get("/api/pagos/cierre-diario")
def cierre_diario(user: dict = Depends(requiere_rol(*PERSONAL))):
    with get_conn(ESQUEMA) as c:
        return c.execute("SELECT * FROM vw_cierre_diario_pagos ORDER BY fecha DESC, metodo_pago").fetchall()


@app.get("/api/resumen")
def resumen(user: dict = Depends(requiere_rol(*PERSONAL))):
    with get_conn(ESQUEMA) as c:
        return c.execute(
            """SELECT
                 (SELECT COUNT(*) FROM facturas_fel WHERE estado_pago = 'Pendiente') AS facturas_pendientes,
                 (SELECT COALESCE(SUM(monto_total), 0) FROM facturas_fel WHERE estado_pago = 'Pendiente') AS monto_pendiente,
                 (SELECT COUNT(*) FROM pagos WHERE fecha_pago::date = CURRENT_DATE) AS cobros_hoy,
                 (SELECT COALESCE(SUM(monto_pagado), 0) FROM pagos WHERE fecha_pago::date = CURRENT_DATE) AS recaudado_hoy,
                 (SELECT COALESCE(SUM(monto_pagado), 0) FROM pagos
                   WHERE date_trunc('month', fecha_pago) = date_trunc('month', CURRENT_DATE)) AS recaudado_mes""").fetchone()


@app.get("/", include_in_schema=False)
def inicio():
    return RedirectResponse("/portal")


@app.get("/portal", response_class=HTMLResponse, include_in_schema=False)
def portal():
    return (PORTAL_HTML
            .replace("__AUTH_URL__", os.getenv("AUTH_PUBLIC_URL", "http://localhost:3000"))
            .replace("__CATALOGO_URL__", os.getenv("CATALOGO_PUBLIC_URL", "http://localhost:3001"))
            .replace("__PEDIDOS_URL__", os.getenv("PEDIDOS_PUBLIC_URL", "http://localhost:3002")))
