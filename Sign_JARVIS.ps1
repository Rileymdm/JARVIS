# Sign_JARVIS.ps1
# Self-sign JARVIS.exe for testing on administrated PCs

$certName = "JARVIS Rocket Simulation"
$exePath = "rocket-simulation-ui\dist\JARVIS.exe"

# Check if certificate already exists
$existingCert = Get-ChildItem -Path Cert:\CurrentUser\My | Where-Object { $_.Subject -like "*$certName*" }

if (-not $existingCert) {
    Write-Host "Creating self-signed certificate..." -ForegroundColor Cyan
    
    # Create self-signed certificate
    $cert = New-SelfSignedCertificate `
        -Type CodeSigningCert `
        -Subject "CN=$certName" `
        -CertStoreLocation Cert:\CurrentUser\My `
        -NotAfter (Get-Date).AddYears(5)
    
    Write-Host "Certificate created: $($cert.Thumbprint)" -ForegroundColor Green
    
    # Export certificate for distribution
    $certPath = "JARVIS_Certificate.cer"
    Export-Certificate -Cert $cert -FilePath $certPath | Out-Null
    Write-Host "Certificate exported to: $certPath" -ForegroundColor Green
    Write-Host ""
    Write-Host "IMPORTANT: To trust this certificate on other PCs:" -ForegroundColor Yellow
    Write-Host "1. Copy $certPath to the target PC" -ForegroundColor Yellow
    Write-Host "2. Right-click -> Install Certificate" -ForegroundColor Yellow
    Write-Host "3. Select 'Local Machine' -> Next" -ForegroundColor Yellow
    Write-Host "4. Select 'Place all certificates in the following store'" -ForegroundColor Yellow
    Write-Host "5. Browse -> 'Trusted Root Certification Authorities' -> OK" -ForegroundColor Yellow
    Write-Host "6. Finish" -ForegroundColor Yellow
    Write-Host ""
} else {
    $cert = $existingCert[0]
    Write-Host "Using existing certificate: $($cert.Thumbprint)" -ForegroundColor Green
}

# Sign the executable
if (Test-Path $exePath) {
    Write-Host "Signing $exePath..." -ForegroundColor Cyan
    
    Set-AuthenticodeSignature -FilePath $exePath -Certificate $cert -TimestampServer "http://timestamp.digicert.com"
    
    # Verify signature
    $signature = Get-AuthenticodeSignature -FilePath $exePath
    
    if ($signature.Status -eq 'Valid') {
        Write-Host "✓ Successfully signed JARVIS.exe!" -ForegroundColor Green
    } elseif ($signature.Status -eq 'UnknownError') {
        Write-Host "⚠ Signed, but certificate not trusted (expected for self-signed)" -ForegroundColor Yellow
        Write-Host "  Install JARVIS_Certificate.cer on target PCs to trust it." -ForegroundColor Yellow
    } else {
        Write-Host "✗ Signing failed: $($signature.Status)" -ForegroundColor Red
    }
} else {
    Write-Host "✗ Error: $exePath not found!" -ForegroundColor Red
    Write-Host "  Build JARVIS.exe first using build.bat" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Press any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
