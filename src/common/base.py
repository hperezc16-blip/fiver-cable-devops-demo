"""Utilidades compartidas: conexión a PostgreSQL por esquema, JWT y app base.

Cada microservicio se conecta al mismo motor PostgreSQL pero fija su propio
search_path (patrón database-per-service por esquema, Entregable 8).
"""
from __future__ import annotations

import os
import time
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime, timedelta, timezone
from typing import Generator

import jwt
import psycopg
from psycopg import sql
from psycopg_pool import ConnectionPool, PoolTimeout
from psycopg.rows import dict_row
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

JWT_ALG = "HS256"
_pool: ConnectionPool | None = None

# Grupos de roles usados por las dependencias requiere_rol de los microservicios
PERSONAL = ("Tecnico", "Administrador", "Jefatura", "Secretaria")
COBRADORES = ("Tecnico", "Administrador", "Secretaria")
OPERACION = ("Tecnico", "Administrador")


def jwt_secret() -> str:
    return os.getenv("JWT_SECRET", "dev-fivercable-cambiar-en-staging-y-produccion-2026")


def database_url() -> str:
    return os.getenv(
        "DATABASE_URL",
        "postgresql://{u}:{p}@{h}:{port}/{db}".format(
            u=os.getenv("DB_USER", "postgres"),
            p=os.getenv("DB_PASSWORD", "admin123"),
            h=os.getenv("DB_HOST", "localhost"),
            port=os.getenv("DB_PORT", "5432"),
            db=os.getenv("DB_NAME", "fivercable_db"),
        ),
    )


@contextmanager
def get_conn(schema: str) -> Generator[psycopg.Connection, None, None]:
    """Toma una conexión del pool con el esquema limitado a la transacción."""
    if _pool is None:
        raise RuntimeError("El pool de base de datos no está iniciado")

    try:
        with _pool.connection(timeout=float(os.getenv("DB_POOL_TIMEOUT_SECONDS", "10"))) as conn:
            conn.execute(sql.SQL("SET LOCAL search_path TO {}").format(sql.Identifier(schema)))
            yield conn
    except PoolTimeout as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Servicio ocupado; intente nuevamente",
            headers={"Retry-After": "1"},
        ) from exc


def open_connection_pool() -> None:
    global _pool
    if _pool is not None:
        return

    min_size = int(os.getenv("DB_POOL_MIN_SIZE", "1"))
    max_size = int(os.getenv("DB_POOL_MAX_SIZE", "5"))
    timeout = float(os.getenv("DB_POOL_TIMEOUT_SECONDS", "10"))
    if min_size < 0 or max_size < 1 or min_size > max_size or timeout <= 0:
        raise ValueError("Configuración inválida del pool de base de datos")

    pool = ConnectionPool(
        conninfo=database_url(),
        kwargs={"row_factory": dict_row, "autocommit": False},
        min_size=min_size,
        max_size=max_size,
        timeout=timeout,
        open=False,
    )
    try:
        pool.open(wait=True)
    except Exception:
        pool.close()
        raise
    _pool = pool


def close_connection_pool() -> None:
    global _pool
    pool, _pool = _pool, None
    if pool is not None:
        pool.close()


def crear_token(sub: int, rol: str, correo: str, minutos: int = 60) -> str:
    ahora = datetime.now(timezone.utc)
    payload = {"sub": str(sub), "rol": rol, "correo": correo,
               "iat": ahora, "exp": ahora + timedelta(minutes=minutos)}
    return jwt.encode(payload, jwt_secret(), algorithm=JWT_ALG)


def decodificar_token(token: str) -> dict:
    return jwt.decode(token, jwt_secret(), algorithms=[JWT_ALG])


_bearer = HTTPBearer(auto_error=False)


def usuario_actual(cred: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> dict:
    if cred is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token requerido")
    try:
        return decodificar_token(cred.credentials)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token expirado")
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token inválido")


def requiere_rol(*roles: str):
    def _dep(user: dict = Depends(usuario_actual)) -> dict:
        if user.get("rol") not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Rol sin permiso para esta operación")
        return user
    return _dep


def crear_app(nombre: str, esquema: str, version: str = "2.0.0") -> FastAPI:
    @asynccontextmanager
    async def lifespan(_application: FastAPI):
        open_connection_pool()
        _application.state.database_pool = _pool
        try:
            yield
        finally:
            close_connection_pool()
            _application.state.database_pool = None

    app = FastAPI(title=f"Fiver Cable - {nombre}", version=version, lifespan=lifespan)
    cors_origins = [
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "").split(",")
        if origin.strip()
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_methods=["*"], allow_headers=["*"],
    )
    arranque = time.time()

    @app.exception_handler(Exception)
    async def _error_generico(request: Request, exc: Exception):  # no filtrar trazas
        return JSONResponse(status_code=500, content={"detail": "Error interno del servicio"})

    @app.get("/health", tags=["operación"])
    def health():
        db_ok = True
        try:
            with get_conn(esquema) as c:
                c.execute("SELECT 1")
        except Exception:
            db_ok = False
        return {"servicio": nombre, "esquema": esquema, "version": version,
                "estado": "OK" if db_ok else "DEGRADADO", "db": db_ok,
                "uptime_s": round(time.time() - arranque, 1)}

    return app
