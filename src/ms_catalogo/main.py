"""ms_catalogo -> esquema red_db. Planes de servicio e inventario de ONUs."""
from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field
import psycopg

from src.common.base import OPERACION, PERSONAL, crear_app, get_conn, requiere_rol, usuario_actual
from src.ms_catalogo import logic

ESQUEMA = "red_db"
app = crear_app("ms_catalogo", ESQUEMA)


class NuevaOnu(BaseModel):
    id_cliente_ref: int = Field(gt=0)
    mac_address: str
    serial_number: str = Field(min_length=4, max_length=50)
    ip_asignada: str | None = Field(default=None, pattern=r"^\d{1,3}(\.\d{1,3}){3}$")
    puerto_olt: str
    potencia_optica_dbm: float | None = Field(default=None, ge=-40, le=5)


class CambioEstadoOnu(BaseModel):
    id_cliente: int = Field(gt=0)
    nuevo_estado: str


@app.get("/api/planes")
def listar_planes():
    with get_conn(ESQUEMA) as c:
        return c.execute("SELECT * FROM planes_servicio ORDER BY precio_mensual").fetchall()


@app.get("/api/onus")
def listar_onus(id_cliente: int | None = None, user: dict = Depends(usuario_actual)):
    if user["rol"] == "Suscriptor":
        id_cliente = int(user["sub"])
    elif user["rol"] not in PERSONAL:
        raise HTTPException(403, "Rol sin permiso para esta operación")
    sql, params = "SELECT * FROM dispositivos_onu", []
    if id_cliente is not None:
        sql += " WHERE id_cliente_ref = %s"
        params.append(id_cliente)
    with get_conn(ESQUEMA) as c:
        filas = c.execute(sql + " ORDER BY id_onu", params).fetchall()
    for f in filas:
        potencia = f["potencia_optica_dbm"]
        f["clasificacion_senal"] = logic.clasificar_senal(None if potencia is None else float(potencia))
    return filas


@app.post("/api/onus", status_code=201)
def registrar_onu(datos: NuevaOnu, user: dict = Depends(requiere_rol(*OPERACION))):
    try:
        mac = logic.normalizar_mac(datos.mac_address)
    except ValueError as e:
        raise HTTPException(422, str(e))
    if not logic.validar_puerto_olt(datos.puerto_olt):
        raise HTTPException(422, "Puerto OLT inválido (formato SlotN/PonN)")
    try:
        with get_conn(ESQUEMA) as c:
            fila = c.execute(
                """INSERT INTO dispositivos_onu (id_cliente_ref, mac_address, serial_number, ip_asignada,
                   puerto_olt, potencia_optica_dbm) VALUES (%s,%s,%s,%s,%s,%s) RETURNING *""",
                (datos.id_cliente_ref, mac, datos.serial_number, datos.ip_asignada, datos.puerto_olt,
                 datos.potencia_optica_dbm)).fetchone()
    except psycopg.errors.UniqueViolation:
        raise HTTPException(409, "La MAC ya está asignada a otro suscriptor")
    fila["clasificacion_senal"] = logic.clasificar_senal(datos.potencia_optica_dbm)
    return fila


@app.get("/api/onus/criticas")
def onus_senal_critica(user: dict = Depends(requiere_rol(*PERSONAL))):
    with get_conn(ESQUEMA) as c:
        filas = c.execute("SELECT * FROM vw_onus_senal_critica ORDER BY potencia_optica_dbm").fetchall()
    for f in filas:
        f["clasificacion_senal"] = logic.clasificar_senal(float(f["potencia_optica_dbm"]))
    return filas


@app.post("/api/onus/estado")
def actualizar_estado_onu(datos: CambioEstadoOnu, user: dict = Depends(requiere_rol(*OPERACION))):
    if datos.nuevo_estado not in logic.ESTADOS_ONU:
        raise HTTPException(422, "Estado de ONU no válido")
    with get_conn(ESQUEMA) as c:
        c.execute("CALL sp_actualizar_estado_onu(%s, %s)", (datos.id_cliente, datos.nuevo_estado))
        filas = c.execute("SELECT id_onu, mac_address, estado_conexion FROM dispositivos_onu WHERE id_cliente_ref = %s",
                          (datos.id_cliente,)).fetchall()
    if not filas:
        raise HTTPException(404, "El cliente no tiene ONUs registradas")
    return filas
