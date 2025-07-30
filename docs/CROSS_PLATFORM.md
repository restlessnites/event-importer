# Cross-Platform Building Guide

This guide explains how to build Event Importer for different platforms and architectures.

## Important Limitations

PyInstaller creates platform-specific executables. You **cannot** build:
- Windows executables on macOS or Linux
- macOS executables on Windows or Linux  
- Linux executables on Windows or macOS

You must build on the target platform.

## macOS Builds

### Building for Your Current Architecture

```bash
# Build for your current Mac architecture (Apple Silicon or Intel)
make package
```

### Building for Intel Macs on Apple Silicon

If you're on an Apple Silicon Mac (M1/M2/M3) and need to build for Intel Macs:

```bash
# Build specifically for Intel (x86_64) architecture
make package-x86_64
```

This creates:
- `event-importer-x86_64.zip` - Intel-compatible app
- `event-importer-installer` - Intel-compatible installer

### Creating Universal Binaries

To create a universal binary that runs on both Intel and Apple Silicon:

1. Build on Intel Mac:
   ```bash
   make package
   mv dist/event-importer/event-importer event-importer-x86_64
   ```

2. Build on Apple Silicon Mac:
   ```bash
   make package
   mv dist/event-importer/event-importer event-importer-arm64
   ```

3. Combine using `lipo`:
   ```bash
   lipo -create -output event-importer-universal \
     event-importer-x86_64 \
     event-importer-arm64
   ```

4. Replace the binary in the app bundle with the universal binary

## Windows Builds

### Prerequisites

1. Windows 10 or 11
2. Python 3.11 or 3.12
3. Install uv:
   ```powershell
   powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```

### Building on Windows

1. Clone the repository:
   ```powershell
   git clone https://github.com/yourusername/event-importer.git
   cd event-importer
   ```

2. Install dependencies:
   ```powershell
   uv sync
   ```

3. Build the application:
   ```powershell
   uv run pyinstaller --noconfirm event-importer-windows.spec
   ```

4. Build the installer:
   ```powershell
   uv run pyinstaller --noconfirm event-importer-installer-windows.spec
   ```

5. Create zip files:
   ```powershell
   cd dist
   Compress-Archive -Path event-importer -DestinationPath ..\event-importer-windows.zip
   Compress-Archive -Path event-importer-installer.exe -DestinationPath ..\event-importer-installer-windows.zip
   ```

### Windows-Specific Considerations

- Windows Defender may flag the executable as suspicious. You may need to:
  - Sign the executable with a code signing certificate
  - Submit it to Microsoft for analysis
  - Add an exception during development

- The installer will need to handle Windows-specific paths:
  - Installation directory: `%LOCALAPPDATA%\event-importer`
  - Data directory: `%APPDATA%\event-importer`

## Linux Builds

### Prerequisites

1. Ubuntu 20.04+ or similar
2. Python 3.11 or 3.12
3. Install uv:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

### Building on Linux

1. Clone and build:
   ```bash
   git clone https://github.com/yourusername/event-importer.git
   cd event-importer
   uv sync
   uv run pyinstaller --noconfirm event-importer.spec
   ```

2. Create AppImage (recommended for distribution):
   ```bash
   # Install appimagetool
   wget https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage
   chmod +x appimagetool-x86_64.AppImage
   
   # Create AppImage
   ./appimagetool-x86_64.AppImage dist/event-importer
   ```

## CI/CD Building

For automated builds across platforms, consider using:

### GitHub Actions

```yaml
name: Build Cross-Platform

on:
  release:
    types: [created]

jobs:
  build-macos:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v3
      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh
      - name: Build
        run: |
          uv sync
          make package
      - name: Upload artifacts
        uses: actions/upload-artifact@v3
        with:
          name: macos-build
          path: event-importer.zip

  build-windows:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v3
      - name: Install uv
        run: powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
      - name: Build
        run: |
          uv sync
          uv run pyinstaller --noconfirm event-importer-windows.spec
      # ... etc
```

## Architecture Detection

To check what architecture your build supports:

### macOS
```bash
file dist/event-importer/event-importer
# Output will show: Mach-O 64-bit executable x86_64 or arm64
```

### Windows
```powershell
dumpbin /headers dist\event-importer\event-importer.exe | findstr "machine"
```

## Troubleshooting

### "Cannot execute binary file" Error
- You're trying to run a binary built for a different architecture
- Solution: Build for your specific architecture

### Missing Dependencies on Target Machine
- PyInstaller should bundle everything, but some system libraries might be missing
- Solution: Test on a clean VM of the target OS

### Code Signing Issues
- macOS: Unsigned apps require user approval in System Preferences
- Windows: May trigger SmartScreen warnings
- Solution: Sign your executables with proper certificates

## Testing Cross-Platform Builds

Always test your builds on the target platform:

1. Fresh VM or machine without Python installed
2. Different OS versions (Windows 10/11, macOS 12/13/14)
3. Both Intel and Apple Silicon Macs
4. With and without admin privileges