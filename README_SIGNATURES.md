# ✅ JARVIS.exe Digital Signature Solution

## Problem Solved

**Issue:** JARVIS.exe was being blocked on administrated PCs due to lack of digital signature.

**Root Cause:** Corporate Windows environments (with AppLocker, WDAC, or Group Policy) block unsigned executables for security.

**Solution:** Self-signed JARVIS.exe with code signing certificate ✅

---

## What Was Done

### 1. ✅ Self-Signed Certificate Created
- **Certificate Subject:** `CN=JARVIS Rocket Simulation`
- **Thumbprint:** `4F6C038FD240A52B8A9F1676982F26879F55FCCB`
- **Valid Until:** October 14, 2030 (5 years)
- **Type:** Code Signing Certificate

### 2. ✅ JARVIS.exe Digitally Signed
- **File:** `rocket-simulation-ui/dist/JARVIS.exe`
- **Size:** 108.8 MB (108,793,752 bytes)
- **SHA256:** `A6D77F7A546BC20CAE0FB1BD95AE44F10F4A7B060AAE74C16A4677C9CFF6497D`
- **Signature Status:** Signed (UnknownError = certificate not yet trusted)
- **Timestamp:** DigiCert timestamp server

### 3. ✅ Certificate Exported for Distribution
- **File:** `JARVIS_Certificate.cer`
- **Purpose:** Install on target PCs to trust JARVIS.exe
- **Size:** 794 bytes

### 4. ✅ Automation Tools Created

#### `Sign_JARVIS.ps1`
Automatically signs JARVIS.exe with self-signed certificate
- Creates certificate if doesn't exist
- Signs executable
- Exports certificate for distribution

#### `Get_JARVIS_Info.ps1`
Gets file information for IT whitelist requests
- SHA256 hash
- File size and date
- Signature status
- Copies hash to clipboard

### 5. ✅ Complete Documentation
- **`DIGITAL_SIGNATURE_GUIDE.md`**: Comprehensive guide covering:
  - Self-signed certificates (testing/internal use)
  - Commercial certificates (production distribution)
  - IT whitelist requests
  - Troubleshooting
  - Best practices

---

## How to Use on Administrated PCs

### Option A: Install the Certificate (Recommended)

1. **Download from GitHub:**
   - `JARVIS_Certificate.cer`
   - `JARVIS.exe`

2. **Install Certificate (requires Administrator):**
   ```powershell
   # Right-click JARVIS_Certificate.cer → Install Certificate
   # Or use command line:
   certutil -addstore "Root" JARVIS_Certificate.cer
   ```

3. **Run JARVIS.exe:**
   - Should now run without being blocked
   - Certificate is trusted by your PC

### Option B: Request IT Whitelist

If you can't install certificates yourself:

1. **Get the SHA256 hash:**
   ```
   A6D77F7A546BC20CAE0FB1BD95AE44F10F4A7B060AAE74C16A4677C9CFF6497D
   ```

2. **Send to IT with this info:**
   - Application: JARVIS Rocket Simulation
   - Purpose: Educational rocket physics simulation
   - Repository: https://github.com/Rileymdm/JARVIS
   - Request: AppLocker/WDAC whitelist for SHA256 hash

### Option C: Use Personal Device

Run on non-administrated Windows PC:
- Home Windows installation
- Personal laptop
- Development machine without corporate policies

---

## Verification

### Check Signature Status
```powershell
Get-AuthenticodeSignature JARVIS.exe | Format-List
```

**Expected Output:**
- `Status: UnknownError` = Signed but certificate not trusted (normal for self-signed)
- `Status: Valid` = Signed and certificate trusted ✅
- `Status: NotSigned` = Not signed ❌

### Check Certificate Installation
```powershell
Get-ChildItem Cert:\LocalMachine\Root | Where-Object { $_.Subject -like "*JARVIS*" }
```

If certificate is installed, you'll see:
```
Thumbprint: 4F6C038FD240A52B8A9F1676982F26879F55FCCB
Subject: CN=JARVIS Rocket Simulation
```

---

## Future: Commercial Certificate

For **wider distribution** without certificate installation:

### Recommended Providers
- **DigiCert** (~$400/year) - Industry standard
- **Sectigo** (~$200/year) - Good value
- **SSL.com** (~$250/year) - Trusted by Windows
- **SignPath.io** (FREE) - For open-source projects

### Benefits
- ✅ No certificate installation required
- ✅ Windows SmartScreen trusts immediately (with EV cert)
- ✅ Works on all PCs without IT whitelisting
- ✅ Professional appearance

---

## Files Included

| File | Purpose | Size |
|------|---------|------|
| `JARVIS.exe` | Signed executable | 108.8 MB |
| `JARVIS_Certificate.cer` | Certificate for installation | 794 bytes |
| `Sign_JARVIS.ps1` | Automated signing script | - |
| `Get_JARVIS_Info.ps1` | Get hash/info for IT | - |
| `DIGITAL_SIGNATURE_GUIDE.md` | Complete documentation | - |

---

## Quick Commands

```powershell
# Install certificate (as Administrator)
certutil -addstore "Root" JARVIS_Certificate.cer

# Verify signature
Get-AuthenticodeSignature JARVIS.exe

# Re-sign executable (if modified)
.\Sign_JARVIS.ps1

# Get info for IT whitelist
.\Get_JARVIS_Info.ps1
```

---

## Security Notes

### Self-Signed Certificate Security
- ✅ **Pros:** Free, immediate, good for internal/testing use
- ⚠️ **Cons:** Requires manual installation, not trusted by default

### When to Use
- ✅ Internal company use
- ✅ Testing and development
- ✅ Small team distribution
- ✅ Educational purposes

### When to Upgrade to Commercial
- 📦 Public distribution
- 🏢 Large organization deployment
- 💼 Professional/commercial software
- 🔒 Maximum trust/no warnings

---

## Troubleshooting

### ❌ "This app can't run on your PC"
**Fix:** Install `JARVIS_Certificate.cer` in Trusted Root

### ❌ "Windows protected your PC"
**Fix:** Click "More info" → "Run anyway" (if certificate not installed)

### ❌ Certificate installation fails
**Fix:** Run PowerShell as Administrator

### ❌ Still blocked after certificate installed
**Fix:** Contact IT department for AppLocker exception

---

## Questions?

- **Documentation:** See `DIGITAL_SIGNATURE_GUIDE.md` for complete guide
- **Issues:** https://github.com/Rileymdm/JARVIS/issues
- **Repository:** https://github.com/Rileymdm/JARVIS

---

**Status:** ✅ JARVIS.exe is now digitally signed and ready for administrated PC use!

**Updated:** October 14, 2025
