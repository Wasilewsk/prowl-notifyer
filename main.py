import sys

import config_io as _config_io

sys.modules["config-io"] = _config_io

from config_io import config_exists
from gui import run_app, run_wizard


def main() -> None:
    if config_exists():
        run_app()
    else:
        run_wizard()


if __name__ == "__main__":
    main()
