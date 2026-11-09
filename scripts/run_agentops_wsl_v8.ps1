$ErrorActionPreference = 'Stop'
$taskWorkspace = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$taskWsl = Join-Path $env:SystemRoot 'System32\wsl.exe'
$taskOutput = Join-Path $taskWorkspace 'runs\agentops-native-eligibility\linux-socket-resume-v8'
if (Test-Path -LiteralPath $taskOutput) {
    throw 'This resume attempt already exists. Preserve its receipts; do not repeat.'
}
& $taskWsl --distribution Ubuntu --cd $taskWorkspace --exec python3 scripts/resume_agentops_socket_observer_v8.py
if ($LASTEXITCODE -ne 0) {
    throw 'Runtime resume stopped. Preserve its output and receipts for inspection.'
}
