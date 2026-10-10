# Guion de demostración de las aplicaciones

Este guion sirve para la demostración en vivo de la exposición. Cubre las tres aplicaciones del proyecto: el portal de cobro, el prototipo web y las APIs. Hay videos de respaldo grabados de la ejecución real en [evidencias/videos](evidencias/videos/).

| Aplicación | Dirección | Qué demuestra | Video de respaldo |
|---|---|---|---|
| Portal de cobro en campo (producción local) | `http://localhost:3003/portal` | Proceso automatizado con las APIs y PostgreSQL | [demo-portal-cobro.mp4](evidencias/videos/demo-portal-cobro.mp4) (52 s) |
| Prototipo web por perfiles | `prototipo/index.html` | Experiencia de cada rol de la empresa | [demo-prototipo-roles.mp4](evidencias/videos/demo-prototipo-roles.mp4) (59 s) |
| APIs (OpenAPI) | `http://localhost:3000/docs` a `:3003/docs` | Servicios, endpoints y estado | Incluido en el video del portal |

---

## Preparación (10 minutos antes)

1. Abrir **Docker Desktop** y esperar a que diga *Engine running*.
2. En la terminal de VS Code, dentro de la carpeta del proyecto, reiniciar los datos para que las facturas de demostración vuelvan a estar pendientes:
   ```powershell
   docker compose down -v
   docker compose up -d --build --wait
   docker compose ps
   ```
   Los seis contenedores deben aparecer como `healthy` o `Up`.
3. Abrir estas pestañas en el navegador, en este orden:
   1. `http://localhost:3003/health`
   2. `http://localhost:3003/portal`
   3. `http://localhost:3003/api/facturas?id_cliente=1`
   4. `prototipo/index.html` (doble clic en el archivo)
   5. La presentación
4. Dejar los dos videos abiertos en otra ventana, por si algo falla.
5. Cerrar el archivo `.env` y cualquier ventana que muestre contraseñas.
6. Subir el zoom del navegador a 125 % para que se lea desde el fondo del salón.

---

## Demo 1: Portal de cobro en campo (2 min 30 s) · aplicación en producción

| # | Acción | Qué decir |
|---|---|---|
| 1 | Mostrar la terminal con `docker compose ps` | "La aplicación corre en contenedores: PostgreSQL y cuatro microservicios, todos sanos." |
| 2 | Pestaña `/health` | "Cada servicio reporta su estado y la conexión a su base de datos." |
| 3 | Pestaña `/portal`, escribir el correo del técnico y una contraseña **incorrecta** | "Si la contraseña es incorrecta, no entra, y el mensaje no revela si el correo existe." |
| 4 | Iniciar sesión con la cuenta técnica de demostración (escribir la contraseña sin mostrarla) | "El sistema entrega un token firmado que expira en 60 minutos." |
| 5 | Código de cliente **2**, método **Tarjeta**, campo de autorización vacío, **Buscar facturas** | "Aparecen sus dos facturas pendientes." |
| 6 | Seleccionar **Cobrar Q 499.00** | "Con tarjeta, el sistema exige el código de autorización. La API rechaza el cobro." |
| 7 | Cambiar a **Efectivo**, **Buscar facturas**, **Cobrar** | "Cobro registrado: la factura pasa a Pagado y se genera el recibo único FC-…" |
| 8 | **Buscar facturas** otra vez | "La factura pagada desaparece de las pendientes. No se puede cobrar dos veces." |
| 9 | **Cerrar sesión** | "La sesión se borra de la memoria del navegador." |
| 10 | Pestaña `/api/facturas?id_cliente=1` | "Sin token, la API responde 401. Nadie consulta datos sin autenticarse." |

**Si alguien pregunta por la base de datos** (opcional, 20 s):

```powershell
docker exec fiver_postgres psql -U postgres -d fivercable_db -c "SELECT id_factura, estado_pago FROM billing_db.facturas_fel;"
```

---

## Demo 2: Prototipo web por perfiles (1 min, opcional si sobra tiempo)

Abrir `prototipo/index.html`. Si el tiempo es corto, mostrar solo los pasos 1, 3 y 5, o reproducir el video de 59 segundos sin audio mientras se explica.

| # | Perfil | Acción | Qué decir |
|---|---|---|---|
| 1 | Cliente | **Cliente** → **Ingresar** → **Facturas** → **Ver detalle** → **Pagar ahora** → **Continuar** → **Confirmar pago** | "El cliente también podrá pagar desde su cuenta." |
| 2 | Cliente | **Soporte** → falla *Sin señal* → **Enviar reporte** | "Reporta una falla y recibe su número de ticket." |
| 3 | Técnico | **Técnico** → **Ingresar** → **Iniciar visita** → **Registrar cobro** → **Confirmar cobro** | "La visión móvil del técnico: rutas del día y cobro." |
| 4 | Administrador | **Inventario** → **Registrar** un equipo; repetir la misma serie | "No se permite repetir la serie de un equipo." |
| 5 | Jefatura | **Jefatura** → **Ingresar** | "Indicadores de la operación para la toma de decisiones." |
| 6 | Secretaría | **Agendar visita técnica** → **Programar visita** | "Coordinación de visitas desde oficina." |

> Aclaración para la exposición: el prototipo funciona con datos simulados en el navegador. El flujo real conectado a la base de datos es el del portal (Demo 1). Los perfiles Jefatura y Secretaría todavía no tienen permisos en la API.

---

## Plan B

| Problema | Qué hacer |
|---|---|
| Docker no arranca o el portal no carga | Reproducir `demo-portal-cobro.mp4` y explicar sobre el video |
| No hay facturas pendientes (ya se cobraron en un ensayo) | `docker compose down -v` y `docker compose up -d --wait` (tarda unos 30 s) |
| "No se pudo conectar con autenticación" | Verificar que `ms_auth` esté en `docker compose ps`; si no, `docker compose up -d ms_auth` |
| Se acaba el tiempo | Saltar el Demo 2 y pasar a la diapositiva de seguridad |

## Regenerar las capturas de evidencia

```powershell
docker compose down -v; docker compose up -d --wait
python docs/evidencias/capturar_evidencias.py
```
