# Fiver Cable - Transformación Digital (DevOps)

Plataforma de microservicios para Fiver Cable (proveedor de internet y cable por fibra óptica).
Proceso prioritario implementado: **cobro digital en campo** (el técnico cobra la factura FEL
desde el celular y el servicio del cliente se reactiva sin pasar por oficina).

Seminario de Tecnologías de Información 2026 - Universidad Mariano Gálvez de Guatemala.

## Arquitectura

| Microservicio | Puerto | Esquema PostgreSQL | Responsabilidad |
|---|---|---|---|
| `ms_auth` | 3000 | `usuarios_db` | Registro, login JWT, roles y estado del suscriptor (auditoría por trigger) |
| `ms_catalogo` | 3001 | `red_db` | Planes de servicio, inventario de ONUs, señal óptica y estado OLT |
| `ms_pedidos` | 3002 | `soporte_db` | Tickets de soporte con prioridad automática y SLA |
| `ms_pagos` | 3003 | `billing_db` | Facturas FEL, pagos, cierre diario y **portal de cobro en campo** (`/portal`) |

- Lenguaje: Python 3.11 + FastAPI - SGBD: PostgreSQL 16 (ambos libres).
- Patrón *database-per-service*: un esquema por microservicio (script en `db/init`).
- Cada servicio expone `/health` y documentación OpenAPI en `/docs`.

## Estructura

```
src/            código de los microservicios (common, ms_auth, ms_catalogo, ms_pedidos, ms_pagos)
db/init/        01_schema.sql (Entregable 8) y 02_seed.sql (datos de prueba)
docker/         Dockerfile por microservicio
tests/          unit, integration, system, acceptance (Selenium), security, performance
infra/azure/    despliegue de Staging en Azure Container Apps
docs/           plan de pruebas y documentación técnica
azure-pipelines.yml   pipeline CI/CD (Checkout -> Build -> Test -> Deploy Staging)
Jenkinsfile           pipeline equivalente para Jenkins
```

## Ejecutar en local

```bash
cp .env.example .env
docker compose up -d --build --wait
# Portal de cobro:  http://localhost:3003/portal
# API docs:         http://localhost:3000/docs  (3001, 3002, 3003)
```

Usuarios de prueba: ver `TEST_*` en `.env.example`.

## Ejecutar las pruebas

```bash
pip install -r requirements-dev.txt
python -m pytest                                  # suite completa
python -m pytest -m unit                          # solo unitarias (no requiere contenedores)
python -m pytest --html=reports/reporte-pruebas.html --self-contained-html --cov=src
```

Marcadores disponibles: `unit`, `integration`, `system`, `acceptance`, `security`, `performance`.
Cada prueba lleva el ID del caso del Plan de Pruebas (`CP-01` ... `CP-26`), visible en el reporte HTML.

## CI/CD en Azure Pipelines

1. Azure DevOps -> Pipelines -> New pipeline -> GitHub -> `fiver-cable-devops` -> *Existing YAML* -> `azure-pipelines.yml`.
2. Cada push a `develop`/`main` ejecuta **Build** (lint, unitarias, imágenes) y **Test** (suite completa, reporte HTML, cobertura).
3. En `main` se ejecuta **Deploy Staging** en el Environment `fivercable-staging`.
   - Por defecto: Staging efímero en el agente con `docker compose` + smoke tests.
   - Con *Run pipeline -> Desplegar Staging en Azure Container Apps = true*: despliega en Azure.
     Requiere una service connection `fivercable-azure` y las variables secretas
     `PG_ADMIN_PASSWORD` y `JWT_SECRET_STAGING`.

## Flujo de ramas

`feature/*` -> Pull Request a `develop` (Build + Test obligatorios) -> Pull Request a `main` -> Deploy Staging.

## Equipo

| Integrante | Carné |
|---|---|
| Hazel Ruvi Perez Carcamo | 0900-21-13727 |
| Byron Enrique Morales | 0900-1015162 |
| Luis Oswaldo Reyes | 0900-98-2342 |
