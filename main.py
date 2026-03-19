import sys
import traceback

import wx

import config_io as _config_io

sys.modules["config-io"] = _config_io

from config_io import CONFIG_DIR, config_exists
from gui import run_app, run_wizard


def _write_crash_log(exc: BaseException) -> str:
    import os

    os.makedirs(CONFIG_DIR, exist_ok=True)
    path = os.path.join(CONFIG_DIR, "crash.log")
    with open(path, "w", encoding="utf-8") as f:
        f.write("Unhandled exception:\\n\\n")
        f.write("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))
    return path


def _show_crash_dialog(path: str) -> None:
    try:
        app = wx.App(False)
        wx.MessageBox(
            f\"The app crashed. A log was saved to:\\n{path}\\n\\nPlease send this log for debugging.\",
            \"Prowl Notifier Error\",
        )
        app.MainLoop()
    except Exception:
        pass


def main() -> None:
    if config_exists():
        run_app()
    else:
        run_wizard()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        log_path = _write_crash_log(exc)
        _show_crash_dialog(log_path)
