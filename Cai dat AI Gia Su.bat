@echo off
setlocal EnableExtensions
title Gia Su AI - Tai va cai dat tu dong

set "REPO_URL=https://github.com/xuanbachnguyen2013-dotcom/AI2026-v2.git"
set "BRANCH=main"
set "INSTALL_DIR=%USERPROFILE%\Gia Su AI v2"
set "SCRIPT_DIR=%~dp0"

echo.
echo ============================================================
echo       GIA SU AI - TAI VA CAI DAT TU DONG
echo ============================================================
echo.
echo Script se tai project tu GitHub, cai thu vien va mo website.
echo Vui long giu cua so nay mo den khi thay thong bao hoan tat.
echo.

where node >nul 2>nul
if errorlevel 1 (
  echo [LOI] Chua cai Node.js.
  echo Hay tai Node.js ban LTS tai: https://nodejs.org/
  pause
  exit /b 1
)

where npm >nul 2>nul
if errorlevel 1 (
  echo [LOI] Khong tim thay npm. Hay cai Node.js ban LTS.
  pause
  exit /b 1
)

where git >nul 2>nul
if errorlevel 1 (
  echo [LOI] Chua cai Git.
  echo Hay tai Git tai: https://git-scm.com/download/win
  echo Sau khi cai xong, nhap lai file BAT nay.
  pause
  exit /b 1
)

where py >nul 2>nul
if not errorlevel 1 goto :python_ready
where python >nul 2>nul
if not errorlevel 1 goto :python_ready

echo [LOI] Chua cai Python.
echo Hay tai Python 3.12 tai: https://www.python.org/downloads/
echo Khi cai, nho chon "Add python.exe to PATH".
pause
exit /b 1

:python_ready
rem Neu BAT dang nam trong project, dung luon project hien tai.
if exist "%SCRIPT_DIR%package.json" (
  set "INSTALL_DIR=%SCRIPT_DIR%"
  goto :project_ready
)

echo [1/5] Dang tai project tu GitHub...
if exist "%INSTALL_DIR%\.git" (
  echo Project da ton tai, dang cap nhat phien ban moi...
  git -C "%INSTALL_DIR%" fetch origin "%BRANCH%"
  if errorlevel 1 goto :download_failed
  git -C "%INSTALL_DIR%" reset --hard "origin/%BRANCH%"
  if errorlevel 1 goto :download_failed
) else (
  if exist "%INSTALL_DIR%" (
    echo Thu muc dich da ton tai nhung khong phai Git repository.
    echo Hay doi ten hoac xoa thu muc:
    echo %INSTALL_DIR%
    pause
    exit /b 1
  )
  git clone --depth 1 --branch "%BRANCH%" "%REPO_URL%" "%INSTALL_DIR%"
  if errorlevel 1 goto :download_failed
)

:project_ready
cd /d "%INSTALL_DIR%"
if not exist "src\App.tsx" goto :project_incomplete
if not exist "backend\app.py" goto :project_incomplete
if not exist "backend\requirements.txt" goto :project_incomplete
if not exist "backend\.env" (
  echo [CANH BAO] Khong co backend\.env trong repository.
  echo Hay chep backend\.env.example thanh backend\.env va dien GEMINI_API_KEY.
  echo Khong co key thi giao dien van mo duoc nhung Mimo se khong tra loi.
)

echo.
echo Dang dung Gia Su AI dang chay (neu co) de tranh khoa file...
call :stop_running_app

echo.
echo [2/5] Dang cai thu vien giao dien...
call :npm_install
if errorlevel 1 (
  echo Cai lan 1 that bai, doi 5 giay roi thu lai...
  call :stop_running_app
  timeout /t 5 /nobreak >nul
  call :npm_install
)
if errorlevel 1 goto :install_failed

echo.
echo [3/5] Dang tao moi truong Python...
if not exist ".venv\Scripts\python.exe" (
  rem PyMuPDF co wheel on CPython thuong; uu tien Python 3.13 neu may da cai.
  py -3.13 -m venv ".venv" >nul 2>nul
  if errorlevel 1 py -3 -m venv ".venv" >nul 2>nul
  if errorlevel 1 python -m venv ".venv"
  if errorlevel 1 goto :install_failed
)

echo.
echo [4/5] Dang cai thu vien backend...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto :install_failed
".venv\Scripts\python.exe" -m pip install -r "backend\requirements.txt"
if errorlevel 1 goto :install_failed

echo.
echo [5/5] Dang kiem tra build giao dien...
call npm run build
if errorlevel 1 goto :install_failed

echo.
echo ============================================================
echo TAI VA CAI DAT HOAN TAT
echo Dang khoi dong san pham...
echo ============================================================
call "%INSTALL_DIR%\Chay AI Gia Su.bat"
exit /b %errorlevel%

:npm_install
if exist "package-lock.json" (
  call npm ci --no-audit --no-fund
) else (
  call npm install --no-audit --no-fund
)
exit /b %errorlevel%

:stop_running_app
rem Dung frontend (cong 5173), backend (cong 8000) va moi tien trinh chay tu thu muc project
rem (vd. .venv\Scripts\python.exe), vi chung khoa file trong node_modules va .venv.
powershell -NoProfile -ExecutionPolicy Bypass -Command "$d=(Resolve-Path $env:INSTALL_DIR).Path.TrimEnd('\'); $ids=@(); $ids+=Get-NetTCPConnection -State Listen -LocalPort 5173,8000 -ErrorAction SilentlyContinue | Where-Object { (Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue).ProcessName -match '^(node|python|py)$' } | Select-Object -ExpandProperty OwningProcess; $ids+=Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -and $_.ExecutablePath.StartsWith($d, [StringComparison]::OrdinalIgnoreCase) } | Select-Object -ExpandProperty ProcessId; $ids | Where-Object { $_ -gt 0 } | Sort-Object -Unique | ForEach-Object { taskkill /PID $_ /T /F 2>$null | Out-Null }; Start-Sleep -Seconds 1"
exit /b 0

:download_failed
echo [LOI] Khong tai duoc project tu GitHub.
echo Hay kiem tra Internet va thu lai.
pause
exit /b 1

:project_incomplete
echo [LOI] Repository GitHub thieu file can thiet cua san pham.
echo Can co:
echo   src\App.tsx
echo   backend\app.py
echo   backend\requirements.txt
echo Hay push day du project len repository:
echo %REPO_URL%
pause
exit /b 1

:install_failed
echo [LOI] Cai dat that bai. Xem thong bao phia tren de biet chi tiet.
pause
exit /b 1
