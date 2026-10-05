"""Colours, fonts and spacing. Kept in one place so the look can be changed
without touching any logic."""

BG        = "#FFFFFF"   # window background
SURFACE   = "#F6F7F9"   # cards
BORDER    = "#E3E6EA"
TEXT      = "#14181D"
MUTED     = "#6B7480"
ACCENT    = "#2563EB"   # primary action
ACCENT_FG = "#FFFFFF"
ACCENT_DIM = "#1D4FD7"
DANGER    = "#B42318"
SUCCESS   = "#0F7B3F"
CODE_BG   = "#F0F2F5"

# Windows ships Segoe UI; the fallbacks cover everything else.
FAMILY = "Segoe UI"
MONO = "Consolas"

TITLE   = (FAMILY, 19, "bold")
H2      = (FAMILY, 12, "bold")
BODY    = (FAMILY, 10)
BODY_B  = (FAMILY, 10, "bold")
SMALL   = (FAMILY, 9)
CODE    = (MONO, 9)
INPUT   = (FAMILY, 12)

PAD = 16
GAP = 10


def pick_fonts(root) -> None:
    """Fall back gracefully if Segoe UI or Consolas are not installed."""
    global FAMILY, MONO, TITLE, H2, BODY, BODY_B, SMALL, CODE, INPUT
    try:
        from tkinter import font as tkfont
        available = set(tkfont.families(root))
    except Exception:                                    # noqa: BLE001
        return
    for candidate in (FAMILY, "Helvetica Neue", "DejaVu Sans", "Arial"):
        if candidate in available:
            FAMILY = candidate
            break
    for candidate in (MONO, "DejaVu Sans Mono", "Courier New", "Courier"):
        if candidate in available:
            MONO = candidate
            break
    TITLE  = (FAMILY, 19, "bold")
    H2     = (FAMILY, 12, "bold")
    BODY   = (FAMILY, 10)
    BODY_B = (FAMILY, 10, "bold")
    SMALL  = (FAMILY, 9)
    CODE   = (MONO, 9)
    INPUT  = (FAMILY, 12)
