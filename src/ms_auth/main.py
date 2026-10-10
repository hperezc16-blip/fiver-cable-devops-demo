"""ms_auth -> esquema usuarios_db. Autenticación JWT, registro y estado de suscriptores."""
from fastapi import Depends, HTTPException, status
from pydantic import BaseModel, Field
import psycopg

from src.common.base import crear_app, crear_token, get_conn, requiere_rol, usuario_actual
from src.ms_auth import logic

ESQUEMA = "usuarios_db"
app = crear_app("ms_auth", ESQUEMA)


class Registro(BaseModel):
    id_plan_ref: int = Field(gt=0)
    dpi_nit: str
    nombres: str = Field(min_length=1, max_length=100)
    apellidos: str = Field(min_length=1, max_length=100)
    direccion_instalacion: str = Field(min_length=3)
    telefono: str = Field(pattern=r"^\d{8,15}$")
    correo: str
    password: str


class Login(BaseModel):
    correo: str
    password: str


class CambioPassword(BaseModel):
    password_actual: str = Field(min_length=1, max_length=128)
    password_nueva: str = Field(min_length=1, max_length=128)


class CambioEstado(BaseModel):
    estado_servicio: str


@app.post("/api/auth/registro", status_code=201)
def registrar(datos: Registro):
    if not logic.validar_correo(datos.correo):
        raise HTTPException(422, "Correo inválido")
    if not logic.validar_nit(datos.dpi_nit):
        raise HTTPException(422, "NIT/DPI inválido")
    if not logic.validar_password(datos.password):
        raise HTTPException(422, "La contraseña no cumple la política (8+ caracteres, mayúscula, minúscula y número)")
    try:
        with get_conn(ESQUEMA) as c:
            fila = c.execute(
                """INSERT INTO clientes (id_plan_ref, dpi_nit, nombres, apellidos, direccion_instalacion,
                   telefono, correo, password_hash, rol)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'Suscriptor') RETURNING id_cliente, correo, rol, estado_servicio""",
                (datos.id_plan_ref, datos.dpi_nit, datos.nombres, datos.apellidos, datos.direccion_instalacion,
                 datos.telefono, datos.correo.lower(), logic.hash_password(datos.password)),
            ).fetchone()
    except psycopg.errors.UniqueViolation:
        raise HTTPException(409, "El correo ya está registrado")
    return fila


@app.post("/api/auth/login")
def login(datos: Login):
    with get_conn(ESQUEMA) as c:
        u = c.execute("SELECT id_cliente, correo, password_hash, rol, estado_servicio FROM clientes WHERE correo = %s",
                      (datos.correo.lower(),)).fetchone()
    if not u or not logic.verificar_password(datos.password, u["password_hash"]):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciales inválidas")
    if u["estado_servicio"] == "Inactivo":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cuenta inactiva")
    return {"access_token": crear_token(u["id_cliente"], u["rol"], u["correo"]),
            "token_type": "bearer", "rol": u["rol"], "id_cliente": u["id_cliente"]}


@app.put("/api/auth/cambiar-password")
def cambiar_password(datos: CambioPassword, user: dict = Depends(usuario_actual)):
    if not logic.validar_password(datos.password_nueva):
        raise HTTPException(422, "La contraseña nueva debe tener 8+ caracteres, mayúscula, minúscula y número")

    with get_conn(ESQUEMA) as c:
        fila = c.execute(
            "SELECT password_hash FROM clientes WHERE id_cliente = %s",
            (int(user["sub"]),),
        ).fetchone()
        if not fila:
            raise HTTPException(404, "Cuenta no encontrada")
        if not logic.verificar_password(datos.password_actual, fila["password_hash"]):
            raise HTTPException(401, "La contraseña actual es incorrecta")
        if logic.verificar_password(datos.password_nueva, fila["password_hash"]):
            raise HTTPException(422, "La contraseña nueva debe ser distinta a la actual")

        c.execute(
            "UPDATE clientes SET password_hash = %s WHERE id_cliente = %s",
            (logic.hash_password(datos.password_nueva), int(user["sub"])),
        )

    return {"mensaje": "Contraseña actualizada"}


@app.get("/api/clientes/{id_cliente}")
def obtener_cliente(id_cliente: int, user: dict = Depends(usuario_actual)):
    if user["rol"] == "Suscriptor" and int(user["sub"]) != id_cliente:
        raise HTTPException(403, "Solo puede consultar su propio perfil")
    with get_conn(ESQUEMA) as c:
        fila = c.execute(
            """SELECT id_cliente, id_plan_ref, dpi_nit, nombres, apellidos, direccion_instalacion, telefono,
                      correo, estado_servicio, rol, fecha_registro FROM clientes WHERE id_cliente = %s""",
            (id_cliente,)).fetchone()
    if not fila:
        raise HTTPException(404, "Cliente no encontrado")
    return fila


@app.patch("/api/clientes/{id_cliente}/estado")
def cambiar_estado(id_cliente: int, datos: CambioEstado,
                   user: dict = Depends(requiere_rol("Tecnico", "Administrador"))):
    if datos.estado_servicio not in logic.ESTADOS:
        raise HTTPException(422, "Estado no válido")
    with get_conn(ESQUEMA) as c:
        actual = c.execute("SELECT estado_servicio FROM clientes WHERE id_cliente = %s", (id_cliente,)).fetchone()
        if not actual:
            raise HTTPException(404, "Cliente no encontrado")
        if not logic.transicion_valida(actual["estado_servicio"], datos.estado_servicio):
            raise HTTPException(409, f"Transición no permitida: {actual['estado_servicio']} -> {datos.estado_servicio}")
        c.execute("UPDATE clientes SET estado_servicio = %s WHERE id_cliente = %s",
                  (datos.estado_servicio, id_cliente))
    return {"id_cliente": id_cliente, "estado_anterior": actual["estado_servicio"],
            "estado_nuevo": datos.estado_servicio}


@app.get("/api/suscriptores/activos")
def suscriptores_activos(user: dict = Depends(requiere_rol("Tecnico", "Administrador"))):
    with get_conn(ESQUEMA) as c:
        return c.execute("SELECT * FROM vw_suscriptores_activos ORDER BY id_cliente").fetchall()
