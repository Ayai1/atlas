"""Small reusable pieces. Plain tk widgets with explicit colours, because
ttk ignores background colour on Windows."""

from __future__ import annotations

import tkinter as tk

from ui import theme as T


def label(parent, text, font=None, fg=None, bg=None, wrap=0, **kw):
    return tk.Label(
        parent, text=text, font=font or T.BODY, fg=fg or T.TEXT,
        bg=bg or T.BG, wraplength=wrap, justify="left", anchor="w", **kw
    )


def button(parent, text, command, primary=False, danger=False, width=None):
    """A flat button. tk.Button honours colours on Windows; ttk.Button does not."""
    if primary:
        bg, fg, active = T.ACCENT, T.ACCENT_FG, T.ACCENT_DIM
    elif danger:
        bg, fg, active = T.BG, T.DANGER, T.SURFACE
    else:
        bg, fg, active = T.BG, T.TEXT, T.SURFACE

    btn = tk.Button(
        parent, text=text, command=command, font=T.BODY,
        bg=bg, fg=fg, activebackground=active,
        activeforeground=T.ACCENT_FG if primary else T.TEXT,
        relief="solid", bd=1, highlightthickness=0,
        padx=14, pady=6, cursor="hand2",
    )
    if width:
        btn.configure(width=width)
    # tk.Button has no border colour option; a 1px solid border in the
    # accent colour is close enough and looks intentional.
    btn.configure(highlightbackground=T.BORDER)
    return btn


def card(parent, padding=T.PAD):
    """A bordered panel."""
    outer = tk.Frame(parent, bg=T.BORDER, bd=0, highlightthickness=0)
    inner = tk.Frame(outer, bg=T.SURFACE, bd=0, highlightthickness=0)
    inner.pack(fill="both", expand=True, padx=1, pady=1)
    body = tk.Frame(inner, bg=T.SURFACE)
    body.pack(fill="both", expand=True, padx=padding, pady=padding)
    outer.body = body                # type: ignore[attr-defined]
    return outer


def code_line(parent, text):
    """The exact command, shown in monospace so it reads as a literal."""
    box = tk.Frame(parent, bg=T.CODE_BG, bd=0, highlightthickness=0)
    tk.Label(
        box, text=text, font=T.CODE, fg=T.TEXT, bg=T.CODE_BG,
        anchor="w", justify="left", wraplength=560,
    ).pack(fill="x", padx=10, pady=7)
    return box


def divider(parent):
    return tk.Frame(parent, bg=T.BORDER, height=1)


class Scrollable(tk.Frame):
    """A vertically scrolling area. The content goes in `.body`."""

    def __init__(self, parent, bg=T.BG):
        super().__init__(parent, bg=bg)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0)
        self.bar = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.body = tk.Frame(self.canvas, bg=bg)

        self._window = self.canvas.create_window(
            (0, 0), window=self.body, anchor="nw"
        )
        self.canvas.configure(yscrollcommand=self.bar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.bar.pack(side="right", fill="y")

        self.body.bind("<Configure>", self._on_body_resize)
        self.canvas.bind("<Configure>", self._on_canvas_resize)
        # Wheel support: Windows/macOS send <MouseWheel>, X11 sends Buttons 4/5.
        for widget in (self.canvas, self.body):
            widget.bind("<MouseWheel>", self._on_wheel)
            widget.bind("<Button-4>", self._on_wheel)
            widget.bind("<Button-5>", self._on_wheel)

    def _on_body_resize(self, _event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_resize(self, event):
        self.canvas.itemconfigure(self._window, width=event.width)

    def _on_wheel(self, event):
        if getattr(event, "num", None) == 4:
            delta = -1
        elif getattr(event, "num", None) == 5:
            delta = 1
        else:
            delta = -1 if event.delta > 0 else 1
        self.canvas.yview_scroll(delta, "units")

    def clear(self):
        for child in self.body.winfo_children():
            child.destroy()
        self.canvas.yview_moveto(0)
