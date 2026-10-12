"""Start the window.

Double-click this file, or run:  python run_ui.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


def main() -> int:
    try:
        import tkinter                                   # noqa: F401
    except ImportError:
        print(
            "This needs tkinter, which normally ships with Python.\n"
            "On Windows: re-run the Python installer and tick 'tcl/tk and IDLE'.\n"
            "On Linux:   sudo apt install python3-tk"
        )
        return 1

    from ui.app import launch
    return launch()


if __name__ == "__main__":
    sys.exit(main())
