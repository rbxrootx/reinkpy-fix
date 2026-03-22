# ReInkPy Fix

`reinkpy-fix` is a maintained fork of the original `reinkpy` project for resetting waste ink counters on supported Epson printers.

This fork focuses on the path most people actually need:

- Epson printers reachable over the local network
- A simple Windows GUI that can be packaged as a single `.exe`
- A small CLI for advanced users
- Fixes for SNMP write support so LAN resets can work

This is still printer maintenance software, not magic. It does not replace pads, tanks, or other hardware.

## What Changed In This Fork

- Fixed SNMP write support required for LAN waste-counter resets
- Passed custom SNMP read/write community strings through the device stack
- Added a Windows GUI entrypoint: `reinkpy_fix_gui.py`
- Added a CLI entrypoint for scanning and resetting printers
- Added a PyInstaller spec and build script for `ReInkPyFix.exe`
- Cleaned up repo metadata and packaging for GitHub use

## End-User Windows Build

The easiest path for non-technical users is the packaged Windows executable.

### Build It

```powershell
python -m pip install -r requirements.txt
powershell -ExecutionPolicy Bypass -File .\build-exe.ps1
```

The finished executable will be written to:

`dist\ReInkPyFix.exe`

### Use It

1. Connect the printer and PC to the same local network.
2. Run `ReInkPyFix.exe`.
3. Click `Scan`, or enter the printer IP manually.
4. Click `Connect`.
5. If autodetection fails, choose the printer model manually.
6. Click `Reset Waste Counter`.

Default SNMP settings are:

- Read community: `public`
- Write community: `private`

If your printer uses different values, change them in the app before connecting.

## CLI Usage

Install locally:

```powershell
python -m pip install -e .[net]
```

Scan for printers:

```powershell
python -m reinkpy.main --scan
```

Show printer info:

```powershell
python -m reinkpy.main --ip 192.168.1.50 --info
```

Reset a printer:

```powershell
python -m reinkpy.main --ip 192.168.1.50 --reset
```

Force a specific model profile:

```powershell
python -m reinkpy.main --ip 192.168.1.50 --model L3060 --reset
```

## Development

Install editable dependencies:

```powershell
python -m pip install -e .[net]
```

Optional extras:

- `.[usb]` for USB support experiments
- `.[ui]` for the original text UI

## Publishing Your Fork

If you want to publish your own GitHub fork:

1. Create a new empty repository on GitHub.
2. Point `origin` at your repo.
3. Push this branch.

Example:

```powershell
git remote rename origin upstream-fork
git remote add origin https://github.com/YOUR-USER/reinkpy-fix.git
git push -u origin main
```

## Safety

Use this at your own risk.

- Confirm the printer model before resetting.
- Service the waste ink pads/tank as needed.
- Power-cycle the printer after the reset if the error does not clear immediately.

## License

This project remains under AGPL-3.0-or-later. See [LICENSE](LICENSE).

## Upstream

Original project:

https://codeberg.org/atufi/reinkpy
