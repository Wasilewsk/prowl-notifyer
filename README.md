# Windows Prowl Notifier

A screen-reader friendly wxPython onboarding/configuration wizard for sending Prowl notifications from Windows.

## Features

- Battery low, CPU high, memory high, disk low alerts
- Power adapter plug/unplug alerts
- Network connectivity change alerts
- Port open/close alerts (optional)
- File create/modify/delete alerts (optional)
- Accessible wizard-based setup
- Settings panel for changing configuration
- Hides to system tray
- Configuration saved to `%USERPROFILE%\prowl-notifyer-config\config.toml`

## Setup

1. Install Python 3.11+.
2. Install dependencies:

```bash
python -m pip install -r requirements.txt
```

3. Run the app:

```bash
python main.py
```

## Configuration

- Config path: `%USERPROFILE%\prowl-notifyer-config\config.toml`
- You can start from `config.example.toml` if you prefer editing manually.

## Notes

- The wizard includes a “Send Test Notification” button.
- The app can start monitoring immediately after the wizard finishes.
- The app hides to the system tray; use the tray icon to open Settings or Exit.
- Port monitoring can be noisy; you can limit to specific ports.
- The app stores a tiny state file at `data/state.json` for cooldown tracking.

## Build (after you confirm it works)

```bash
pyinstaller ProwlNotifier.spec
```

## Libraries & Docs

- [wxPython](https://wxpython.org/Phoenix/docs/html/)
- [PyInstaller](https://pyinstaller.org/en/stable/)
- [psutil](https://psutil.readthedocs.io/)
- [Requests](https://requests.readthedocs.io/)
- [Prowl API](https://www.prowlapp.com/api.php)

## Updates

- The app can check GitHub for new releases.
- Downloads are saved to your `Downloads` folder and must be replaced manually.
