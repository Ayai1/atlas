"""The Atlas window.

Deliberately thin. Every decision is made in viewmodel.py; this file draws
the result and forwards clicks. Mutating changes still go through
engine.executor, so the window cannot skip the confirmation gate any
more than the command line can.
"""

from __future__ import annotations

import tkinter as tk

from engine.tool import Preview
from ui import theme as T
from ui.viewmodel import Match, Outcome, ViewModel
from ui.widgets import (
    Scrollable, button, card, code_line, divider, label,
)

SUGGESTIONS = [
    "I keep losing the mouse pointer",
    "the text is too small to read",
    "double clicking never works for me",
    "my screen keeps going dark while I read",
]


class ConfirmDialog(tk.Toplevel):
    """The confirmation card. The whole product, in one window.

    Plain English, the literal command, and where the value is moving from
    and to. Nothing is applied until Apply is pressed here.
    """

    def __init__(self, parent, preview: Preview, tool_name: str):
        super().__init__(parent)
        self.approved = False
        self.title("Confirm this change")
        self.configure(bg=T.BG)
        self.resizable(False, False)
        self.transient(parent)

        wrap = tk.Frame(self, bg=T.BG)
        wrap.pack(fill="both", expand=True, padx=T.PAD + 4, pady=T.PAD + 4)

        label(wrap, "About to change a setting", font=T.H2).pack(anchor="w")
        label(wrap, preview.summary, fg=T.TEXT, wrap=520).pack(
            anchor="w", pady=(6, T.GAP)
        )

        rows = tk.Frame(wrap, bg=T.BG)
        rows.pack(fill="x", pady=(0, T.GAP))
        self._row(rows, 0, "Setting", tool_name)
        self._row(rows, 1, "Right now", preview.current_value)
        self._row(rows, 2, "Will become", preview.new_value)
        self._row(
            rows, 3, "Reversible",
            "Yes — you can undo this" if preview.reversible else "No",
        )

        label(wrap, "The exact command that will run:",
              font=T.SMALL, fg=T.MUTED).pack(anchor="w", pady=(4, 4))
        code_line(wrap, preview.command).pack(fill="x", pady=(0, T.PAD))

        actions = tk.Frame(wrap, bg=T.BG)
        actions.pack(fill="x")
        button(actions, "Apply this change", self._accept, primary=True).pack(
            side="right"
        )
        button(actions, "Cancel", self._reject).pack(side="right", padx=(0, 8))

        self.bind("<Escape>", lambda _e: self._reject())
        self.bind("<Return>", lambda _e: self._accept())
        self.protocol("WM_DELETE_WINDOW", self._reject)

        self._centre(parent)
        self.grab_set()          # modal: nothing else is clickable
        self.focus_set()

    def _row(self, parent, r, key, value):
        label(parent, key, font=T.SMALL, fg=T.MUTED).grid(
            row=r, column=0, sticky="w", pady=2
        )
        label(parent, value, font=T.BODY_B).grid(
            row=r, column=1, sticky="w", padx=(18, 0), pady=2
        )

    def _centre(self, parent):
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        x = parent.winfo_rootx() + (parent.winfo_width() - w) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - h) // 3
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")

    def _accept(self):
        self.approved = True
        self.destroy()

    def _reject(self):
        self.approved = False
        self.destroy()


