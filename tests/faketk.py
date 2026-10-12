"""A stand-in for tkinter, so the window's wiring can be tested headlessly.

This does NOT prove the UI looks right — only a human running it can do that.
What it does prove is that every handler runs, every widget is built with
option names that real tkinter accepts, and no code path raises.

Option whitelists below are the real tk option sets for each widget.
"""

from __future__ import annotations

# Options every tk widget accepts.
_COMMON = {
    "bg", "background", "fg", "foreground", "bd", "borderwidth", "relief",
    "highlightthickness", "highlightbackground", "highlightcolor", "cursor",
    "width", "height", "padx", "pady", "takefocus", "state", "font",
}
_TEXTISH = {
    "text", "textvariable", "anchor", "justify", "wraplength", "image",
    "compound", "underline",
}

_VALID = {
    "Frame":     _COMMON | {"class_", "container"},
    "Label":     _COMMON | _TEXTISH,
    "Button":    _COMMON | _TEXTISH | {
        "command", "activebackground", "activeforeground", "default",
        "overrelief", "repeatdelay", "repeatinterval",
    },
    "Entry":     _COMMON | {
        "textvariable", "insertbackground", "show", "justify", "validate",
        "validatecommand", "xscrollcommand", "readonlybackground",
        "selectbackground", "selectforeground", "exportselection",
    },
    "Canvas":    _COMMON | {
        "yscrollcommand", "xscrollcommand", "scrollregion", "confine",
        "closeenough", "xscrollincrement", "yscrollincrement",
    },
    "Scrollbar": _COMMON | {
        "orient", "command", "activerelief", "elementborderwidth",
        "jump", "repeatdelay", "repeatinterval", "troughcolor",
    },
    "Tk":        _COMMON | {"class_", "screenName", "baseName", "useTk"},
    "Toplevel":  _COMMON | {"class_", "container", "menu"},
}

_PACK = {"side", "fill", "expand", "padx", "pady", "ipadx", "ipady",
         "anchor", "before", "after", "in_"}
_GRID = {"row", "column", "sticky", "padx", "pady", "ipadx", "ipady",
         "rowspan", "columnspan", "in_"}


class BadOption(AssertionError):
    """A widget option real tkinter would reject."""


class _Widget:
    _kind = "Frame"

    def __init__(self, master=None, **kw):
        self.master = master
        self.children: list[_Widget] = []
        self.options: dict = {}
        self.bindings: dict = {}
        self._destroyed = False
        if isinstance(master, _Widget):
            master.children.append(self)
        self._check(kw)
        self.options.update(kw)

    def _check(self, kw):
        allowed = _VALID.get(self._kind, _COMMON)
        for key in kw:
            if key not in allowed:
                raise BadOption(
                    f"tk.{self._kind} does not accept '{key}'. "
                    f"Valid: {', '.join(sorted(allowed))}"
                )

    # geometry
    def pack(self, **kw):
        for k in kw:
            if k not in _PACK:
                raise BadOption(f"pack() does not accept '{k}'")
        return self

    def grid(self, **kw):
        for k in kw:
            if k not in _GRID:
                raise BadOption(f"grid() does not accept '{k}'")
        return self

    def place(self, **kw):
        return self

    def pack_propagate(self, flag=None): return None
    def grid_propagate(self, flag=None): return None
    def pack_forget(self): return self
    def grid_forget(self): return self

    # configuration
    def configure(self, **kw):
        self._check(kw)
        self.options.update(kw)
        return self
    config = configure

    def cget(self, key):
        return self.options.get(key)

    def __getitem__(self, key):
        return self.options.get(key)

    # events
    def bind(self, sequence, func, add=None):
        self.bindings[sequence] = func
        return "id"

    def bind_all(self, sequence, func, add=None):
        return "id"

    def unbind(self, sequence, funcid=None): pass

    # tree
    def winfo_children(self):
        return list(self.children)

    def destroy(self):
        self._destroyed = True
        if isinstance(self.master, _Widget) and self in self.master.children:
            self.master.children.remove(self)
        for c in list(self.children):
            c.destroy()

    def winfo_width(self):  return 840
    def winfo_height(self): return 660
    def winfo_rootx(self):  return 0
    def winfo_rooty(self):  return 0
    def winfo_exists(self): return not self._destroyed

    def focus_set(self): pass
    def update_idletasks(self): pass
    def update(self): pass
    def after(self, ms, func=None, *a):
        if func:
            func(*a)
        return "id"


class Frame(_Widget):     _kind = "Frame"
class Label(_Widget):     _kind = "Label"
class Canvas(_Widget):
    _kind = "Canvas"
    def create_window(self, coords, **kw): return 1
    def itemconfigure(self, item, **kw): pass
    def configure(self, **kw):
        # scrollregion is set via configure and is a valid Canvas option
        return super().configure(**kw)
    def bbox(self, tag): return (0, 0, 800, 1200)
    def yview(self, *a): pass
    def yview_scroll(self, n, what): pass
    def yview_moveto(self, f): pass


class Scrollbar(_Widget):
    _kind = "Scrollbar"
    def set(self, *a): pass


class Button(_Widget):
    _kind = "Button"
    def invoke(self):
        cmd = self.options.get("command")
        if cmd:
            return cmd()


class Entry(_Widget):
    _kind = "Entry"
    def __init__(self, master=None, **kw):
        super().__init__(master, **kw)
        self._text = ""
    def insert(self, index, s): self._text = f"{self._text}{s}"
    def delete(self, first, last=None): self._text = ""
    def get(self): return self._text
    def set_text(self, s): self._text = s


class Tk(_Widget):
    _kind = "Tk"
    def __init__(self, **kw):
        super().__init__(None, **kw)
    def title(self, s=None): pass
    def geometry(self, s=None): pass
    def minsize(self, w, h): pass
    def resizable(self, w, h): pass
    def mainloop(self): pass
    def wait_window(self, win=None): pass
    def protocol(self, name, func): pass


class Toplevel(Tk):
    _kind = "Toplevel"
    def __init__(self, master=None, **kw):
        _Widget.__init__(self, master, **kw)
    def transient(self, parent=None): pass
    def grab_set(self): pass
    def grab_release(self): pass


class font:                                    # noqa: N801
    @staticmethod
    def families(root=None):
        return ("Segoe UI", "Consolas", "Arial", "Courier New")


def install():
    """Put this module in place of tkinter. Returns a restore callable."""
    import sys
    import types

    saved = {k: sys.modules.get(k) for k in ("tkinter", "tkinter.font")}
    fake = types.ModuleType("tkinter")
    for name in ("Frame", "Label", "Button", "Entry", "Canvas", "Scrollbar",
                 "Tk", "Toplevel", "BadOption"):
        setattr(fake, name, globals()[name])
    fake_font = types.ModuleType("tkinter.font")
    fake_font.families = font.families
    fake.font = fake_font
    sys.modules["tkinter"] = fake
    sys.modules["tkinter.font"] = fake_font

    def restore():
        for k, v in saved.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v
    return restore
