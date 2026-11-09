$ErrorActionPreference = 'Stop'
$taskWorkspace = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$taskWsl = Join-Path $env:SystemRoot 'System32\wsl.exe'
$taskOutput = Join-Path $taskWorkspace 'runs\agentops-native-eligibility\linux-filesystem-v5'
if (Test-Path -LiteralPath $taskOutput) {
    throw "This environment attempt already exists: $taskOutput. Preserve it for inspection; do not repeat."
}
& $taskWsl --distribution Ubuntu --cd $taskWorkspace --exec python3 scripts/run_agentops_linux_workspace_v5.py
if ($LASTEXITCODE -ne 0) {
    throw 'The Linux filesystem attempt stopped. Preserve all output and saved receipts for inspection.'
}
