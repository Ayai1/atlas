"""Per-user Windows settings held in the registry.

Two facts this module exists to hide:

1. These values live under HKEY_CURRENT_USER, so changing them needs no
   administrator rights — which matters, because our user should not be
   trained to click through elevation prompts.
2. Writing the registry value alone often changes nothing on screen. Windows
   only notices when SystemParametersInfoW is called to broadcast the change.
   Every SPI constant used here was checked against Microsoft's documentation;
   we do not call one we could not verify.

Read-before-write is enforced: read_value() is always called before
write_value(), which is what makes undo possible (ARCHITECTURE.md P3, P4).
"""

from __future__ import annotations

import platform
from dataclasses import dataclass

if platform.system() == "Windows":                       # pragma: no cover
    import ctypes
    import winreg
else:                                                    # tests and Linux
    ctypes = None                                        # type: ignore
    winreg = None                                        # type: ignore


class SettingError(RuntimeError):
    """The setting could not be read, written, or applied."""


# --- SystemParametersInfoW ------------------------------------------------
# Verified constants only. SPI_SETMESSAGEDURATION is deliberately absent:
# we could not confirm its value, and calling the wrong action code would
# change some other system parameter without the user's consent.
SPI_SETDOUBLECLICKTIME = 0x0020   # 32   — uiParam carries the value
SPI_SETCURSORS         = 0x0057   # 87   — signal only, reloads cursors
SPI_SETMOUSESPEED      = 0x0071   # 113  — pvParam carries the value
SPI_SETCARETWIDTH      = 0x2007   # 8199 — pvParam carries the value

SPIF_UPDATEINIFILE = 0x01
SPIF_SENDCHANGE    = 0x02
_SPIF = SPIF_UPDATEINIFILE | SPIF_SENDCHANGE


@dataclass(frozen=True)
class Setting:
    """One per-user Windows setting."""

    key: str                 # registry subkey under HKEY_CURRENT_USER
    name: str                # value name
    kind: str                # "dword" | "sz"
    default: int = 0         # what Windows behaves as when the value is absent
    spi: int | None = None   # SystemParametersInfo action, if any
    spi_mode: str = "none"   # "ui" | "pv" | "signal" | "none"
    needs_signout: bool = False
    notify: str = "none"     # "theme" | "internet" | "none" — see _notify()


def _require_windows() -> None:
    if platform.system() != "Windows":
        raise SettingError(
            f"These settings are Windows-only; this machine reports "
            f"'{platform.system()}'."
        )


def read_state(setting: Setting) -> tuple[int, bool]:
    """Return (value, exists_in_registry).

    Windows omits these values until they are changed once. An absent value is
    not an error: it means the setting is at its documented default. We record
    whether it existed so undo can put the registry back exactly — including
    removing a value we created.
    """
    _require_windows()
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, setting.key) as k:
            raw, _kind = winreg.QueryValueEx(k, setting.name)
    except FileNotFoundError:
        return setting.default, False
    except OSError as exc:
        raise SettingError(f"Could not read '{setting.name}': {exc}") from exc
    try:
        return int(raw), True
    except (TypeError, ValueError):
        # Present but unreadable — treat as the default rather than guessing.
        return setting.default, False


def read_value(setting: Setting) -> int:
    """Current value, falling back to the Windows default when absent."""
    return read_state(setting)[0]


def delete_value(setting: Setting) -> str:
    """Remove a value we created, so undo restores the registry exactly."""
    _require_windows()
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, setting.key, 0, winreg.KEY_SET_VALUE
        ) as k:
            winreg.DeleteValue(k, setting.name)
    except FileNotFoundError:
        pass                                   # already gone; nothing to do
    except OSError as exc:
        raise SettingError(f"Could not remove '{setting.name}': {exc}") from exc
    _apply_live(setting, setting.default)
    return f"removed HKCU\\{setting.key}\\{setting.name} (back to Windows default)"


def write_value(setting: Setting, value: int) -> str:
    """Write the value and ask Windows to apply it. Returns what was done."""
    _require_windows()
    try:
        with winreg.CreateKeyEx(
            winreg.HKEY_CURRENT_USER, setting.key, 0, winreg.KEY_SET_VALUE
        ) as k:
            if setting.kind == "dword":
                winreg.SetValueEx(k, setting.name, 0, winreg.REG_DWORD, int(value))
            else:
                winreg.SetValueEx(k, setting.name, 0, winreg.REG_SZ, str(value))
    except OSError as exc:
        raise SettingError(f"Windows refused the change: {exc}") from exc

    applied = _apply_live(setting, value)
    shown = f'HKCU\\{setting.key}\\{setting.name} = {value}'
    return shown + ("" if applied else "   (takes effect after sign-out)")


def read_text(key: str, name: str) -> str | None:
    """A text value under HKEY_CURRENT_USER, or None if absent."""
    _require_windows()
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key) as k:
            raw, _kind = winreg.QueryValueEx(k, name)
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise SettingError(f"Could not read '{name}': {exc}") from exc
    return str(raw) if raw not in (None, "") else None


