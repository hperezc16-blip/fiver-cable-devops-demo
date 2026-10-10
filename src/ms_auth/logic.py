"""Reglas de negocio puras de ms_auth (sin BD) -> objeto de las pruebas unitarias."""
import re

import bcrypt

ROLES = {"Suscriptor", "Tecnico", "Administrador", "Jefatura", "Secretaria"}
ROLES_PERSONAL = ROLES - {"Suscriptor"}
ESTADOS = {"Activo", "Moroso", "Suspendido", "Inactivo"}
# Transiciones permitidas del estado de servicio del suscriptor
TRANSICIONES = {
    "Activo": {"Moroso", "Suspendido", "Inactivo"},
    "Moroso": {"Activo", "Suspendido"},
    "Suspendido": {"Activo", "Inactivo"},
    "Inactivo": {"Activo"},
}

_CORREO = re.compile(r"^[\w.+-]+@[\w-]+(\.[\w-]+)+$")


def validar_correo(correo: str) -> bool:
    return bool(correo) and len(correo) <= 100 and bool(_CORREO.match(correo))


def validar_nit(nit: str) -> bool:
    """NIT guatemalteco (dígitos + dígito verificador numérico o K), 'CF' o DPI de 13 dígitos."""
    if not nit:
        return False
    nit = nit.replace("-", "").upper().strip()
    if nit == "CF":
        return True
    if re.fullmatch(r"\d{13}", nit):  # DPI
        return True
    if not re.fullmatch(r"\d{1,12}[\dK]", nit):
        return False
    cuerpo, verificador = nit[:-1], nit[-1]
    total = sum(int(d) * (len(cuerpo) + 1 - i) for i, d in enumerate(cuerpo))
    esperado = (11 - (total % 11)) % 11
    return verificador == ("K" if esperado == 10 else str(esperado))


def validar_password(pw: str) -> bool:
    """Mínimo 8 caracteres, una mayúscula, una minúscula y un número."""
    return (len(pw) >= 8 and re.search(r"[A-Z]", pw) is not None
            and re.search(r"[a-z]", pw) is not None and re.search(r"\d", pw) is not None)


def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt(rounds=10)).decode()


def verificar_password(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode(), hashed.encode())
    except ValueError:
        return False


def transicion_valida(actual: str, nuevo: str) -> bool:
    return nuevo in TRANSICIONES.get(actual, set())
