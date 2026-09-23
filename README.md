# Fiver Cable DevOps Demo

Prototipo académico para demostrar una implementación inicial de DevOps 1 mediante cuatro microservicios Spring Boot contenedorizados.

## Alcance

El repositorio demuestra estructura, compilación, pruebas, contenedores y automatización. No es una implementación productiva ni utiliza información real de Fiver Cable.

## Microservicios

| Servicio | Endpoint | Puerto |
|---|---|---:|
| auth-service | http://localhost:8081/health | 8081 |
| red-service | http://localhost:8082/health | 8082 |
| soporte-service | http://localhost:8083/health | 8083 |
| pagos-service | http://localhost:8084/health | 8084 |

## Requisitos

- Git
- Docker Desktop con Docker Compose
- Visual Studio Code
- Java 17 y Maven 3.9, únicamente si se desea ejecutar fuera de Docker

## Ejecutar con Docker

```bash
docker compose up --build
```

En otra terminal:

```bash
docker compose ps
```

Validar los endpoints:

```bash
sh tests/validar-endpoints.sh
```

Detener los servicios:

```bash
docker compose down
```

## Ejecutar las pruebas con Maven

```bash
mvn clean test
```

## Control de versiones

```bash
git status
git branch
git log --oneline
```

## Archivos importantes para explicar

- `src/`: código independiente de los cuatro microservicios.
- `docker/`: Dockerfile de cada servicio.
- `docker-compose.yml`: construye y levanta todo el prototipo.
- `azure-pipelines.yml`: pipeline para Azure DevOps.
- `.github/workflows/ci.yml`: pipeline equivalente para GitHub Actions.
- `docs/ARQUITECTURA.md`: responsabilidades y alcance.
- `docs/GUION_VIDEO.md`: guion listo para grabar.

