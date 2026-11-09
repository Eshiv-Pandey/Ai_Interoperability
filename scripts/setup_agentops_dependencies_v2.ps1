# Run this once in normal PowerShell from the project folder.
# Downloads the upstream-pinned tool, verifies it, and syncs the unchanged lock.
# No model, agent service, benchmark case, cloud deployment, or source edit runs.
$ErrorActionPreference = 'Stop'
$taskWorkspace = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$taskRuntime = Join-Path $taskWorkspace 'external\runtime-agentops-v2'
$taskReceipts = Join-Path $taskWorkspace 'runs\agentops-native-eligibility\dependencies-v2'
$taskProject = Join-Path $taskWorkspace 'external\agentops-c806b7f1\agents\python'
$taskPython = Join-Path $taskWorkspace '.venv\Scripts\python.exe'
$taskUvUrl = 'https://github.com/astral-sh/uv/releases/download/0.12.0/uv-x86_64-pc-windows-msvc.zip'
$taskUvSha = '68200e25de594df92387186bbfb9d9df606ec1d87efaa0ae0c7f690970e53db6'
foreach ($taskPath in @($taskRuntime, $taskReceipts)) {
    if (-not ([IO.Path]::GetFullPath($taskPath).StartsWith($taskWorkspace + '\', [StringComparison]::OrdinalIgnoreCase))) {
        throw 'Resolved output is outside the workspace.'
    }
    if (Test-Path -LiteralPath $taskPath) { throw "Refusing to overwrite prior setup: $taskPath" }
}
if (-not (Test-Path -LiteralPath (Join-Path $taskProject 'uv.lock'))) { throw 'The ingested source lock is missing.' }
if (-not (Test-Path -LiteralPath $taskPython)) { throw 'The existing Python 3.13 environment is missing.' }
$taskInterpreter = (& $taskPython --version 2>&1 | Out-String).Trim()
if ($taskInterpreter -notmatch '^Python 3\.13\.') { throw "Unsupported interpreter: $taskInterpreter" }
New-Item -ItemType Directory -Path $taskRuntime, $taskReceipts | Out-Null
$taskTools = Join-Path $taskRuntime 'tools'
$taskTemporary = Join-Path $taskRuntime 'tmp'
New-Item -ItemType Directory -Path $taskTools, $taskTemporary | Out-Null
$taskZip = Join-Path $taskRuntime 'uv-0.12.0-windows.zip'
$taskUv = Join-Path $taskTools 'uv.exe'
$taskLock = Join-Path $taskProject 'uv.lock'
$taskLockBefore = (Get-FileHash -LiteralPath $taskLock -Algorithm SHA256).Hash.ToLowerInvariant()
$taskUtf8 = New-Object Text.UTF8Encoding($false)
$taskPre = [ordered]@{
    schema_version = 'agentops-user-dependency-setup/2'; started_at_utc = [DateTime]::UtcNow.ToString('o')
    tool_url = $taskUvUrl; expected_tool_zip_sha256 = $taskUvSha; interpreter = $taskInterpreter
    project = $taskProject; runtime = $taskRuntime; lock_sha256_before = $taskLockBefore
    tool_pin_source = 'external/agentops-c806b7f1/mise.lock, platforms.windows-x64'
    source_changes = $false; application_requests = 0; model_calls = 0; tests = 0
}
[IO.File]::WriteAllText((Join-Path $taskReceipts 'pre-execution.json'), ($taskPre | ConvertTo-Json -Depth 8) + "`n", $taskUtf8)
$taskEnvNames = @('UV_PROJECT_ENVIRONMENT', 'UV_CACHE_DIR', 'UV_PYTHON_DOWNLOADS', 'UV_HTTP_TIMEOUT', 'UV_HTTP_RETRIES', 'PYTHONDONTWRITEBYTECODE', 'TEMP', 'TMP', 'TMPDIR')
$taskPreviousEnv = @{}
foreach ($taskName in $taskEnvNames) { $taskPreviousEnv[$taskName] = [Environment]::GetEnvironmentVariable($taskName, 'Process') }
$taskStatus = 'failed'
$taskStep = 'download-tool'
$taskFailure = $null
$taskSyncExit = $null
try {
    Write-Host 'Downloading the pinned uv tool...'
    Invoke-WebRequest -Uri $taskUvUrl -OutFile $taskZip -UseBasicParsing
    $taskActualSha = (Get-FileHash -LiteralPath $taskZip -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($taskActualSha -ne $taskUvSha) { throw "Tool ZIP checksum mismatch: $taskActualSha" }
    $taskStep = 'extract-tool'
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $taskArchive = [IO.Compression.ZipFile]::OpenRead($taskZip)
    try {
        $taskEntries = @($taskArchive.Entries | Where-Object { $_.Name -eq 'uv.exe' })
        if ($taskEntries.Count -ne 1) { throw 'Expected exactly one uv.exe in the tool ZIP.' }
        [IO.Compression.ZipFileExtensions]::ExtractToFile($taskEntries[0], $taskUv, $false)
    } finally { $taskArchive.Dispose() }
    $taskToolVersion = (& $taskUv --version 2>&1 | Out-String).Trim()
    [IO.File]::WriteAllText((Join-Path $taskReceipts 'tool-version.txt'), $taskToolVersion + "`n", $taskUtf8)
    if ($LASTEXITCODE -ne 0 -or $taskToolVersion -notmatch '^uv 0\.12\.0(?:\s|$)') { throw "Unexpected tool version: $taskToolVersion" }
    $env:UV_PROJECT_ENVIRONMENT = Join-Path $taskRuntime 'venv'
    $env:UV_CACHE_DIR = Join-Path $taskRuntime 'uv-cache'
    $env:UV_PYTHON_DOWNLOADS = 'never'
    $env:UV_HTTP_TIMEOUT = '15'
    $env:UV_HTTP_RETRIES = '0'
    $env:PYTHONDONTWRITEBYTECODE = '1'
    $env:TEMP = $taskTemporary; $env:TMP = $taskTemporary; $env:TMPDIR = $taskTemporary
    $taskStep = 'locked-sync'
    Write-Host 'Installing the exact locked runtime and offline-test dependencies...'
    # Start-Process calls the executable directly; quoted paths preserve spaces.
    $taskArguments = @('sync', '--locked', '--project', ('"' + $taskProject + '"'), '--python', ('"' + $taskPython + '"'))
    $taskProcess = Start-Process -FilePath $taskUv -ArgumentList $taskArguments -WorkingDirectory $taskWorkspace -WindowStyle Hidden -Wait -PassThru -RedirectStandardOutput (Join-Path $taskReceipts 'sync.stdout.txt') -RedirectStandardError (Join-Path $taskReceipts 'sync.stderr.txt')
    $taskSyncExit = $taskProcess.ExitCode
    if ($taskSyncExit -ne 0) { throw "Locked dependency sync failed (exit $taskSyncExit); see retained sync.stderr.txt." }
    if ((Get-FileHash -LiteralPath $taskLock -Algorithm SHA256).Hash.ToLowerInvariant() -ne $taskLockBefore) { throw 'The source lock changed.' }
    $taskStatus = 'dependencies_ready'
    $taskStep = 'complete'
    Write-Host 'Dependencies are ready. No application test or model call has run.'
} catch {
    $taskFailure = $_.Exception.Message
    Write-Warning $taskFailure
} finally {
    foreach ($taskName in $taskEnvNames) { [Environment]::SetEnvironmentVariable($taskName, $taskPreviousEnv[$taskName], 'Process') }
    $taskResult = [ordered]@{
        schema_version = 'agentops-user-dependency-setup-result/2'; finished_at_utc = [DateTime]::UtcNow.ToString('o')
        status = $taskStatus; stopped_at = $taskStep; error = $taskFailure; sync_exit_code = $taskSyncExit
        source_lock_unchanged = ((Get-FileHash -LiteralPath $taskLock -Algorithm SHA256).Hash.ToLowerInvariant() -eq $taskLockBefore)
        dependencies_verified_by_agent = $false; tests = 0; application_requests = 0; model_calls = 0
        qualified_second_domain = $false; progress_percent = 5
    }
    [IO.File]::WriteAllText((Join-Path $taskReceipts 'result.json'), ($taskResult | ConvertTo-Json -Depth 8) + "`n", $taskUtf8)
}
if ($taskStatus -ne 'dependencies_ready') { throw 'Setup stopped. Preserve the receipts; do not rerun this script over the same attempt.' }
