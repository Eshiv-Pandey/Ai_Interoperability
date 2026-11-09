# Launch a local executable with the saved Gemini key in its process environment.
# This helper itself makes no API request and changes no persistent environment.
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$Program,
    [Parameter(Position = 1, ValueFromRemainingArguments = $true)]
    [string[]]$ProgramArguments = @()
)

$ErrorActionPreference = 'Stop'
$localRoot = [Environment]::GetFolderPath([Environment+SpecialFolder]::LocalApplicationData)
if ([string]::IsNullOrWhiteSpace($localRoot)) {
    Write-Error 'Windows local application data is unavailable.' -ErrorAction Continue
    exit 1
}
$localRoot = [IO.Path]::GetFullPath($localRoot)
$appRoot = Join-Path $localRoot 'AiInteroperability'
$credentialRoot = Join-Path $appRoot 'credentials'
$credentialPath = [IO.Path]::GetFullPath((Join-Path $credentialRoot 'gemini-api-key.dpapi'))
foreach ($folder in @($appRoot, $credentialRoot)) {
    if (-not ([IO.Path]::GetFullPath($folder)).StartsWith($localRoot.TrimEnd('\') + '\', [StringComparison]::OrdinalIgnoreCase) -or
        ([IO.Directory]::Exists($folder) -and
         (([IO.File]::GetAttributes($folder) -band [IO.FileAttributes]::ReparsePoint) -ne 0))) {
        Write-Error 'The credential folder must be a regular folder under local application data.' -ErrorAction Continue
        exit 1
    }
}
if (-not [IO.File]::Exists($credentialPath)) {
    Write-Error 'No saved Gemini key was found. Double-click "Configure Gemini.cmd" in the project folder first.' -ErrorAction Continue
    exit 1
}
if (([IO.File]::GetAttributes($credentialPath) -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
    Write-Error 'The saved Gemini key must be a regular local credential file.' -ErrorAction Continue
    exit 1
}

$secret = $null
$bstr = [IntPtr]::Zero
$plainKey = $null
$prior = @{}
$changed = $false
$exitCode = 1
try {
    $command = Get-Command -Name $Program -CommandType Application -ErrorAction Stop
    try {
        $secret = ConvertTo-SecureString -String ([IO.File]::ReadAllText($credentialPath).Trim()) -ErrorAction Stop
        if ($secret.Length -eq 0) { throw 'Empty credential' }
        $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secret)
        $plainKey = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
    }
    catch {
        throw 'The saved key cannot be opened by this Windows account. Run Configure Gemini.cmd and save it again.'
    }
    foreach ($name in @('GOOGLE_API_KEY', 'GEMINI_API_KEY', 'GOOGLE_GENAI_USE_VERTEXAI')) {
        $prior[$name] = [Environment]::GetEnvironmentVariable($name, [EnvironmentVariableTarget]::Process)
    }
    $changed = $true
    [Environment]::SetEnvironmentVariable('GOOGLE_API_KEY', $plainKey, [EnvironmentVariableTarget]::Process)
    [Environment]::SetEnvironmentVariable('GEMINI_API_KEY', $plainKey, [EnvironmentVariableTarget]::Process)
    [Environment]::SetEnvironmentVariable('GOOGLE_GENAI_USE_VERTEXAI', 'false', [EnvironmentVariableTarget]::Process)
    & $command.Source @ProgramArguments
    $exitCode = $LASTEXITCODE
    if ($null -eq $exitCode) { $exitCode = 1 }
}
catch {
    Write-Error 'Gemini launch failed. Check the executable name and the saved key using Configure Gemini.cmd.' -ErrorAction Continue
}
finally {
    if ($changed) {
        foreach ($name in @('GOOGLE_API_KEY', 'GEMINI_API_KEY', 'GOOGLE_GENAI_USE_VERTEXAI')) {
            [Environment]::SetEnvironmentVariable($name, $prior[$name], [EnvironmentVariableTarget]::Process)
        }
    }
    if ($bstr -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
    }
    if ($null -ne $secret) { $secret.Dispose() }
    $plainKey = $null
    $prior.Clear()
}
exit $exitCode
