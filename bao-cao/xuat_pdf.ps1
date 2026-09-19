# Xuất hồ sơ Word sang PDF và in ra số trang.
# Cách dùng:  powershell -ExecutionPolicy Bypass -File bao-cao\xuat_pdf.ps1
#             powershell -ExecutionPolicy Bypass -File bao-cao\xuat_pdf.ps1 -Docx bao-cao\thu.docx
# Cần có Microsoft Word trên máy, và file .docx phải đang đóng.
# Chạy lại mỗi lần sửa make_report.py để khỏi nộp nhầm PDF cũ.

param([string]$Docx)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
if ($Docx) {
    $docx = [System.IO.Path]::GetFullPath((Join-Path $root $Docx))
} else {
    $docx = Join-Path $root 'bao-cao\Ho_so_du_an_Gia_Su_AI_Mimo_v4.docx'
}
$pdf = [System.IO.Path]::ChangeExtension($docx, '.pdf')

if (-not (Test-Path $docx)) { throw "Khong thay $docx. Chay 'python bao-cao/make_report.py' truoc." }

$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {
    $doc = $word.Documents.Open($docx, $false, $true)
    $doc.Repaginate()
    $pages = $doc.ComputeStatistics(2)   # wdStatisticPages
    $doc.ExportAsFixedFormat($pdf, 17)  # wdExportFormatPDF
    $doc.Close(0)
    Write-Output "PDF: $pdf"
    Write-Output "So trang: $pages"
} finally {
    $word.Quit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($word) | Out-Null
}
