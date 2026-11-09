# Save a Gemini API key with Windows current-user DPAPI. No network requests.
[CmdletBinding()]
param([switch]$CheckOnly)

$ErrorActionPreference = 'Stop'

function Get-GeminiCredentialPath {
    $localRoot = [Environment]::GetFolderPath([Environment+SpecialFolder]::LocalApplicationData)
    if ([string]::IsNullOrWhiteSpace($localRoot)) {
        throw 'Windows local application data is unavailable.'
    }
    $localRoot = [IO.Path]::GetFullPath($localRoot)
    $appRoot = Join-Path $localRoot 'AiInteroperability'
    $credentialRoot = Join-Path $appRoot 'credentials'
    foreach ($folder in @($appRoot, $credentialRoot)) {
        $absolute = [IO.Path]::GetFullPath($folder)
        if (-not $absolute.StartsWith($localRoot.TrimEnd('\') + '\', [StringComparison]::OrdinalIgnoreCase)) {
            throw 'The credential folder is outside local application data.'
        }
        if ([IO.File]::Exists($absolute)) {
            throw 'The credential folder path is occupied by a file.'
        }
        if ([IO.Directory]::Exists($absolute) -and
            (([IO.File]::GetAttributes($absolute) -band [IO.FileAttributes]::ReparsePoint) -ne 0)) {
            throw 'A redirected credential folder is not supported.'
        }
    }
    $target = [IO.Path]::GetFullPath((Join-Path $credentialRoot 'gemini-api-key.dpapi'))
    if ([IO.Path]::GetDirectoryName($target) -ne [IO.Path]::GetFullPath($credentialRoot)) {
        throw 'The credential filename is outside its intended folder.'
    }
    if ([IO.Directory]::Exists($target) -or
        ([IO.File]::Exists($target) -and
         (([IO.File]::GetAttributes($target) -band [IO.FileAttributes]::ReparsePoint) -ne 0))) {
        throw 'The credential file must be a regular local file.'
    }
    return $target
}

$credentialPath = Get-GeminiCredentialPath
if ($CheckOnly) {
    $configured = $false
    $savedSecret = $null
    try {
        if ([IO.File]::Exists($credentialPath)) {
            $savedSecret = ConvertTo-SecureString -String ([IO.File]::ReadAllText($credentialPath).Trim()) -ErrorAction Stop
            $configured = $savedSecret.Length -gt 0
        }
    }
    catch {
        $configured = $false
    }
    finally {
        if ($null -ne $savedSecret) { $savedSecret.Dispose() }
    }
    [pscustomobject]@{ configured = $configured; path = $credentialPath } | ConvertTo-Json -Compress
    exit 0
}

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
[Windows.Forms.Application]::EnableVisualStyles()
$form = New-Object Windows.Forms.Form
$form.Text = 'Configure Gemini for this project'
$form.ClientSize = New-Object Drawing.Size(510, 225)
$form.StartPosition = 'CenterScreen'
$form.FormBorderStyle = 'FixedDialog'
$form.MaximizeBox = $false
$form.MinimizeBox = $false
$form.AutoScaleMode = 'Dpi'
$font = New-Object Drawing.Font('Segoe UI', 10)
$form.Font = $font

$intro = New-Object Windows.Forms.Label
$intro.Location = New-Object Drawing.Point(18, 15)
$intro.Size = New-Object Drawing.Size(475, 47)
$intro.Text = 'Paste your Gemini API key below. It will be encrypted for this Windows account and stored outside the project.'
$form.Controls.Add($intro)

$keyBox = New-Object Windows.Forms.TextBox
$keyBox.Location = New-Object Drawing.Point(20, 72)
$keyBox.Size = New-Object Drawing.Size(470, 28)
$keyBox.UseSystemPasswordChar = $true
$keyBox.MaxLength = 1024
$keyBox.ShortcutsEnabled = $true
$keyBox.TabIndex = 0
$form.Controls.Add($keyBox)

$status = New-Object Windows.Forms.Label
$status.Location = New-Object Drawing.Point(18, 111)
$status.Size = New-Object Drawing.Size(475, 45)
$status.Text = 'Save replaces any previously saved key. Setup makes no API calls.'
$form.Controls.Add($status)

$save = New-Object Windows.Forms.Button
$save.Text = 'Save'
$save.Location = New-Object Drawing.Point(291, 175)
$save.Size = New-Object Drawing.Size(95, 31)
$save.TabIndex = 1
$form.Controls.Add($save)
$cancel = New-Object Windows.Forms.Button
$cancel.Text = 'Cancel'
$cancel.Location = New-Object Drawing.Point(396, 175)
$cancel.Size = New-Object Drawing.Size(95, 31)
$cancel.TabIndex = 2
$cancel.DialogResult = [Windows.Forms.DialogResult]::Cancel
$form.Controls.Add($cancel)
$form.AcceptButton = $save
$form.CancelButton = $cancel
$form.Add_Shown({ [void]$keyBox.Focus() })

$save.Add_Click({
    $secret = $null
    $candidate = $null
    $temporaryPath = $null
    $writer = $null
    $stream = $null
    try {
        $candidate = $keyBox.Text.Trim()
        if ([string]::IsNullOrWhiteSpace($candidate) -or $candidate -match '\s') {
            $status.Text = 'Paste the API key only, without spaces or line breaks.'
            return
        }
        $secret = ConvertTo-SecureString -String $candidate -AsPlainText -Force
        $candidate = $null
        $keyBox.Clear()
        $target = Get-GeminiCredentialPath
        $folder = [IO.Path]::GetDirectoryName($target)
        [void][IO.Directory]::CreateDirectory($folder)
        $target = Get-GeminiCredentialPath
        $temporaryPath = [IO.Path]::GetFullPath((Join-Path $folder ('gemini-api-key.' + [Guid]::NewGuid().ToString('N') + '.tmp')))
        if ([IO.Path]::GetDirectoryName($temporaryPath) -ne $folder) {
            throw 'The temporary credential path is outside its intended folder.'
        }
        $protectedValue = ConvertFrom-SecureString -SecureString $secret
        $stream = New-Object IO.FileStream($temporaryPath, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
        $writer = New-Object IO.StreamWriter($stream, (New-Object Text.UTF8Encoding($false)))
        $writer.WriteLine($protectedValue)
        $writer.Flush()
        $stream.Flush($true)
        $writer.Dispose()
        $writer = $null
        $stream = $null
        $target = Get-GeminiCredentialPath
        if ([IO.File]::Exists($target)) {
            [IO.File]::Replace($temporaryPath, $target, $null)
        }
        else {
            [IO.File]::Move($temporaryPath, $target)
        }
        $temporaryPath = $null
        [void][Windows.Forms.MessageBox]::Show($form,
            'Saved for this Windows account. No API request was made.', 'Gemini configured',
            [Windows.Forms.MessageBoxButtons]::OK, [Windows.Forms.MessageBoxIcon]::Information)
        $form.DialogResult = [Windows.Forms.DialogResult]::OK
        $form.Close()
    }
    catch {
        $status.Text = 'The key could not be saved. Check access to your local application-data folder, then paste it again.'
    }
    finally {
        $candidate = $null
        $protectedValue = $null
        if ($null -ne $writer) { $writer.Dispose() }
        elseif ($null -ne $stream) { $stream.Dispose() }
        if ($null -ne $temporaryPath -and [IO.File]::Exists($temporaryPath)) {
            [IO.File]::Delete($temporaryPath)
        }
        if ($null -ne $secret) { $secret.Dispose() }
    }
})

try {
    [void]$form.ShowDialog()
}
finally {
    $keyBox.Clear()
    $form.Dispose()
    $font.Dispose()
}