class AtlasApp(tk.Tk):
    def __init__(self, viewmodel: ViewModel | None = None):
        super().__init__()
        T.pick_fonts(self)
        self.vm = viewmodel or ViewModel()

        self.title("Settings Companion")
        self.geometry("840x660")
        self.minsize(720, 560)
        self.configure(bg=T.BG)

        self._build_header()
        self._build_search()
        # The status bar must be packed BEFORE the expanding content area.
        # tkinter's packer allocates in order, so a widget with expand=True
        # packed first will take the remaining space and squeeze anything
        # packed after it to zero height.
        self._build_status()
        self.content = Scrollable(self)
        self.content.pack(fill="both", expand=True, padx=T.PAD + 8, pady=(4, 0))

        self.show_welcome()
        self.entry.focus_set()

    # ---- chrome ----------------------------------------------------
    def _build_header(self):
        head = tk.Frame(self, bg=T.BG)
        head.pack(fill="x", padx=T.PAD + 8, pady=(T.PAD, 6))

        left = tk.Frame(head, bg=T.BG)
        left.pack(side="left")
        label(left, "Settings Companion", font=T.TITLE).pack(anchor="w")
        label(left, "local  ·  offline  ·  everything reversible",
              font=T.SMALL, fg=T.MUTED).pack(anchor="w")

        right = tk.Frame(head, bg=T.BG)
        right.pack(side="right")
        self.undo_btn = button(right, "Undo last change", self.on_undo)
        self.undo_btn.pack(side="right")
        button(right, "History", self.show_history).pack(side="right", padx=6)
        button(right, "This computer", self.show_system_info).pack(side="right")

    def _build_search(self):
        bar = tk.Frame(self, bg=T.BG)
        bar.pack(fill="x", padx=T.PAD + 8, pady=(10, 6))

        label(bar, "What do you want to do?", font=T.SMALL, fg=T.MUTED).pack(
            anchor="w", pady=(0, 4)
        )
        row = tk.Frame(bar, bg=T.BG)
        row.pack(fill="x")

        self.entry = tk.Entry(
            row, font=T.INPUT, bg=T.BG, fg=T.TEXT, relief="solid", bd=1,
            insertbackground=T.TEXT, highlightthickness=1,
            highlightbackground=T.BORDER, highlightcolor=T.ACCENT,
        )
        self.entry.pack(side="left", fill="x", expand=True, ipady=6)
        self.entry.bind("<Return>", lambda _e: self.on_search())
        button(row, "Find", self.on_search, primary=True).pack(
            side="left", padx=(8, 0)
        )

    def _build_status(self):
        # With side="bottom" the first packed widget sits lowest, so the
        # status text goes down first and the rule lands above it.
        self.status = label(
            self, "Nothing has been changed on this computer.",
            font=T.SMALL, fg=T.MUTED,
        )
        self.status.pack(side="bottom", fill="x", padx=T.PAD + 8, pady=8)
        rule = divider(self)
        rule.pack(side="bottom", fill="x")
        # An empty frame would collapse to nothing; stop it shrinking.
        rule.pack_propagate(False)

    def _set_status(self, text, tone="muted"):
        colours = {"muted": T.MUTED, "good": T.SUCCESS, "bad": T.DANGER}
        self.status.configure(text=text, fg=colours.get(tone, T.MUTED))
        self.undo_btn.configure(
            state="normal" if self.vm.has_undo() else "disabled"
        )

    # ---- screens ---------------------------------------------------
    def show_welcome(self):
        self.content.clear()
        body = self.content.body

        label(body, "Ask in your own words", font=T.H2).pack(
            anchor="w", pady=(T.GAP, 2)
        )
        label(
            body,
            "It finds the setting, shows you exactly what it would run, "
            "and lets you undo it afterwards. Nothing changes until you say so.",
            fg=T.MUTED, wrap=680,
        ).pack(anchor="w", pady=(0, T.PAD))

        for text in SUGGESTIONS:
            row = card(body)
            row.pack(fill="x", pady=4)
            label(row.body, f"“{text}”", bg=T.SURFACE).pack(
                side="left"
            )
            button(row.body, "Try this",
                   lambda t=text: self._run_suggestion(t)).pack(side="right")

        self._set_status("Nothing has been changed on this computer.")

    def _run_suggestion(self, text):
        self.entry.delete(0, "end")
        self.entry.insert(0, text)
        self.on_search()

    def show_results(self, query: str, matches: list[Match]):
        self.content.clear()
        body = self.content.body

        if not matches:
            label(body, "Nothing matched that", font=T.H2).pack(
                anchor="w", pady=(T.GAP, 4)
            )
            label(
                body,
                f"Nothing matches “{query}” yet. This is early, and only "
                "knows a few settings so far.",
                fg=T.MUTED, wrap=680,
            ).pack(anchor="w")
            button(body, "See everything it can change",
                   self.show_all_tools).pack(anchor="w", pady=T.GAP)
            self._set_status("Nothing matched. Nothing was changed.")
            return

        label(body, f"For “{query}”", font=T.H2).pack(
            anchor="w", pady=(T.GAP, 2)
        )
        label(body, "Matched by keyword, not by AI. Pick the one you meant.",
              font=T.SMALL, fg=T.MUTED).pack(anchor="w", pady=(0, T.GAP))

        for m in matches:
            self._match_row(body, m)
        self._set_status(f"{len(matches)} match(es). Nothing changed yet.")

    def _match_row(self, parent, m: Match):
        row = card(parent)
        row.pack(fill="x", pady=4)
        left = tk.Frame(row.body, bg=T.SURFACE)
        left.pack(side="left", fill="x", expand=True)

        label(left, m.name, font=T.BODY_B, bg=T.SURFACE).pack(anchor="w")
        label(left, m.description, fg=T.MUTED, bg=T.SURFACE, wrap=520).pack(
            anchor="w"
        )
        badge = f"{m.badge}"
        if m.confidence:
            badge += f"   ·   {m.confidence}% match"
        label(left, badge, font=T.SMALL,
              fg=T.DANGER if m.is_mutating else T.SUCCESS, bg=T.SURFACE).pack(
            anchor="w", pady=(4, 0)
        )
        button(row.body, "Open", lambda n=m.name: self.open_tool(n)).pack(
            side="right"
        )

    def show_all_tools(self):
        self.show_results("everything", self.vm.all_tools())

    def open_tool(self, name: str):
        view = self.vm.open_tool(name)
        if not view.is_mutating:
            self._show_outcome(self.vm.run_read_only(name))
            return

        self.content.clear()
        body = self.content.body

        label(body, view.name, font=T.H2).pack(anchor="w", pady=(T.GAP, 2))
        label(body, view.description, fg=T.MUTED, wrap=680).pack(anchor="w")

        if view.error:
            panel = card(body)
            panel.pack(fill="x", pady=T.PAD)
            label(panel.body, "Could not read this setting",
                  font=T.BODY_B, fg=T.DANGER, bg=T.SURFACE).pack(anchor="w")
            label(panel.body, view.error, fg=T.MUTED, bg=T.SURFACE,
                  wrap=620).pack(anchor="w", pady=(4, 0))
            button(body, "Back", self.show_welcome).pack(anchor="w")
            self._set_status("Could not read that setting.", "bad")
            return

        panel = card(body)
        panel.pack(fill="x", pady=T.PAD)

        label(panel.body, "Right now", font=T.SMALL, fg=T.MUTED,
              bg=T.SURFACE).pack(anchor="w")
        label(panel.body, f"{view.current_value} {view.argument_name}",
              font=T.H2, bg=T.SURFACE).pack(anchor="w", pady=(0, T.GAP))

        label(panel.body, f"Change {view.argument_name} to",
              font=T.SMALL, fg=T.MUTED, bg=T.SURFACE).pack(anchor="w")

        entry_row = tk.Frame(panel.body, bg=T.SURFACE)
        entry_row.pack(fill="x", pady=(4, 6))
        self.value_entry = tk.Entry(
            entry_row, font=T.INPUT, width=20 if view.choices else 8, bg=T.BG, fg=T.TEXT,
            relief="solid", bd=1, highlightthickness=1,
            highlightbackground=T.BORDER, highlightcolor=T.ACCENT,
        )
        self.value_entry.insert(0, view.current_value)
        self.value_entry.pack(side="left", ipady=4)
        self.value_entry.bind(
            "<Return>", lambda _e, n=name: self.on_preview(n)
        )
        button(entry_row, "Review the change",
               lambda n=name: self.on_preview(n), primary=True).pack(
            side="left", padx=(8, 0)
        )

        if view.minimum is not None and view.maximum is not None:
            label(panel.body,
                  f"{view.argument_hint}  (between {view.minimum} and "
                  f"{view.maximum})",
                  font=T.SMALL, fg=T.MUTED, bg=T.SURFACE, wrap=560).pack(
                anchor="w"
            )
        elif view.choices:
            label(panel.body,
                  f"{view.argument_hint}  (one of: {', '.join(view.choices)})",
                  font=T.SMALL, fg=T.MUTED, bg=T.SURFACE, wrap=560).pack(
                anchor="w"
            )

        self.error_label = label(body, "", fg=T.DANGER, wrap=680)
        self.error_label.pack(anchor="w", pady=(0, 6))

        button(body, "Back", self.show_welcome).pack(anchor="w")
        self.value_entry.focus_set()
        self._set_status("Nothing has changed yet.")

    def show_history(self):
        self.content.clear()
        body = self.content.body
        rows = self.vm.history()

        label(body, "What has been changed", font=T.H2).pack(
            anchor="w", pady=(T.GAP, 2)
        )
        label(body,
              "Every change made to this computer, oldest at the "
              "bottom. This list is kept on your machine.",
              font=T.SMALL, fg=T.MUTED, wrap=680).pack(anchor="w", pady=(0, T.GAP))

        if not rows:
            label(body, "Nothing has been changed yet.",
                  fg=T.MUTED).pack(anchor="w")
            self._set_status("Nothing has been changed on this computer.")
            return

        for r in rows:
            item = card(body)
            item.pack(fill="x", pady=3)
            left = tk.Frame(item.body, bg=T.SURFACE)
            left.pack(side="left", fill="x", expand=True)

            if r.is_undo_record:
                label(left, "Reverted an earlier change", font=T.BODY_B,
                      fg=T.MUTED, bg=T.SURFACE).pack(anchor="w")
            else:
                headline = r.what + ("   (undone)" if r.undone else "")
                label(left, headline, font=T.BODY_B, bg=T.SURFACE).pack(
                    anchor="w"
                )
                label(left, r.detail, fg=T.MUTED, bg=T.SURFACE).pack(anchor="w")
            label(left, r.when, font=T.SMALL, fg=T.MUTED, bg=T.SURFACE).pack(
                anchor="w", pady=(2, 0)
            )

            if not r.is_undo_record and not r.undone:
                button(item.body, "Undo",
                       lambda i=r.id: self.on_undo_entry(i),
                       danger=True).pack(side="right")

    def show_system_info(self):
        self._show_outcome(self.vm.system_info())

    def _show_outcome(self, outcome: Outcome):
        self.content.clear()
        body = self.content.body

        label(body, outcome.title, font=T.H2,
              fg=T.TEXT if outcome.ok else T.DANGER).pack(
            anchor="w", pady=(T.GAP, 6)
        )

        if outcome.rows:
            panel = card(body)
            panel.pack(fill="x", pady=(0, T.GAP))
            grid = tk.Frame(panel.body, bg=T.SURFACE)
            grid.pack(fill="x")
            for i, (k, v) in enumerate(outcome.rows.items()):
                label(grid, str(k), font=T.SMALL, fg=T.MUTED,
                      bg=T.SURFACE).grid(row=i, column=0, sticky="w", pady=2)
                text = ", ".join(str(x) for x in v) if isinstance(v, (list, tuple)) else str(v)
                label(grid, text, bg=T.SURFACE, wrap=470).grid(
                    row=i, column=1, sticky="w", padx=(18, 0), pady=2
                )

        if outcome.command:
            label(body, "Command that ran", font=T.SMALL, fg=T.MUTED).pack(
                anchor="w", pady=(4, 4)
            )
            code_line(body, outcome.command).pack(fill="x", pady=(0, T.GAP))

        label(body, outcome.explanation, wrap=680).pack(anchor="w")

        actions = tk.Frame(body, bg=T.BG)
        actions.pack(anchor="w", pady=T.PAD)
        button(actions, "Back", self.show_welcome).pack(side="left")
        if outcome.undo_available:
            button(actions, "Undo this", self.on_undo, danger=True).pack(
                side="left", padx=8
            )

        if outcome.ok and outcome.command:
            self._set_status("Change applied. You can undo it.", "good")
        elif outcome.ok:
            self._set_status("Nothing was changed — this only read information.")
        else:
            self._set_status("Nothing was changed.", "bad")

    # ---- actions ---------------------------------------------------
    def on_search(self):
        query = self.entry.get().strip()
        if not query:
            return
        self.show_results(query, self.vm.search(query))

    def on_preview(self, name: str):
        raw = self.value_entry.get()
        preview, error = self.vm.build_preview(name, raw)
        if error:
            self.error_label.configure(text=error)
            self._set_status("That value was not accepted. Nothing changed.", "bad")
            return
        self.error_label.configure(text="")

        dialog = ConfirmDialog(self, preview, name)
        self.wait_window(dialog)
        if not dialog.approved:
            self._set_status("Cancelled. Nothing was changed.")
            return
        self._show_outcome(self.vm.apply(name, raw, preview))

    def on_undo(self):
        self._show_outcome(self.vm.undo_last())

    def on_undo_entry(self, entry_id: str):
        self._show_outcome(self.vm.undo(entry_id))


def launch() -> int:
    AtlasApp().mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(launch())
