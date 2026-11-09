param(
    [string]$Distribution = 'Ubuntu',
    [switch]$PreflightOnly
)

$ErrorActionPreference = 'Stop'
$taskWorkspace = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$taskWsl = Join-Path $env:SystemRoot 'System32\wsl.exe'
if (-not (Test-Path -LiteralPath $taskWsl)) { throw 'WSL is not installed.' }
if ($Distribution -like 'docker-desktop*') {
    throw 'Select a general-purpose Linux distribution such as Ubuntu, not Docker Desktop internal storage.'
}

# Select the distribution explicitly; never change the user's WSL default.
# --cd supplies the absolute Windows workspace path as one native argument.
$taskProbe = "import sys, platform, os; print(sys.version.split()[0]); print(platform.system(), platform.machine(), platform.libc_ver()[0]); print(os.getcwd()); sys.exit(0 if sys.version_info >= (3, 11) and sys.platform == 'linux' and platform.machine() == 'x86_64' and platform.libc_ver()[0] == 'glibc' and os.path.isfile('scripts/run_agentops_linux_v4.py') and os.path.isfile('external/agentops-c806b7f1/agents/python/uv.lock') else 11)"
& $taskWsl --distribution $Distribution --cd $taskWorkspace --exec python3 -c $taskProbe
$taskProbeExit = $LASTEXITCODE
if ($taskProbeExit -ne 0) {
    throw "WSL preflight failed in '$Distribution' (exit $taskProbeExit). Linux x86_64, glibc, Python >=3.11 and an accessible project folder are required. No research attempt was started."
}
if ($PreflightOnly) {
    Write-Output 'WSL preflight passed. No dependencies or research attempt started.'
    return
}

foreach ($taskRelativePath in @(
    'external\runtime-agentops-linux-v4',
    'runs\agentops-native-eligibility\dependencies-linux-v4',
    'runs\agentops-native-eligibility\native-probe-v4'
)) {
    if (Test-Path -LiteralPath (Join-Path $taskWorkspace $taskRelativePath)) {
        throw "Existing Linux setup or attempt found at $taskRelativePath. Preserve its receipts for inspection; do not rerun."
    }
}

& $taskWsl --distribution $Distribution --cd $taskWorkspace --exec python3 scripts/run_agentops_linux_v4.py
if ($LASTEXITCODE -ne 0) {
    throw 'Linux setup/control stopped. Preserve the output and any saved receipts for inspection; do not rerun an existing attempt.'
}
