# Guion breve para el video de implementación DevOps 1

## Introducción

Buen día. Somos el equipo responsable de la propuesta de transformación digital para Fiver Cable. En este video presentaremos un prototipo académico de DevOps 1 compuesto por cuatro microservicios Spring Boot, control de versiones, contenedores Docker, pruebas automatizadas y un pipeline de integración continua. El prototipo demuestra la base técnica para un desarrollo futuro y no representa una implementación productiva dentro de la empresa.

## Demostración

1. Mostrar el repositorio y el historial de Git.
2. Abrir la carpeta `src` y explicar los cuatro microservicios.
3. Abrir el controlador `HealthController` de uno de los servicios.
4. Mostrar los cuatro Dockerfiles.
5. Abrir `docker-compose.yml` y explicar los puertos.
6. Ejecutar `docker compose up --build`.
7. Ejecutar `docker compose ps`.
8. Visitar los cuatro endpoints `/health`.
9. Mostrar `azure-pipelines.yml` y explicar las etapas de compilación, pruebas y construcción de imágenes.
10. Ejecutar `docker compose down`.

## Conclusión

Con esta demostración se estableció una base organizada para el desarrollo futuro de Fiver Cable. Los servicios pueden construirse de manera independiente, Docker estandariza su ejecución y el pipeline permite verificar automáticamente el código. Las funciones empresariales completas y el despliegue productivo corresponden a etapas posteriores, sujetas a la aprobación de la propuesta.