# Some settings are not SystemParametersInfo values; Windows learns about them
# from a broadcast instead. Constants from the Win32 headers.
HWND_BROADCAST = 0xFFFF
WM_SETTINGCHANGE = 0x001A
SMTO_ABORTIFHUNG = 0x0002
INTERNET_OPTION_REFRESH = 37
INTERNET_OPTION_SETTINGS_CHANGED = 39


def _notify(kind: str) -> bool:
    """Tell running programs a setting changed. Never raises.

    "theme": broadcast WM_SETTINGCHANGE with "ImmersiveColorSet", the signal
    the taskbar and apps listen for when light/dark mode or transparency
    changes. "internet": tell WinINet to reload its proxy settings, so the
    change applies without signing out.
    """
    if ctypes is None:
        return False
    try:
        if kind == "theme":
            result = ctypes.c_size_t()
            ctypes.windll.user32.SendMessageTimeoutW(
                HWND_BROADCAST, WM_SETTINGCHANGE, 0,
                ctypes.c_wchar_p("ImmersiveColorSet"), SMTO_ABORTIFHUNG,
                2000, ctypes.byref(result))
            return True
        if kind == "internet":
            wininet = ctypes.windll.wininet
            ok1 = wininet.InternetSetOptionW(
                None, INTERNET_OPTION_SETTINGS_CHANGED, None, 0)
            ok2 = wininet.InternetSetOptionW(None, INTERNET_OPTION_REFRESH, None, 0)
            return bool(ok1 and ok2)
    except Exception:                           # noqa: BLE001
        return False
    return False


def _apply_live(setting: Setting, value: int) -> bool:
    """Best effort: ask Windows to adopt the change now. Never raises."""
    if setting.notify != "none":
        return _notify(setting.notify)
    if setting.spi is None or ctypes is None:
        return not setting.needs_signout
    spi = ctypes.windll.user32.SystemParametersInfoW
    spi.restype = ctypes.c_bool
    try:
        if setting.spi_mode == "ui":
            ok = spi(setting.spi, int(value), None, _SPIF)
        elif setting.spi_mode == "pv":
            ok = spi(setting.spi, 0, ctypes.c_void_p(int(value)), _SPIF)
        else:                                   # "signal"
            ok = spi(setting.spi, 0, None, _SPIF)
        return bool(ok)
    except Exception:                           # noqa: BLE001
        return False


# --- the settings we support ---------------------------------------------
POINTER_SIZE = Setting(
    default=32,
    key=r"Control Panel\Cursors", name="CursorBaseSize", kind="dword",
    spi=SPI_SETCURSORS, spi_mode="signal")

DOUBLE_CLICK_SPEED = Setting(
    default=500,
    key=r"Control Panel\Mouse", name="DoubleClickSpeed", kind="sz",
    spi=SPI_SETDOUBLECLICKTIME, spi_mode="ui")

POINTER_SPEED = Setting(
    default=10,
    key=r"Control Panel\Mouse", name="MouseSensitivity", kind="sz",
    spi=SPI_SETMOUSESPEED, spi_mode="pv")

CARET_WIDTH = Setting(
    default=1,
    key=r"Control Panel\Desktop", name="CaretWidth", kind="dword",
    spi=SPI_SETCARETWIDTH, spi_mode="pv")

TEXT_SCALE = Setting(
    default=100,
    key=r"Software\Microsoft\Accessibility", name="TextScaleFactor",
    kind="dword", spi=None, spi_mode="none", needs_signout=False)


# --- display --------------------------------------------------------------
_PERSONALIZE = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"

APPS_LIGHT = Setting(                     # 1 = light, 0 = dark
    default=1, key=_PERSONALIZE, name="AppsUseLightTheme", kind="dword",
    notify="theme")

SYSTEM_LIGHT = Setting(                   # taskbar, Start, notifications
    default=1, key=_PERSONALIZE, name="SystemUsesLightTheme", kind="dword",
    notify="theme")

TRANSPARENCY = Setting(
    default=1, key=_PERSONALIZE, name="EnableTransparency", kind="dword",
    notify="theme")

# --- network --------------------------------------------------------------
INTERNET_SETTINGS = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"

PROXY_ENABLE = Setting(
    default=0, key=INTERNET_SETTINGS, name="ProxyEnable", kind="dword",
    notify="internet")

# --- storage --------------------------------------------------------------
# Storage Sense keeps its options as numbered DWORDs. Absent values mean the
# defaults the Settings page shows on a fresh install.
_STORAGE_POLICY = (r"Software\Microsoft\Windows\CurrentVersion\StorageSense"
                   r"\Parameters\StoragePolicy")

STORAGE_SENSE = Setting(default=0, key=_STORAGE_POLICY, name="01", kind="dword")
STORAGE_SENSE_SCHEDULE = Setting(
    default=0, key=_STORAGE_POLICY, name="2048", kind="dword")
STORAGE_SENSE_TEMP = Setting(
    default=1, key=_STORAGE_POLICY, name="04", kind="dword")
STORAGE_SENSE_RECYCLE_DAYS = Setting(
    default=30, key=_STORAGE_POLICY, name="256", kind="dword")
