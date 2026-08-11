$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

$pythonExe = $null
$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
if ($pythonCommand) {
    $pythonExe = $pythonCommand.Source
}
elseif (Test-Path "$root\.venv312\Scripts\python.exe") {
    $pythonExe = "$root\.venv312\Scripts\python.exe"
}
elseif (Test-Path "$root\.venv\Scripts\python.exe") {
    $pythonExe = "$root\.venv\Scripts\python.exe"
}

if (-not $pythonExe) {
    throw "No Python interpreter was found. Create a virtual environment first."
}

Start-Process -FilePath $pythonExe -ArgumentList "-m uvicorn app.main:app --host 0.0.0.0 --port 8000" -WorkingDirectory $root
Start-Sleep -Seconds 3
Start-Process -FilePath $pythonExe -ArgumentList "-m streamlit run streamlit_app.py --server.address 0.0.0.0 --server.port 8501" -WorkingDirectory $root
Write-Host "Backend: http://localhost:8000/docs"
Write-Host "Frontend: http://localhost:8501"
