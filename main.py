#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Frida-XTr v2.0 - Created By Anonre
Launcher supporting both the interactive Textual TUI and the classic ANSI CLI interface.
"""

import argparse
import os
import sys
from pathlib import Path

# Ensure root directory is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main():
    parser = argparse.ArgumentParser(
        description="Frida-XTr: Created By Anonre",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py         # Launch modern Textual TUI (auto-detect)
  python main.py --tui   # Force interactive Textual TUI dashboard
  python main.py --cli   # Force classic ANSI terminal menu
        """
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--tui", action="store_true", help="Launch interactive Textual TUI dashboard")
    group.add_argument("--cli", action="store_true", help="Launch classic ANSI terminal menu")
    parser.add_argument("-v", "--version", action="store_true", help="Show version and exit")

    args = parser.parse_args()

    if args.version:
        print("Frida-XTr v2.0 - Created By Anonre")
        print("Created by Anonre | Tuan Hades")
        sys.exit(0)

    # Force CLI mode
    if args.cli:
        from ui.console import run_cli
        run_cli()
        return

    # Force TUI mode
    if args.tui:
        try:
            from ui.tui import run_tui
            run_tui()
            return
        except ImportError as e:
            print(f"[!] Error: Textual is required for TUI mode. Run: pip install textual>=0.50.0")
            print(f"[!] Details: {e}")
            sys.exit(1)

    # Default auto-detect:
    # If stdout is a TTY and textual is available, launch TUI; otherwise fallback to classic CLI
    if sys.stdout.isatty():
        try:
            import textual
            from ui.tui import run_tui
            run_tui()
            return
        except ImportError:
            pass  # Fallback to CLI

    from ui.console import run_cli
    run_cli()


if __name__ == "__main__":
    main()
