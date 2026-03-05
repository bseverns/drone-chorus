# Setup Guide for Non-Coders (a.k.a. How to Get Python Ready Without Losing Your Mind)

Welcome to the pit crew. This repo sings when Python is tuned to **3.10 or newer** and `pip` is ready to feed it dependencies.
This guide walks through installing/verifying Python + `pip`, opening a terminal, and running the one command we need: 

```bash
pip install -r software/midi-bridge/requirements.txt
```

If you've never cracked open a terminal before, you're in the right place. Grab your OS section and follow along.

---

## Windows

### Option A: Microsoft Store (fastest if you're on Windows 10/11)
1. Open the **Microsoft Store** app.
2. Search for **"Python 3.11"** (or newer 3.x release). Install the official Python app from the Python Software Foundation.
3. Launch the Python app once so Windows wires it into your PATH.

### Option B: python.org installer (if the Store is blocked)
1. Visit [https://www.python.org/downloads/windows/](https://www.python.org/downloads/windows/).
2. Grab the latest **Python 3.x** installer (`python-3.x.y-amd64.exe`).
3. Run it and **check the box** that says **"Add python.exe to PATH"**.
4. Choose **Customize installation** if you want, but the defaults work fine.

### Verify Python + pip
1. Press **Win + X**, choose **Windows Terminal**, **Command Prompt**, or **PowerShell**.
2. In the terminal, run:
   ```powershell
   python --version
   pip --version
   ```
   - You should see Python `3.10.x` or newer. If you see something older, uninstall and reinstall with a fresh download.
   - If `pip` complains, reinstall using the python.org installer with the "Install pip" checkbox enabled.

### Run the dependency install
With the repo cloned and your terminal pointed at its root (`cd path\to\drone-chorus`):
```powershell
pip install -r software/midi-bridge/requirements.txt
```

---

## macOS

### Option A: Homebrew (recommended for folks who like package managers)
1. If Homebrew isn't installed, follow the directions at [https://brew.sh](https://brew.sh) — it gives you a single command to paste into Terminal.
2. Open **Terminal** (`Cmd + Space`, type *Terminal*, press Enter).
3. Install Python:
   ```bash
   brew install python@3.11
   ```
   Homebrew sets up `python3` and `pip3` for you.

### Option B: Official installer
1. Visit [https://www.python.org/downloads/macos/](https://www.python.org/downloads/macos/).
2. Download the latest **macOS 64-bit universal installer**.
3. Open the `.pkg` file and run through the installer. It drops Python into `/Library/Frameworks/...` and adds the `python3` launcher.

### Verify Python + pip
In **Terminal**, run:
```bash
python3 --version
pip3 --version
```
- Confirm Python `3.10+`. If macOS shows `Python 2.7` when you type `python`, ignore it and use `python3` instead.

### Run the dependency install
From the repo root:
```bash
pip3 install -r software/midi-bridge/requirements.txt
```
> If you prefer using `python3 -m pip`, that's also cool:
> ```bash
> python3 -m pip install -r software/midi-bridge/requirements.txt
> ```

---

## Linux

You're spoiled for choice depending on your distro. The goal is Python `3.10+` and `pip`.

### Debian/Ubuntu
```bash
sudo apt update
sudo apt install python3 python3-pip
```
If the default Python is older than 3.10, install from [deadsnakes](https://launchpad.net/~deadsnakes/+archive/ubuntu/ppa) or use `pyenv`.

### Fedora
```bash
sudo dnf install python3 python3-pip
```

### Arch / Manjaro
```bash
sudo pacman -S python python-pip
```

### Verify Python + pip
Open your terminal emulator of choice (GNOME Terminal, Konsole, kitty, etc.) and run:
```bash
python3 --version
pip3 --version
```
- Look for Python `3.10+`. If your distro defaults to `python` pointing to Python 3, the commands might work without the `3` suffix.

### Run the dependency install
From the repo root:
```bash
pip3 install -r software/midi-bridge/requirements.txt
```
If your distro calls the binary `pip`, that's fine:
```bash
pip install -r software/midi-bridge/requirements.txt
```

---

## How to open a terminal (if you're not sure)
- **Windows**: Press **Win + X** → choose **Windows Terminal** or **Command Prompt**. Old-school? Press **Win + R**, type `cmd`, hit Enter.
- **macOS**: Press **Cmd + Space**, type *Terminal*, hit Enter. Or find it in `/Applications/Utilities/`.
- **Linux**: Most desktops respond to **Ctrl + Alt + T**. Otherwise search for *Terminal* in your app launcher.

---

## Checklist before you run anything else
- [ ] Python `3.10.x` or newer shows up when you run `python --version` or `python3 --version`.
- [ ] `pip --version` (or `pip3 --version`) reports the same Python path.
- [ ] `pip install -r software/midi-bridge/requirements.txt` finishes without errors.

---

## Optional: build a desktop app (less terminal use later)

If you want a clickable app bundle for the control room GUI:

```bash
./scripts/build_gui_binary.sh
```

That command builds `dist/DroneChorusControlRoom` via PyInstaller.

---

## Optional: run in a container (advanced helper)

If your Python setup is unstable or workshop machines differ, use Docker:

```bash
docker build -f software/midi-bridge/Dockerfile -t drone-chorus-bridge .
docker run --rm -it --device /dev/ttyUSB0 drone-chorus-bridge --serial /dev/ttyUSB0
```

You now have the MSP→MIDI bridge dependencies staged. Flip back to the README quickstart and let the drones sing.
