@echo off
REM Ejecuta las pruebas de Selenium sobre el prototipo con el navegador visible
python -m pip install -r requirements-selenium.txt
set HEADLESS=0
set PAUSA=1
python -m pytest tests/acceptance -v --html=reports/reporte-selenium.html --self-contained-html
pause
