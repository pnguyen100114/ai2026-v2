# Tắt mọi backend đang giữ cổng (kể cả bản do phiên AI khác bật, chạy code cũ) rồi bật lại bằng --reload.
# Chạy: powershell -NoProfile -ExecutionPolicy Bypass -File scripts\restart-backend.ps1
# -StopOnly: chỉ tắt bản cũ rồi thoát (Chay AI Gia Su.bat dùng để chờ cổng trống trước khi bật).
param([int]$Port = 8000, [switch]$StopOnly)

$root = Split-Path $PSScriptRoot -Parent
$python = Join-Path $root '.venv\Scripts\python.exe'

# Tiến trình nghe cổng có thể là tiến trình con (launcher của .venv, worker của --reload).
# Đi ngược lên các tiến trình python cha để tắt cả cây, không thì tiến trình cha bật lại worker.
$roots = foreach ($conn in Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) {
    $id = $conn.OwningProcess
    while ($true) {
        $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$id"
        $parent = if ($proc) { Get-CimInstance Win32_Process -Filter "ProcessId=$($proc.ParentProcessId)" }
        if ($parent -and $parent.Name -like 'python*' -and $parent.CommandLine -match 'uvicorn') { $id = $parent.ProcessId } else { break }
    }
    $id
}
foreach ($id in $roots | Sort-Object -Unique) {
    Write-Host "Tat backend cu PID $id"
    taskkill /PID $id /T /F | Out-Null
}

for ($i = 0; $i -lt 20 -and (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue); $i++) {
    Start-Sleep -Milliseconds 500
}
if (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) {
    Write-Error "Cong $Port van bi giu, khong bat duoc backend moi."
    exit 1
}
if ($StopOnly) { exit 0 }

Set-Location $root
& $python -m uvicorn backend.app:app --host 127.0.0.1 --port $Port --reload
