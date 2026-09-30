"""Pruebas de RENDIMIENTO básicas (línea base del Sprint 2).

Umbrales configurables por variables de entorno para que el pipeline los ajuste por entorno.
"""
import os
import statistics
import time
from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest

from tests.conftest import CATALOGO, PAGOS, auth

pytestmark = pytest.mark.performance
P95_MAX_MS = float(os.getenv("PERF_P95_MAX_MS", "300"))


def _medir(cliente, url, headers=None):
    t0 = time.perf_counter()
    r = cliente.get(url, headers=headers)
    return (time.perf_counter() - t0) * 1000, r.status_code


@pytest.mark.caso("CP-25", "Catálogo de planes: 200 solicitudes secuenciales con p95 < umbral")
def test_latencia_catalogo():
    with httpx.Client(timeout=5) as c:
        muestras = [_medir(c, f"{CATALOGO}/api/planes") for _ in range(200)]
    tiempos = sorted(t for t, _ in muestras)
    p95 = tiempos[int(len(tiempos) * 0.95) - 1]
    print(f"\nCP-25 promedio={statistics.mean(tiempos):.1f} ms p95={p95:.1f} ms max={max(tiempos):.1f} ms")
    assert all(s == 200 for _, s in muestras)
    assert p95 < P95_MAX_MS


@pytest.mark.caso("CP-26", "Consulta de facturas con 20 técnicos concurrentes sin errores")
def test_concurrencia_facturas(token_tecnico):
    url = f"{PAGOS}/api/facturas?id_cliente=2"
    with httpx.Client(timeout=10) as c, ThreadPoolExecutor(max_workers=20) as ex:
        resultados = list(ex.map(lambda _: _medir(c, url, auth(token_tecnico)), range(200)))
    tiempos = sorted(t for t, _ in resultados)
    p95 = tiempos[int(len(tiempos) * 0.95) - 1]
    errores = sum(1 for _, s in resultados if s != 200)
    print(f"\nCP-26 solicitudes=200 concurrencia=20 p95={p95:.1f} ms errores={errores}")
    assert errores == 0
    assert p95 < P95_MAX_MS * 3
