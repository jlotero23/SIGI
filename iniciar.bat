
@echo off
echo ========================================
echo  Sistema IA - Reabastecimiento
echo ========================================
echo.

cd /d "%~dp0"

echo [1/3] Verificando entorno Python...
py -m ensurepip --upgrade 2>nul
py -m pip install -r requirements.txt -q

echo [2/3] Iniciando Backend (FastAPI) en puerto 8000...
start "Backend API" cmd /k "cd backend && py -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

timeout /t 3 /nobreak >nul

echo [3/3] Iniciando Dashboard (React) en puerto 5173...
cd dashboard
if not exist node_modules (
    echo Instalando dependencias del dashboard...
    call npm install
)
start "Dashboard" cmd /k "npm run dev"

echo.
echo ========================================
echo  Sistema iniciado correctamente
echo  Backend:   http://localhost:8000
echo  Dashboard: http://localhost:5173
echo  API Docs:  http://localhost:8000/docs
echo ========================================
echo.
echo Para WhatsApp (opcional):
echo   cd whatsapp ^&^& npm install ^&^& npm start
echo.
pause
