"""ms_pagos -> esquema billing_db. Facturas FEL, pagos y cierre diario."""
from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field

from src.common.base import crear_app, get_conn, requiere_rol, usuario_actual
from src.ms_pagos import logic

ESQUEMA = "billing_db"
app = crear_app("ms_pagos", ESQUEMA)


class NuevoPago(BaseModel):
    id_factura: int = Field(gt=0)
    monto_pagado: float
    metodo_pago: str
    codigo_autorizacion: str | None = Field(default=None, max_length=50)


@app.get("/api/facturas")
def facturas_cliente(id_cliente: int, estado: str | None = None, user: dict = Depends(usuario_actual)):
    if user["rol"] == "Suscriptor" and int(user["sub"]) != id_cliente:
        raise HTTPException(403, "Solo puede consultar sus propias facturas")
    sql = "SELECT * FROM facturas_fel WHERE id_cliente_ref = %s"
    params: list = [id_cliente]
    if estado:
        sql += " AND estado_pago = %s"
        params.append(estado)
    with get_conn(ESQUEMA) as c:
        return c.execute(sql + " ORDER BY fecha_emision", params).fetchall()


@app.post("/api/pagos", status_code=201)
def registrar_pago(datos: NuevoPago, user: dict = Depends(requiere_rol("Tecnico", "Administrador"))):
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
            """INSERT INTO pagos (id_factura, id_transaccion_pasarela, monto_pagado, metodo_pago, codigo_autorizacion)
               VALUES (%s,%s,%s,%s,%s) RETURNING *""",
            (datos.id_factura, logic.generar_id_transaccion(), monto, datos.metodo_pago,
             datos.codigo_autorizacion)).fetchone()
        # El trigger trg_procesar_pago_exitoso marca la factura como 'Pagado'
        estado = c.execute("SELECT estado_pago FROM facturas_fel WHERE id_factura = %s",
                           (datos.id_factura,)).fetchone()["estado_pago"]
    pago["estado_factura"] = estado
    pago["cobrado_por"] = user["correo"]
    return pago


@app.get("/api/pagos/cierre-diario")
def cierre_diario(user: dict = Depends(requiere_rol("Tecnico", "Administrador"))):
    with get_conn(ESQUEMA) as c:
        return c.execute("SELECT * FROM vw_cierre_diario_pagos ORDER BY fecha DESC, metodo_pago").fetchall()

