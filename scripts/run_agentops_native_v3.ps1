$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskPython = Join-Path $taskRoot '.venv\Scripts\python.exe'
$taskRunner = Join-Path $PSScriptRoot 'agentops_native_probe_v3.py'
$taskOutput = Join-Path $taskRoot 'runs\agentops-native-eligibility\native-probe-v3'
if (-not (Test-Path -LiteralPath (Join-Path $taskOutput 'plan.json'))) {
    throw 'The prepared v3 plan is missing. Return to Codex for inspection.'
}
if (Test-Path -LiteralPath (Join-Path $taskOutput 'execution.json')) {
    throw 'This attempt already started. Preserve its evidence and return to Codex; do not rerun.'
}
& $taskPython -B -X utf8 $taskRunner run --output $taskOutput
if ($LASTEXITCODE -ne 0) {
    throw 'The original control or evidence check failed. Retain all outputs for inspection; do not rerun.'
}
Write-Output "Finished. Results: $taskOutput\result.json"
