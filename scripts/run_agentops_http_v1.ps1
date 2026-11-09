$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskPython = Join-Path $taskRoot '.venv\Scripts\python.exe'
$taskRunner = Join-Path $PSScriptRoot 'agentops_http_control_v1.py'
& $taskPython -B -X utf8 $taskRunner run
if ($LASTEXITCODE -ne 0) {
    throw 'Control did not pass. Preserve all receipts and return to Codex; do not rerun.'
}
