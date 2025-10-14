# Digital Signature Guide for JARVIS.exe

## Why Digital Signatures Are Important

Enterprise and administrated Windows PCs often block unsigned executables due to:

- **Windows Defender Application Control (WDAC)** - Enforces code integrity policies
- **AppLocker** - Restricts application execution to trusted publishers
- **SmartScreen Filter** - Warns or blocks files from unknown publishers
- **Group Policy** - IT-enforced security policies

**Without a digital signature, JARVIS.exe may be blocked or flagged as untrusted.**

---

## Solution 1: Self-Signed Certificate (Testing/Internal Use)

### Quick Start

1. **Sign the executable:**
   ```powershell
   .\Sign_JARVIS.ps1
   ```

2. **Distribute the certificate:**
   - Copy `JARVIS_Certificate.cer` to target PCs
   - Install it in "Trusted Root Certification Authorities"

### Detailed Steps

#### A. Sign JARVIS.exe

Run PowerShell as **Administrator**:

```powershell
cd C:\Users\YOUR_USERNAME\Documents\GitHub\JARVIS
.\Sign_JARVIS.ps1
```

This will:
- Create a self-signed code signing certificate
- Sign `JARVIS.exe` with the certificate
- Export `JARVIS_Certificate.cer` for distribution

#### B. Install Certificate on Target PCs

On each PC where you want to run JARVIS.exe:

1. Copy `JARVIS_Certificate.cer` to the PC
2. **Right-click** `JARVIS_Certificate.cer` → **Install Certificate**
3. Select **Local Machine** → Next (requires Administrator)
4. Select **"Place all certificates in the following store"**
5. Click **Browse** → Select **"Trusted Root Certification Authorities"**
6. Click **OK** → **Next** → **Finish**
7. Confirm the security warning

**Alternative (Command Line):**
```powershell
# Run as Administrator
certutil -addstore "Root" JARVIS_Certificate.cer
```

#### C. Verify Signature

```powershell
Get-AuthenticodeSignature rocket-simulation-ui\dist\JARVIS.exe | Format-List
```

---

## Solution 2: Commercial Code Signing Certificate (Production)

### Recommended Providers

| Provider | Price/Year | Notes |
|----------|-----------|-------|
| **DigiCert** | ~$400 | Industry standard, fastest validation |
| **Sectigo (Comodo)** | ~$200 | Good value, trusted by Windows |
| **SSL.com** | ~$250 | Offers EV certificates |
| **SignPath.io** | **FREE** | For open-source projects only |

### Purchase Process

1. **Choose provider** and certificate type (Standard or EV)
2. **Verify your identity:**
   - Organization validation (documents required)
   - Domain ownership verification
   - EV requires additional phone/legal verification
3. **Receive certificate** (.pfx or .p12 file)
4. **Install certificate** in Windows Certificate Store

### Signing with Commercial Certificate

```powershell
# Using SignTool (part of Windows SDK)
$signtool = "C:\Program Files (x86)\Windows Kits\10\bin\10.0.22621.0\x64\signtool.exe"
$certPath = "path\to\your\certificate.pfx"
$exePath = "rocket-simulation-ui\dist\JARVIS.exe"

# Sign with timestamp (recommended)
& $signtool sign `
    /f $certPath `
    /p "YOUR_PASSWORD" `
    /tr http://timestamp.digicert.com `
    /td sha256 `
    /fd sha256 `
    $exePath
```

### Automated Signing in Build Process

Update `build.bat` to sign automatically:

```batch
@echo off
echo Building JARVIS.exe...
cd rocket-simulation-ui

REM Build executable
..\. venv\Scripts\pyinstaller.exe --onefile --windowed --name=JARVIS ^
    --icon=src\JARVIS.ico --add-data "src\JARVIS.ico;." ^
    --add-data "src\jarvis.gif;." --add-data "src\Rocket.png;." ^
    --add-data "src\istockphoto-1360257728-612x612.jpg;." ^
    --add-data "thrust_curves;thrust_curves" ^
    --clean --noconfirm src\main.py

REM Sign executable
echo Signing JARVIS.exe...
"C:\Program Files (x86)\Windows Kits\10\bin\10.0.22621.0\x64\signtool.exe" sign ^
    /f "path\to\certificate.pfx" ^
    /p "PASSWORD" ^
    /tr http://timestamp.digicert.com ^
    /td sha256 ^
    /fd sha256 ^
    dist\JARVIS.exe

echo Build complete!
pause
```

---

## Solution 3: Request IT Whitelist

If you can't sign the executable, request an exception from your IT department.

### Get File Information

```powershell
.\Get_JARVIS_Info.ps1
```

This will display and copy the SHA256 hash to your clipboard.

### Information to Provide IT

**Email Template:**

```
Subject: AppLocker Whitelist Request - JARVIS Rocket Simulation

Hi IT Team,

I need to run a custom application for rocket trajectory simulation called JARVIS.
Please whitelist the following:

