"""Command line.

A dispatcher and nothing more. All formatting lives in engine/renderer.py and
all safety logic in engine/executor.py, so this file stays readable.

    atlas info                              what this computer is
    atlas run network.status                run any read-only report
    atlas list [category]                   every setting it can change
    atlas find "my screen keeps going off"  which tool matches that
    atlas show power.monitor_timeout        what a tool does and takes
    atlas set power.monitor_timeout 30      change it (asks first)
    atlas undo                              put the last change back
    atlas history                           everything that has been changed
    atlas gui                               open the window instead
"""

from __future__ import annotations

import argparse
import sys

from engine import executor, renderer
from engine.journal import Journal
from engine.registry import build_default_registry
from engine.tool import Safety
from windows.powercfg import PowercfgError


def _parse_set_args(tool, raw: list[str]) -> dict:
    """Accept either 'minutes=30' or a bare '30' for single-argument tools."""
    args: dict = {}
    positional = [v for v in raw if "=" not in v]
    named = [v for v in raw if "=" in v]

    for item in named:
        key, _, value = item.partition("=")
        args[key.strip()] = value.strip()

    if positional:
        required = [p for p in tool.parameters if p.required]
        if len(positional) == 1 and len(required) == 1:
            args[required[0].name] = positional[0]
        else:
            raise SystemExit(
                f"Could not tell what {positional} means. Use name=value, "
                f"e.g. {required[0].name}=30" if required else
                f"{tool.name} takes no arguments."
            )

    # coerce strings to the declared types; validate() does the real checking
    typed: dict = {}
    for p in tool.parameters:
        if p.name not in args:
            continue
        raw_value = args[p.name]
        if p.type is int:
            try:
                typed[p.name] = int(raw_value)
            except (TypeError, ValueError):
                raise SystemExit(
                    f"'{p.name}' needs to be a whole number, got '{raw_value}'."
                )
        elif p.type is bool:
            typed[p.name] = str(raw_value).lower() in {"1", "true", "yes", "on"}
        else:
            typed[p.name] = raw_value
    for key in args:
        if key not in typed:
            typed[key] = args[key]     # let validate() reject unknown names
    return typed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="atlas",
        description="A local-first companion for understanding and changing "
                    "your own computer.",
    )
    parser.add_argument(
        "--yes", "-y", action="store_true",
        help="skip the confirmation prompt (you still see the command)",
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("info", help="what this computer is")
    p_run = sub.add_parser("run", help="run a read-only report, e.g. network.status")
    p_run.add_argument("tool")
    sub.add_parser("gui", help="open the window")

    p_list = sub.add_parser("list", help="every setting it can change")
    p_list.add_argument("category", nargs="?")

    p_find = sub.add_parser("find", help="find the tool for a plain-English need")
    p_find.add_argument("query", nargs="+")

    p_show = sub.add_parser("show", help="what a tool does and what it takes")
    p_show.add_argument("tool")

    p_set = sub.add_parser("set", help="change a setting")
    p_set.add_argument("tool")
    p_set.add_argument("args", nargs="*")

    p_undo = sub.add_parser("undo", help="put the last change back")
    p_undo.add_argument("id", nargs="?", help="a specific change id")

    p_hist = sub.add_parser("history", help="everything that has been changed")
    p_hist.add_argument("--limit", type=int, default=20)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    opts = parser.parse_args(argv)
    registry = build_default_registry()
    journal = Journal()

    if opts.command is None:
        parser.print_help()
        print()
        print(f"{len(registry)} tools available. Try 'atlas info' to start.")
        return 0

    try:
        if opts.command == "gui":
            try:
                import tkinter                            # noqa: F401
            except ImportError:
                print("This needs tkinter, which normally ships with Python.\n"
                      "On Windows: re-run the Python installer and tick "
                      "'tcl/tk and IDLE'.\nOn Linux: sudo apt install python3-tk")
                return 1
            from ui.app import launch
            return launch()

        if opts.command == "info":
            result = executor.run(registry.get("system.info"), journal=journal)
            print(renderer.render(result))
            return 0

        if opts.command == "run":
            tool = registry.get(opts.tool)
            if tool.is_mutating:
                print(f"{tool.name} changes a setting. Use "
                      f"'atlas set {tool.name} ...' so you can see and approve "
                      f"the change first.")
                return 1
            print(renderer.render(executor.run(tool, journal=journal)))
            return 0

        if opts.command == "list":
            tools = (registry.by_category(opts.category)
                     if opts.category else registry.all())
            if not tools:
                print(f"No tools in category '{opts.category}'. "
                      f"Categories: {', '.join(registry.categories())}")
                return 1
            print(renderer.render_tool_list(tools))
            return 0

        if opts.command == "find":
            query = " ".join(opts.query)
            matches = registry.shortlist(query)
            if not matches:
                print(f"Nothing matched \"{query}\". "
                      f"Try 'atlas list' to see everything.")
                return 1
            print(f"For \"{query}\", the closest matches are:\n")
            for tool, score in matches:
                bar = "#" * max(1, round(score * 10))
                print(f"  {bar:<10} {tool.name:<28} {tool.description}")
            print("\nNo AI was used to pick these — it is keyword matching. "
                  "A local model will choose from this shortlist later.")
            return 0

        if opts.command == "show":
            print(renderer.render_tool_detail(registry.get(opts.tool)))
            return 0

        if opts.command == "set":
            tool = registry.get(opts.tool)
            if tool.safety is not Safety.MUTATING:
                print(f"{tool.name} does not change anything. "
                      f"Run it with 'atlas run {tool.name}'.")
                return 1
            args = _parse_set_args(tool, opts.args)
            result = executor.run(
                tool, args, journal=journal, assume_yes=opts.yes
            )
            print()
            print(renderer.render(result))
            return 0

        if opts.command == "undo":
            result = (executor.undo_entry(registry, opts.id, journal)
                      if opts.id else executor.undo_last(registry, journal))
            print(renderer.render(result))
            return 0

        if opts.command == "history":
            print(renderer.render_history(journal.history(opts.limit)))
            return 0

    except executor.Cancelled as exc:
        print(exc)
        return 0
    except PowercfgError as exc:
        # Expected and explainable: wrong OS, missing admin rights, odd locale.
        print(f"{exc}")
        return 1
    except KeyError as exc:
        print(f"{exc}\nRun 'atlas list' to see what is available.")
        return 1
    except (LookupError, ValueError, NotImplementedError,
            executor.NeedsConfirmation) as exc:
        print(f"{exc}")
        return 1
    except Exception as exc:                     # noqa: BLE001
        print(f"Something went wrong and nothing was changed: {exc}")
        return 2

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
