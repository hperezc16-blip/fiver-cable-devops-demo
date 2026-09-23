# Arquitectura propuesta

Este repositorio demuestra una arquitectura inicial de cuatro microservicios independientes para Fiver Cable.

| Servicio | Responsabilidad | Puerto |
|---|---|---:|
| auth-service | Usuarios y autenticación | 8081 |
| red-service | Equipos y aprovisionamiento de red | 8082 |
| soporte-service | Tickets y soporte técnico | 8083 |
| pagos-service | Cobros, pagos y comprobantes | 8084 |

Cada servicio se compila y ejecuta de forma independiente. Docker Compose coordina su construcción y arranque para fines de demostración. Esta entrega es un prototipo académico y no representa una instalación productiva dentro de Fiver Cable.

