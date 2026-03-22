$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repoRoot

Write-Host "Building ReInkPyFix.exe..."
if (Test-Path build) {
    Remove-Item build -Recurse -Force
}
if (Test-Path dist) {
    Remove-Item dist -Recurse -Force
}

python -m PyInstaller --noconfirm ReInkPyFix.spec

Write-Host ""
Write-Host "Build complete:"
Write-Host "  $repoRoot\dist\ReInkPyFix.exe"