Application Name: JARVIS Rocket Simulation
File Name:        JARVIS.exe
File Size:        108.8 MB
SHA256 Hash:      [paste hash from Get_JARVIS_Info.ps1]
Publisher:        Unsigned (internal development tool)
Purpose:          Educational rocket physics simulation software
Repository:       https://github.com/Rileymdm/JARVIS

Please add an AppLocker exception for this SHA256 hash.

Thank you!
```

### IT Department Options

IT can whitelist using:

1. **AppLocker Hash Rule:**
   ```powershell
   New-AppLockerPolicy -RuleType Hash -Path "JARVIS.exe" -User Everyone
   ```

2. **WDAC Policy Exception:**
   ```powershell
   Add-SignerRule -FilePath "WDAC_Policy.xml" -FileInfo (Get-Item "JARVIS.exe")
   ```

3. **Group Policy:**
   - Add hash to Software Restriction Policies
   - Create unrestricted zone for specific folder

---

## Solution 4: Run in Unrestricted Environment

### Option A: Virtual Machine

1. Create Windows VM without enterprise policies
2. Run JARVIS.exe without restrictions
3. Good for testing, not for daily use

### Option B: Windows Sandbox

```powershell
# Enable Windows Sandbox
Enable-WindowsOptionalFeature -Online -FeatureName Containers-DisposableClientVM

# Copy JARVIS to Sandbox and run
```

### Option C: Personal Device

Run on non-administrated PC:
- Home Windows installation
- Personal laptop
- Development machine without corporate policies

---

## Verification Commands

### Check if JARVIS.exe is Signed

```powershell
Get-AuthenticodeSignature rocket-simulation-ui\dist\JARVIS.exe | Select-Object Status, SignerCertificate
```

**Expected Output:**
- `Status: Valid` → Properly signed and trusted
- `Status: UnknownError` → Signed but certificate not trusted (self-signed)
- `Status: NotSigned` → No signature

### View Certificate Details

```powershell
$sig = Get-AuthenticodeSignature rocket-simulation-ui\dist\JARVIS.exe
$sig.SignerCertificate | Format-List Subject, Issuer, NotBefore, NotAfter, Thumbprint
```

### Check Windows Trust

```powershell
# List trusted root certificates
Get-ChildItem Cert:\LocalMachine\Root | Where-Object { $_.Subject -like "*JARVIS*" }
```

---

## Troubleshooting

### Error: "This app can't run on your PC"

**Cause:** AppLocker or SmartScreen blocking unsigned executable

**Solutions:**
1. Sign with self-signed certificate (see Solution 1)
2. Request IT whitelist (see Solution 3)
3. Run on personal device

### Error: "Windows Defender SmartScreen prevented an unrecognized app"

**Cause:** File not signed or unknown publisher

**Temporary Bypass (if allowed):**
1. Click "More info"
2. Click "Run anyway"

**Permanent Fix:**
- Sign with commercial certificate
- Build reputation by having many users download

### Error: Certificate Not Trusted

**Cause:** Self-signed certificate not installed in Trusted Root

**Fix:**
```powershell
# Run as Administrator
certutil -addstore "Root" JARVIS_Certificate.cer
```

### Error: "SignTool not found"

**Cause:** Windows SDK not installed

**Fix:**
1. Download [Windows SDK](https://developer.microsoft.com/en-us/windows/downloads/windows-sdk/)
2. Install with "Windows SDK Signing Tools" component
3. Add to PATH or use full path

---

## Best Practices

### For Development
- ✅ Use self-signed certificates for internal testing
- ✅ Keep certificate password secure
- ✅ Timestamp signatures (allows validation after cert expires)

### For Distribution
- ✅ Use commercial code signing certificate
- ✅ Sign on isolated/secure machine
- ✅ Store certificates in HSM or secure vault
- ✅ Use EV certificate for immediate SmartScreen reputation

### For Users
- ✅ Verify certificate before installation
- ✅ Check SHA256 hash matches expected value
- ✅ Only install certificates from trusted sources

---

## Additional Resources

- [Microsoft: Code Signing](https://docs.microsoft.com/en-us/windows-hardware/drivers/install/code-signing)
- [SignTool Documentation](https://docs.microsoft.com/en-us/dotnet/framework/tools/signtool-exe)
- [AppLocker Overview](https://docs.microsoft.com/en-us/windows/security/threat-protection/windows-defender-application-control/applocker/applocker-overview)
- [WDAC Policies](https://docs.microsoft.com/en-us/windows/security/threat-protection/windows-defender-application-control/windows-defender-application-control)

---

## Quick Reference

```powershell
# Self-sign JARVIS.exe
.\Sign_JARVIS.ps1

# Get file info for IT
.\Get_JARVIS_Info.ps1

# Verify signature
Get-AuthenticodeSignature rocket-simulation-ui\dist\JARVIS.exe

# Install certificate (as Admin)
certutil -addstore "Root" JARVIS_Certificate.cer

# Check certificate trust
Get-ChildItem Cert:\LocalMachine\Root | Where-Object { $_.Subject -like "*JARVIS*" }
```

---

**Need Help?** Open an issue at https://github.com/Rileymdm/JARVIS/issues
