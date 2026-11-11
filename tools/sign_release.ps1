# Authenticode-sign all Windows PE binaries in a Jarvis onedir distribution.
# Never commit code-signing private keys. Configure encrypted GitHub Actions secrets.
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Distribution,
    [Parameter(Mandatory = $true)][string]$CertificateBase64,
    [Parameter(Mandatory = $true)][string]$CertificatePassword
)

$ErrorActionPreference = 'Stop'
$directory = (Resolve-Path -LiteralPath $Distribution).Path
$kitsRoot = Join-Path ([Environment]::GetFolderPath('ProgramFilesX86')) 'Windows Kits\10\bin'
$signTool = Get-ChildItem -Path $kitsRoot -Filter 'signtool.exe' -Recurse -File -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -match '\\x64\\signtool\.exe$' } |
    Sort-Object FullName -Descending | Select-Object -First 1
if (-not $signTool) { throw 'Windows SDK signtool.exe not found on this runner.' }
if (-not $CertificateBase64.Trim() -or -not $CertificatePassword) {
    throw 'Trusted publisher certificate and password must be configured as GitHub secrets.'
}

$pfx = Join-Path $env:RUNNER_TEMP ('jarvis-signing-' + [guid]::NewGuid().ToString('N') + '.pfx')
try {
    [IO.File]::WriteAllBytes($pfx, [Convert]::FromBase64String($CertificateBase64))
    $certificate = [System.Security.Cryptography.X509Certificates.X509Certificate2]::new(
        $pfx, $CertificatePassword,
        [System.Security.Cryptography.X509Certificates.X509KeyStorageFlags]::EphemeralKeySet
    )
    if (-not $certificate.HasPrivateKey) { throw 'Signing certificate does not include a private key.' }
    $usage = $certificate.Extensions | Where-Object { $_.Oid.Value -eq '2.5.29.37' }
    if (-not $usage -or -not ($usage.Format($false) -match 'Code Signing|1\.3\.6\.1\.5\.5\.7\.3\.3')) {
        throw 'Certificate must have the Code Signing extended key usage.'
    }
    $now = Get-Date
    if ($now -lt $certificate.NotBefore -or $now -gt $certificate.NotAfter) {
        throw 'Code-signing certificate is not currently valid.'
    }
    Write-Host ('Signing using certificate subject: ' + $certificate.Subject)
    $files = @(Get-ChildItem -LiteralPath $directory -Recurse -File |
        Where-Object { $_.Extension -in @('.exe', '.dll', '.pyd') })
    if (-not $files -or -not (Test-Path -LiteralPath (Join-Path $directory 'Jarvis.exe'))) {
        throw 'Jarvis executable and bundled PE files not found.'
    }
    Write-Host ('Signing ' + $files.Count + ' Windows binaries')
    foreach ($file in $files) {
        & $signTool.FullName sign /f $pfx /p $CertificatePassword /fd SHA256 /tr 'http://timestamp.digicert.com' /td SHA256 /v $file.FullName
        if ($LASTEXITCODE -ne 0) { throw ('Signing failed for ' + $file.Name) }
    }
    foreach ($file in $files) {
        & $signTool.FullName verify /pa /v $file.FullName
        if ($LASTEXITCODE -ne 0) { throw ('Signature verification failed for ' + $file.Name) }
    }
    Write-Host 'PASS: All Windows binaries have verifiable Authenticode signatures.'
}
finally {
    if (Test-Path -LiteralPath $pfx) {
        Remove-Item -LiteralPath $pfx -Force -ErrorAction SilentlyContinue
    }
}
