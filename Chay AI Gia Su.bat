@echo off
setlocal EnableExtensions
title Gia Su AI - Khoi dong
cd /d "%~dp0"

if not exist "package.json" (
  echo [LOI] Khong tim thay project.
  echo Hay nhap lai file "Cai dat AI Gia Su.bat" de tai project tu GitHub.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo Chua co moi truong Python. Dang cai tu dong...
  call "%~dp0Cai dat AI Gia Su.bat"
  exit /b %errorlevel%
)

if not exist "node_modules\vite\bin\vite.js" (
  echo Chua co thu vien giao dien. Dang cai tu dong...
  call "%~dp0Cai dat AI Gia Su.bat"
  exit /b %errorlevel%
)

rem Luon khoi dong lai backend: ban dang chay co the la code cu (bat truoc khi sua hoac cap nhat).
echo Dang tat backend cu (neu co)...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\restart-backend.ps1" -StopOnly
if errorlevel 1 (
  echo [LOI] Cong 8000 dang bi chuong trinh khac giu, khong tat duoc.
  pause
  exit /b 1
)
echo Dang khoi dong backend...
start "Gia Su AI - Backend" /min powershell -NoProfile -ExecutionPolicy Bypass -NoExit -File "%~dp0scripts\restart-backend.ps1"
for /l %%i in (1,1,60) do (
  powershell -NoProfile -ExecutionPolicy Bypass -Command "try { $r = Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:8000/api/health' -TimeoutSec 1; if ($r.StatusCode -eq 200) { exit 0 } } catch { exit 1 }"
  if not errorlevel 1 goto :backend_ready
  timeout /t 1 /nobreak >nul
)
echo [LOI] Backend chua khoi dong duoc.
echo Hay xem cua so Backend de biet loi chi tiet.
pause
exit /b 1

:backend_ready
echo Dang kiem tra giao dien...
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { $r = Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:5173/' -TimeoutSec 2; if ($r.StatusCode -eq 200) { exit 0 } } catch { exit 1 }"
if errorlevel 1 (
  echo Dang khoi dong giao dien...
  start "Gia Su AI - Frontend" /min cmd /k "cd /d ""%~dp0"" && call npm run dev -- --host 127.0.0.1"
  for /l %%i in (1,1,60) do (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "try { $r = Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:5173/' -TimeoutSec 1; if ($r.StatusCode -eq 200) { exit 0 } } catch { exit 1 }"
    if not errorlevel 1 goto :frontend_ready
    timeout /t 1 /nobreak >nul
  )
  echo [LOI] Giao dien chua khoi dong duoc.
  echo Hay xem cua so Frontend de biet loi chi tiet.
  pause
  exit /b 1
) else (
  echo Giao dien dang chay.
)

:frontend_ready
start "" "http://127.0.0.1:5173/"
echo.
echo ============================================================
echo SAN PHAM DA SAN SANG
echo Website: http://127.0.0.1:5173/
echo API:     http://127.0.0.1:8000/api/health
echo.
echo Co the dong cua so nay.
echo Khong dong cac cua so Backend va Frontend dang chay ngam.
echo ============================================================
timeout /t 8 /nobreak >nul
exit /b 0
