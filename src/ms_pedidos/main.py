"""ms_pedidos -> esquema soporte_db. Tickets de soporte técnico."""
from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field

from src.common.base import OPERACION, PERSONAL, crear_app, get_conn, requiere_rol, usuario_actual
from src.ms_pedidos import logic

ESQUEMA = "soporte_db"
app = crear_app("ms_pedidos", ESQUEMA)


class NuevoTicket(BaseModel):
    id_cliente_ref: int = Field(gt=0)
    tipo_incidencia: str = Field(min_length=3, max_length=50)
    descripcion_falla: str = Field(min_length=5)
    prioridad: str | None = None


@app.post("/api/tickets", status_code=201)
def crear_ticket(datos: NuevoTicket, user: dict = Depends(usuario_actual)):
    if user["rol"] == "Suscriptor" and int(user["sub"]) != datos.id_cliente_ref:
        raise HTTPException(403, "Solo puede reportar fallas de su propio servicio")
    prioridad = datos.prioridad or logic.sugerir_prioridad(datos.tipo_incidencia, datos.descripcion_falla)
    if prioridad not in logic.PRIORIDADES:
        raise HTTPException(422, "Prioridad inválida")
    with get_conn(ESQUEMA) as c:
        fila = c.execute(
            """INSERT INTO tickets_soporte (id_cliente_ref, tipo_incidencia, descripcion_falla, prioridad)
               VALUES (%s,%s,%s,%s) RETURNING *""",
            (datos.id_cliente_ref, datos.tipo_incidencia, datos.descripcion_falla, prioridad)).fetchone()
    fila["sla_horas"] = logic.sla_horas(prioridad)
    return fila


@app.get("/api/tickets")
def listar_tickets(id_cliente: int | None = None, user: dict = Depends(usuario_actual)):
    if user["rol"] == "Suscriptor":
        id_cliente = int(user["sub"])
    elif user["rol"] not in PERSONAL:
        raise HTTPException(403, "Rol sin permiso para esta operación")
    sql, params = "SELECT * FROM tickets_soporte", []
    if id_cliente is not None:
        sql += " WHERE id_cliente_ref = %s"
        params.append(id_cliente)
    with get_conn(ESQUEMA) as c:
        filas = c.execute(sql + " ORDER BY id_ticket DESC LIMIT 200", params).fetchall()
    for f in filas:
        f["sla_horas"] = logic.sla_horas(f["prioridad"])
    return filas


@app.get("/api/tickets/pendientes")
def tickets_pendientes(user: dict = Depends(requiere_rol(*PERSONAL))):
    with get_conn(ESQUEMA) as c:
        return c.execute("SELECT * FROM vw_tickets_pendientes ORDER BY fecha_apertura").fetchall()


@app.post("/api/tickets/{id_ticket}/tomar")
def tomar_ticket(id_ticket: int, user: dict = Depends(requiere_rol(*OPERACION))):
    with get_conn(ESQUEMA) as c:
        fila = c.execute(
            """UPDATE tickets_soporte SET estado_ticket = 'En_Proceso', id_tecnico_asignado = %s
               WHERE id_ticket = %s AND estado_ticket = 'Abierto' RETURNING *""",
            (int(user["sub"]), id_ticket)).fetchone()
    if not fila:
        raise HTTPException(409, "El ticket no existe o ya fue tomado")
    return fila


@app.post("/api/tickets/{id_ticket}/cerrar")
def cerrar_ticket(id_ticket: int, user: dict = Depends(requiere_rol(*OPERACION))):
    with get_conn(ESQUEMA) as c:
        existe = c.execute("SELECT estado_ticket FROM tickets_soporte WHERE id_ticket = %s", (id_ticket,)).fetchone()
        if not existe:
            raise HTTPException(404, "Ticket no encontrado")
        if existe["estado_ticket"] == "Cerrado":
            raise HTTPException(409, "El ticket ya está cerrado")
        c.execute("CALL sp_cerrar_ticket(%s, %s)", (id_ticket, int(user["sub"])))
        return c.execute("SELECT * FROM tickets_soporte WHERE id_ticket = %s", (id_ticket,)).fetchone()
