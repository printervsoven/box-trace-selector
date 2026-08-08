$ErrorActionPreference = 'Stop'

$distro = 'Ubuntu-24.04'
$windowsNotebookDirectory = $PSScriptRoot
$linuxUser = 'kawon'

Write-Host 'Starting Cadabra2 Jupyter Notebook on http://127.0.0.1:8888/' -ForegroundColor Cyan
Write-Host 'Keep this window open. Open the tokenised URL printed below in your browser.' -ForegroundColor Yellow
& wsl.exe -d $distro -u $linuxUser --cd $windowsNotebookDirectory -- `
    jupyter notebook --no-browser --ip=127.0.0.1 --port=8888 box2_verification.ipynb
