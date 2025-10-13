# Git LFS Setup Guide for JARVIS Project

## What is Git LFS?
Git LFS (Large File Storage) is designed for versioning large files like executables, images, videos, and datasets. Instead of storing the actual file content in Git, it stores pointers and keeps the large files on a separate LFS server.

## Why Use Git LFS for JARVIS.exe?
- Your executable is 108MB (large for Git)
- Keeps your repository clone times fast
- Prevents repository bloat
- Better for binary files that change frequently

## Setup Instructions

### 1. Install Git LFS (if not already installed)
```bash
# Download and install from: https://git-lfs.github.io/
# Or if you have GitHub CLI:
gh extension install github/gh-lfs

# Verify installation:
git lfs version
```

### 2. Initialize Git LFS in your repository
```bash
cd "C:\Users\wickerrd\Documents\GitHub\JARVIS"
git lfs install
```

### 3. Track your executable files
```bash
# Track all .exe files
git lfs track "*.exe"

# Or track specific files:
git lfs track "rocket-simulation-ui/dist/JARVIS.exe"

# Track other large files (optional):
git lfs track "*.zip"
git lfs track "*.msi"
git lfs track "*.dmg"
```

### 4. Commit the LFS tracking configuration
```bash
git add .gitattributes
git commit -m "Add Git LFS tracking for executables"
```

### 5. Add and commit your executable
```bash
git add rocket-simulation-ui/dist/JARVIS.exe
git commit -m "Add JARVIS executable via Git LFS"
git push origin main
```

## Current Repository Structure
After setup, your `.gitattributes` file will contain:
```
*.exe filter=lfs diff=lfs merge=lfs -text
```

## Verification Commands
```bash
# Check what files are tracked by LFS
git lfs ls-files

# Check LFS status
git lfs status

# See LFS file info
git lfs pointer --file="rocket-simulation-ui/dist/JARVIS.exe"
```

## Best Practices

### Files to Track with LFS:
- ✅ `JARVIS.exe` (108MB executable)
- ✅ `*.exe` (all executables)
- ✅ Large images (>10MB)
- ✅ Video files
- ✅ Binary assets
- ✅ Large datasets

### Files NOT to Track with LFS:
- ❌ Source code (`.py`, `.js`, etc.)
- ❌ Text files (`.md`, `.txt`)
- ❌ Small images (<1MB)
- ❌ Configuration files

## GitHub LFS Limits
- **Free:** 1GB storage, 1GB bandwidth/month
- **Pro:** 50GB storage, 50GB bandwidth/month
- **Additional:** $5/month per 50GB pack

## Alternative: Release Assets
Instead of LFS, you could use GitHub Releases:
```bash
# Create a release and upload JARVIS.exe as an asset
gh release create v1.0.0 rocket-simulation-ui/dist/JARVIS.exe --title "JARVIS v1.0.0" --notes "Initial release of JARVIS Rocket Simulation"
```

## Commands to Run Now
```bash
# Navigate to your repository
cd "C:\Users\wickerrd\Documents\GitHub\JARVIS"

# Initialize LFS
git lfs install

# Track exe files
git lfs track "*.exe"

# Commit LFS config
git add .gitattributes
git commit -m "Configure Git LFS for executables"

# Add your executable
git add rocket-simulation-ui/dist/JARVIS.exe
git commit -m "Add JARVIS.exe via Git LFS"

# Push to GitHub
git push origin main
```

This will properly manage your large executable file without bloating your Git repository!