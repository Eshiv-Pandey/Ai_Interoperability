$ErrorActionPreference = 'Stop'
$taskWorkspace = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$taskWsl = Join-Path $env:SystemRoot 'System32\wsl.exe'
$taskOutput = Join-Path $taskWorkspace 'runs\agentops-native-eligibility\linux-protocol-v9'
if (Test-Path -LiteralPath $taskOutput) {
    throw 'This protocol attempt already exists. Preserve its receipts; do not repeat.'
}
Write-Host 'Starting two offline protocol controls in the existing WSL runtime.'
Write-Host 'Results: runs/agentops-native-eligibility/linux-protocol-v9'
# A pipe gives the noninteractive WSL command finite input instead of forwarding
# terminal keystrokes. No prompts or interactive shell are used by this launch.
'' | & $taskWsl --distribution Ubuntu --cd $taskWorkspace --exec python3 -B scripts/resume_agentops_protocol_v9.py
if ($LASTEXITCODE -ne 0) {
    throw 'Protocol control stopped. Preserve all output and receipts for inspection.'
}
