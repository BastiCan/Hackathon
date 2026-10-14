@echo off
setlocal
title Integra - app local
rem Abre la app en tu computador con un solo proceso liviano:
rem sin Vite, sin recarga automatica y sin instalar nada.
rem Para apagarla, cierra esta ventana.

cd /d "%~dp0backend"

if not exist ".venv\Scripts\python.exe" (
  echo No encuentro el entorno de Python en backend\.venv
  echo Crealo una vez desde la carpeta backend con:
  echo   python -m venv .venv
  echo   .venv\Scripts\python -m pip install -r requirements.txt
  pause
  exit /b 1
)

if not exist "..\frontend\dist\index.html" (
  echo No encuentro las pantallas compiladas en frontend\dist
  echo Compilalas una vez desde la carpeta frontend con: npm run build
  pause
  exit /b 1
)

echo App en http://localhost:8000
echo Para apagarla, cierra esta ventana.
echo.

rem Abre el navegador apenas el servidor responde (SIN_NAVEGADOR=1 lo evita).
if not defined SIN_NAVEGADOR start "" /min powershell -NoProfile -WindowStyle Hidden -Command "for ($i = 0; $i -lt 40; $i++) { try { (New-Object Net.Sockets.TcpClient '127.0.0.1', 8000).Close(); break } catch { Start-Sleep -Milliseconds 500 } }; Start-Process 'http://localhost:8000'"

".venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000

echo.
echo La app se detuvo. Si arriba dice que la direccion ya esta en uso, ya estaba abierta en otra ventana.
pause
