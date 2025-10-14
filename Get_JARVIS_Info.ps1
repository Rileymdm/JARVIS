# Get_JARVIS_Info.ps1
# Get JARVIS.exe information for IT whitelist requests

$exePath = "rocket-simulation-ui\dist\JARVIS.exe"

if (Test-Path $exePath) {
    $file = Get-Item $exePath
    $hash = Get-FileHash -Path $exePath -Algorithm SHA256
    
    Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "  JARVIS.exe Whitelist Information" -ForegroundColor Cyan
    Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "File Name:" -ForegroundColor Yellow -NoNewline
    Write-Host "      $($file.Name)"
    Write-Host "File Size:" -ForegroundColor Yellow -NoNewline
    Write-Host "      $([math]::Round($file.Length/1MB, 2)) MB ($($file.Length) bytes)"
    Write-Host "Last Modified:" -ForegroundColor Yellow -NoNewline
    Write-Host "   $($file.LastWriteTime)"
    Write-Host ""
    Write-Host "SHA256 Hash:" -ForegroundColor Yellow
    Write-Host "  $($hash.Hash)" -ForegroundColor Green
    Write-Host ""
    
    # Check signature
    $signature = Get-AuthenticodeSignature -FilePath $exePath
    Write-Host "Digital Signature:" -ForegroundColor Yellow
    if ($signature.Status -eq 'Valid') {
        Write-Host "  Status: ✓ VALID" -ForegroundColor Green
        Write-Host "  Signer: $($signature.SignerCertificate.Subject)"
    } elseif ($signature.Status -eq 'NotSigned') {
        Write-Host "  Status: ✗ NOT SIGNED" -ForegroundColor Red
        Write-Host "  This file is unsigned and may be blocked by security policies." -ForegroundColor Yellow
    } else {
        Write-Host "  Status: $($signature.Status)" -ForegroundColor Yellow
        if ($signature.SignerCertificate) {
            Write-Host "  Signer: $($signature.SignerCertificate.Subject)"
        }
    }
    Write-Host ""
    Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "To request IT whitelist:" -ForegroundColor Cyan
    Write-Host "1. Send them this SHA256 hash" -ForegroundColor White
    Write-Host "2. Explain this is JARVIS Rocket Simulation software" -ForegroundColor White
    Write-Host "3. Request AppLocker/WDAC policy exception" -ForegroundColor White
    Write-Host ""
    
    # Copy hash to clipboard
    $hash.Hash | Set-Clipboard
    Write-Host "✓ SHA256 hash copied to clipboard!" -ForegroundColor Green
} else {
    Write-Host "✗ Error: $exePath not found!" -ForegroundColor Red
}

Write-Host ""
Write-Host "Press any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
