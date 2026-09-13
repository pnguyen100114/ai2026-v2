@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Chua co moi truong Python .venv.
  echo Hay chay "Cai dat AI Gia Su.bat" truoc.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" backend\train_model.py
copy /Y "runs\posture-demo\weights\best.pt" "sitting posture.v4-sitting_posture_4keypoint.yolov8\best.pt" >nul
echo Da cap nhat best.pt trong thu muc model.
pause
