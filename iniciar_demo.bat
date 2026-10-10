@echo off
REM Prepara la demostracion: reinicia los datos, levanta los servicios y abre el portal
cd /d "%~dp0"
docker info >/dev/null 2>&1
if errorlevel 1 (
  echo Docker Desktop no esta activo. Abralo, espere a que diga "Engine running" y ejecute de nuevo este archivo.
  pause
  exit /b 1
)
if not exist .env copy .env.example .env >nul
echo Reiniciando los datos de demostracion...
docker compose down -v
docker compose up -d --build --wait
if errorlevel 1 (
  echo Algun servicio no inicio. Revise con: docker compose ps
  pause
  exit /b 1
)
docker compose ps
echo.
echo Listo. Portal: http://localhost:3003/portal
start "" http://localhost:3003/portal
pause
